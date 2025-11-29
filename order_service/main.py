from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import httpx
from sqlalchemy.orm import Session
from jose import jwt, JWTError

import models
from database import SessionLocal, engine

# --- CẤU HÌNH ---
SECRET_KEY = "chuoi_bi_mat_sieu_kho_doan_cua_ban"
ALGORITHM = "HS256"

# URL các service (Lưu ý: Thêm CART_SERVICE_URL)
RESTAURANT_SERVICE_URL = "http://restaurant_service:8002"
PAYMENT_SERVICE_URL = "http://payment_service:8004"
CART_SERVICE_URL = "http://cart_service:8005"

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
        user_id: int = payload.get("id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token không chứa ID")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ")

# --- API ---

@app.post("/checkout")
async def checkout(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    token: str = Depends(oauth2_scheme) # Lấy nguyên chuỗi token để gửi đi
):
    # 1. Gọi sang Cart Service để lấy danh sách món
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": token} # Gửi kèm Token để Cart biết là User nào
        
        try:
            # Lấy giỏ hàng
            cart_res = await client.get(f"{CART_SERVICE_URL}/cart", headers=headers)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Không kết nối được Cart Service: {e}")

        if cart_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Lỗi khi lấy giỏ hàng")
        
        cart_items = cart_res.json() # Dạng: [{"food_id": 1, "quantity": 2}, ...]
        
        if not cart_items:
            raise HTTPException(status_code=400, detail="Giỏ hàng đang trống!")

        # 2. Tính tiền & Chuẩn bị dữ liệu Order
        total_price = 0
        db_items = []

        for item in cart_items:
            # Gọi Restaurant Service lấy giá mới nhất của từng món
            food_res = await client.get(f"{RESTAURANT_SERVICE_URL}/foods/{item['food_id']}")
            if food_res.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Món ăn ID {item['food_id']} không tồn tại hoặc đã bị xóa")
            
            food_data = food_res.json()
            subtotal = food_data['price'] * item['quantity']
            total_price += subtotal
            
            # Tạo chi tiết đơn hàng (OrderItem)
            db_item = models.OrderItem(
                food_name=food_data['name'],
                quantity=item['quantity'],
                unit_price=food_data['price'],
                subtotal=subtotal
            )
            db_items.append(db_item)

        # 3. Lưu Order vào DB
        new_order = models.Order(
            user_name=f"User ID {user_id}",
            total_price=total_price,
            status="PENDING"
        )
        db.add(new_order)
        db.commit()
        db.refresh(new_order)

        # Lưu các món vào đơn
        for item in db_items:
            item.order_id = new_order.id
            db.add(item)
        db.commit()

        # 4. Gọi Payment Service
        await client.post(f"{PAYMENT_SERVICE_URL}/payments", json={"order_id": new_order.id, "amount": total_price})
        
        # 5. QUAN TRỌNG: Quay lại Cart Service để xóa sạch giỏ hàng
        await client.delete(f"{CART_SERVICE_URL}/cart", headers=headers)

    return {"message": "Checkout thành công", "order_id": new_order.id, "total": total_price}

@app.get("/orders")
def get_orders(db: Session = Depends(get_db)):
    return db.query(models.Order).all()

# ... (Code cũ ở trên)

class OrderStatusUpdate(BaseModel):
    status: str

@app.put("/orders/{order_id}/status")  # <--- Đảm bảo dòng này đã có
def update_order_status(
    order_id: int, 
    status_update: OrderStatusUpdate,
    db: Session = Depends(get_db)
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Đơn hàng không tồn tại")
    
    order.status = status_update.status
    db.commit()
    db.refresh(order)
    return {"message": "Status updated", "status": order.status}