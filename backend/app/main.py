import sys
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles # Importante
from fastapi.responses import FileResponse # Importante
from app.api.v1 import endpoints

# Configuración de rutas para módulos
root_path = Path(__file__).resolve().parent.parent
sys.path.append(str(root_path))

app = FastAPI(title="Crypto Prediction API")

# --- PASO A: Localizar el Frontend ---
# Esto busca la carpeta 'dist' que crea React cuando haces el build
frontend_path = Path(__file__).parent.parent / "frontend" / "dist"

# --- PASO B: Configurar CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- PASO C: Tus rutas de la API ---
app.include_router(endpoints.router, prefix="/api/v1", tags=["Predictions"])

# --- PASO D: Servir React ---
# 1. Montamos los archivos estáticos (JS, CSS, imágenes)
if frontend_path.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_path / "assets")), name="assets")

# 2. Ruta raíz que entrega el Dashboard
@app.get("/")
async def root():
    if frontend_path.exists():
        return FileResponse(str(frontend_path / "index.html"))
    return {"status": "running", "info": "Frontend dist not found. Did you build React?"} 