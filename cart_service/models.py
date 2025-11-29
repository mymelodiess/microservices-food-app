from sqlalchemy import Column, Integer
from database import Base

class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True) # Giỏ của ai
    food_id = Column(Integer)             # Món gì
    quantity = Column(Integer, default=1) # Số lượng