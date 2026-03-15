import logging
import pandas as pd
import numpy as np
from binance.spot import Spot as Client # Usamos la librería oficial
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BinanceDataLoader:
    def __init__(self, data_dir=None):
        # Para la App, nos conectamos directamente a la API pública (sin keys necesarias para leer)
        self.client = Client()
        
        # Diccionario para convertir tus temporalidades a formato Binance
        self.intervals = {
            "1h": "1h",
            "4h": "4h",
            "15m": "15m",
            "1d": "1d"
        }

    def fetch_multi_timeframe(self, symbol="BTCUSDT", limit=100) -> pd.DataFrame:
        """Descarga datos en vivo de Binance para los 4 timeframes"""
        logger.info(f"Descargando datos en vivo de Binance para {symbol}...")
        
        try:
            dfs = {}
            for tf_name, tf_binance in self.intervals.items():
                # Descargar velas (klines)
                # limit + 50 para tener margen para los indicadores técnicos
                klines = self.client.klines(symbol, tf_binance, limit=limit + 50)
                
                df = pd.DataFrame(klines, columns=[
                    "open_time", "open", "high", "low", "close", "volume",
                    "close_time", "quote_vol", "num_trades",
                    "taker_buy_vol", "taker_buy_quote_vol", "ignore"
                ])
                
                # Limpieza y conversión
                df["open_time"] = pd.to_datetime(df["open_time"], unit='ms')
                numeric_cols = ["open", "high", "low", "close", "volume", "quote_vol", "num_trades", "taker_buy_vol", "taker_buy_quote_vol"]
                df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)
                
                # Añadir prefijos según tu pipeline (s_, m_, d_)
                prefix = ""
                if tf_name == "4h": prefix = "s_"
                elif tf_name == "15m": prefix = "m_"
                elif tf_name == "1d": prefix = "d_"
                
                if prefix:
                    df = df.rename(columns={c: f"{prefix}{c}" for c in numeric_cols})
                
                dfs[tf_name] = df
                
            # Unir todos los timeframes (Merge) usando el 1h como base
            df_final = dfs["1h"].copy()
            
            for tf in ["4h", "15m", "1d"]:
                # Alineamos cronológicamente
                df_final = pd.merge_asof(
                    df_final.sort_values("open_time"),
                    dfs[tf].sort_values("open_time"),
                    on="open_time",
                    direction="backward",
                    suffixes=("", f"_{tf}")
                )
            
            logger.info("✅ Datos descargados y alineados correctamente.")
            return df_final

        except Exception as e:
            logger.error(f"❌ Error descargando de Binance: {e}")
            return None