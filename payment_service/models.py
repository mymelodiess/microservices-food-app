from sqlalchemy import Column, Integer, String, Float, DateTime
from database import Base
import datetime

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, index=True)
    amount = Column(Float)
    
    # Mã giao dịch (Ví dụ: PAY_123456)
    transaction_id = Column(String(100), unique=True)
    
    status = Column(String(50), default="SUCCESS")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)