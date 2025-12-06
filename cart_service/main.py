import httpx
from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models

# Tạo lại bảng
Base.metadata.create_all(bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- AUTH HELPER ---
async def get_user_id(request: Request):
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Missing Token")
    try:
        # Gọi User Service xác thực (qua Gateway hoặc trực tiếp)
        async with httpx.AsyncClient() as client:
            res = await client.get("http://user_service:8001/verify", headers={"Authorization": token})
            if res.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid Token")
            return res.json()['id']
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

# ==========================================
# API GIỎ HÀNG THÔNG MINH
# ==========================================

@app.post("/cart")
async def add_to_cart(item: dict, request: Request, db: Session = Depends(get_db)):
    user_id = await get_user_id(request)
    
    # Nhận dữ liệu từ UI
    f_id = item.get('food_id')
    qty = item.get('quantity', 1)
    b_id = item.get('branch_id') # UI bắt buộc phải gửi cái này
    
    if not b_id:
        raise HTTPException(status_code=400, detail="Missing branch_id")

    # 1. Kiểm tra giỏ hàng hiện tại
    existing_items = db.query(models.CartItem).filter(models.CartItem.user_id == user_id).all()
    
    if existing_items:
        # Lấy branch_id của món đầu tiên trong giỏ
        current_branch = existing_items[0].branch_id
        
        # Nếu khác branch -> Báo lỗi ngay
        if current_branch != b_id:
             raise HTTPException(status_code=409, detail=f"Giỏ hàng đang chứa món của quán khác. Vui lòng xóa giỏ hàng cũ trước!")
            
        # Nếu cùng branch -> Cộng dồn số lượng nếu trùng món
        found = False
        for cart_item in existing_items:
            if cart_item.food_id == f_id:
                cart_item.quantity += qty
                found = True
                break
        
        if not found:
            new_item = models.CartItem(user_id=user_id, food_id=f_id, quantity=qty, branch_id=b_id)
            db.add(new_item)
            
    else:
        # Giỏ trống -> Thêm mới
        new_item = models.CartItem(user_id=user_id, food_id=f_id, quantity=qty, branch_id=b_id)
        db.add(new_item)

    db.commit()
    return {"message": "Added"}

@app.get("/cart")
async def get_my_cart(request: Request, db: Session = Depends(get_db)):
    user_id = await get_user_id(request)
    return db.query(models.CartItem).filter(models.CartItem.user_id == user_id).all()

@app.put("/cart")
async def update_cart(item: dict, request: Request, db: Session = Depends(get_db)):
    user_id = await get_user_id(request)
    f_id = item.get('food_id')
    qty = item.get('quantity')
    
    cart_item = db.query(models.CartItem).filter(models.CartItem.user_id == user_id, models.CartItem.food_id == f_id).first()
    if cart_item:
        if qty <= 0: db.delete(cart_item)
        else: cart_item.quantity = qty
        db.commit()
        return {"message": "Updated"}
    raise HTTPException(status_code=404, detail="Item not found")

@app.delete("/cart")
async def clear_cart(request: Request, db: Session = Depends(get_db)):
    user_id = await get_user_id(request)
    db.query(models.CartItem).filter(models.CartItem.user_id == user_id).delete()
    db.commit()
    return {"message": "Cleared"}