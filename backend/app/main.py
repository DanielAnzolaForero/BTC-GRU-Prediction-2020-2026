import sys
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import endpoints

# --- CONFIGURACIÓN DE RUTAS PARA MÓDULOS ---
# Esto permite que 'import ml_service' funcione correctamente
root_path = Path(__file__).resolve().parent.parent
sys.path.append(str(root_path))

app = FastAPI(title="Crypto Prediction API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(endpoints.router, prefix="/api/v1", tags=["Predictions"])

@app.get("/")
async def root():
    return {"status": "running", "model": "XGBoost v2"}