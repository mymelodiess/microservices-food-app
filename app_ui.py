import streamlit as st
import httpx
import time
import pandas as pd

# --- CẤU HÌNH API (Đảm bảo port đúng với máy bạn) ---
USER_URL = "http://localhost:8001"
RESTAURANT_URL = "http://localhost:8002"
ORDER_URL = "http://localhost:8003"
CART_URL = "http://localhost:8005"

# --- KHỞI TẠO SESSION ---
if 'token' not in st.session_state: st.session_state['token'] = None
if 'user_role' not in st.session_state: st.session_state['user_role'] = ""
if 'user_name' not in st.session_state: st.session_state['user_name'] = ""
if 'branch_id' not in st.session_state: st.session_state['branch_id'] = None # ID chi nhánh của Seller
if 'cart' not in st.session_state: st.session_state['cart'] = []

st.set_page_config(page_title="Micro Food App", page_icon="🍔", layout="wide")

# --- CSS TÙY CHỈNH ---
st.markdown("""
<style>
    .food-card { border: 1px solid #ddd; border-radius: 10px; padding: 15px; margin-bottom: 10px; background: white; }
    .price-tag { color: #e44d26; font-weight: bold; font-size: 1.1rem; }
    .role-badge { background-color: #f0f2f6; padding: 5px 10px; border-radius: 5px; font-weight: bold; }
    input[type=number]::-webkit-inner-spin-button, input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
</style>
""", unsafe_allow_html=True)

def get_food_image(food_name):
    name = food_name.lower()
    if "phở" in name: return "https://upload.wikimedia.org/wikipedia/commons/thumb/5/53/Pho_Bo_-_Beef_Noodle_Soup.jpg/640px-Pho_Bo_-_Beef_Noodle_Soup.jpg"
    if "bún" in name: return "https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/Bun_Cha_Hanoi.jpg/640px-Bun_Cha_Hanoi.jpg"
    if "trà sữa" in name: return "https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Milk_tea_with_pearls.jpg/640px-Milk_tea_with_pearls.jpg"
    if "cơm" in name: return "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/C%C6%A1m_T%E1%BA%A5m_B%C3%A0_Ghi%E1%BB%81n_-_Broken_Rice_with_Pork_Chop_%286869406244%29.jpg/640px-C%C6%A1m_T%E1%BA%A5m_B%C3%A0_Ghi%E1%BB%81n_-_Broken_Rice_with_Pork_Chop_%286869406244%29.jpg"
    if "bánh mì" in name: return "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Banh_mi_thit_nuong.jpg/640px-Banh_mi_thit_nuong.jpg"
    return "https://placehold.co/600x400?text=Food"

# ==========================================
# SIDEBAR: ĐĂNG NHẬP / ĐĂNG KÝ
# ==========================================
with st.sidebar:
    st.title("Micro Food 🚀")
    
    # TRẠNG THÁI: CHƯA ĐĂNG NHẬP
    if st.session_state['token'] is None:
        tab_login, tab_register = st.tabs(["🔐 Đăng Nhập", "📝 Đăng Ký"])
        
        # --- TAB ĐĂNG NHẬP ---
        with tab_login:
            email_login = st.text_input("Email Login", value="seller_1@gmail.com") 
            password_login = st.text_input("Mật khẩu Login", type="password", value="123")
            if st.button("Đăng nhập", type="primary", use_container_width=True):
                try:
                    res = httpx.post(f"{USER_URL}/login", json={"email": email_login, "password": password_login})
                    if res.status_code == 200:
                        data = res.json()
                        st.session_state['token'] = data['access_token']
                        st.session_state['user_role'] = data['role']
                        st.session_state['user_name'] = email_login.split('@')[0]
                        # QUAN TRỌNG: Lưu ID chi nhánh nếu là Seller
                        st.session_state['branch_id'] = data.get('branch_id')
                        
                        st.success("Thành công!")
                        time.sleep(0.5)
                        st.rerun()
                    else: st.error(f"Lỗi: {res.json().get('detail')}")
                except Exception as e: st.error(f"Lỗi kết nối: {e}")

        # --- TAB ĐĂNG KÝ ---
        with tab_register:
            with st.form("reg_form"):
                new_name = st.text_input("Họ và tên")
                new_email = st.text_input("Email")
                new_pass = st.text_input("Mật khẩu", type="password")
                confirm_pass = st.text_input("Nhập lại", type="password")
                
                # Mặc định là Buyer. Nếu muốn tạo Seller, hãy dùng script init_data.py hoặc tạo qua Adminer
                role = "buyer" 

                if st.form_submit_button("Đăng ký ngay"):
                    if new_pass != confirm_pass:
                        st.error("Mật khẩu không khớp")
                    else:
                        try:
                            payload = {"name": new_name, "email": new_email, "password": new_pass, "role": role}
                            res = httpx.post(f"{USER_URL}/register", json=payload)
                            if res.status_code == 200: st.success("Đăng ký thành công! Hãy đăng nhập.")
                            else: st.error(f"Lỗi: {res.text}")
                        except Exception as e: st.error(f"Lỗi kết nối: {e}")

    # TRẠNG THÁI: ĐÃ ĐĂNG NHẬP
    else:
        st.success(f"Xin chào, **{st.session_state['user_name']}**")
        st.markdown(f"<span class='role-badge'>Role: {st.session_state['user_role'].upper()}</span>", unsafe_allow_html=True)
        if st.session_state['branch_id']:
            st.info(f"📍 Quản lý Chi nhánh ID: {st.session_state['branch_id']}")
            
        st.write("")
        if st.button("Đăng xuất", use_container_width=True):
            st.session_state['token'] = None
            st.session_state['branch_id'] = None
            st.session_state['cart'] = []
            st.rerun()

# ==========================================
# GIAO DIỆN CHÍNH
# ==========================================
if st.session_state['token']:
    headers = {"Authorization": st.session_state['token']}
    
    # ----------------------------------------
    # [1] GIAO DIỆN NGƯỜI BÁN (SELLER)
    # ----------------------------------------
    if st.session_state['user_role'] == 'seller':
        st.header("👨‍🍳 Kênh Người Bán")
        
        # Kiểm tra xem Seller đã được gán chi nhánh chưa
        if not st.session_state['branch_id']:
            st.warning("⚠️ Tài khoản của bạn chưa được gán vào Chi nhánh nào. Vui lòng liên hệ Admin (hoặc sửa trong Database)!")
            st.stop()
            
        tab_create, tab_my_foods, tab_manage_orders = st.tabs(["➕ Thêm Món", "📋 Thực Đơn Của Tôi", "📦 Quản Lý Đơn"])
        
        with tab_create:
            with st.form("add_food"):
                st.write(f"Đang thêm món vào Chi nhánh ID: **{st.session_state['branch_id']}**")
                name = st.text_input("Tên món")
                price = st.number_input("Giá", min_value=0, step=1000)
                
                if st.form_submit_button("Lưu món ăn"):
                    try:
                        # Tự động lấy branch_id từ session
                        payload = {
                            "name": name, 
                            "price": price, 
                            "branch_id": st.session_state['branch_id']
                        }
                        res = httpx.post(f"{RESTAURANT_URL}/foods", json=payload, headers=headers)
                        if res.status_code == 200: 
                            st.success(f"Đã thêm: {name}")
                            time.sleep(1); st.rerun()
                        else: st.error(f"Lỗi: {res.text}")
                    except Exception as e: st.error(f"Lỗi kết nối: {e}")

        # --- TÌM TAB THỰC ĐƠN VÀ THAY THẾ BẰNG CODE DƯỚI ĐÂY ---
        with tab_my_foods:
            try:
                # Lấy danh sách món của chi nhánh hiện tại
                res = httpx.get(f"{RESTAURANT_URL}/foods", params={"branch_id": st.session_state['branch_id']})
                
                if res.status_code == 200:
                    my_foods = res.json()
                    
                    if my_foods:
                        st.success(f"Chi nhánh đang có {len(my_foods)} món")
                        
                        # Tạo tiêu đề bảng
                        h1, h2, h3 = st.columns([3, 1, 1])
                        h1.markdown("**Tên món**")
                        h2.markdown("**Giá bán**")
                        h3.markdown("**Hành động**")
                        st.divider()
                        
                        # Duyệt qua từng món để hiển thị
                        for f in my_foods:
                            c1, c2, c3 = st.columns([3, 1, 1])
                            
                            # Cột 1: Tên + Ảnh (nếu muốn)
                            c1.write(f"🍛 {f['name']}")
                            
                            # Cột 2: Giá
                            c2.write(f"{f['price']:,} đ")
                            
                            # Cột 3: Nút Xóa
                            # Key=... để Streamlit phân biệt nút của các món khác nhau
                            if c3.button("🗑️ Xóa", key=f"del_{f['id']}"):
                                with st.spinner("Đang xóa..."):
                                    # Gọi API DELETE
                                    del_res = httpx.delete(f"{RESTAURANT_URL}/foods/{f['id']}", headers=headers)
                                    
                                    if del_res.status_code == 200:
                                        st.success("Đã xóa!")
                                        time.sleep(0.5) # Đợi xíu cho đẹp
                                        st.rerun()      # Tải lại trang
                                    else:
                                        st.error(f"Lỗi: {del_res.json().get('detail')}")
                            
                            st.divider() # Kẻ đường gạch ngang ngăn cách
                    else:
                        st.info("Chi nhánh chưa có món nào. Hãy thêm món mới!")
                else:
                    st.error("Lỗi kết nối Server")
            except Exception as e:
                st.error(f"Lỗi: {e}")

        with tab_manage_orders:
            st.subheader("Đơn hàng cần xử lý")
            if st.button("🔄 Cập nhật"): st.rerun()
            # Phần này cần cập nhật Order Service để lọc theo branch_id sau
            # Tạm thời vẫn hiển thị đơn như cũ
            try:
                res = httpx.get(f"{ORDER_URL}/orders", headers=headers)
                if res.status_code == 200:
                    orders = res.json()
                    for o in orders:
                        with st.expander(f"Đơn #{o['id']} - {o['status']} ({o['total_price']:,} đ)"):
                            st.write(f"Khách: {o['user_name']}")
                            c1, c2, c3 = st.columns(3)
                            if c1.button("Nấu", key=f"c_{o['id']}"): httpx.put(f"{ORDER_URL}/orders/{o['id']}/status", json={"status":"COOKING"}, headers=headers); st.rerun()
                            if c2.button("Giao", key=f"s_{o['id']}"): httpx.put(f"{ORDER_URL}/orders/{o['id']}/status", json={"status":"DELIVERING"}, headers=headers); st.rerun()
                            if c3.button("Xong", key=f"d_{o['id']}"): httpx.put(f"{ORDER_URL}/orders/{o['id']}/status", json={"status":"COMPLETED"}, headers=headers); st.rerun()
                else: st.warning("Chưa tải được đơn hàng (Check Order Service)")
            except: st.error("Lỗi kết nối Order Service")

    # ----------------------------------------
    # [2] GIAO DIỆN NGƯỜI MUA (BUYER)
    # ----------------------------------------
    elif st.session_state['user_role'] == 'buyer':
        st.header("😋 Trang Đặt Món")
        
        # --- BƯỚC 1: CHỌN CHI NHÁNH ---
        try:
            branches_res = httpx.get(f"{RESTAURANT_URL}/branches")
            branches = branches_res.json() if branches_res.status_code == 200 else []
        except: branches = []

        if not branches:
            st.error("⚠️ Hệ thống chưa có chi nhánh nào hoạt động.")
            st.stop()

        branch_map = {b['id']: b['name'] for b in branches}
        
        # Selectbox chọn chi nhánh
        col_br, col_none = st.columns([1, 2])
        with col_br:
            selected_branch_id = st.selectbox(
                "📍 Chọn chi nhánh gần bạn:", 
                options=list(branch_map.keys()), 
                format_func=lambda x: branch_map[x]
            )
        
        st.divider()

        # --- BƯỚC 2: HIỆN MENU CỦA CHI NHÁNH ĐÓ ---
        try:
            # Gọi API lấy món ăn theo branch_id
            all_foods = httpx.get(f"{RESTAURANT_URL}/foods", params={"branch_id": selected_branch_id}).json()
            food_map = {f['id']: f for f in all_foods}
        except: 
            all_foods = []
            food_map = {}

        tab_menu, tab_cart, tab_history = st.tabs(["🍔 Thực Đơn", "🛒 Giỏ Hàng", "📜 Lịch Sử Đơn"])

        # MENU
        with tab_menu:
            if all_foods:
                cols = st.columns(3)
                for i, food in enumerate(all_foods):
                    with cols[i % 3]:
                        with st.container(border=True):
                            st.image(get_food_image(food['name']), use_container_width=True)
                            st.markdown(f"**{food['name']}**")
                            st.markdown(f"<span class='price-tag'>{food['price']:,} đ</span>", unsafe_allow_html=True)
                            
                            if st.button("Thêm ➕", key=f"add_{food['id']}", use_container_width=True):
                                try:
                                    res = httpx.post(f"{CART_URL}/cart", json={"food_id": food['id'], "quantity": 1}, headers=headers)
                                    if res.status_code == 200: st.toast(f"Đã thêm {food['name']}", icon="😋")
                                    else: st.error("Lỗi thêm giỏ")
                                except: st.error("Lỗi kết nối Cart")
            else:
                st.info(f"Chi nhánh {branch_map[selected_branch_id]} hiện chưa cập nhật thực đơn.")

        # GIỎ HÀNG
        with tab_cart:
            try:
                cart_res = httpx.get(f"{CART_URL}/cart", headers=headers)
                cart_items = cart_res.json() if cart_res.status_code == 200 else []
                
                if cart_items:
                    total = 0
                    for item in cart_items:
                        # Lưu ý: food_map chỉ chứa món của chi nhánh đang chọn. 
                        # Nếu trong giỏ có món của chi nhánh khác, tên có thể bị lỗi None.
                        # Ta nên gọi API lấy chi tiết món nếu cần, nhưng tạm thời lấy từ map.
                        info = food_map.get(item['food_id']) 
                        
                        if info:
                            sub = info['price'] * item['quantity']
                            total += sub
                            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                            c1.markdown(f"**{info['name']}**")
                            with c2:
                                cm1, cm2, cm3 = st.columns([1,1,1])
                                if cm1.button("➖", key=f"dec_{item['food_id']}"):
                                    httpx.put(f"{CART_URL}/cart", json={"food_id": item['food_id'], "quantity": item['quantity']-1}, headers=headers); st.rerun()
                                cm2.write(f"**{item['quantity']}**")
                                if cm3.button("➕", key=f"inc_{item['food_id']}"):
                                    httpx.put(f"{CART_URL}/cart", json={"food_id": item['food_id'], "quantity": item['quantity']+1}, headers=headers); st.rerun()
                            c3.write(f"{sub:,} đ")
                            if c4.button("🗑️", key=f"del_{item['food_id']}"):
                                httpx.put(f"{CART_URL}/cart", json={"food_id": item['food_id'], "quantity": 0}, headers=headers); st.rerun()
                            st.divider()
                        else:
                            st.warning(f"Món ID {item['food_id']} thuộc chi nhánh khác hoặc không tồn tại.")
                    
                    st.markdown(f"### Tổng: :red[{total:,} đ]")
                    if st.button("Thanh Toán", type="primary", use_container_width=True):
                        try:
                            res = httpx.post(f"{ORDER_URL}/checkout", headers=headers)
                            if res.status_code == 200:
                                st.success(f"Đặt hàng thành công! Mã đơn: {res.json()['order_id']}")
                                st.balloons()
                                httpx.delete(f"{CART_URL}/cart", headers=headers)
                                time.sleep(2); st.rerun()
                            else: st.error(f"Lỗi: {res.text}")
                        except: st.error("Lỗi Order Service")
                    
                    if st.button("Xóa hết giỏ hàng"):
                        httpx.delete(f"{CART_URL}/cart", headers=headers); st.rerun()
                else: st.info("Giỏ hàng trống.")
            except Exception as e: st.error(f"Lỗi tải giỏ hàng: {e}")

        # LỊCH SỬ
        with tab_history:
            if st.button("Tải lại lịch sử"):
                try:
                    orders = httpx.get(f"{ORDER_URL}/orders", headers=headers).json()
                    if orders:
                        df = pd.DataFrame(orders)
                        st.dataframe(df[['id', 'total_price', 'status']], use_container_width=True)
                    else: st.info("Chưa có đơn hàng nào.")
                except: st.error("Lỗi kết nối")
    else:
        st.error("Role không xác định")
else:
    st.info("👈 Vui lòng đăng nhập hoặc đăng ký ở menu bên trái.")