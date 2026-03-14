import pandas as pd
import numpy as np
from binance.spot import Spot as Client
import logging
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BinanceDataLoader:
    def __init__(self, api_key=None, api_secret=None):
        self.client = Client(api_key, api_secret)

    def fetch_historical_data(self, symbol="BTCUSDT", interval="1h", limit=5000):
        """
        Fetch historical Klines from Binance using pagination going BACKWARDS in time.
        """
        logger.info(f"Fetching {limit} candles for {symbol} with interval {interval}...")
        all_klines = []
        end_time = None
        
        chunk_size = 1000
        rounds = (limit // chunk_size) + (1 if limit % chunk_size > 0 else 0)
        
        try:
            for _ in range(rounds):
                current_limit = min(chunk_size, limit - len(all_klines))
                if current_limit <= 0: break
                
                params = {"symbol": symbol, "interval": interval, "limit": current_limit}
                if end_time:
                    # Fetching 1000 candles BEFORE end_time
                    params["endTime"] = end_time - 1
                
                klines = self.client.klines(**params)
                if not klines: break
                
                # Prepend new klines because we are fetching backwards
                all_klines = klines + all_klines
                
                # The next end time is the first kline's open time
                end_time = klines[0][0]
                
                if len(klines) < current_limit: break
            
            columns = [
                "open_time", "open", "high", "low", "close", "volume",
                "close_time", "quote_asset_volume", "number_of_trades",
                "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
            ]
            df = pd.DataFrame(all_klines, columns=columns)
            df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)
                
            return df[["open_time", "open", "high", "low", "close", "volume"]]
        except Exception as e:
            logger.error(f"Error fetching data from Binance: {e}")
            return None

    def fetch_multi_timeframe(self, symbol="BTCUSDT", primary_interval="1h", secondary_interval="4h", limit=5000):
        """
        Fetch and align data from two different timeframes.
        """
        logger.info(f"Fetching multi-timeframe data ({primary_interval} & {secondary_interval})...")
        
        df_primary = self.fetch_historical_data(symbol, primary_interval, limit)
        df_secondary = self.fetch_historical_data(symbol, secondary_interval, limit // 4 + 100)
        
        if df_primary is None or df_secondary is None:
            return None
            
        df_secondary = df_secondary.rename(columns={
            "open": "s_open", "high": "s_high", "low": "s_low", "close": "s_close", "volume": "s_volume"
        })
        
        df_primary = df_primary.sort_values("open_time")
        df_secondary = df_secondary.sort_values("open_time")
        
        merged_df = pd.merge_asof(
            df_primary, 
            df_secondary, 
            on="open_time", 
            direction="backward"
        )
        
        return merged_df

if __name__ == "__main__":
    loader = BinanceDataLoader()
    df = loader.fetch_multi_timeframe()
    if df is not None:
        print(f"Merged Data Shape: {df.shape}")
        print(df.tail())
