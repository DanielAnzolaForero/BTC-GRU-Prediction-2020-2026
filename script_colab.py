# SCRIPT MAESTRO PARA GOOGLE COLAB v2.0
# Copia todo este código en una celda de Colab y presiona Play

# 1. Instalar solo lo esencial
print("📦 Instalando librerías especializadas...")
!pip install binance-connector pandas-ta --no-cache-dir

import os
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
try:
    import pandas_ta as ta
except ImportError:
    print("❌ Error: No se encontró pandas_ta. REINICIA LA SESIÓN en Colab.")
from binance.spot import Spot as Client
import logging
import joblib
import shutil
from sklearn.preprocessing import MinMaxScaler
from google.colab import files

# Configuración de Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ColabV2")

# --- MODELO GRU POTENCIADO ---
class CryptoGRU(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, output_size=1, dropout=0.3):
        super(CryptoGRU, self).__init__()
        self.gru = nn.GRU(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)
        self.fc = nn.Linear(hidden_size, output_size)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        out, _ = self.gru(x)
        out = self.fc(out[:, -1, :])
        return self.sigmoid(out)

# --- CARGADOR DE DATOS RESILIENTE ---
class BinanceDataLoader:
    def __init__(self):
        self.client = Client()

    def fetch_historical_data(self, symbol="BTCUSDT", interval="1h", limit=30000):
        all_klines = []
        end_time = None
        chunk_size = 1000
        rounds = (limit // chunk_size) + (1 if limit % chunk_size > 0 else 0)
        
        print(f"-> Descargando {limit} velas de {symbol} ({interval})...")
        try:
            for i in range(rounds):
                current_limit = min(chunk_size, limit - len(all_klines))
                if current_limit <= 0: break
                params = {"symbol": symbol, "interval": interval, "limit": current_limit}
                if end_time: params["endTime"] = end_time - 1
                
                # Fetch with error handling
                klines = self.client.klines(**params)
                if not klines: 
                    print("AVISO: No se recibieron más datos de Binance.")
                    break
                
                all_klines = klines + all_klines
                end_time = klines[0][0]
                if (i+1) % 5 == 0: print(f"   Progreso: {len(all_klines)}/{limit} velas...")
        except Exception as e:
            print(f"ERROR CRÍTICO EN DESCARGA: {e}")
            return None
        
        columns = ["open_time", "open", "high", "low", "close", "volume", "c1", "c2", "c3", "c4", "c5", "c6"]
        df = pd.DataFrame(all_klines, columns=columns)
        df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
        for col in ["open", "high", "low", "close", "volume"]: df[col] = df[col].astype(float)
        return df[["open_time", "open", "high", "low", "close", "volume"]]

    def fetch_multi_timeframe(self, symbol="BTCUSDT", primary="1h", secondary="4h", limit=30000):
        print("Iniciando carga de datos Multi-Timeframe...")
        df_p = self.fetch_historical_data(symbol, primary, limit)
        if df_p is None: return None
        
        df_s = self.fetch_historical_data(symbol, secondary, limit // 4 + 100)
        if df_s is None: return df_p # Fallback to single timeframe if 4h fails
        
        df_s = df_s.rename(columns={"open":"s_open", "high":"s_high", "low":"s_low", "close":"s_close", "volume":"s_volume"})
        df_p = df_p.sort_values("open_time")
        df_s = df_s.sort_values("open_time")
        return pd.merge_asof(df_p, df_s, on="open_time", direction="backward")

# --- PREPROCESAMIENTO PROFESIONAL ---
class DataPreprocessor:
    def __init__(self, sequence_length=30):
        self.sequence_length = sequence_length
        self.scaler = MinMaxScaler()

    def add_indicators(self, df):
        df = df.copy()
        print("Calculando indicadores técnicos (Triple Barrier + ATR)...")
        df.ta.ema(length=20, append=True)
        df.ta.ema(length=50, append=True)
        df.ta.rsi(length=14, append=True)
        df.ta.macd(append=True)
        df.ta.bbands(length=20, std=2, append=True)
        df.ta.atr(length=14, append=True)
        
        if "s_close" in df.columns:
            df["s_ema20"] = df["s_close"].ewm(span=20).mean()
            df["s_trend"] = (df["s_close"] > df["s_ema20"]).astype(int)
        
        df["vol_sma"] = df["volume"].rolling(window=20).mean()
        df["rel_vol"] = df["volume"] / df["vol_sma"]
        
        atr_col = [col for col in df.columns if col.startswith("ATR")][0]
        df["tp_price"] = df["close"] + (df[atr_col] * 2.5)
        df["sl_price"] = df["close"] - (df[atr_col] * 1.5)
        look_ahead = 24
        
        def label_triple_barrier(idx):
            if idx >= len(df) - look_ahead: return 0
            c_p, tp_p, sl_p = df.iloc[idx]["close"], df.iloc[idx]["tp_price"], df.iloc[idx]["sl_price"]
            future = df.iloc[idx+1 : idx+look_ahead+1]["close"]
            for p in future:
                if p >= tp_p: return 1
                if p <= sl_p: return 0
            return 1 if df.iloc[idx+look_ahead]["close"] > c_p else 0

        df["target"] = [label_triple_barrier(i) for i in range(len(df))]
        df.dropna(inplace=True)
        return df

    def prepare(self, df):
        feats = [c for c in df.columns if c not in ["target", "open_time", "tp_price", "sl_price"]]
        scaled = self.scaler.fit_transform(df[feats])
        X, y = [], []
        for i in range(self.sequence_length, len(scaled)):
            X.append(scaled[i-self.sequence_length:i]); y.append(df["target"].iloc[i])
        return np.array(X), np.array(y), feats

# --- FLUJO DE ENTRENAMIENTO v4.0 (Optimizado para Memoria) ---
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"\n--- INICIANDO SISTEMA EN {DEVICE} ---")

CSV_FILE = "datos_crypto_colab.csv"
BATCH_SIZE = 128  # Procesar en trozos pequeños para no saturar la GPU

if not os.path.exists(CSV_FILE):
    print(f"❌ ERROR: No se encuentra el archivo '{CSV_FILE}'.")
    print("Súbelo usando el icono de carpeta a la izquierda.")
else:
    print(f"✅ Cargando datos...")
    df = pd.read_csv(CSV_FILE)
    
    pre = DataPreprocessor()
    df_p = pre.add_indicators(df)
    X, y, features = pre.prepare(df_p)

    # Convertir a Tensores
    X_t = torch.tensor(X, dtype=torch.float32)
    y_t = torch.tensor(y, dtype=torch.float32).unsqueeze(1)

    # Dividir datos
    train_size = int(len(X) * 0.8)
    X_train, X_test = X_t[:train_size], X_t[train_size:]
    y_train, y_test = y_t[:train_size], y_t[train_size:]

    # USAR DATALOADER (Esto evita el error OutOfMemory)
    train_loader = DataLoader(TensorDataset(X_train, y_train), batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(TensorDataset(X_test, y_test), batch_size=BATCH_SIZE)

    model = CryptoGRU(X.shape[2], 512, 3, dropout=0.4).to(DEVICE) 
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.0005)

    print("\n🚀 Entrenando con procesamiento por lotes...")
    best_acc = 0
    for epoch in range(150):
        model.train()
        train_loss = 0
        for batch_X, batch_y in train_loader:
            batch_X, batch_y = batch_X.to(DEVICE), batch_y.to(DEVICE)
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward(); optimizer.step()
            train_loss += loss.item()
        
        if (epoch+1) % 10 == 0:
            model.eval()
            correct, total = 0, 0
            with torch.no_grad():
                for batch_X, batch_y in test_loader:
                    batch_X, batch_y = batch_X.to(DEVICE), batch_y.to(DEVICE)
                    preds = (model(batch_X) > 0.5).float()
                    total += batch_y.size(0)
                    correct += (preds == batch_y).sum().item()
            
            acc = 100 * correct / total
            if acc > best_acc: 
                best_acc = acc
                torch.save(model.state_dict(), "modelo_71.pt")
            print(f"Época {epoch+1:3d} | Loss: {train_loss/len(train_loader):.4f} | Accuracy: {acc:.2f}% (Mejor: {best_acc:.2f}%)")
            
            # Limpiar memoria GPU
            torch.cuda.empty_cache()

    print(f"\n--- PROCESO FINALIZADO ---")
    print(f"Mejor Accuracy alcanzado: {best_acc:.2f}%")
    
    # EMPAQUETADO
    joblib.dump(pre.scaler, "escalador_71.gz")
    joblib.dump(features, "features_71.gz")
    os.makedirs("resultados", exist_ok=True)
    shutil.copy("modelo_71.pt", "resultados/modelo_71.pt")
    shutil.copy("escalador_71.gz", "resultados/escalador_71.gz")
    shutil.copy("features_71.gz", "resultados/features_71.gz")
    shutil.make_archive("resultado_final_70", 'zip', "resultados")
    files.download("resultado_final_70.zip")
