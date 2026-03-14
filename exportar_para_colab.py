import os
import sys
import pandas as pd

# Añadir el path del proyecto
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from ml_service.src.data_loader import BinanceDataLoader

def export_data():
    print("📦 Iniciando exportación de datos locales para Google Colab...")
    loader = BinanceDataLoader()
    
    # Descargamos los datos en tu PC (donde Binance SÍ funciona)
    df = loader.fetch_multi_timeframe(limit=50000)
    
    if df is not None:
        filename = "datos_crypto_colab.csv"
        df.to_csv(filename, index=False)
        print(f"✅ ¡ÉXITO! Archivo creado: {os.path.abspath(filename)}")
        print("\nPASOS SIGUIENTES:")
        print("1. Sube este archivo CSV a tu Google Colab (icono de carpeta a la izquierda).")
        print("2. Usa el nuevo script de Colab v3.0 que te dará Antigravity.")
    else:
        print("❌ Error al obtener datos locales.")

if __name__ == "__main__":
    export_data()
