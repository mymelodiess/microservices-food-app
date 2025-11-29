from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from typing import List

import models
from database import SessionLocal, engine

# --- CẤU HÌNH BẢO MẬT ---
SECRET_KEY = "chuoi_bi_mat_sieu_kho_doan_cua_ban"
ALGORITHM = "HS256"

# Tạo bảng trong DB
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# --- CẤU HÌNH CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = APIKeyHeader(name="Authorization")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- HÀM LẤY USER ID TỪ TOKEN ---
def get_current_user_id(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token thiếu ID")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ")

# --- SCHEMAS ---
class CartAdd(BaseModel):
    food_id: int
    quantity: int = 1

class CartUpdate(BaseModel):
    food_id: int
    quantity: int

class CartResponse(BaseModel):
    food_id: int
    quantity: int
    class Config:
        from_attributes = True

# --- API ENDPOINTS ---

# 1. Thêm vào giỏ (Cộng dồn nếu đã có)
@app.post("/cart")
def add_to_cart(item: CartAdd, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    existing_item = db.query(models.CartItem).filter(
        models.CartItem.user_id == user_id,
        models.CartItem.food_id == item.food_id
    ).first()

    if existing_item:
        existing_item.quantity += item.quantity
    else:
        new_item = models.CartItem(user_id=user_id, food_id=item.food_id, quantity=item.quantity)
        db.add(new_item)
    
    db.commit()
    return {"message": "Đã thêm vào giỏ"}

# 2. Cập nhật số lượng (MỚI)
@app.put("/cart")
def update_cart_item(item: CartUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    existing_item = db.query(models.CartItem).filter(
        models.CartItem.user_id == user_id,
        models.CartItem.food_id == item.food_id
    ).first()

    if not existing_item:
        raise HTTPException(status_code=404, detail="Món ăn không có trong giỏ")

    if item.quantity <= 0:
        # Nếu số lượng <= 0 thì xóa luôn
        db.delete(existing_item)
        msg = "Đã xóa món khỏi giỏ"
    else:
        existing_item.quantity = item.quantity
        msg = "Đã cập nhật số lượng"
    
    db.commit()
    return {"message": msg}

# 3. Xem giỏ hàng
@app.get("/cart", response_model=List[CartResponse])
def get_cart(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    items = db.query(models.CartItem).filter(models.CartItem.user_id == user_id).all()
    return items

# 4. Xóa sạch giỏ hàng
@app.delete("/cart")
def clear_cart(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    db.query(models.CartItem).filter(models.CartItem.user_id == user_id).delete()
    db.commit()
    return {"message": "Đã xóa giỏ hàng"}