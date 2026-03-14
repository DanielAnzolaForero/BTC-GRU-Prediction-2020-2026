from sqlalchemy import Column, Integer, String, Float, DateTime
from app.core.database import Base
from datetime import datetime

class PredictionHistory(Base):
    __tablename__ = "prediction_history"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    prediction = Column(String) # UP or DOWN
    probability = Column(Float)
    price_at_prediction = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
