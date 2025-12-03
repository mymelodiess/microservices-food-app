from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Branch(Base):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True) # Tên chi nhánh (VD: Cơm Tấm Quận 1)
    address = Column(String(255))          # Địa chỉ hiển thị cho khách
    phone = Column(String(50))             # Hotline chi nhánh

    # Quan hệ: Một chi nhánh có nhiều món ăn
    foods = relationship("Food", back_populates="branch")

class Food(Base):
    __tablename__ = "foods"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    price = Column(Float)
    
    # Thay owner_id bằng branch_id
    branch_id = Column(Integer, ForeignKey("branches.id"))
    
    # Quan hệ ngược lại
    branch = relationship("Branch", back_populates="foods")