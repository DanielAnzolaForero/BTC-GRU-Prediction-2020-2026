from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Importamos el servicio de Machine Learning
from app.services.predictor import PredictorService 
# Importamos la función que guarda en la base de datos
from app.core.database import guardar_prediccion

router = APIRouter()

# 1. Definimos la estructura de la respuesta (Frontend lo recibirá así)
class PredictionResponse(BaseModel):
    symbol: str
    prediction: str
    probability: float
    current_price: float

# 2. El Endpoint principal de Predicción
@router.get("/predict/{symbol}", response_model=PredictionResponse)
async def get_prediction(symbol: str):
    try:
        print(f"DEBUG: Iniciando solicitud de predicción para {symbol.upper()}")
        
        # A. Instanciamos el servicio y calculamos la predicción
        predictor = PredictorService(symbol=symbol.upper())
        result = predictor.predict_next()
        
        # B. ¡EL PUENTE A LA BASE DE DATOS! 
        # Enviamos el diccionario 'result' a Supabase de forma silenciosa
        print(f"DEBUG: Predicción generada. Intentando guardar en Supabase: {result}")
        db_response = guardar_prediccion(result)
        
        if db_response:
            print("DEBUG: ✅ Guardado exitoso en Supabase.")
        else:
            print("DEBUG: ⚠️ La predicción se hizo, pero hubo un problema al guardar (revisa logs de database.py).")
            
        # C. Retornamos el JSON al navegador o frontend
        return result
        
    except Exception as e:
        # Si algo falla gravemente, lo imprimimos en Render y lanzamos error 500
        print(f"❌ DEBUG ERROR CRÍTICO en endpoint predict: {e}") 
        raise HTTPException(status_code=500, detail=str(e))

# 3. Endpoint para el historial (Para expandir en el futuro)
@router.get("/history/{symbol}")
async def get_history(symbol: str):
    # Aquí en el futuro puedes hacer un "select" a Supabase para devolver los datos guardados
    return {"symbol": symbol, "history": []}