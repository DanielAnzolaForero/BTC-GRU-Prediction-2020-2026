from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# ✅ Imports corregidos — ruta completa desde la raíz del proyecto
from backend.app.services.predictor import PredictorService
from backend.app.core.database import guardar_prediccion

router = APIRouter()

# 1. Estructura de la respuesta
class PredictionResponse(BaseModel):
    symbol: str
    prediction: str
    probability: float
    current_price: float

# 2. Endpoint principal de predicción
@router.get("/predict/{symbol}", response_model=PredictionResponse)
async def get_prediction(symbol: str):
    try:
        print(f"DEBUG: Iniciando solicitud de predicción para {symbol.upper()}")

        # A. Instanciar servicio y calcular predicción
        predictor = PredictorService(symbol=symbol.upper())
        result = predictor.predict_next()

        # B. Guardar en Supabase
        print(f"DEBUG: Predicción generada. Intentando guardar en Supabase: {result}")
        db_response = guardar_prediccion(result)

        if db_response:
            print("DEBUG: ✅ Guardado exitoso en Supabase.")
        else:
            print("DEBUG: ⚠️ Predicción realizada, pero hubo un problema al guardar (revisa logs de database.py).")

        # C. Retornar JSON al frontend
        return result

    except Exception as e:
        print(f"❌ DEBUG ERROR CRÍTICO en endpoint predict: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 3. Endpoint de historial (para expansión futura)
@router.get("/history/{symbol}")
async def get_history(symbol: str):
    return {"symbol": symbol, "history": []}
