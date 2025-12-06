import httpx
import asyncio
from jose import jwt
from datetime import datetime, timedelta

# --- CẤU HÌNH ---
GATEWAY_URL = "http://localhost:8000" 
SECRET_KEY = "chuoi_bi_mat_sieu_kho_doan_cua_ban" # Phải khớp với User Service
ALGORITHM = "HS256"

# Hàm tạo Token giả lập (Quan trọng: Phải chứa đủ thông tin để vượt qua Auth)
def create_headers(user_id, role="seller", branch_id=None, seller_mode="owner"):
    expire = datetime.utcnow() + timedelta(minutes=10)
    to_encode = {
        "sub": f"admin_seed_{user_id}",
        "id": user_id,
        "role": role,
        "branch_id": branch_id,      # Quan trọng: Để biết thêm món vào quán nào
        "seller_mode": seller_mode,  # Quan trọng: Để vượt qua check Owner
        "exp": expire
    }
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return {"Authorization": f"Bearer {token}"} # Thêm chữ Bearer cho chuẩn

async def seed_data():
    print("🚀 Đang khởi tạo dữ liệu mẫu (Version Phân Quyền)...")
    print(f"🎯 Target: {GATEWAY_URL}")

    # ==========================================
    # 1. TẠO CHI NHÁNH (BRANCHES)
    # ==========================================
    branches_data = [
        {"name": "Cơm Tấm Quận 1 (Luxury)", "address": "123 Lê Lợi, Q.1", "phone": "0909111"},
        {"name": "Cơm Tấm Thủ Đức (Bình Dân)", "address": "Khu A Làng Đại Học", "phone": "0909222"},
        {"name": "Bếp Mẹ Nấu (Bình Thạnh)", "address": "456 Xô Viết Nghệ Tĩnh", "phone": "0909333"}
    ]
    
    # Map index -> real_id
    branch_map = {} 

    async with httpx.AsyncClient() as client:
        print("\n--- 1. TẠO CHI NHÁNH ---")
        for i, b in enumerate(branches_data):
            try:
                # Dùng token bừa để gọi API (vì API tạo branch hiện tại chưa check gắt)
                headers = create_headers(999) 
                res = await client.post(f"{GATEWAY_URL}/branches", json=b, headers=headers)
                
                if res.status_code == 200:
                    data = res.json()
                    b_id = data['id']
                    print(f"✅ Đã tạo: {data['name']} (ID: {b_id})")
                    branch_map[i] = b_id
                else:
                    print(f"⚠️ Lỗi tạo chi nhánh: {res.text}")
            except Exception as e:
                print(f"❌ Kết nối thất bại: {e}")
                return

        if not branch_map:
            print("🛑 Không tạo được chi nhánh nào. Dừng.")
            return

        # ==========================================
        # 2. TẠO MÓN ĂN & COUPON (DÙNG TOKEN OWNER)
        # ==========================================
        
        foods_data = [
            # QUÁN 1 (Index 0)
            {"name": "Cơm Tấm Sườn Bì", "price": 65000, "discount": 20, "branch_idx": 0},
            {"name": "Phở Bò Wagyu", "price": 120000, "discount": 0, "branch_idx": 0},
            
            # QUÁN 2 (Index 1)
            {"name": "Cơm Tấm Sinh Viên", "price": 35000, "discount": 0, "branch_idx": 1},
            {"name": "Bún Đậu Mắm Tôm", "price": 30000, "discount": 10, "branch_idx": 1},
            
            # QUÁN 3 (Index 2)
            {"name": "Bánh Mì Chảo", "price": 40000, "discount": 15, "branch_idx": 2},
        ]

        print("\n--- 2. TẠO MÓN ĂN & COUPON ---")
        for f in foods_data:
            real_branch_id = branch_map[f['branch_idx']]
            
            # QUAN TRỌNG: Tạo header với tư cách là OWNER của quán này
            # ID 999 chỉ là giả, quan trọng là branch_id và seller_mode
            headers = create_headers(user_id=999, role="seller", branch_id=real_branch_id, seller_mode="owner")
            
            # Tạo món
            payload_food = {
                "name": f['name'],
                "price": f['price'],
                "discount": f['discount']
                # Không cần gửi branch_id trong body, server tự lấy từ token
            }
            try:
                res = await client.post(f"{GATEWAY_URL}/foods", json=payload_food, headers=headers)
                if res.status_code == 200:
                    print(f"🍛 Thêm món '{f['name']}' vào Branch {real_branch_id}")
                else:
                    print(f"❌ Lỗi thêm món: {res.text}")
            except Exception as e:
                print(f"❌ Lỗi mạng: {e}")

        # Tạo Coupon cho mỗi quán
        for idx, real_id in branch_map.items():
            headers = create_headers(user_id=999, role="seller", branch_id=real_id, seller_mode="owner")
            coupon_payload = {"code": "GIAM20", "discount_percent": 20}
            try:
                await client.post(f"{GATEWAY_URL}/coupons", json=coupon_payload, headers=headers)
                print(f"🎟️  Tạo Coupon 'GIAM20' cho Branch {real_id}")
            except: pass

        # ==========================================
        # 3. TẠO USER (OWNER, STAFF, BUYER)
        # ==========================================
        print("\n--- 3. TẠO TÀI KHOẢN (USER SERVICE) ---")
        
        # Tạo Owner và Staff cho từng quán
        for idx, real_id in branch_map.items():
            # OWNER
            owner_email = f"owner_quan{real_id}@gmail.com"
            await client.post(f"{GATEWAY_URL}/register", json={
                "email": owner_email, "password": "123", "name": f"Chủ Quán {real_id}",
                "role": "seller", "seller_mode": "owner", "phone": "0909000111", "address": "Tại quán"
            })
            print(f"👤 Tạo Owner: {owner_email}")

            # STAFF
            staff_email = f"staff_quan{real_id}@gmail.com"
            await client.post(f"{GATEWAY_URL}/register", json={
                "email": staff_email, "password": "123", "name": f"Nhân viên Quán {real_id}",
                "role": "seller", "seller_mode": "staff", "phone": "0909000222", "address": "Tại quán"
            })
            print(f"👤 Tạo Staff: {staff_email}")

        # BUYER
        await client.post(f"{GATEWAY_URL}/register", json={
            "email": "khach_vip@gmail.com", "password": "123", "name": "Khách Hàng Vip",
            "role": "buyer", "phone": "0912345678", "address": "Nhà riêng Quận 1"
        })
        print(f"👤 Tạo Buyer: khach_vip@gmail.com")

        print("\n⚠️  LƯU Ý QUAN TRỌNG CUỐI CÙNG:")
        print("👉 Code Register chưa tự gán 'managed_branch_id'.")
        print("👉 Hãy vào Adminer -> Bảng 'users' -> UPDATE cột 'managed_branch_id' cho các Owner và Staff tương ứng với ID quán (1, 2, 3...) thì họ mới thấy đơn hàng!")

    print("\n✅ --- HOÀN TẤT DỮ LIỆU MẪU ---")

if __name__ == "__main__":
    asyncio.run(seed_data())