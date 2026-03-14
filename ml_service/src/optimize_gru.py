import os
import sys
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import optuna
from optuna.trial import TrialState
from sklearn.preprocessing import StandardScaler

# Asegurar que se encuentren los módulos locales
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import BinanceDataLoader
from src.preprocessing import DataPreprocessor
from src.validation import PurgedKFold
from models.gru import CryptoGRU

# --- Configuración Base ---
SYMBOL = "BTCUSDT"
INTERVAL = "1h"
SAMPLES = 30000
N_SPLITS = 5
PURGE_PCT = 0.01
SEQ_LEN = 30
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def calculate_sharpe(y_true, y_pred, prices):
    """Calcula únicamente el Sharpe Ratio para la función objetivo"""
    prices_safe = np.where(prices[:-1] == 0, 1e-8, prices[:-1])
    hourly_returns = np.diff(prices) / prices_safe
    strat_returns = (y_pred[:-1] * 2 - 1) * hourly_returns 
    
    std_ret = np.std(strat_returns)
    avg_ret = np.mean(strat_returns)
    sharpe = (avg_ret / std_ret * np.sqrt(24 * 365)) if std_ret > 1e-6 else -2.0 # Penalización severa por falta de volatilidad
    return sharpe

def create_sequences_for_gru(X, y, seq_length):
    X_seq, y_seq = [], []
    for i in range(len(X) - seq_length + 1):
        X_seq.append(X[i : i + seq_length])
        y_seq.append(y[i + seq_length - 1])
    return np.array(X_seq), np.array(y_seq)

def objective(trial):
    """Función objetivo que Optuna intentará maximizar"""
    
    # 1. Definir el espacio de búsqueda de Hiperparámetros
    hidden_size = trial.suggest_categorical("hidden_size", [16, 32, 64, 128])
    num_layers = trial.suggest_int("num_layers", 1, 3)
    dropout = trial.suggest_float("dropout", 0.1, 0.5) if num_layers > 1 else 0.0
    lr = trial.suggest_float("lr", 1e-5, 1e-2, log=True)
    batch_size = trial.suggest_categorical("batch_size", [128, 256, 512, 1024])
    
    # Cargar y preparar datos (simplificado para el ejemplo, idealmente cargar una vez fuera)
    loader = BinanceDataLoader()
    df = loader.fetch_historical_data(symbol=SYMBOL, interval=INTERVAL, limit=SAMPLES)
    df['log_return'] = np.log(df['close'] / df['close'].shift(1))
    df = df.dropna()
    
    preprocessor = DataPreprocessor(sequence_length=SEQ_LEN)
    df_processed = preprocessor.add_indicators(df)
    
    leakage_cols = ["open", "high", "low", "close", "s_open", "s_high", "s_low", "s_close", "target_direction", "open_time", "close_time"]
    features = [col for col in df_processed.columns if col not in leakage_cols]
    
    X = df_processed[features].values
    y = df_processed["target_direction"].values
    prices = df_processed["close"].values
    
    pkf = PurgedKFold(n_splits=N_SPLITS, purge_pct=PURGE_PCT)
    fold_sharpes = []
    
    # 2. Bucle de Validación Cruzada
    for fold, (train_idx, test_idx) in enumerate(pkf.split(X)):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]
        test_prices = prices[test_idx]
        
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        X_train_seq, y_train_seq = create_sequences_for_gru(X_train_scaled, y_train, SEQ_LEN)
        X_test_seq, y_test_seq = create_sequences_for_gru(X_test_scaled, y_test, SEQ_LEN)
        test_prices_gru = test_prices[SEQ_LEN-1:]
        
        # 3. Inicializar Modelo con parámetros del Trial
        model = CryptoGRU(
            input_size=len(features), 
            hidden_size=hidden_size, 
            num_layers=num_layers,
            dropout=dropout # Asegúrate de que tu clase CryptoGRU acepte este parámetro
        ).to(DEVICE)
        
        criterion = nn.BCELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
        
        X_train_t = torch.tensor(X_train_seq, dtype=torch.float32).to(DEVICE)
        y_train_t = torch.tensor(y_train_seq, dtype=torch.float32).unsqueeze(1).to(DEVICE)
        X_test_t = torch.tensor(X_test_seq, dtype=torch.float32).to(DEVICE)
        
        # 4. Entrenamiento en Batches
        model.train()
        dataset_size = len(X_train_t)
        for epoch in range(15): # Épocas fijas para la búsqueda
            permutation = torch.randperm(dataset_size)
            for i in range(0, dataset_size, batch_size):
                indices = permutation[i:i+batch_size]
                batch_x, batch_y = X_train_t[indices], y_train_t[indices]
                
                optimizer.zero_grad()
                outputs = model(batch_x)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                
        # 5. Evaluación
        model.eval()
        with torch.no_grad():
            y_prob = model(X_test_t).cpu().numpy().flatten()
        y_pred = (y_prob > 0.5).astype(int)
        
        fold_sharpe = calculate_sharpe(y_test_seq, y_pred, test_prices_gru)
        fold_sharpes.append(fold_sharpe)
        
        # Pruning (Opcional): Si el primer fold es un desastre, abortar el trial
        if fold == 0 and fold_sharpe < -1.0:
            raise optuna.TrialPruned()

    # Retornar la media del Sharpe Ratio de todos los pliegues
    return np.mean(fold_sharpes)

if __name__ == "__main__":
    print("Iniciando Optimización Bayesiana para GRU...")
    # Crear un estudio buscando MAXIMIZAR el valor retornado
    study = optuna.create_study(direction="maximize", study_name="GRU_Sharpe_Opt")
    
    # Ejecutar 30 intentos (trials)
    study.optimize(objective, n_trials=30)
    
    print("\n" + "="*50)
    print("¡Optimización Completada!")
    print("="*50)
    print("Mejor Sharpe Ratio encontrado:", study.best_value)
    print("Mejores Hiperparámetros:")
    for key, value in study.best_params.items():
        print(f"  {key}: {value}")