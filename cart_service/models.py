from sqlalchemy import Column, Integer
from database import Base

class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    food_id = Column(Integer)
    quantity = Column(Integer, default=1)
    
    # --- UPDATE: Lưu thêm branch_id ---
    branch_id = Column(Integer)