from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import List, Optional
import os

SECRET_KEY = os.getenv("SECRET_KEY", "chuoi_mac_dinh_phong_khi_quen_set_env")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

Base.metadata.create_all(bind=engine)

app = FastAPI()
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
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- MODELS ---
class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: str = "buyer"
    phone: str = None
    address: str = None
    seller_mode: str = None # Mới

class LoginRequest(BaseModel):
    email: str
    password: str

class AddressCreate(BaseModel):
    title: str
    address: str
    phone: str

class AddressResponse(AddressCreate):
    id: int
    user_id: int
    class Config:
        orm_mode = True

# --- API AUTH ---
@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user: raise HTTPException(400, "Email exists")
    
    hashed_pw = get_password_hash(user.password)
    
    # Logic mặc định: Nếu là Seller mà ko chọn mode -> Mặc định là Owner
    final_seller_mode = None
    if user.role == 'seller':
        final_seller_mode = user.seller_mode if user.seller_mode else 'owner'

    new_user = models.User(
        email=user.email, 
        hashed_password=hashed_pw,
        name=user.name,
        role=user.role,
        phone=user.phone,
        address=user.address,
        seller_mode=final_seller_mode
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"message": "User created", "id": new_user.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))

@app.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(401, "Incorrect email/password")
    
    token_data = {
        "sub": user.email, 
        "id": user.id, 
        "role": user.role,
        "branch_id": user.managed_branch_id,
        "seller_mode": user.seller_mode # Thêm vào Token
    }
    access_token = create_access_token(token_data)
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "role": user.role,
        "branch_id": user.managed_branch_id,
        "seller_mode": user.seller_mode
    }

@app.get("/verify")
def verify_token(authorization: str = Header(None)):
    if not authorization: raise HTTPException(401, "Missing Token")
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError: raise HTTPException(401, "Invalid Token")

# --- API ADDRESS ---
def get_current_user_id(authorization: str):
    if not authorization: return None
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("id")
    except: return None

@app.post("/users/addresses", response_model=AddressResponse)
def add_address(addr: AddressCreate, authorization: str = Header(None), db: Session = Depends(get_db)):
    user_id = get_current_user_id(authorization)
    if not user_id: raise HTTPException(401, "Invalid Token")
    new_addr = models.UserAddress(user_id=user_id, title=addr.title, address=addr.address, phone=addr.phone)
    db.add(new_addr)
    db.commit()
    db.refresh(new_addr)
    return new_addr

@app.get("/users/addresses", response_model=List[AddressResponse])
def get_my_addresses(authorization: str = Header(None), db: Session = Depends(get_db)):
    user_id = get_current_user_id(authorization)
    if not user_id: raise HTTPException(401, "Invalid Token")
    return db.query(models.UserAddress).filter(models.UserAddress.user_id == user_id).all()