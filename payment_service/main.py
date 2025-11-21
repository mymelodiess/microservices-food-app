from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import models
from database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class PaymentRequest(BaseModel):
    order_id: int
    amount: float

@app.post("/payments")
def process_payment(payment: PaymentRequest, db: Session = Depends(get_db)):
    new_payment = models.Payment(
        order_id=payment.order_id,
        amount=payment.amount,
        status="SUCCESS"
    )
    db.add(new_payment)
    db.commit()
    db.refresh(new_payment)
    return {"message": "Thanh toán được ghi nhận", "payment_id": new_payment.id}

@app.get("/payments")
def get_payments(db: Session = Depends(get_db)):
    return db.query(models.Payment).all()