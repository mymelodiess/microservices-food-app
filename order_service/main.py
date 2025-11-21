from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List
import httpx
from sqlalchemy.orm import Session
import models
from database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# order_service/main.py

# TRƯỚC ĐÂY (Chạy lẻ):
# USER_SERVICE_URL = "http://localhost:8001"
# RESTAURANT_SERVICE_URL = "http://localhost:8002"
# PAYMENT_SERVICE_URL = "http://localhost:8004"

# BÂY GIỜ (Chạy Docker):
# Tên host phải trùng với tên service khai báo trong docker-compose.yml (ở bước 3)
USER_SERVICE_URL = "http://user_service:8001"
RESTAURANT_SERVICE_URL = "http://restaurant_service:8002"
PAYMENT_SERVICE_URL = "http://payment_service:8004"
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class OrderItemSchema(BaseModel):
    food_id: int
    quantity: int

class OrderCreate(BaseModel):
    user_id: int
    items: List[OrderItemSchema]

@app.post("/orders")
async def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    # 1. Gọi User Service
    async with httpx.AsyncClient() as client:
        user_res = await client.get(f"{USER_SERVICE_URL}/users/{order.user_id}")
    if user_res.status_code != 200:
        raise HTTPException(status_code=400, detail="User không tồn tại")
    user_info = user_res.json()

    # 2. Tính toán tổng tiền và chuẩn bị danh sách items
    total_price = 0
    db_items = []
    
    async with httpx.AsyncClient() as client:
        for item in order.items:
            food_res = await client.get(f"{RESTAURANT_SERVICE_URL}/foods/{item.food_id}")
            if food_res.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Món ăn ID {item.food_id} lỗi")
            
            food_data = food_res.json()
            subtotal = food_data['price'] * item.quantity
            total_price += subtotal
            
            # Tạo object OrderItem (chưa lưu)
            db_item = models.OrderItem(
                food_name=food_data['name'],
                quantity=item.quantity,
                unit_price=food_data['price'],
                subtotal=subtotal
            )
            db_items.append(db_item)

    # 3. Lưu Order và OrderItems vào DB
    new_order = models.Order(
        user_name=user_info['name'],
        total_price=total_price,
        status="PENDING"
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order) # Để lấy được new_order.id

    # Gán id của đơn hàng cho các món ăn và lưu
    for item in db_items:
        item.order_id = new_order.id
        db.add(item)
    db.commit()

    # 4. Gọi Payment Service
    async with httpx.AsyncClient() as client:
        await client.post(f"{PAYMENT_SERVICE_URL}/payments", json={"order_id": new_order.id, "amount": total_price})

    return {"message": "Tạo đơn thành công", "order_id": new_order.id}

@app.get("/orders")
def get_orders(db: Session = Depends(get_db)):
    return db.query(models.Order).all()