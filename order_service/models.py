from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    
    # Người mua
    user_id = Column(Integer, index=True)
    user_name = Column(String(100))
    
    # Thông tin đơn
    branch_id = Column(Integer, index=True)
    total_price = Column(Float) # Giá cuối cùng phải trả (Sau khi trừ KM)
    status = Column(String(50), default="PENDING_PAYMENT")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Giao hàng
    delivery_address = Column(String(255))
    customer_phone = Column(String(20))

    # --- MỚI: THÔNG TIN KHUYẾN MÃI ---
    coupon_code = Column(String(50), nullable=True) # Mã khách nhập (VD: GIAM20)
    discount_amount = Column(Float, default=0.0)    # Số tiền được giảm (VD: 15000)

    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    
    food_id = Column(Integer)
    food_name = Column(String(200))
    price = Column(Float)
    quantity = Column(Integer)
    
    order = relationship("Order", back_populates="items")