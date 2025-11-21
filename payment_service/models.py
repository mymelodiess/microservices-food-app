from sqlalchemy import Column, Integer, String, Float
from database import Base

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, index=True)
    amount = Column(Float)
    status = Column(String, default="SUCCESS")