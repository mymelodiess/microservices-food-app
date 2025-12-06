from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from database import Base
import datetime

# --- BẢNG CŨ (GIỮ NGUYÊN) ---
class Branch(Base):
    __tablename__ = "branches"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    address = Column(String(200))
    phone = Column(String(20))
    
    foods = relationship("Food", back_populates="branch")
    coupons = relationship("Coupon", back_populates="branch")

class Food(Base):
    __tablename__ = "foods"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    price = Column(Float)
    discount = Column(Integer, default=0) 
    
    branch_id = Column(Integer, ForeignKey("branches.id"))
    branch = relationship("Branch", back_populates="foods")

class Coupon(Base):
    __tablename__ = "coupons"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), index=True)
    discount_percent = Column(Integer)
    branch_id = Column(Integer, ForeignKey("branches.id"))
    branch = relationship("Branch", back_populates="coupons")
    is_active = Column(Boolean, default=True)

# --- BẢNG MỚI: REVIEW ---

# 1. Bảng Cha: Đánh giá chung đơn hàng
class OrderReview(Base):
    __tablename__ = "order_reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    user_name = Column(String(100))
    
    order_id = Column(Integer, unique=True, index=True) # 1 Đơn = 1 Review
    branch_id = Column(Integer, index=True)             # Để thống kê theo quán
    
    rating_general = Column(Integer) # 1-5 sao
    comment = Column(String(500))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Quan hệ với bảng con
    details = relationship("FoodRating", back_populates="parent_review", cascade="all, delete-orphan")

# 2. Bảng Con: Điểm số từng món
class FoodRating(Base):
    __tablename__ = "food_ratings"
    
    id = Column(Integer, primary_key=True, index=True)
    
    review_id = Column(Integer, ForeignKey("order_reviews.id"))
    parent_review = relationship("OrderReview", back_populates="details")
    
    food_id = Column(Integer, ForeignKey("foods.id"))
    score = Column(Integer) # Điểm số món (1-5)