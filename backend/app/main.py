import sys
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.app.api.v1 import endpoints

# --- CONFIGURACIÓN DE RUTAS ---
# Subimos 3 niveles: app -> backend -> raíz (crypto-pro)
root_path = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root_path))

app = FastAPI(title="Crypto Prediction API")

# --- LOCALIZAR EL FRONTEND ---
frontend_path = root_path / "frontend" / "dist"

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- RUTAS DE LA API (Deben ir antes que el Front) ---
app.include_router(endpoints.router, prefix="/api/v1", tags=["Predictions"])

# --- SERVIR EL FRONTEND DE REACT ---
if frontend_path.exists():
    # Montamos la carpeta de assets para JS/CSS
    app.mount("/assets", StaticFiles(directory=str(frontend_path / "assets")), name="assets")
    
    # La ruta principal que sirve el dashboard
    @app.get("/")
    async def serve_index():
        return FileResponse(str(frontend_path / "index.html"))

    # Manejador para rutas de React (SPA) - Evita 404 al recargar
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Si la ruta no empieza con api, mandamos al index.html
        if not full_path.startswith("api"):
            return FileResponse(str(frontend_path / "index.html"))
        return {"error": "API route not found"}

# Ruta de salud para verificar en Render
@app.get("/health")
async def health():
    return {
        "status": "running",
        "frontend_detected": frontend_path.exists(),
        "path_buscado": str(frontend_path)
    }
