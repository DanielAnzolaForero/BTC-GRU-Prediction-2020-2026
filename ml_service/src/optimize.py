import optuna
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
import os
import sys
import joblib

# Add the ml_service directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.gru import CryptoGRU
from src.preprocessing import DataPreprocessor
from src.data_loader import BinanceDataLoader

# Configuration
SYMBOL = "BTCUSDT"
INTERVAL = "1h"
LIMIT = 5000
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Fetch data ONCE
loader = BinanceDataLoader()
df_raw = loader.fetch_historical_data(symbol=SYMBOL, interval=INTERVAL, limit=LIMIT)

def objective(trial):
    # Hyperparameters to tune
    n_layers = trial.suggest_int("n_layers", 1, 2) # Reduced for speed
    hidden_size = trial.suggest_int("hidden_size", 32, 128)
    dropout = trial.suggest_float("dropout", 0.1, 0.4)
    lr = trial.suggest_float("lr", 1e-4, 5e-3, log=True)
    batch_size = trial.suggest_categorical("batch_size", [64, 128])
    seq_length = trial.suggest_int("seq_length", 30, 90, step=30)

    # 1. Prepare Data
    preprocessor = DataPreprocessor(sequence_length=seq_length)
    df_processed = preprocessor.add_indicators(df_raw)
    X, y = preprocessor.prepare_sequences(df_processed)
    
    train_size = int(len(X) * 0.8)
    X_train, X_test = X[:train_size], X[train_size:]
    y_train, y_test = y[:train_size], y[train_size:]
    
    X_train_t = torch.tensor(X_train, dtype=torch.float32).to(DEVICE)
    y_train_t = torch.tensor(y_train, dtype=torch.float32).unsqueeze(1).to(DEVICE)
    X_test_t = torch.tensor(X_test, dtype=torch.float32).to(DEVICE)
    y_test_t = torch.tensor(y_test, dtype=torch.float32).unsqueeze(1).to(DEVICE)
    
    train_loader = DataLoader(TensorDataset(X_train_t, y_train_t), batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(TensorDataset(X_test_t, y_test_t), batch_size=batch_size)
    
    # 2. Setup Model
    input_size = X.shape[2]
    model = CryptoGRU(input_size, hidden_size, n_layers, dropout=dropout).to(DEVICE)
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    
    # 3. Fast Training (5 epochs for optimization)
    best_acc = 0
    for epoch in range(5): 
        model.train()
        for batch_X, batch_y in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for batch_X, batch_y in test_loader:
                outputs = model(batch_X)
                predicted = (outputs > 0.5).float()
                total += batch_y.size(0)
                correct += (predicted == batch_y).sum().item()
        
        accuracy = correct / total
        best_acc = max(best_acc, accuracy)
        trial.report(accuracy, epoch)
        
        if trial.should_prune():
            raise optuna.exceptions.TrialPruned()

    return best_acc

if __name__ == "__main__":
    print(f"Starting optimized optimization on {DEVICE}...")
    study = optuna.create_study(direction="maximize", pruner=optuna.pruners.MedianPruner())
    study.optimize(objective, n_trials=30) 
    
    print("\nBest trial:")
    trial = study.best_trial
    print(f"  Value: {trial.value:.4f}")
    print("  Params: ")
    for key, value in trial.params.items():
        print(f"    {key}: {value}")
        
    # Save best params
    os.makedirs("ml_service/models", exist_ok=True)
    joblib.dump(trial.params, f"ml_service/models/{SYMBOL}_best_params.gz")
    print("\nBest parameters saved.")
