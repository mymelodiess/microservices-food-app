import httpx
from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models
from pydantic import BaseModel
import uuid

# Tạo bảng
Base.metadata.create_all(bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- INPUT MODEL ---
class PaymentRequest(BaseModel):
    order_id: int
    amount: float
    # Có thể thêm: payment_method (momo, vnpay...)

# ==========================================
# API THANH TOÁN (GIẢ LẬP)
# ==========================================
@app.post("/pay")
async def process_payment(payload: PaymentRequest, db: Session = Depends(get_db)):
    # 1. (Giả lập) Kiểm tra số dư hoặc gọi cổng thanh toán thật
    # Ở đây mặc định là thành công luôn
    
    # 2. Tạo mã giao dịch duy nhất
    trans_id = f"PAY_{uuid.uuid4().hex[:8].upper()}"
    
    # 3. Lưu lịch sử thanh toán vào DB Payment
    new_payment = models.Payment(
        order_id=payload.order_id,
        amount=payload.amount,
        transaction_id=trans_id,
        status="SUCCESS"
    )
    db.add(new_payment)
    db.commit()
    
    # 4. GỌI SANG ORDER SERVICE ĐỂ CONFIRM
    # (Đây là bước quan trọng nhất)
    order_service_url = f"http://order_service:8003/orders/{payload.order_id}/paid"
    
    async with httpx.AsyncClient() as client:
        try:
            # Gọi API nội bộ của Order Service
            res = await client.put(order_service_url)
            
            if res.status_code != 200:
                # Nếu Order Service lỗi -> Cần rollback hoặc đánh dấu payment failed (để đơn giản ta báo lỗi luôn)
                raise HTTPException(status_code=500, detail="Thanh toán thành công nhưng lỗi cập nhật đơn hàng")
                
        except Exception as e:
             raise HTTPException(status_code=500, detail=f"Lỗi kết nối Order Service: {str(e)}")

    return {
        "message": "Thanh toán thành công",
        "transaction_id": trans_id,
        "order_id": payload.order_id,
        "status": "SUCCESS"
    }

@app.get("/payments")
def get_history(db: Session = Depends(get_db)):
    return db.query(models.Payment).all()