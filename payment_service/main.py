import json
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models
from pydantic import BaseModel
from typing import List, Optional
import uuid
from contextlib import asynccontextmanager
from aiokafka import AIOKafkaProducer

# Tạo bảng
Base.metadata.create_all(bind=engine)

# --- CẤU HÌNH KAFKA ---
KAFKA_TOPIC = "order_paid"
# "kafka:9092" là địa chỉ nội bộ trong Docker network
KAFKA_BOOTSTRAP_SERVERS = "kafka:9092" 

producer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global producer
    print("🚀 Payment Service: Đang khởi động Kafka Producer...")
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await producer.start()
    print("✅ Kafka Producer: Đã kết nối!")
    yield
    await producer.stop()
    print("🛑 Kafka Producer: Đã ngắt kết nối")

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

# --- MODELS ---
class PaymentRequest(BaseModel):
    order_id: int
    amount: float
    bank_name: Optional[str] = None
    card_number: Optional[str] = None

class CardCreate(BaseModel):
    card_number: str
    card_holder: str
    expiry_date: str
    bank_name: str

class CardResponse(CardCreate):
    id: int
    class Config:
        orm_mode = True

# --- API THANH TOÁN (GỬI KAFKA) ---
@app.post("/pay")
async def process_payment(payload: PaymentRequest, db: Session = Depends(get_db)):
    print(f"💰 Payment Service: Nhận yêu cầu thanh toán đơn #{payload.order_id}")

    # 1. Lưu giao dịch vào DB Payment
    trans_id = f"PAY_{uuid.uuid4().hex[:8].upper()}"
    new_payment = models.Payment(
        order_id=payload.order_id,
        amount=payload.amount,
        transaction_id=trans_id,
        status="SUCCESS"
    )
    db.add(new_payment)
    db.commit()
    
    # 2. BẮN TIN NHẮN VÀO KAFKA (Thay vì gọi HTTP)
    message = {
        "event": "ORDER_PAID",
        "order_id": payload.order_id,
        "amount": payload.amount,
        "transaction_id": trans_id
    }
    
    try:
        # Chuyển dict thành JSON bytes
        json_message = json.dumps(message).encode("utf-8")
        # Gửi và chờ xác nhận từ Kafka Broker
        await producer.send_and_wait(KAFKA_TOPIC, json_message)
        print(f"📨 Payment Service: Đã bắn tin nhắn vào Kafka -> {message}")
    except Exception as e:
        print(f"❌ Kafka Error: {e}")
        # Trong thực tế, bạn nên có cơ chế retry hoặc log lỗi nghiêm trọng ở đây

    return {
        "message": "Thanh toán thành công (Đang xử lý)",
        "transaction_id": trans_id,
        "order_id": payload.order_id,
        "status": "SUCCESS"
    }

# --- CÁC API KHÁC ---
@app.get("/payment-methods", response_model=List[CardResponse])
def get_my_cards(db: Session = Depends(get_db)):
    return db.query(models.PaymentMethod).all()

@app.post("/payment-methods", response_model=CardResponse)
def add_card(card: CardCreate, db: Session = Depends(get_db)):
    new_card = models.PaymentMethod(
        user_id=1, card_number=card.card_number,
        card_holder=card.card_holder, expiry_date=card.expiry_date,
        bank_name=card.bank_name
    )
    db.add(new_card)
    db.commit()
    db.refresh(new_card)
    return new_card