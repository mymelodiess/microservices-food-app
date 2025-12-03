import httpx
import asyncio
from jose import jwt
from datetime import datetime, timedelta

# --- CẤU HÌNH ---
# Hãy đảm bảo port đúng với docker-compose của bạn
RESTAURANT_URL = "http://localhost:8002" 
USER_URL = "http://localhost:8001" 

SECRET_KEY = "chuoi_bi_mat_sieu_kho_doan_cua_ban" 
ALGORITHM = "HS256"

# Tạo Token giả để có quyền Seller thêm món
def create_fake_token():
    expire = datetime.utcnow() + timedelta(minutes=10)
    to_encode = {"sub": "admin_seed", "role": "seller", "id": 999, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def seed_data():
    token = create_fake_token()
    headers = {"Authorization": token} 
    
    print("🚀 Đang khởi tạo dữ liệu mẫu cho hệ thống Multi-Branch...")

    # ==========================================
    # PHẦN 1: TẠO CHI NHÁNH (RESTAURANT SERVICE)
    # ==========================================
    branches_data = [
        {"name": "Food App Quận 1", "address": "123 Lê Lợi, Q.1", "phone": "0909111222"},
        {"name": "Food App Thủ Đức", "address": "Khu A Làng Đại Học", "phone": "0909333444"},
        {"name": "Food App Bình Thạnh", "address": "456 Xô Viết Nghệ Tĩnh", "phone": "0909555666"}
    ]
    
    branch_map = {} # Lưu lại ID để dùng cho bước sau

    async with httpx.AsyncClient() as client:
        print("\n--- 1. TẠO CHI NHÁNH ---")
        for b in branches_data:
            try:
                res = await client.post(f"{RESTAURANT_URL}/branches", json=b)
                if res.status_code == 200:
                    data = res.json()
                    b_id = data['id']
                    b_name = data['name']
                    print(f"✅ Đã tạo: {b_name} (ID: {b_id})")
                    branch_map[b_id] = b_name
                else:
                    print(f"⚠️ Chi nhánh '{b['name']}' có thể đã tồn tại hoặc lỗi: {res.status_code}")
            except Exception as e:
                print(f"❌ Lỗi kết nối Restaurant Service: {e}")
                return

        if not branch_map:
            print("🛑 Không có chi nhánh nào được tạo. Dừng chương trình.")
            return

        # ==========================================
        # PHẦN 2: TẠO MÓN ĂN (RESTAURANT SERVICE)
        # ==========================================
        branch_ids = list(branch_map.keys())
        
        foods_data = [
            # Chi nhánh 1 (Quận 1) - Đắt tiền
            {"name": "Cơm Tấm Sườn Bì Chả (Vip)", "price": 65000, "branch_id": branch_ids[0]},
            {"name": "Phở Bò Wagyu", "price": 120000, "branch_id": branch_ids[0]},
            
            # Chi nhánh 2 (Thủ Đức) - Sinh viên (Nếu có)
            {"name": "Cơm Tấm Sinh Viên", "price": 25000, "branch_id": branch_ids[1] if len(branch_ids) > 1 else branch_ids[0]},
            {"name": "Bún Đậu Mắm Tôm", "price": 30000, "branch_id": branch_ids[1] if len(branch_ids) > 1 else branch_ids[0]},
        ]
        
        # Thêm món cho CN3 nếu có
        if len(branch_ids) > 2:
             foods_data.append({"name": "Bánh Mì Chảo", "price": 35000, "branch_id": branch_ids[2]})

        print("\n--- 2. TẠO MÓN ĂN ---")
        for f in foods_data:
            try:
                res = await client.post(f"{RESTAURANT_URL}/foods", json=f, headers=headers)
                if res.status_code == 200:
                    print(f"🍛 Đã thêm món: {f['name']} -> Chi nhánh ID {f['branch_id']}")
                else:
                    print(f"❌ Lỗi thêm món {f['name']}: {res.text}")
            except:
                pass

        # ==========================================
        # PHẦN 3: TẠO USER SELLER (USER SERVICE)
        # ==========================================
        print("\n--- 3. TẠO TÀI KHOẢN SELLER (Tự động) ---")
        print("⚠️ Lưu ý: Script này sẽ tạo user. Bạn cần vào Adminer để gán managed_branch_id thủ công nếu API register chưa hỗ trợ.")
        
        for b_id, b_name in branch_map.items():
            # Email: seller_1@gmail.com, seller_2@gmail.com
            email = f"seller_{b_id}@gmail.com"
            password = "123"
            
            payload = {
                "name": f"Quản lý {b_name}",
                "email": email,
                "password": password,
                "role": "seller",
                "phone": "0909000000",
                "address": "Tại cửa hàng"
            }
            
            try:
                res = await client.post(f"{USER_URL}/register", json=payload)
                if res.status_code == 200:
                    print(f"👤 Đã tạo Seller: {email} (Pass: 123)")
                    print(f"   👉 HÃY VÀO ADMINER -> Bảng 'users' -> Tìm '{email}' -> Sửa cột 'managed_branch_id' thành: {b_id}")
                elif res.status_code == 400 and "tồn tại" in res.text:
                     print(f"ℹ️ User {email} đã tồn tại.")
                else:
                    print(f"❌ Lỗi tạo user {email}: {res.text}")
            except Exception as e:
                print(f"❌ Lỗi kết nối User Service: {e}")

    print("\n✅ --- HOÀN TẤT ---")

if __name__ == "__main__":
    asyncio.run(seed_data())