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

# --- HÀM XỬ LÝ TIN NHẮN (CHẠY NGẦM) ---
async def consume_messages():
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_GROUP_ID,
        auto_offset_reset='earliest' # Đọc từ đầu nếu là consumer mới
    )
    
    print("⏳ Order Service: Đang kết nối Kafka Consumer...")
    await consumer.start()
    print("🎧 Order Service: Đang lắng nghe tin nhắn...")
    
    try:
        async for msg in consumer:
            try:
                # 1. Đọc tin nhắn
                payload = json.loads(msg.value.decode("utf-8"))
                print(f"📥 Order Service: Nhận tin nhắn từ Kafka: {payload}")
                
                if payload.get("event") == "ORDER_PAID":
                    order_id = payload.get("order_id")
                    
                    # 2. Mở DB Session mới (Vì đang ở trong async task riêng biệt)
                    db = SessionLocal()
                    try:
                        order = db.query(models.Order).options(joinedload(models.Order.items)).filter(models.Order.id == order_id).first()
                        if order:
                            # 3. Cập nhật trạng thái
                            order.status = "PAID"
                            db.commit()
                            print(f"✅ DB Updated: Đơn #{order_id} đã chuyển sang PAID")
                            
                            # 4. Gọi Notification (Bắn socket)
                            notify_url = "http://notification_service:8006/notify"
                            item_count = len(order.items)
                            async with httpx.AsyncClient() as client:
                                await client.post(notify_url, json={
                                    "branch_id": order.branch_id,
                                    "message": f"💰 (Kafka) Đơn #{order.id} ĐÃ THANH TOÁN: {item_count} món - {order.total_price:,.0f}đ"
                                })
                                print("🔔 Notification Sent via Kafka Flow")
                        else:
                            print(f"⚠️ Không tìm thấy đơn #{order_id} trong DB")
                    finally:
                        db.close()
                        
            except Exception as e:
                print(f"❌ Lỗi xử lý tin nhắn: {e}")
                
    finally:
        await consumer.stop()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Kích hoạt Consumer chạy nền
    asyncio.create_task(consume_messages())
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
    coupon_code: Optional[str] = None
    note: Optional[str] = None

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

@app.post("/checkout")
async def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    if not payload.items:
        raise HTTPException(400, "Cart is empty")

    total_price = sum(item.price * item.quantity for item in payload.items)
    
    new_order = models.Order(
        user_id=payload.user_id,
        user_name=payload.customer_name,
        branch_id=payload.branch_id,
        total_price=total_price,
        status="PENDING",
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        delivery_address=payload.delivery_address,
        note=payload.note,
        coupon_code=payload.coupon_code,
        discount_amount=0,
        created_at=datetime.utcnow()
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

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

    return { "message": "Order placed", "order_id": new_order.id, "total_price": total_price }