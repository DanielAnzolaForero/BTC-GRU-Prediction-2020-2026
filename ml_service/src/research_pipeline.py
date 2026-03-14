import os
import sys
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import log_loss, precision_recall_curve, auc, brier_score_loss
import xgboost as xgb
from tabulate import tabulate

try:
    import lightgbm as lgb
    import shap
except ImportError:
    print("Warning: LightGBM or SHAP not found.")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import BinanceDataLoader
from src.preprocessing import DataPreprocessor
from src.validation import PurgedKFold
from models.gru import CryptoGRU
from models.tab_transformer import TabTransformer

# --- Configuration ---
SYMBOL = "BTCUSDT"
INTERVAL = "1h"
SAMPLES = 30000
N_SPLITS = 5
PURGE_PCT = 0.01
SEQ_LEN = 30 # Debe coincidir con tu DataPreprocessor
BATCH_SIZE = 256 # Añadido para estabilizar PyTorch
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def calculate_financial_metrics(y_true, y_pred, prices):
    """
    Calcula Sharpe y Max Drawdown corregido.
    """
    # Evitar división por cero
    prices_safe = np.where(prices[:-1] == 0, 1e-8, prices[:-1])
    hourly_returns = np.diff(prices) / prices_safe
    
    # Alinear predicciones con los retornos (el trade de hoy se evalúa mañana)
    strat_returns = (y_pred[:-1] * 2 - 1) * hourly_returns 
    
    avg_ret = np.mean(strat_returns)
    std_ret = np.std(strat_returns)
    sharpe = (avg_ret / std_ret * np.sqrt(24 * 365)) if std_ret > 1e-6 else 0
    
    cum_rets = np.cumsum(strat_returns)
    peak = np.maximum.accumulate(cum_rets)
    drawdowns = (peak - cum_rets) # Drawdown en porcentaje acumulado
    max_dd = np.max(drawdowns) if len(drawdowns) > 0 else 0
    
    return sharpe, max_dd

def create_sequences_for_gru(X, y, seq_length):
    """Reconstruye datos 2D a 3D (Muestras, Secuencia, Features) para la GRU"""
    X_seq, y_seq = [], []
    
    # SOLUCIÓN: Añadimos + 1 al rango para no perder la última secuencia
    for i in range(len(X) - seq_length + 1):
        X_seq.append(X[i : i + seq_length])
        y_seq.append(y[i + seq_length - 1]) # El target al final de la secuencia
        
    return np.array(X_seq), np.array(y_seq)

def train_torch_model(model, X_train, y_train, criterion, optimizer, epochs=20):
    """Función auxiliar para entrenar en batches y evitar colapso de gradiente"""
    model.train()
    dataset_size = len(X_train)
    for epoch in range(epochs):
        permutation = torch.randperm(dataset_size)
        for i in range(0, dataset_size, BATCH_SIZE):
            indices = permutation[i:i+BATCH_SIZE]
            batch_x, batch_y = X_train[indices], y_train[indices]
            
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()

def run_experiment():
    print(f"--- Professional Research Pipeline: {SYMBOL} ({SAMPLES} samples) ---")
    
    # 1. Load Data
    loader = BinanceDataLoader()
    df = loader.fetch_historical_data(symbol=SYMBOL, interval=INTERVAL, limit=SAMPLES)
    
    # 2. ESTACIONARIEDAD (Forzado): Convertir cierres a Log Returns
    df['log_return'] = np.log(df['close'] / df['close'].shift(1))
    df = df.dropna()
    
    preprocessor = DataPreprocessor(sequence_length=SEQ_LEN)
    df_processed = preprocessor.add_indicators(df)
    
    # Filtrar columnas contaminantes (precios nominales)
    leakage_cols = ["open", "high", "low", "close", "s_open", "s_high", "s_low", "s_close", "target_direction", "open_time", "close_time"]
    features = [col for col in df_processed.columns if col not in leakage_cols]
    
    X = df_processed[features].values
    y = df_processed["target_direction"].values
    prices = df_processed["close"].values
    
    pkf = PurgedKFold(n_splits=N_SPLITS, purge_pct=PURGE_PCT)
    all_metrics = {"XGBoost": [], "LightGBM": [], "Transformer": [], "GRU": []}

    print(f"Starting Purged Cross-Validation ({N_SPLITS} folds)...")

    for fold, (train_idx, test_idx) in enumerate(pkf.split(X)):
        print(f"Fold {fold+1}/{N_SPLITS}...")
        
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]
        test_prices = prices[test_idx]
        
        # Scaling
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # --- 1. XGBoost ---
        xgb_model = xgb.XGBClassifier(n_estimators=100, learning_rate=0.05, max_depth=5, early_stopping_rounds=10)
        xgb_model.fit(X_train_scaled, y_train, eval_set=[(X_test_scaled, y_test)], verbose=False)
        y_prob_xgb = xgb_model.predict_proba(X_test_scaled)[:, 1]
        y_pred_xgb = (y_prob_xgb > 0.5).astype(int)
        
        loss_xgb = log_loss(y_test, y_prob_xgb)
        precision, recall, _ = precision_recall_curve(y_test, y_prob_xgb)
        sharpe_xgb, mdd_xgb = calculate_financial_metrics(y_test, y_pred_xgb, test_prices)
        all_metrics["XGBoost"].append([loss_xgb, auc(recall, precision), sharpe_xgb, mdd_xgb])

        # --- 2. LightGBM ---
        try:
            lgb_train = lgb.Dataset(X_train_scaled, y_train)
            lgb_test = lgb.Dataset(X_test_scaled, y_test, reference=lgb_train)
            params = {"objective": "binary", "metric": "binary_logloss", "verbosity": -1, "learning_rate": 0.05}
            lgb_model = lgb.train(params, lgb_train, num_boost_round=100, valid_sets=[lgb_test], callbacks=[lgb.early_stopping(stopping_rounds=10, verbose=False)])
            y_prob_lgbm = lgb_model.predict(X_test_scaled)
            y_pred_lgbm = (y_prob_lgbm > 0.5).astype(int)
            
            precision, recall, _ = precision_recall_curve(y_test, y_prob_lgbm)
            sharpe_lgbm, mdd_lgbm = calculate_financial_metrics(y_test, y_pred_lgbm, test_prices)
            all_metrics["LightGBM"].append([log_loss(y_test, y_prob_lgbm), auc(recall, precision), sharpe_lgbm, mdd_lgbm])
        except NameError: pass

        # --- 3. Transformer (Tabular) ---
        trans_model = TabTransformer(input_size=len(features)).to(DEVICE)
        criterion = nn.BCELoss()
        optimizer = torch.optim.Adam(trans_model.parameters(), lr=0.001, weight_decay=1e-5) # L2 Regularization
        
        X_train_t = torch.tensor(X_train_scaled, dtype=torch.float32).to(DEVICE)
        y_train_t = torch.tensor(y_train, dtype=torch.float32).unsqueeze(1).to(DEVICE)
        X_test_t = torch.tensor(X_test_scaled, dtype=torch.float32).to(DEVICE)
        
        train_torch_model(trans_model, X_train_t, y_train_t, criterion, optimizer, epochs=15)
        
        trans_model.eval()
        with torch.no_grad():
            y_prob_trans = trans_model(X_test_t).cpu().numpy().flatten()
        y_pred_trans = (y_prob_trans > 0.5).astype(int)
        
        sharpe_trans, mdd_trans = calculate_financial_metrics(y_test, y_pred_trans, test_prices)
        all_metrics["Transformer"].append([log_loss(y_test, y_prob_trans), brier_score_loss(y_test, y_prob_trans), sharpe_trans, mdd_trans])

        # --- 4. GRU (Corregido con ventanas 3D) ---
        X_train_gru_seq, y_train_gru_seq = create_sequences_for_gru(X_train_scaled, y_train, seq_length=SEQ_LEN)
        X_test_gru_seq, y_test_gru_seq = create_sequences_for_gru(X_test_scaled, y_test, seq_length=SEQ_LEN)
        test_prices_gru = test_prices[SEQ_LEN-1:] # Alinear precios por la pérdida de secuencia
        
        gru_model = CryptoGRU(input_size=len(features), hidden_size=32, num_layers=1).to(DEVICE)
        X_train_gru_t = torch.tensor(X_train_gru_seq, dtype=torch.float32).to(DEVICE)
        y_train_gru_t = torch.tensor(y_train_gru_seq, dtype=torch.float32).unsqueeze(1).to(DEVICE)
        X_test_gru_t = torch.tensor(X_test_gru_seq, dtype=torch.float32).to(DEVICE)
        
        optimizer_gru = torch.optim.Adam(gru_model.parameters(), lr=0.001)
        train_torch_model(gru_model, X_train_gru_t, y_train_gru_t, criterion, optimizer_gru, epochs=15)
        
        gru_model.eval()
        with torch.no_grad():
            y_prob_gru = gru_model(X_test_gru_t).cpu().numpy().flatten()
        y_pred_gru = (y_prob_gru > 0.5).astype(int)
        
        precision, recall, _ = precision_recall_curve(y_test_gru_seq, y_prob_gru)
        sharpe_gru, mdd_gru = calculate_financial_metrics(y_test_gru_seq, y_pred_gru, test_prices_gru)
        all_metrics["GRU"].append([log_loss(y_test_gru_seq, y_prob_gru), auc(recall, precision), sharpe_gru, mdd_gru])

    # 5. Final Report
    summary_data = []
    for model_name, folds in all_metrics.items():
        if not folds: continue
        avg = np.mean(folds, axis=0)
        summary_data.append([model_name, f"{avg[0]:.4f}", f"{avg[1]:.4f}", f"{avg[2]:.4f}", f"{avg[3]:.4f}"])
        
    headers = ["Model", "Loss (Log/CE)", "Metric 2 (PR-AUC/Brier)", "Sharpe Ratio", "Max Drawdown"]
    print("\n" + "="*70)
    print("FINAL COMPARATIVE EVALUATION (Purged Cross-Validation)")
    print("="*70)
    print(tabulate(summary_data, headers=headers))

if __name__ == "__main__":
    run_experiment()