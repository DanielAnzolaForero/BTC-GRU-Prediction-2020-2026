from pydantic import BaseModel
from datetime import datetime

class PredictionCreate(BaseModel):
    symbol: str
    prediction: str
    probability: float
    price_at_prediction: float

class PredictionHistoryRead(PredictionCreate):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True
