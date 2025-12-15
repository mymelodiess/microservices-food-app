import httpx
import json
import asyncio
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import List, Optional
from database import SessionLocal, engine, Base
import models
from datetime import datetime
from contextlib import asynccontextmanager
from aiokafka import AIOKafkaConsumer

Base.metadata.create_all(bind=engine)

# --- CẤU HÌNH KAFKA CONSUMER ---
KAFKA_TOPIC = "order_paid"
KAFKA_BOOTSTRAP_SERVERS = "kafka:9092"
KAFKA_GROUP_ID = "order_service_group"

async def consume_messages():
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_GROUP_ID,
        auto_offset_reset='earliest'
    )
    
    print("⏳ Kafka Consumer: Starting...")
    await consumer.start()
    
    try:
        async for msg in consumer:
            try:
                payload = json.loads(msg.value.decode("utf-8"))
                if payload.get("event") == "ORDER_PAID":
                    order_id = payload.get("order_id")
                    
                    db = SessionLocal()
                    try:
                        order = db.query(models.Order).options(joinedload(models.Order.items)).filter(models.Order.id == order_id).first()
                        if order:
                            order.status = "PAID"
                            db.commit()
                            
                            # Gửi thông báo Banking thành công
                            notify_url = "http://notification_service:8006/notify"
                            item_count = len(order.items)
                            async with httpx.AsyncClient() as client:
                                await client.post(notify_url, json={
                                    "branch_id": order.branch_id,
                                    "message": f"💰 (Banking) Đơn #{order.id} ĐÃ THANH TOÁN: {item_count} món - {order.total_price:,.0f}đ"
                                })
                    finally:
                        db.close()
            except Exception as e:
                print(f"❌ Kafka Error: {e}")
    finally:
        await consumer.stop()

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(consume_messages())
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- DTOs ---
class OrderItemResponse(BaseModel):
    food_id: int
    food_name: str
    quantity: int
    price: float
    image_url: Optional[str] = None
    class Config:
        orm_mode = True

class OrderResponse(BaseModel):
    id: int
    user_id: int
    total_price: float
    status: str
    payment_method: str # <--- Thêm trường này
    created_at: Optional[datetime] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    delivery_address: Optional[str] = None
    note: Optional[str] = None
    items: List[OrderItemResponse] = []
    class Config:
        orm_mode = True

class OrderItemCreate(BaseModel):
    food_id: int
    quantity: int
    food_name: str
    price: float
    image_url: Optional[str] = None
    branch_id: Optional[int] = None 

class OrderCreate(BaseModel):
    user_id: int
    branch_id: int
    items: List[OrderItemCreate]
    customer_name: str
    customer_phone: str
    delivery_address: str
    payment_method: str # <--- Thêm trường này (COD hoặc BANKING)
    coupon_code: Optional[str] = None
    note: Optional[str] = None

class PaymentRequest(BaseModel):
    order_id: int
    amount: float
    bank_name: Optional[str] = None
    card_number: Optional[str] = None

# --- API ---

@app.get("/orders", response_model=List[OrderResponse])
def get_orders(branch_id: Optional[int] = None, user_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.Order).options(joinedload(models.Order.items))
    if branch_id:
        query = query.filter(models.Order.branch_id == branch_id)
    if user_id:
        query = query.filter(models.Order.user_id == user_id)
    return query.order_by(models.Order.created_at.desc()).all()

@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_order_detail(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).options(joinedload(models.Order.items)).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    return order

@app.put("/orders/{order_id}/status")
async def update_order_status(order_id: int, status: str, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    order.status = status
    db.commit()
    return {"message": "Status updated", "status": order.status}

@app.put("/orders/{order_id}/paid")
async def mark_order_as_paid(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).options(joinedload(models.Order.items)).filter(models.Order.id == order_id).first()
    if not order: raise HTTPException(404, "Order not found")
    
    order.status = "PAID"
    db.commit()
    
    # Bắn thông báo (Trường hợp gọi trực tiếp không qua Kafka)
    try:
        notify_url = "http://notification_service:8006/notify" 
        async with httpx.AsyncClient() as client:
            await client.post(notify_url, json={
                "branch_id": order.branch_id,
                "message": f"💰 (Direct) Đơn #{order.id} ĐÃ THANH TOÁN: {order.total_price:,.0f}đ"
            })
    except: pass
    
    return {"message": "Order PAID", "order_id": order_id}

# ==========================================
# API CHECKOUT (ĐÃ SỬA: CÓ TÍNH TOÁN COUPON)
# ==========================================
@app.post("/checkout")
async def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    if not payload.items:
        raise HTTPException(400, "Cart is empty")

    # 1. Tính giá gốc
    original_total = sum(item.price * item.quantity for item in payload.items)
    discount_amount = 0
    final_price = original_total

    # 2. LOGIC XỬ LÝ COUPON (Gọi sang Restaurant Service)
    if payload.coupon_code:
        try:
            # Lưu ý: Trong Docker, các service gọi nhau qua tên service (restaurant_service)
            # URL này phải khớp với API /verify bạn vừa thêm bên Restaurant Service
            verify_url = "http://restaurant_service:8002/coupons/verify"
            
            async with httpx.AsyncClient() as client:
                resp = await client.get(verify_url, params={
                    "code": payload.coupon_code,
                    "branch_id": payload.branch_id
                })
                
                if resp.status_code == 200:
                    coupon_data = resp.json()
                    # Lấy % giảm giá từ kết quả trả về
                    discount_percent = coupon_data.get("discount_percent", 0)
                    
                    # Tính tiền giảm
                    discount_amount = original_total * (discount_percent / 100)
                    final_price = original_total - discount_amount
                    
                    print(f"✅ Áp dụng Coupon {payload.coupon_code}: Giảm {discount_percent}% (-{discount_amount:,.0f}đ)")
                else:
                    print(f"⚠️ Coupon không hợp lệ hoặc lỗi server: {resp.text}")
                    
        except Exception as e:
            print(f"❌ Lỗi khi gọi Restaurant Service check coupon: {e}")
            # Nếu lỗi mạng thì tạm thời tính giá gốc, không crash app

    # 3. Tạo đơn hàng với GIÁ ĐÃ GIẢM (final_price)
    new_order = models.Order(
        user_id=payload.user_id,
        user_name=payload.customer_name,
        branch_id=payload.branch_id,
        
        total_price=final_price,       # <--- Dùng giá đã trừ khuyến mãi
        discount_amount=discount_amount, # <--- Lưu lại số tiền được giảm
        
        status="PENDING",
        payment_method=payload.payment_method,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        delivery_address=payload.delivery_address,
        note=payload.note,
        coupon_code=payload.coupon_code,
        created_at=datetime.utcnow()
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # 4. Lưu chi tiết món ăn
    for item in payload.items:
        db_item = models.OrderItem(
            order_id=new_order.id,
            food_id=item.food_id,
            food_name=item.food_name,
            image_url=item.image_url,
            price=item.price,
            quantity=item.quantity
        )
        db.add(db_item)
    db.commit()

    # 5. Gửi thông báo nếu là COD
    if payload.payment_method == "COD":
        try:
            notify_url = "http://notification_service:8006/notify" 
            item_count = len(payload.items)
            
            async with httpx.AsyncClient() as client:
                await client.post(notify_url, json={
                    "branch_id": payload.branch_id,
                    "message": f"🛵 Đơn MỚI (COD) #{new_order.id}: {item_count} món - {final_price:,.0f}đ (Đã giảm: {discount_amount:,.0f}đ)"
                })
        except Exception as e:
            print(f"⚠️ COD Notification Failed: {e}")

    # Trả về kết quả cho Frontend
    return { 
        "message": "Order placed", 
        "order_id": new_order.id, 
        "total_price": final_price,  # Trả về giá đúng để trang Payment hiển thị
        "discount_amount": discount_amount 
    }