import httpx
import shutil
import os
import uuid
from datetime import datetime
from typing import List, Optional
from collections import defaultdict

from fastapi import FastAPI, Depends, HTTPException, Request, File, UploadFile, Form, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import SessionLocal, engine, Base
import models

# 1. TẠO BẢNG DỮ LIỆU (Nếu chưa có)
Base.metadata.create_all(bind=engine)

app = FastAPI()

# 2. CẤU HÌNH CORS (Để Frontend React gọi được API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. CẤU HÌNH THƯ MỤC CHỨA ẢNH UPLOAD
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 4. DEPENDENCIES (Kết nối DB & Xác thực User)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def verify_user(request: Request):
    token = request.headers.get("Authorization")
    if not token: 
        raise HTTPException(401, "Missing Token")
    
    try:
        async with httpx.AsyncClient() as client:
            # Gọi sang User Service để check token
            # Đảm bảo 'user_service' là tên container hoặc localhost:8001 tùy môi trường của bạn
            service_url = "http://user_service:8001/verify" 
            res = await client.get(service_url, headers={"Authorization": token})
            if res.status_code != 200: 
                raise HTTPException(401, "Invalid Token from Auth Service")
            return res.json()
    except httpx.RequestError:
        print("⚠️ Dev Mode: User Service Unavailable (Bypass Auth)")
        # Trả về user giả để test khi không chạy User Service
        return {"id": 1, "role": "seller"} 
    except Exception as e:
        raise HTTPException(401, "Token verification failed")

# 5. PYDANTIC MODELS (Định nghĩa dữ liệu đầu vào/ra)
class BranchCreate(BaseModel):
    name: str
    address: str
    phone: str

class CouponCreate(BaseModel):
    code: str
    discount_percent: int
    branch_id: int
    start_date: datetime
    end_date: datetime
    is_active: bool = True

class FoodSearchResponse(BaseModel):
    name: str
    image_url: Optional[str]
    min_price: float
    max_price: float
    avg_rating: float = 0.0
    review_count: int = 0
    branch_count: int

# ==========================================
# API CHI NHÁNH (BRANCH)
# ==========================================
@app.post("/branches")
async def create_branch(branch: BranchCreate, db: Session = Depends(get_db)):
    new_branch = models.Branch(name=branch.name, address=branch.address, phone=branch.phone)
    db.add(new_branch)
    db.commit()
    db.refresh(new_branch)
    return new_branch

@app.get("/branches")
def get_branches(db: Session = Depends(get_db)):
    return db.query(models.Branch).all()

@app.get("/branches/{branch_id}")
def get_branch_detail(branch_id: int, db: Session = Depends(get_db)):
    branch = db.query(models.Branch).filter(models.Branch.id == branch_id).first()
    if not branch: raise HTTPException(404, "Branch not found")
    return branch

# ==========================================
# API COUPON (MÃ GIẢM GIÁ)
# ==========================================
@app.post("/coupons")
async def create_coupon(coupon: CouponCreate, db: Session = Depends(get_db)):
    new_coupon = models.Coupon(
        code=coupon.code, discount_percent=coupon.discount_percent,
        branch_id=coupon.branch_id, start_date=coupon.start_date,
        end_date=coupon.end_date, is_active=coupon.is_active
    )
    db.add(new_coupon)
    db.commit()
    db.refresh(new_coupon)
    return new_coupon

@app.get("/coupons")
def get_coupons(branch_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Lấy danh sách coupon (Hỗ trợ lọc theo branch_id cho Dashboard)"""
    query = db.query(models.Coupon)
    if branch_id:
        query = query.filter(models.Coupon.branch_id == branch_id)
    return query.all()

@app.get("/coupons/check/{code}")
def check_coupon(code: str, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    coupon = db.query(models.Coupon).filter(
        models.Coupon.code == code, models.Coupon.is_active == True, models.Coupon.end_date > now
    ).first()
    if not coupon: raise HTTPException(404, "Coupon invalid")
    return coupon

# ==========================================
# API TÌM KIẾM & OPTIONS (DÀNH CHO KHÁCH HÀNG - SHOP.JSX)
# ==========================================

@app.get("/foods/search", response_model=List[FoodSearchResponse])
def search_food(q: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Tìm kiếm và gom nhóm món ăn theo tên để hiển thị min/max price"""
    query = db.query(models.Food)
    if q and q.strip() != "":
        query = query.filter(models.Food.name.ilike(f"%{q}%"))
    
    raw_foods = query.all()
    grouped = defaultdict(list)
    for food in raw_foods:
        grouped[food.name].append(food)

    results = []
    for name, items in grouped.items():
        prices = [f.price for f in items]
        image = next((f.image_url for f in items if f.image_url), None)
        min_p = min(prices) if prices else 0
        max_p = max(prices) if prices else 0
        branch_cnt = len(set(f.branch_id for f in items))
        
        results.append(FoodSearchResponse(
            name=name,
            image_url=image,
            min_price=min_p,
            max_price=max_p,
            branch_count=branch_cnt
        ))
    return results

@app.get("/foods/options")
def get_food_options(name: str = Query(...), db: Session = Depends(get_db)):
    """Lấy danh sách các quán bán món này (cho Modal chọn quán)"""
    foods = db.query(models.Food).filter(models.Food.name == name).all()
    options = []
    for f in foods:
        branch_name = f.branch.name if f.branch else "Chi nhánh ẩn"
        options.append({
            "food_id": f.id,
            "branch_id": f.branch_id,
            "branch_name": branch_name,
            "image_url": f.image_url,
            "final_price": f.price * (1 - f.discount/100) if f.discount else f.price,
            "original_price": f.price,
            "discount": f.discount
        })
    return options

# ==========================================
# API QUẢN LÝ MÓN ĂN (DÀNH CHO CHỦ QUÁN - DASHBOARD)
# ==========================================

# 1. API Lấy danh sách món (Đã sửa lỗi 405 Method Not Allowed)
@app.get("/foods")
def get_foods(branch_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    query = db.query(models.Food)
    if branch_id:
        query = query.filter(models.Food.branch_id == branch_id)
    return query.all()

# 2. Lấy chi tiết 1 món
@app.get("/foods/{food_id}")
def get_food_detail(food_id: int, db: Session = Depends(get_db)):
    food = db.query(models.Food).filter(models.Food.id == food_id).first()
    if not food: raise HTTPException(404, "Not found")
    return food

# 3. Tạo món mới (Có upload ảnh)
@app.post("/foods")
async def create_food(
    request: Request, name: str = Form(...), price: float = Form(...),
    discount: int = Form(0), branch_id: int = Form(...),
    image: Optional[UploadFile] = File(None), db: Session = Depends(get_db)
):
    user = await verify_user(request)
    if user.get('role') != 'seller': raise HTTPException(403, "Forbidden")
    
    image_url = ""
    if image:
        ext = image.filename.split(".")[-1]
        fname = f"{uuid.uuid4()}.{ext}"
        fpath = f"static/{fname}"
        with open(fpath, "wb") as buffer: shutil.copyfileobj(image.file, buffer)
        image_url = f"/static/{fname}"

    new_food = models.Food(
        name=name, price=price, branch_id=branch_id, 
        discount=discount, image_url=image_url
    )
    db.add(new_food)
    db.commit()
    db.refresh(new_food)
    return new_food

# 4. Cập nhật món (Thêm vào cho đầy đủ, phòng khi cần dùng)
@app.put("/foods/{food_id}")
async def update_food(
    food_id: int, request: Request, name: str = Form(...),
    price: float = Form(...), discount: int = Form(0),
    image: Optional[UploadFile] = File(None), db: Session = Depends(get_db)
):
    await verify_user(request)
    food = db.query(models.Food).filter(models.Food.id == food_id).first()
    if not food: raise HTTPException(404, "Not found")
    
    food.name = name
    food.price = price
    food.discount = discount

    if image:
        ext = image.filename.split(".")[-1]
        fname = f"{uuid.uuid4()}.{ext}"
        fpath = f"static/{fname}"
        with open(fpath, "wb") as buffer: shutil.copyfileobj(image.file, buffer)
        food.image_url = f"/static/{fname}"
    
    db.commit()
    return food

# 5. Xóa món
@app.delete("/foods/{food_id}")
async def delete_food(food_id: int, request: Request, db: Session = Depends(get_db)):
    await verify_user(request)
    item = db.query(models.Food).filter(models.Food.id == food_id).first()
    if not item: raise HTTPException(404, "Not found")
    db.delete(item)
    db.commit()
    return {"message": "Deleted"}