from sqlalchemy import Column, Integer, String, Boolean
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    role = Column(String(50), default="buyer") # buyer / seller
    
    # --- THÔNG TIN MỞ RỘNG CHO BUYER ---
    full_name = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)
    address = Column(String(255), nullable=True) # Địa chỉ mặc định
    
    # --- THÔNG TIN CHO SELLER ---
    # Người này quản lý chi nhánh nào? (Lưu ID bên restaurant_service)
    managed_branch_id = Column(Integer, nullable=True)