import httpx
from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models
from pydantic import BaseModel
from typing import List

Base.metadata.create_all(bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def verify_user(request: Request):
    token = request.headers.get("Authorization")
    if not token: raise HTTPException(401, "Missing Token")
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get("http://user_service:8001/verify", headers={"Authorization": token})
            if res.status_code != 200: raise HTTPException(401, "Invalid Token")
            return res.json()
    except Exception as e: raise HTTPException(401, str(e))

# --- API REVIEW ---
class FoodRatingInput(BaseModel):
    food_id: int
    score: int

class ReviewInput(BaseModel):
    order_id: int
    rating_general: int
    comment: str
    items: List[FoodRatingInput]

@app.post("/reviews")
async def create_review(payload: ReviewInput, request: Request, db: Session = Depends(get_db)):
    user = await verify_user(request)
    async with httpx.AsyncClient() as client:
        check_url = f"http://order_service:8003/orders/{payload.order_id}/check-review"
        try:
            res = await client.get(check_url, params={"user_id": user['id']})
            if res.status_code != 200: raise HTTPException(400, res.json().get("detail", "Error"))
            branch_id = res.json().get('branch_id')
        except Exception as e: raise HTTPException(500, str(e))

    try:
        new_review = models.OrderReview(user_id=user['id'], user_name=user.get('sub'), order_id=payload.order_id, branch_id=branch_id, rating_general=payload.rating_general, comment=payload.comment)
        db.add(new_review)
        db.flush()
        for item in payload.items:
            db.add(models.FoodRating(review_id=new_review.id, food_id=item.food_id, score=item.score))
        db.commit()
        return {"message": "Success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))

# --- API QUẢN LÝ (CÓ PHÂN QUYỀN RBAC) ---

@app.post("/coupons")
async def create_coupon(coupon: dict, request: Request, db: Session = Depends(get_db)):
    user = await verify_user(request)
    # RBAC: Chỉ Seller và phải là Owner
    if user['role'] != 'seller': raise HTTPException(403, "Only Seller")
    if user.get('seller_mode') != 'owner': raise HTTPException(403, "Only Owner can create coupons")

    seller_branch_id = user.get('branch_id')
    if not seller_branch_id: raise HTTPException(400, "No branch")
    
    exist = db.query(models.Coupon).filter(models.Coupon.code == coupon['code'].upper(), models.Coupon.branch_id == seller_branch_id).first()
    if exist: raise HTTPException(400, "Exists")

    new_coupon = models.Coupon(code=coupon['code'].upper(), discount_percent=coupon['discount_percent'], branch_id=seller_branch_id)
    db.add(new_coupon)
    db.commit()
    db.refresh(new_coupon)
    return new_coupon

@app.get("/coupons/verify")
def verify_coupon(code: str, branch_id: int, db: Session = Depends(get_db)):
    coupon = db.query(models.Coupon).filter(models.Coupon.code == code.upper(), models.Coupon.branch_id == branch_id, models.Coupon.is_active == True).first()
    if not coupon: raise HTTPException(404, "Invalid")
    return {"valid": True, "discount_percent": coupon.discount_percent, "code": coupon.code}

@app.get("/foods/search")
def search_foods(q: str = None, db: Session = Depends(get_db)):
    query = db.query(models.Food)
    if q: query = query.filter(models.Food.name.contains(q))
    all_foods = query.all()
    grouped = {}
    for f in all_foods:
        final_price = f.price * (1 - f.discount / 100)
        if f.name not in grouped: grouped[f.name] = {"name": f.name, "min_price": final_price, "max_price": final_price, "branch_count": 1}
        else:
            if final_price < grouped[f.name]["min_price"]: grouped[f.name]["min_price"] = final_price
            if final_price > grouped[f.name]["max_price"]: grouped[f.name]["max_price"] = final_price
            grouped[f.name]["branch_count"] += 1
    return list(grouped.values())

@app.get("/foods/options")
def get_food_options(name: str, db: Session = Depends(get_db)):
    foods = db.query(models.Food).filter(models.Food.name == name).all()
    results = []
    for f in foods:
        branch = db.query(models.Branch).filter(models.Branch.id == f.branch_id).first()
        final_price = f.price * (1 - f.discount / 100)
        results.append({"food_id": f.id, "branch_id": f.branch_id, "branch_name": branch.name if branch else "Unknown", "original_price": f.price, "discount": f.discount, "final_price": final_price})
    results.sort(key=lambda x: x['final_price'])
    return results

@app.post("/foods")
async def create_food(food: dict, request: Request, db: Session = Depends(get_db)):
    user = await verify_user(request)
    # RBAC: Chỉ Owner mới được tạo món
    if user['role'] != 'seller': raise HTTPException(403, "Only Seller")
    if user.get('seller_mode') != 'owner': raise HTTPException(403, "Only Owner can add food")
    
    new_food = models.Food(name=food['name'], price=food['price'], branch_id=user.get('branch_id'), discount=food.get('discount', 0))
    db.add(new_food)
    db.commit()
    db.refresh(new_food)
    return new_food

@app.get("/foods") 
def read_foods(branch_id: int = None, db: Session = Depends(get_db)):
    if branch_id: return db.query(models.Food).filter(models.Food.branch_id == branch_id).all()
    return db.query(models.Food).all()

@app.delete("/foods/{food_id}")
async def delete_food(food_id: int, request: Request, db: Session = Depends(get_db)):
    user = await verify_user(request)
    # RBAC: Chỉ Owner mới được xóa món
    if user.get('seller_mode') != 'owner': raise HTTPException(403, "Only Owner can delete food")
    
    item = db.query(models.Food).filter(models.Food.id == food_id).first()
    if not item: raise HTTPException(404, "Not found")
    if item.branch_id != user.get('branch_id'): raise HTTPException(403, "Not your food")
    db.delete(item)
    db.commit()
    return {"message": "Deleted"}

@app.post("/branches")
def create_branch(branch: dict, db: Session = Depends(get_db)):
    new_b = models.Branch(name=branch['name'], address=branch.get('address'), phone=branch.get('phone'))
    db.add(new_b)
    db.commit()
    db.refresh(new_b) # Lấy ID
    return new_b

@app.get("/branches")
def get_branches(db: Session = Depends(get_db)):
    return db.query(models.Branch).all()