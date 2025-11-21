from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import models
from database import SessionLocal, engine

# Tạo bảng trong DB (nếu chưa có)
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Hàm phụ thuộc để lấy kết nối DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Model Pydantic (Dữ liệu đầu vào/ra API)
class UserCreate(BaseModel):
    name: str
    email: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    
    class Config:
        from_attributes = True # Cho phép đọc dữ liệu từ ORM

# --- CÁC API ---

# 1. Tạo User mới
@app.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # Kiểm tra email trùng
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email đã tồn tại")
    
    # Tạo user mới
    new_user = models.User(name=user.name, email=user.email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# 2. Lấy User theo ID
@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)