import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import pandas as pd
import numpy as np
import os
import sys
import joblib

# Add the ml_service directory to the path so we can import from models and src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.lstm import CryptoLSTM
from models.gru import CryptoGRU
from models.ensemble import CryptoEnsemble
from src.preprocessing import DataPreprocessor
from src.data_loader import BinanceDataLoader

# Configuration
SYMBOL = "BTCUSDT"
INTERVAL = "1h"
LIMIT = 5000 # Increased limit for better training
SEQUENCE_LENGTH = 60
HIDDEN_SIZE = 64
NUM_LAYERS = 2
BATCH_SIZE = 64
EPOCHS = 30
LEARNING_RATE = 0.001

def evaluate_torch_model(model, loader, criterion):
    model.eval()
    total_loss = 0
    correct = 0
    total = 0
    with torch.no_grad():
        for batch_X, batch_y in loader:
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            total_loss += loss.item()
            predicted = (outputs > 0.5).float()
            total += batch_y.size(0)
            correct += (predicted == batch_y).sum().item()
    return total_loss / len(loader), 100 * correct / total

def train_model():
    # 1. Fetch and Preprocess Data
    loader = BinanceDataLoader()
    df = loader.fetch_historical_data(symbol=SYMBOL, interval=INTERVAL, limit=LIMIT)
    if df is None: return
    
    preprocessor = DataPreprocessor(sequence_length=SEQUENCE_LENGTH)
    df_processed = preprocessor.add_indicators(df)
    X, y = preprocessor.prepare_sequences(df_processed)
    
    # 2. Split Data
    train_size = int(len(X) * 0.8)
    X_train, X_test = X[:train_size], X[train_size:]
    y_train, y_test = y[:train_size], y[train_size:]
    
    # Convert to Tensors for Deep Learning
    X_train_t = torch.tensor(X_train, dtype=torch.float32)
    y_train_t = torch.tensor(y_train, dtype=torch.float32).unsqueeze(1)
    X_test_t = torch.tensor(X_test, dtype=torch.float32)
    y_test_t = torch.tensor(y_test, dtype=torch.float32).unsqueeze(1)
    
    train_loader = DataLoader(TensorDataset(X_train_t, y_train_t), batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(TensorDataset(X_test_t, y_test_t), batch_size=BATCH_SIZE)
    
    input_size = X.shape[2]
    models_to_train = {
        "LSTM": CryptoLSTM(input_size, HIDDEN_SIZE, NUM_LAYERS),
        "GRU": CryptoGRU(input_size, HIDDEN_SIZE, NUM_LAYERS)
    }
    
    criterion = nn.BCELoss()
    results = {}

    # 3. Train LSTM & GRU
    for name, model in models_to_train.items():
        print(f"\n--- Training {name} ---")
        optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
        best_acc = 0
        
        for epoch in range(EPOCHS):
            model.train()
            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
            
            _, accuracy = evaluate_torch_model(model, test_loader, criterion)
            if accuracy > best_acc:
                best_acc = accuracy
                torch.save(model.state_dict(), f"ml_service/models/{SYMBOL}_{name.lower()}.pt")
            
            if (epoch + 1) % 5 == 0:
                print(f"Epoch [{epoch+1}/{EPOCHS}], Test Accuracy: {accuracy:.2f}%")
        
        results[name] = best_acc

    # 4. Train XGBoost
    print(f"\n--- Training XGBoost ---")
    xgb_model = CryptoEnsemble()
    xgb_model.train(X_train, y_train)
    
    # Evaluate XGBoost
    y_pred_xgb = xgb_model.predict(X_test)
    y_pred_xgb_binary = (y_pred_xgb > 0.5).astype(int)
    xgb_acc = 100 * (y_pred_xgb_binary == y_test).mean()
    xgb_model.save(f"ml_service/models/{SYMBOL}_xgb.gz")
    results["XGBoost"] = xgb_acc
    print(f"XGBoost Test Accuracy: {xgb_acc:.2f}%")

    # 5. Summary
    print("\n" + "="*30)
    print("FINAL RESULTS (BEST ACCURACY)")
    print("="*30)
    for name, acc in results.items():
        print(f"{name}: {acc:.2f}%")
    
    joblib.dump(preprocessor.scaler, f"ml_service/models/{SYMBOL}_scaler.gz")
    joblib.dump(preprocessor.features, f"ml_service/models/{SYMBOL}_features.gz")
    print("\nAll models and metadata saved successfully.")

if __name__ == "__main__":
    train_model()
