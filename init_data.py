import httpx

# Cấu hình
USER_URL = "http://localhost:8001"
RESTAURANT_URL = "http://localhost:8002"

def init_data():
    print("⏳ Đang khởi tạo dữ liệu mẫu...")

    # 1. Đăng ký CHỦ QUÁN (Seller)
    seller_data = {"name": "Chu Quan", "email": "seller@gmail.com", "password": "123", "role": "seller"}
    try:
        res = httpx.post(f"{USER_URL}/register", json=seller_data)
        if res.status_code == 200:
            print("✅ Đã tạo tài khoản Seller: seller@gmail.com / 123")
        else:
            print(f"⚠️ Seller có thể đã tồn tại: {res.text}")
    except:
        print("❌ Lỗi kết nối User Service (8001). Bạn đã bật Docker chưa?")
        return

    # 2. Đăng ký KHÁCH HÀNG (Buyer)
    buyer_data = {"name": "Khach A", "email": "khacha@gmail.com", "password": "123", "role": "buyer"}
    try:
        res = httpx.post(f"{USER_URL}/register", json=buyer_data)
        if res.status_code == 200:
            print("✅ Đã tạo tài khoản Buyer: khacha@gmail.com / 123")
    except:
        pass

    # 3. Đăng nhập Seller để lấy Token tạo món
    login_res = httpx.post(f"{USER_URL}/login", json={"email": "seller@gmail.com", "password": "123"})
    token = login_res.json().get("access_token")
    
    # 4. Tạo Món ăn (Nếu chưa có)
    headers = {"Authorization": token}
    foods = [
        {"name": "Phở Bò Tái", "price": 50000},
        {"name": "Bún Chả Hà Nội", "price": 45000},
        {"name": "Trà Sữa Trân Châu", "price": 25000}
    ]
    
    print("\n⏳ Đang tạo thực đơn...")
    for food in foods:
        try:
            res = httpx.post(f"{RESTAURANT_URL}/foods", json=food, headers=headers)
            if res.status_code == 200:
                print(f"   - Đã thêm món: {food['name']}")
        except:
            print(f"❌ Lỗi tạo món {food['name']}")

    print("\n🎉 HOÀN TẤT! Bây giờ bạn có thể vào Web đăng nhập được rồi.")

if __name__ == "__main__":
    init_data()