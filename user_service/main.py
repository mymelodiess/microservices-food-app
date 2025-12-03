from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

import models
from database import SessionLocal, engine

# --- CẤU HÌNH ---
SECRET_KEY = "chuoi_bi_mat_sieu_kho_doan_cua_ban"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Tạo bảng (Lưu ý: Nếu bảng cũ chưa xóa, lệnh này sẽ không tự thêm cột mới đâu)
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- SCHEMAS ---
class UserRegister(BaseModel):
    name: str          # Map vào full_name
    email: str
    password: str
    role: str = "buyer"
    # Các trường optional lúc đăng ký (có thể cập nhật sau)
    phone: Optional[str] = None
    address: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    user_id: int
    branch_id: Optional[int] = None # Trả về cho Frontend biết luôn

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    role: str
    class Config:
        from_attributes = True

# --- API ---

@app.post("/register", response_model=UserResponse)
def register(user: UserRegister, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email đã tồn tại")
    
    hashed_pw = get_password_hash(user.password)
    
    new_user = models.User(
        email=user.email,
        hashed_password=hashed_pw,
        full_name=user.name,   # Lưu tên
        phone_number=user.phone,
        address=user.address,
        role=user.role
    )
    
    # Logic nhỏ: Nếu đăng ký là Seller, mặc định chưa có chi nhánh (sẽ update trong Adminer sau)
    # hoặc bạn có thể cho phép gửi managed_branch_id từ client nếu muốn test nhanh.
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=Token)
def login(user_login: UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_login.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Sai email hoặc mật khẩu")
    
    if not verify_password(user_login.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Sai email hoặc mật khẩu")
    
    # --- TẠO TOKEN CHỨA THÔNG TIN CHI NHÁNH ---
    token_payload = {
        "sub": user.email,
        "id": user.id,
        "role": user.role,
        # QUAN TRỌNG: Nhét ID chi nhánh vào token
        "branch_id": user.managed_branch_id 
    }
    
    access_token = create_access_token(data=token_payload)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "user_id": user.id,
        "branch_id": user.managed_branch_id
    }