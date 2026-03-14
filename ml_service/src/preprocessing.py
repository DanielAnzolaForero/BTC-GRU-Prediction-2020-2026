import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import pandas_ta as ta

class DataPreprocessor:
    def __init__(self, sequence_length=60):
        self.sequence_length = sequence_length
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.features = []

    def add_indicators(self, df):
        """
        Add professional technical indicators and advanced labeling.
        """
        df = df.copy()
        
        # 1. Primary Indicators (1h)
        df.ta.ema(length=20, append=True)
        df.ta.ema(length=50, append=True)
        df.ta.rsi(length=14, append=True)
        df.ta.macd(append=True)
        df.ta.bbands(length=20, std=2, append=True)
        df.ta.atr(length=14, append=True)
        
        # 2. Secondary Indicators (4h context - columns start with s_)
        if "s_close" in df.columns:
            df["s_ema20"] = df["s_close"].ewm(span=20).mean()
            df["s_trend"] = (df["s_close"] > df["s_ema20"]).astype(int)
        
        # 3. Relative Volume
        df["vol_sma"] = df["volume"].rolling(window=20).mean()
        df["rel_vol"] = df["volume"] / df["vol_sma"]
        
        # 4. Triple Barrier Method (Original 71% Logic)
        # 1 if price hits +1.5% TP before -1% SL in 12h, else 0
        tp_threshold = 0.015
        sl_threshold = 0.010
        look_ahead = 12
        
        def label_triple_barrier(current_idx):
            if current_idx >= len(df) - look_ahead:
                return 0
            current_price = df.iloc[current_idx]["close"]
            future_prices = df.iloc[current_idx+1 : current_idx+look_ahead+1]["close"]
            
            for price in future_prices:
                pct_change = (price - current_price) / current_price
                if pct_change >= tp_threshold: return 1 # Take Profit
                if pct_change <= -sl_threshold: return 0 # Stop Loss
            return 0 # Time limit hit

        df["target_direction"] = [label_triple_barrier(i) for i in range(len(df))]
        
        df.dropna(inplace=True)
        return df

    def prepare_sequences(self, df):
        """
        Prepare sequences for LSTM/GRU and a flat version for XGBoost.
        """
        # Select features (excluding target columns)
        self.features = [col for col in df.columns if col not in ["target", "target_direction", "open_time"]]
        
        scaled_data = self.scaler.fit_transform(df[self.features])
        
        X, y = [], []
        for i in range(self.sequence_length, len(scaled_data)):
            X.append(scaled_data[i-self.sequence_length:i])
            y.append(df["target_direction"].iloc[i])
            
        return np.array(X), np.array(y)

if __name__ == "__main__":
    # Test preprocessing
    try:
        df = pd.read_csv("ml_service/data/btc_historical.csv")
        preprocessor = DataPreprocessor()
        df_with_indicators = preprocessor.add_indicators(df)
        X, y = preprocessor.prepare_sequences(df_with_indicators)
        print(f"X shape: {X.shape}, y shape: {y.shape}")
    except FileNotFoundError:
        print("CSV not found. Run data_loader.py first.")
