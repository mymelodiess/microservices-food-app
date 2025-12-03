from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import APIKeyHeader 
from pydantic import BaseModel
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from typing import List, Optional

import models
from database import SessionLocal, engine

# --- CẤU HÌNH ---
SECRET_KEY = "chuoi_bi_mat_sieu_kho_doan_cua_ban"
ALGORITHM = "HS256"

# Lệnh này sẽ tạo bảng branches và foods mới (nếu bạn đã xóa bảng cũ trong Adminer)
models.Base.metadata.create_all(bind=engine)

app = FastAPI()
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

# --- HELPER BẢO MẬT ---
def verify_seller(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        role: str = payload.get("role")
        if role != "seller":
            raise HTTPException(status_code=403, detail="Chỉ Seller mới được quyền này")
        return payload # Trả về toàn bộ payload để lấy thêm thông tin nếu cần
    except JWTError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ")

# --- SCHEMAS (Pydantic) ---

# 1. Schema cho Chi Nhánh
class BranchCreate(BaseModel):
    name: str
    address: str
    phone: str

class BranchResponse(BaseModel):
    id: int
    name: str
    address: str
    phone: str
    class Config:
        from_attributes = True

# 2. Schema cho Món Ăn
class FoodCreate(BaseModel):
    name: str
    price: float
    branch_id: int # Khi tạo món phải biết món này của quán nào

class FoodResponse(BaseModel):
    id: int
    name: str
    price: float
    branch_id: int
    class Config:
        from_attributes = True

# --- API ENDPOINTS ---

# === API CHI NHÁNH (BRANCHES) ===

# API tạo chi nhánh (Tạm thời ai cũng tạo được để bạn setup dữ liệu)
@app.post("/branches", response_model=BranchResponse)
def create_branch(branch: BranchCreate, db: Session = Depends(get_db)):
    new_branch = models.Branch(name=branch.name, address=branch.address, phone=branch.phone)
    db.add(new_branch)
    db.commit()
    db.refresh(new_branch)
    return new_branch

# API lấy danh sách chi nhánh (Cho khách chọn)
@app.get("/branches", response_model=List[BranchResponse])
def get_branches(db: Session = Depends(get_db)):
    return db.query(models.Branch).all()


# === API MÓN ĂN (FOODS) ===

@app.post("/foods", response_model=FoodResponse)
def create_food(
    food: FoodCreate, 
    db: Session = Depends(get_db), 
    token_payload: dict = Depends(verify_seller) # Chỉ cần check là seller
):
    # Kiểm tra chi nhánh có tồn tại không
    branch = db.query(models.Branch).filter(models.Branch.id == food.branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Chi nhánh không tồn tại")

    new_food = models.Food(
        name=food.name, 
        price=food.price, 
        branch_id=food.branch_id # Gắn món vào chi nhánh
    )
    db.add(new_food)
    db.commit()
    db.refresh(new_food)
    return new_food

# API Lấy món ăn (Có lọc theo chi nhánh)
@app.get("/foods", response_model=List[FoodResponse])
def get_all_foods(
    branch_id: Optional[int] = None, # Quan trọng: Khách chọn chi nhánh nào thì chỉ hiện món chi nhánh đó
    q: Optional[str] = None,
    min_price: Optional[float] = None, 
    max_price: Optional[float] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Food)
    
    # Lọc theo chi nhánh (QUAN TRỌNG NHẤT)
    if branch_id:
        query = query.filter(models.Food.branch_id == branch_id)

    if q:
        query = query.filter(models.Food.name.ilike(f"%{q}%"))
    if min_price:
        query = query.filter(models.Food.price >= min_price)
    if max_price:
        query = query.filter(models.Food.price <= max_price)
        
    return query.all()

# --- Thêm vào restaurant_service/main.py ---

@app.get("/foods/{food_id}", response_model=FoodResponse)
def get_food_detail(food_id: int, db: Session = Depends(get_db)):
    food = db.query(models.Food).filter(models.Food.id == food_id).first()
    if not food:
        raise HTTPException(status_code=404, detail="Food not found")
    return food

# --- THÊM VÀO CUỐI FILE restaurant_service/main.py ---

@app.delete("/foods/{food_id}")
def delete_food(
    food_id: int, 
    db: Session = Depends(get_db),
    # Hàm verify_seller này bạn đã có ở phần trên file main.py rồi
    token_payload: dict = Depends(verify_seller) 
):
    # 1. Tìm món ăn trong DB
    food = db.query(models.Food).filter(models.Food.id == food_id).first()
    if not food:
        raise HTTPException(status_code=404, detail="Món ăn không tồn tại")
    
    # 2. KIỂM TRA QUYỀN (Quan trọng)
    # Lấy ID chi nhánh của Seller từ Token
    seller_branch_id = token_payload.get("branch_id")
    
    # So sánh: Nếu món này KHÔNG thuộc chi nhánh của Seller -> Chặn
    if food.branch_id != seller_branch_id:
         raise HTTPException(status_code=403, detail="Bạn chỉ được xóa món thuộc chi nhánh của mình!")

    # 3. Xóa
    db.delete(food)
    db.commit()
    return {"message": "Đã xóa món ăn thành công"}