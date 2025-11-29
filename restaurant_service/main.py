from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import APIKeyHeader 
from pydantic import BaseModel
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from typing import List  
from typing import Optional

import models
from database import SessionLocal, engine

# --- CẤU HÌNH BẢO MẬT ---
SECRET_KEY = "chuoi_bi_mat_sieu_kho_doan_cua_ban"
ALGORITHM = "HS256"

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khai báo cách lấy token
oauth2_scheme = APIKeyHeader(name="Authorization")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- CÁC HÀM BẢO MẬT ---

def get_current_user_id(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token không chứa ID")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ")

def verify_seller(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        role: str = payload.get("role")
        if role != "seller":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền! Chỉ Seller mới được tạo món."
            )
        return True
    except JWTError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ")

# --- MODELS (Pydantic) ---
class FoodCreate(BaseModel):
    name: str
    price: float

class FoodResponse(BaseModel):
    id: int
    name: str
    price: float
    owner_id: int
    class Config:
        from_attributes = True

# --- API ENDPOINTS ---

@app.post("/foods", response_model=FoodResponse)
def create_food(
    food: FoodCreate, 
    db: Session = Depends(get_db), 
    authorized: bool = Depends(verify_seller),
    owner_id: int = Depends(get_current_user_id)
):
    new_food = models.Food(
        name=food.name, 
        price=food.price, 
        owner_id=owner_id
    )
    db.add(new_food)
    db.commit()
    db.refresh(new_food)
    return new_food

@app.get("/foods/{food_id}", response_model=FoodResponse)
def get_food(food_id: int, db: Session = Depends(get_db)):
    food = db.query(models.Food).filter(models.Food.id == food_id).first()
    if food is None:
        raise HTTPException(status_code=404, detail="Food not found")
    return food

# API MỚI: Đã sửa 'list' thành 'List' để chạy được trên Python 3.8
@app.get("/seller/foods", response_model=List[FoodResponse]) # <--- 2. SỬA CHỖ NÀY
def get_my_foods(
    db: Session = Depends(get_db),
    owner_id: int = Depends(get_current_user_id)
):
    foods = db.query(models.Food).filter(models.Food.owner_id == owner_id).all()
    return foods

# API MỚI: Lấy danh sách tất cả món ăn (Công khai cho Menu)
@app.get("/foods", response_model=List[FoodResponse])
def get_all_foods(
    q: Optional[str] = None,  # Tham số tìm kiếm (tên món)
    min_price: Optional[float] = None, # Tìm theo giá thấp nhất
    max_price: Optional[float] = None, # Tìm theo giá cao nhất
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    query = db.query(models.Food)
    
    # 1. Lọc theo tên (Không phân biệt hoa thường)
    if q:
        query = query.filter(models.Food.name.ilike(f"%{q}%")) # ilike là search không phân biệt hoa thường trong Postgres/MySQL
    
    # 2. Lọc theo giá
    if min_price:
        query = query.filter(models.Food.price >= min_price)
    if max_price:
        query = query.filter(models.Food.price <= max_price)
        
    return query.offset(skip).limit(limit).all()