import torch
import numpy as np
import joblib
import os
from ml_service.models.lstm import CryptoLSTM
from ml_service.src.preprocessing import DataPreprocessor
from ml_service.src.data_loader import BinanceDataLoader

class PredictorService:
    def __init__(self, symbol="BTCUSDT"):
        self.symbol = symbol
        self.model_path = f"ml_service/models/{symbol}_lstm.pt"
        self.scaler_path = f"ml_service/models/{symbol}_scaler.gz"
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.model = None
        self.scaler = None
        self.preprocessor = DataPreprocessor()
        self.loader = BinanceDataLoader()

    def load_resources(self):
        if not os.path.exists(self.model_path) or not os.path.exists(self.scaler_path):
            raise FileNotFoundError(f"Model or Scaler not found for {self.symbol}. Please train the model first.")
        
        # Load scaler
        self.scaler = joblib.load(self.scaler_path)
        
        # Load model
        # Note: We need to know input_size, hidden_size, etc. In a real project, store these in a config file.
        input_size = 8 
        hidden_size = 64
        num_layers = 2
        
        self.model = CryptoLSTM(input_size, hidden_size, num_layers)
        self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
        self.model.to(self.device)
        self.model.eval()

    def predict_next(self):
        if self.model is None:
            self.load_resources()
            
        # 1. Fetch recent data
        df = self.loader.fetch_historical_data(symbol=self.symbol, limit=100)
        df_processed = self.preprocessor.add_indicators(df)
        
        # 2. Scale features
        features = ["open", "high", "low", "close", "volume", "ma_7", "ma_25", "rsi"]
        scaled_data = self.scaler.transform(df_processed[features])
        
        # 3. Prepare latest sequence
        seq_len = 60
        last_sequence = scaled_data[-seq_len:]
        input_tensor = torch.tensor(last_sequence, dtype=torch.float32).unsqueeze(0).to(self.device)
        
        # 4. Infer
        with torch.no_grad():
            prediction_prob = self.model(input_tensor).item()
            
        return {
            "symbol": self.symbol,
            "prediction": "UP" if prediction_prob > 0.5 else "DOWN",
            "probability": prediction_prob,
            "current_price": df["close"].iloc[-1]
        }
