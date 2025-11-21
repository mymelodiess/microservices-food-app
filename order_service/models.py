from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String)
    total_price = Column(Float)
    status = Column(String, default="PENDING")
    
    # Quan hệ 1-N: Một đơn hàng có nhiều món
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    food_name = Column(String)
    quantity = Column(Integer)
    unit_price = Column(Float)
    subtotal = Column(Float)
    
    order = relationship("Order", back_populates="items")