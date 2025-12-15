import httpx
import asyncio
import os
from jose import jwt
from datetime import datetime, timedelta

# --- CẤU HÌNH ---
GATEWAY_URL = "http://localhost:8000"
SECRET_KEY = "supersecretkey123"
ALGORITHM = "HS256"
IMAGE_FOLDER = "demo_images"

# --- HÀM HỖ TRỢ ---
def create_headers(user_id, role="seller", branch_id=None, seller_mode="owner"):
    expire = datetime.utcnow() + timedelta(minutes=10)
    payload = {
        "sub": f"admin_seed_{user_id}",
        "id": user_id,
        "role": role,
        "branch_id": branch_id,
        "seller_mode": seller_mode,
        "exp": expire
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return {"Authorization": f"Bearer {token}"}

def ensure_dummy_image(filename):
    if not os.path.exists(IMAGE_FOLDER): os.makedirs(IMAGE_FOLDER)
    path = os.path.join(IMAGE_FOLDER, filename)
    if not os.path.exists(path):
        with open(path, "wb") as f: f.write(b"\x00" * 1024) # Tạo file rỗng
    return path

async def seed_data():
    print("🚀 ĐANG KHỞI TẠO DỮ LIỆU DEMO (NGUYÊN BẢN)...")
    STRONG_PASS = "Admin@123"
    branch_owners = {} 

    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # 1. TẠO CHI NHÁNH
        print("\n🏢 [1] TẠO CHI NHÁNH...")
        branches = [
            {"name": "CHI NHÁNH THAO DIEN", "address": "Q2", "phone": "0901"},
            {"name": "CHI NHÁNH Q10", "address": "Q10", "phone": "0902"},
        ]
        branch_ids = []
        for b in branches:
            try:
                res = await client.post(f"{GATEWAY_URL}/branches", json=b, headers=create_headers(1))
                if res.status_code == 200:
                    bid = res.json()["id"]
                    branch_ids.append(bid)
                    print(f"   ✅ Đã tạo: {b['name']} (ID: {bid})")
            except Exception as e: print(f"Lỗi tạo branch: {e}")

        if not branch_ids: return print("Lỗi: Không tạo được chi nhánh nào.")

        # 2. TẠO KHÁCH HÀNG (BUYER)
        print("\n👤 [2] TẠO KHÁCH HÀNG...")
        for i in range(1, 3):
            email = f"khach{i}@gmail.com"
            try:
                await client.post(f"{GATEWAY_URL}/register", json={
                    "email": email, "password": STRONG_PASS,
                    "name": f"Khách Hàng {i}", "role": "buyer",
                    "phone": f"091000000{i}", "address": "TP.HCM"
                })
                print(f"   👤 Đã tạo Buyer: {email}")
            except: pass

        # 3. TẠO CHỦ QUÁN (SELLER)
        print("\n👔 [3] TẠO CHỦ QUÁN...")
        for b_id in branch_ids:
            email = f"owner_cn{b_id}@gmail.com"
            try:
                res = await client.post(f"{GATEWAY_URL}/register", json={
                    "email": email, "password": STRONG_PASS, "name": f"Chủ CN {b_id}",
                    "role": "seller", "seller_mode": "owner", "phone": "0909090909", "address": "HCM"
                })
                
                if res.status_code == 200:
                    owner_id = res.json()["id"]
                else:
                    # Nếu đã tồn tại, login lấy ID
                    l_res = await client.post(f"{GATEWAY_URL}/login", json={"email": email, "password": STRONG_PASS})
                    owner_id = l_res.json()["id"]

                branch_owners[b_id] = owner_id
                
                # Cập nhật quán cho chủ
                await client.put(f"{GATEWAY_URL}/users/{owner_id}/branch", params={"branch_id": b_id})
                print(f"   👔 Owner: {email} -> Branch {b_id}")

            except Exception as e: print(f"Lỗi tạo owner: {e}")

        # 4. TẠO MÓN ĂN & COUPON
        print("\n🍛 [4] TẠO MÓN ĂN...")
        foods_data = [
            {"name": "Cơm Sườn", "price": 50000, "img": "food1.jpg"},
            {"name": "Bún Bò", "price": 60000, "img": "food2.jpg"},
            {"name": "Phở Bò", "price": 70000, "img": "food3.jpg"},
        ]
        
        for f in foods_data: ensure_dummy_image(f["img"])

        for b_id in branch_ids:
            owner_id = branch_owners.get(b_id)
            if not owner_id: continue

            # Dùng token của chính chủ quán đó để thêm món (Tránh lỗi 403)
            headers = create_headers(owner_id, branch_id=b_id, seller_mode="owner")

            for f in foods_data:
                try:
                    payload = {
                        "name": f"{f['name']} - CN{b_id}", 
                        "price": str(f["price"]),
                        "branch_id": str(b_id),
                        "discount": "0"
                    }
                    files = {"image": (f["img"], open(f"demo_images/{f['img']}", "rb"), "image/jpeg")}
                    
                    res = await client.post(f"{GATEWAY_URL}/foods", data=payload, files=files, headers=headers)
                    files["image"][1].close()
                    
                    if res.status_code == 200:
                        print(f"   ✅ Đã thêm: {payload['name']}")
                except Exception as e: print(f"Lỗi thêm món: {e}")

            # Tạo Coupon
            try:
                now = datetime.utcnow()
                coupon = {
                    "code": f"SALE{b_id}0",
                    "discount_percent": 10,
                    "start_date": str(now),
                    "end_date": str(now + timedelta(days=30)),
                    "branch_id": b_id,
                    "is_active": True
                }
                # Thử tạo coupon (nếu backend hỗ trợ)
                await client.post(f"{GATEWAY_URL}/coupons", json=coupon, headers=headers)
            except: pass

    print("\n-------------------------------------")
    print("🎉 KHỞI TẠO XONG!")
    print("👉 Khách hàng: khach1@gmail.com / Admin@123")
    print("👉 Chủ quán 1: owner_cn1@gmail.com / Admin@123")
    print("-------------------------------------")

if __name__ == "__main__":
    asyncio.run(seed_data())