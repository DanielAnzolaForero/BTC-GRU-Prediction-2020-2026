from fastapi import APIRouter, HTTPException
from app.services.predictor import PredictService
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
        predictor = PredictorService(symbol=symbol.upper())
        result = predictor.predict_next()
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

@router.get("/history/{symbol}")
async def get_history(symbol: str):
    # For now, return a placeholder. In a full implementation, this hits SQLite.
    return {"symbol": symbol, "history": []}
