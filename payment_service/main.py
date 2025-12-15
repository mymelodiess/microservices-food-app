import json
import asyncio # <--- QUAN TRỌNG
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

Base.metadata.create_all(bind=engine)

# --- CẤU HÌNH KAFKA ---
KAFKA_TOPIC = "order_paid"
KAFKA_BOOTSTRAP_SERVERS = "kafka:9092"
producer = None

# --- [FIX QUAN TRỌNG] CƠ CHẾ KHỞI ĐỘNG AN TOÀN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global producer
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    
    # Thử kết nối tối đa 10 lần, mỗi lần cách nhau 5 giây
    max_retries = 10
    for i in range(max_retries):
        try:
            print(f"🚀 Payment Service: Đang kết nối Kafka (Lần {i+1}/{max_retries})...")
            await producer.start()
            print("✅ Kafka Producer: Đã kết nối thành công!")
            break # Kết nối được thì thoát vòng lặp
        except Exception as e:
            print(f"⚠️ Chưa kết nối được Kafka: {e}")
            print("⏳ Đang chờ Kafka khởi động... (5s)")
            await asyncio.sleep(5) 
            
            if i == max_retries - 1:
                print("❌ BỎ CUỘC: Không thể kết nối Kafka. Service sẽ chạy mà không có Kafka.")
                # Vẫn cho app chạy tiếp để không bị lỗi 503, nhưng tính năng Kafka sẽ tịt
    
    yield
    
    # Dừng producer khi tắt app
    try:
        if producer: await producer.stop()
    except: pass

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

# --- API ---
@app.post("/pay")
async def process_payment(payload: PaymentRequest, db: Session = Depends(get_db)):
    print(f"💰 Payment Service: Xử lý đơn #{payload.order_id}")

    trans_id = f"PAY_{uuid.uuid4().hex[:8].upper()}"
    new_payment = models.Payment(
        order_id=payload.order_id,
        amount=payload.amount,
        transaction_id=trans_id,
        status="SUCCESS"
    )
    db.add(new_payment)
    db.commit()
    
    message = {
        "event": "ORDER_PAID",
        "order_id": payload.order_id,
        "amount": payload.amount,
        "transaction_id": trans_id
    }
    
    # Gửi Kafka (Chỉ gửi nếu Producer đã kết nối OK)
    try:
        if producer:
            await producer.send_and_wait(KAFKA_TOPIC, json.dumps(message).encode("utf-8"))
            print(f"📨 Kafka Sent: {message}")
        else:
            print("⚠️ Cảnh báo: Kafka chưa sẵn sàng, không gửi được tin nhắn.")
    except Exception as e:
        print(f"❌ Lỗi gửi Kafka: {e}")

    return {
        "message": "Thanh toán thành công",
        "transaction_id": trans_id,
        "order_id": payload.order_id,
        "status": "SUCCESS"
    }

@app.get("/payment-methods", response_model=List[CardResponse])
def get_my_cards(db: Session = Depends(get_db)):
    return db.query(models.PaymentMethod).all()

@app.post("/payment-methods", response_model=CardResponse)
def add_card(card: CardCreate, db: Session = Depends(get_db)):
    new_card = models.PaymentMethod(
        user_id=1, 
        card_number=card.card_number,
        card_holder=card.card_holder,
        expiry_date=card.expiry_date,
        bank_name=card.bank_name
    )
    db.add(new_card)
    db.commit()
    db.refresh(new_card)
    return new_card