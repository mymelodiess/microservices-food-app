from fastapi import FastAPI, HTTPException, Depends
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

class FoodResponse(BaseModel):
    id: int
    name: str
    price: float
    class Config:
        from_attributes = True

# API tạo món ăn (để bạn nhập liệu test)
class FoodCreate(BaseModel):
    name: str
    price: float

@app.post("/foods", response_model=FoodResponse)
def create_food(food: FoodCreate, db: Session = Depends(get_db)):
    new_food = models.Food(name=food.name, price=food.price)
    db.add(new_food)
    db.commit()
    db.refresh(new_food)
    return new_food

@app.get("/foods/{food_id}", response_model=FoodResponse)
def get_food(food_id: int, db: Session = Depends(get_db)):
    food = db.query(models.Food).filter(models.Food.id == food_id).first()
    if food is None:
        raise HTTPException(status_code=404, detail="Food not found")
    return food