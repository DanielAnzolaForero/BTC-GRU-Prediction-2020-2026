from fastapi import APIRouter, HTTPException
from app.services.predictor import PredictorService # <--- Asegúrate que diga PredictorService
from pydantic import BaseModel

router = APIRouter()

class PredictionResponse(BaseModel):
    symbol: str
    prediction: str
    probability: float
    current_price: float

@router.get("/predict/{symbol}", response_model=PredictionResponse)
async def get_prediction(symbol: str):
    try:
        # Instanciamos el servicio correctamente
        predictor = PredictorService(symbol=symbol.upper())
        result = predictor.predict_next()
        return result
    except Exception as e:
        # Esto imprimirá el error real en tu terminal de VS Code
        print(f"DEBUG ERROR: {e}") 
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{symbol}")
async def get_history(symbol: str):
    return {"symbol": symbol, "history": []}