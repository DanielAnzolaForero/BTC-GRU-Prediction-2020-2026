import os
import sys
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
import joblib
import pandas as pd
from sklearn.metrics import roc_auc_score, f1_score

# Add the ml_service directory to the path FIRST
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.gru import CryptoGRU
from src.preprocessing import DataPreprocessor
from src.data_loader import BinanceDataLoader

# --- Professional Configuration ---
SYMBOL = "BTCUSDT"
INTERVAL = "1h"
LIMIT = 50000 
SEQUENCE_LENGTH = 30
HIDDEN_SIZE = 64      # Reduced from 117 to prevent overfitting
NUM_LAYERS = 2
DROPOUT = 0.35        # Increased from 0.17 for better generalization
BATCH_SIZE = 128
EPOCHS = 100          # Higher max epochs because we have Early Stopping
LEARNING_RATE = 0.001 # Reduced for stability
PATIENCE = 10         # Early Stopping patience

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def calculate_financial_metrics(y_true, y_pred, prices):
    """
    Calculates Sharpe, Sortino and Max Drawdown based on model predictions.
    Assumes taking a long position when y_pred == 1.
    """
    # Calculate hourly returns
    hourly_returns = np.diff(prices) / prices[:-1]
    # Align returns with predictions (returns[i] is return from price[i] to price[i+1])
    # Predictions y_pred[i] are for the window ending at price[i]
    strat_returns = y_pred[:-1] * hourly_returns
    
    # Sharpe Ratio (Annualized)
    avg_ret = np.mean(strat_returns)
    std_ret = np.std(strat_returns)
    sharpe = (avg_ret / std_ret * np.sqrt(24 * 365)) if std_ret > 0 else 0
    
    # Sortino Ratio
    downside_rets = strat_returns[strat_returns < 0]
    downside_std = np.std(downside_rets) if len(downside_rets) > 0 else 0
    sortino = (avg_ret / downside_std * np.sqrt(24 * 365)) if downside_std > 0 else 0
    
    # Max Drawdown
    cum_rets = np.cumsum(strat_returns)
    peak = np.maximum.accumulate(cum_rets)
    drawdown = peak - cum_rets
    max_dd = np.max(drawdown) if len(drawdown) > 0 else 0
    
    return sharpe, sortino, max_dd

def evaluate_professional(model, loader, prices):
    model.eval()
    all_outputs = []
    all_targets = []
    
    with torch.no_grad():
        for batch_X, batch_y in loader:
            outputs = model(batch_X)
            all_outputs.extend(outputs.cpu().numpy())
            all_targets.extend(batch_y.cpu().numpy())
    
    all_outputs = np.array(all_outputs).flatten()
    all_targets = np.array(all_targets).flatten()
    preds_binary = (all_outputs > 0.5).astype(int)
    
    # ML Metrics
    acc = 100 * (preds_binary == all_targets).mean()
    auc = roc_auc_score(all_targets, all_outputs)
    f1 = f1_score(all_targets, preds_binary)
    
    # Financial Metrics
    sharpe, sortino, max_dd = calculate_financial_metrics(all_targets, preds_binary, prices)
    
    return {
        "acc": acc, "auc": auc, "f1": f1,
        "sharpe": sharpe, "sortino": sortino, "max_dd": max_dd
    }

def train_final_model():
    print(f"Starting PROFESSIONAL training session on {DEVICE}")
    print(f"Protection: Early Stopping (Patience {PATIENCE}), Dropout {DROPOUT}, Neurons {HIDDEN_SIZE}")
    
    # 1. Fetch and Preprocess
    loader = BinanceDataLoader()
    df = loader.fetch_multi_timeframe(symbol=SYMBOL, primary_interval=INTERVAL, limit=LIMIT)
    if df is None: return
        
    preprocessor = DataPreprocessor(sequence_length=SEQUENCE_LENGTH)
    df_processed = preprocessor.add_indicators(df)
    X, y = preprocessor.prepare_sequences(df_processed)
    
    # Close prices for financial metrics (test set)
    close_prices = df_processed['close'].values[SEQUENCE_LENGTH:]
    
    # 2. Split
    train_size = int(len(X) * 0.8)
    X_train, X_test = X[:train_size], X[train_size:]
    y_train, y_test = y[:train_size], y[train_size:]
    test_prices = close_prices[train_size:]
    
    # Tensors
    X_train_t = torch.tensor(X_train, dtype=torch.float32).to(DEVICE)
    y_train_t = torch.tensor(y_train, dtype=torch.float32).unsqueeze(1).to(DEVICE)
    X_test_t = torch.tensor(X_test, dtype=torch.float32).to(DEVICE)
    y_test_t = torch.tensor(y_test, dtype=torch.float32).unsqueeze(1).to(DEVICE)
    
    train_loader = DataLoader(TensorDataset(X_train_t, y_train_t), batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(TensorDataset(X_test_t, y_test_t), batch_size=BATCH_SIZE)
    
    # 3. Model & Optimizer
    input_size = X.shape[2]
    model = CryptoGRU(input_size, HIDDEN_SIZE, NUM_LAYERS, dropout=DROPOUT).to(DEVICE)
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-5)
    
    # 4. Training Loop with Early Stopping
    best_val_loss = float('inf')
    early_stop_count = 0
    best_results = None
    
    print("\nEpoch | Loss | Acc | AUC | F1 | Sharpe | MaxDD")
    print("-" * 65)
    
    for epoch in range(EPOCHS):
        model.train()
        epoch_loss = 0
        for batch_X, batch_y in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            
        # Evaluation
        metrics = evaluate_professional(model, test_loader, test_prices)
        val_loss = epoch_loss / len(train_loader)
        
        # Logging
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"{epoch+1:3d} | {val_loss:.3f} | {metrics['acc']:.1f}% | {metrics['auc']:.2f} | {metrics['f1']:.2f} | {metrics['sharpe']:.2f} | {metrics['max_dd']:.2f}")
            
        # Early Stopping Logic (Monitor Validation Loss)
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            early_stop_count = 0
            best_results = metrics
            torch.save(model.state_dict(), f"ml_service/models/{SYMBOL}_final_gru.pt")
        else:
            early_stop_count += 1
            
        if early_stop_count >= PATIENCE:
            print(f"\n[Early Stopping] Triggered at epoch {epoch+1}")
            break

    # 5. Final Report
    print("\n" + "="*40)
    print("FINAL PROFESSIONAL REPORT")
    print("="*40)
    if best_results:
        for k, v in best_results.items():
            print(f"{k.upper():10}: {v:.4f}")
    
    joblib.dump(preprocessor.scaler, f"ml_service/models/{SYMBOL}_scaler.gz")
    joblib.dump(preprocessor.features, f"ml_service/models/{SYMBOL}_features.gz")
    print("\nModel and professional metadata saved.")

if __name__ == "__main__":
    train_final_model()
