import httpx
from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models
from pydantic import BaseModel
from typing import Optional

# Tạo bảng (Nếu chưa có)
Base.metadata.create_all(bind=engine)

app = FastAPI()

# --- DATABASE DEPENDENCY ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- INPUT MODELS (Các dữ liệu đầu vào) ---
class CheckoutRequest(BaseModel):
    address: str
    phone: str
    coupon_code: Optional[str] = None # Mã giảm giá (không bắt buộc)

class OrderStatusUpdate(BaseModel):
    status: str

# --- HELPER: GỌI USER SERVICE ĐỂ XÁC THỰC ---
async def verify_user(request: Request):
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Missing Token")
    
    try:
        # Gọi sang User Service (Port 8001)
        async with httpx.AsyncClient() as client:
            res = await client.get("http://user_service:8001/verify", headers={"Authorization": token})
            
            if res.status_code == 200:
                return res.json() # Trả về info user (id, role, branch_id...)
            else:
                raise HTTPException(status_code=401, detail="Invalid Token from User Service")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="User Service Unavailable")
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

# ==========================================
# API 1: CHECKOUT (TẠO ĐƠN HÀNG)
# ==========================================
@app.post("/checkout")
async def checkout(payload: CheckoutRequest, request: Request, db: Session = Depends(get_db)):
    # 1. Xác thực User
    user = await verify_user(request)
    user_id = user['id']
    token = request.headers.get("Authorization")
    headers = {"Authorization": token}

    # 2. Lấy items từ Cart Service
    async with httpx.AsyncClient() as client:
        try:
            cart_res = await client.get("http://cart_service:8005/cart", headers=headers)
            if cart_res.status_code != 200:
                raise HTTPException(status_code=400, detail="Lỗi kết nối Cart Service")
            cart_items = cart_res.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Cart Service Error: {e}")

    if not cart_items:
        raise HTTPException(status_code=400, detail="Giỏ hàng trống")

    # 3. Tính toán tiền (Gọi Restaurant Service để lấy giá chuẩn)
    branch_id = cart_items[0]['branch_id']
    final_items = []
    subtotal = 0 # Tổng tiền hàng (đã trừ khuyến mãi món ăn)

    async with httpx.AsyncClient() as client:
        # Lấy menu của quán đó để tra cứu
        food_res = await client.get(f"http://restaurant_service:8002/foods?branch_id={branch_id}")
        if food_res.status_code != 200:
             raise HTTPException(status_code=500, detail="Lỗi kết nối Restaurant Service")
        
        # Tạo map để tra cứu nhanh: {id: food_info}
        menu_map = {f['id']: f for f in food_res.json()}

        for item in cart_items:
            f_id = item['food_id']
            qty = item['quantity']
            
            food_info = menu_map.get(f_id)
            if food_info:
                # Tính giá sau giảm giá (Discount từng món)
                original_price = food_info['price']
                item_discount = food_info.get('discount', 0)
                final_item_price = original_price * (1 - item_discount/100)
                
                line_total = final_item_price * qty
                subtotal += line_total
                
                final_items.append({
                    "food_id": f_id,
                    "food_name": food_info['name'],
                    "price": final_item_price,
                    "quantity": qty
                })

    if not final_items:
        raise HTTPException(status_code=400, detail="Không tìm thấy thông tin món ăn hợp lệ")

    # 4. Xử lý Coupon (Nếu có)
    coupon_discount_amount = 0
    if payload.coupon_code:
        async with httpx.AsyncClient() as client:
            verify_url = "http://restaurant_service:8002/coupons/verify"
            try:
                cp_res = await client.get(verify_url, params={"code": payload.coupon_code, "branch_id": branch_id})
                
                if cp_res.status_code == 200:
                    coupon_data = cp_res.json()
                    percent = coupon_data['discount_percent']
                    # Tính tiền giảm
                    coupon_discount_amount = subtotal * (percent / 100)
                else:
                    raise HTTPException(status_code=400, detail="Mã giảm giá không hợp lệ")
            except httpx.RequestError:
                 raise HTTPException(status_code=500, detail="Lỗi kiểm tra Coupon")

    # Giá cuối cùng (Không âm)
    final_total_price = max(0, subtotal - coupon_discount_amount)

    # 5. Lưu đơn hàng vào DB
    new_order = models.Order(
        user_id=user_id,
        user_name=user.get('sub', 'Unknown'),
        branch_id=branch_id,
        total_price=final_total_price,
        status="PENDING_PAYMENT",       # Mặc định chờ thanh toán
        
        # Thông tin giao hàng
        delivery_address=payload.address,
        customer_phone=payload.phone,
        
        # Thông tin Coupon
        coupon_code=payload.coupon_code,
        discount_amount=coupon_discount_amount
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # 6. Lưu chi tiết đơn hàng
    for item in final_items:
        order_item = models.OrderItem(
            order_id=new_order.id,
            food_id=item['food_id'],
            food_name=item['food_name'],
            price=item['price'],
            quantity=item['quantity']
        )
        db.add(order_item)
    
    db.commit()

    # 7. Xóa giỏ hàng
    async with httpx.AsyncClient() as client:
        await client.delete("http://cart_service:8005/cart", headers=headers)

    return {
        "message": "Order created successfully", 
        "order_id": new_order.id, 
        "total": final_total_price,
        "status": "PENDING_PAYMENT"
    }

# ==========================================
# API 2: LẤY DANH SÁCH ĐƠN HÀNG
# ==========================================
@app.get("/orders")
async def get_orders(request: Request, db: Session = Depends(get_db)):
    user = await verify_user(request)
    
    # Seller: Chỉ thấy đơn quán mình
    if user['role'] == 'seller':
        branch_id = user.get('branch_id')
        if not branch_id: return [] 
        return db.query(models.Order).filter(models.Order.branch_id == branch_id).order_by(models.Order.id.desc()).all()
    
    # Buyer: Chỉ thấy đơn của mình
    else:
        return db.query(models.Order).filter(models.Order.user_id == user['id']).order_by(models.Order.id.desc()).all()

# ... (Giữ nguyên phần đầu file: import, helper, checkout...)
# Chỉ cần thay đổi API update_order_status ở gần cuối thôi.
# Để an toàn, đây là đoạn code bạn cần thay thế cho API đó:

@app.put("/orders/{order_id}/status")
async def update_order_status(order_id: int, payload: OrderStatusUpdate, request: Request, db: Session = Depends(get_db)):
    user = await verify_user(request)
    
    # Chỉ Seller (Owner hoặc Staff đều được)
    if user['role'] != 'seller':
        raise HTTPException(status_code=403, detail="Chỉ Seller mới được cập nhật")

    # Staff cũng cần có branch_id thì mới biết đang làm cho quán nào
    if not user.get('branch_id'):
        raise HTTPException(status_code=403, detail="Tài khoản này chưa được gán vào quán nào")

    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")
        
    if order.branch_id != user.get('branch_id'):
        raise HTTPException(status_code=403, detail="Đơn hàng này không thuộc quán của bạn")

    order.status = payload.status
    db.commit()
    
    return {"message": "Updated status", "status": payload.status}

# ... (Các API Confirm Payment, Cancel, Check Review giữ nguyên)
# ==========================================
# API 4: XÁC NHẬN THANH TOÁN (Internal - Payment Service gọi)
# ==========================================
@app.put("/orders/{order_id}/paid")
def confirm_payment(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Chỉ xác nhận khi đơn đang chờ thanh toán
    if order.status == "PENDING_PAYMENT":
        order.status = "WAITING_CONFIRM"
        db.commit()
        
    return {"status": order.status}

# ==========================================
# API 5: HỦY ĐƠN HÀNG (CHO BUYER)
# ==========================================
@app.put("/orders/{order_id}/cancel")
async def cancel_order(order_id: int, request: Request, db: Session = Depends(get_db)):
    user = await verify_user(request)
    
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order: raise HTTPException(404, "Not found")
    
    if order.user_id != user['id']: raise HTTPException(403, "Not your order")
    
    if order.status not in ["PENDING_PAYMENT", "WAITING_CONFIRM"]:
        raise HTTPException(400, "Không thể hủy đơn hàng đang xử lý")
    
    order.status = "CANCELLED"
    db.commit()
    return {"status": "CANCELLED", "message": "Đã hủy đơn hàng"}

# ==========================================
# API 6: CHECK QUYỀN REVIEW (Internal - Restaurant Service gọi)
# ==========================================
@app.get("/orders/{order_id}/check-review")
def check_review_permission(order_id: int, user_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    
    if not order:
        raise HTTPException(404, detail="Đơn hàng không tồn tại")
        
    if order.user_id != user_id:
        raise HTTPException(403, detail="Bạn không phải chủ đơn hàng này")
        
    if order.status != "COMPLETED":
        raise HTTPException(400, detail="Đơn hàng chưa hoàn tất, chưa thể đánh giá")
        
    return {
        "status": "ok", 
        "branch_id": order.branch_id
    }