import streamlit as st
import httpx
import time
import pandas as pd

# --- CẤU HÌNH API ---
USER_URL = "http://127.0.0.1:8001"
RESTAURANT_URL = "http://127.0.0.1:8002"
ORDER_URL = "http://127.0.0.1:8003"
CART_URL = "http://127.0.0.1:8005"

# --- KHỞI TẠO SESSION ---
if 'token' not in st.session_state: st.session_state['token'] = None
if 'user_role' not in st.session_state: st.session_state['user_role'] = ""
if 'user_name' not in st.session_state: st.session_state['user_name'] = ""
if 'cart' not in st.session_state: st.session_state['cart'] = []

st.set_page_config(page_title="Micro Food App", page_icon="🍔", layout="wide")

# --- CSS ---
st.markdown("""
<style>
    .food-card { border: 1px solid #ddd; border-radius: 10px; padding: 15px; margin-bottom: 10px; background: white; }
    .price-tag { color: #e44d26; font-weight: bold; font-size: 1.1rem; }
    .role-badge { background-color: #f0f2f6; padding: 5px 10px; border-radius: 5px; font-weight: bold; }
    /* Ẩn nút tăng giảm mặc định của input number để giao diện sạch hơn */
    input[type=number]::-webkit-inner-spin-button, input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
</style>
""", unsafe_allow_html=True)

def get_food_image(food_name):
    name = food_name.lower()
    if "phở" in name: return "https://upload.wikimedia.org/wikipedia/commons/thumb/5/53/Pho_Bo_-_Beef_Noodle_Soup.jpg/640px-Pho_Bo_-_Beef_Noodle_Soup.jpg"
    if "bún" in name: return "https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/Bun_Cha_Hanoi.jpg/640px-Bun_Cha_Hanoi.jpg"
    if "trà sữa" in name: return "https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Milk_tea_with_pearls.jpg/640px-Milk_tea_with_pearls.jpg"
    if "cơm" in name: return "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/C%C6%A1m_T%E1%BA%A5m_B%C3%A0_Ghi%E1%BB%81n_-_Broken_Rice_with_Pork_Chop_%286869406244%29.jpg/640px-C%C6%A1m_T%E1%BA%A5m_B%C3%A0_Ghi%E1%BB%81n_-_Broken_Rice_with_Pork_Chop_%286869406244%29.jpg"
    return "https://placehold.co/600x400?text=Food"

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.title("Micro Food 🚀")
    if st.session_state['token'] is None:
        st.subheader("🔐 Đăng Nhập")
        email = st.text_input("Email", value="khacha@gmail.com") 
        password = st.text_input("Mật khẩu", type="password", value="123")
        if st.button("Đăng nhập", type="primary", use_container_width=True):
            try:
                res = httpx.post(f"{USER_URL}/login", json={"email": email, "password": password})
                if res.status_code == 200:
                    data = res.json()
                    st.session_state['token'] = data['access_token']
                    st.session_state['user_role'] = data['role']
                    st.session_state['user_name'] = email.split('@')[0]
                    st.success("Thành công!")
                    st.rerun()
                else: st.error(f"Lỗi: {res.json().get('detail')}")
            except Exception as e: st.error(f"Lỗi kết nối: {e}")
    else:
        st.success(f"Xin chào, **{st.session_state['user_name']}**")
        st.markdown(f"<span class='role-badge'>Role: {st.session_state['user_role'].upper()}</span>", unsafe_allow_html=True)
        st.write("")
        if st.button("Đăng xuất", use_container_width=True):
            st.session_state['token'] = None
            st.rerun()

# ==========================================
# GIAO DIỆN CHÍNH
# ==========================================
if st.session_state['token']:
    headers = {"Authorization": st.session_state['token']}
    
    # ---------------- SELLER ----------------
    if st.session_state['user_role'] == 'seller':
        st.header("👨‍🍳 Kênh Người Bán")
        tab_create, tab_my_foods, tab_manage_orders = st.tabs(["➕ Thêm Món", "📋 Thực Đơn", "📦 Quản Lý Đơn"])
        
        with tab_create:
            with st.form("add_food"):
                name = st.text_input("Tên món")
                price = st.number_input("Giá", min_value=0, step=1000)
                if st.form_submit_button("Lưu"):
                    try:
                        res = httpx.post(f"{RESTAURANT_URL}/foods", json={"name": name, "price": price}, headers=headers)
                        if res.status_code == 200: st.success(f"Đã thêm: {name}"); time.sleep(1); st.rerun()
                        else: st.error("Lỗi thêm món")
                    except: st.error("Lỗi kết nối")

        with tab_my_foods:
            try:
                my_foods = httpx.get(f"{RESTAURANT_URL}/seller/foods", headers=headers).json()
                if my_foods: st.table([{"ID": f['id'], "Tên": f['name'], "Giá": f"{f['price']:,}"} for f in my_foods])
                else: st.info("Chưa có món nào")
            except: st.error("Lỗi tải danh sách")

        with tab_manage_orders:
            st.subheader("Bảng Theo Dõi Đơn Hàng")
            if st.button("🔄 Cập nhật"): st.rerun()
            try:
                res = httpx.get(f"{ORDER_URL}/orders", headers=headers)
                if res.status_code == 200:
                    orders = res.json()
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown("### 🟠 Chờ Duyệt")
                        for o in [x for x in orders if x['status']=='PENDING']:
                            with st.container(border=True):
                                st.write(f"**#{o['id']}** - {o['user_name']}")
                                st.write(f"💰 {o['total_price']:,} đ")
                                if st.button("🔥 Nấu", key=f"c_{o['id']}", use_container_width=True):
                                    httpx.put(f"{ORDER_URL}/orders/{o['id']}/status", json={"status":"COOKING"}, headers=headers); st.rerun()
                    with c2:
                        st.markdown("### 🔵 Đang Nấu")
                        for o in [x for x in orders if x['status']=='COOKING']:
                            with st.container(border=True):
                                st.write(f"**#{o['id']}** - {o['user_name']}")
                                if st.button("🚚 Giao", key=f"s_{o['id']}", use_container_width=True):
                                    httpx.put(f"{ORDER_URL}/orders/{o['id']}/status", json={"status":"DELIVERING"}, headers=headers); st.rerun()
                    with c3:
                        st.markdown("### 🟣 Đang Giao")
                        for o in [x for x in orders if x['status']=='DELIVERING']:
                            with st.container(border=True):
                                st.write(f"**#{o['id']}** - {o['user_name']}")
                                if st.button("✅ Xong", key=f"d_{o['id']}", use_container_width=True):
                                    httpx.put(f"{ORDER_URL}/orders/{o['id']}/status", json={"status":"COMPLETED"}, headers=headers); st.rerun()
                else: st.error("Lỗi tải đơn")
            except: st.error("Lỗi kết nối")

    # ---------------- BUYER (Sửa đổi chính ở đây) ----------------
    elif st.session_state['user_role'] == 'buyer':
        st.header("😋 Trang Đặt Món")
        
        try:
            all_foods = httpx.get(f"{RESTAURANT_URL}/foods").json()
            food_map = {f['id']: f for f in all_foods}
        except: 
            all_foods = []
            food_map = {}

        tab_menu, tab_cart, tab_history = st.tabs(["🍔 Thực Đơn", "🛒 Giỏ Hàng", "📜 Lịch Sử Đơn"])

        # TAB 1: MENU - ĐƠN GIẢN (Chỉ nút thêm)
        with tab_menu:
            c_search, c_filter = st.columns([3, 1])
            query = c_search.text_input("🔍 Tìm kiếm món ăn...", placeholder="Nhập tên món...")
            with st.expander("💰 Lọc theo giá"):
                c1, c2 = st.columns(2)
                min_p = c1.number_input("Min", 0, step=5000)
                max_p = c2.number_input("Max (0=All)", 0, step=5000)

            params = {}
            if query: params['q'] = query
            if min_p: params['min_price'] = min_p
            if max_p: params['max_price'] = max_p
            
            try:
                display_foods = httpx.get(f"{RESTAURANT_URL}/foods", params=params).json()
            except: display_foods = []

            if display_foods:
                cols = st.columns(3)
                for i, food in enumerate(display_foods):
                    with cols[i % 3]:
                        with st.container(border=True):
                            st.image(get_food_image(food['name']), use_container_width=True)
                            st.markdown(f"**{food['name']}**")
                            st.markdown(f"<span class='price-tag'>{food['price']:,} đ</span>", unsafe_allow_html=True)
                            
                            # NÚT THÊM ĐƠN GIẢN (Mặc định thêm 1)
                            if st.button("Thêm vào giỏ ➕", key=f"add_{food['id']}", use_container_width=True):
                                try:
                                    res = httpx.post(f"{CART_URL}/cart", json={"food_id": food['id'], "quantity": 1}, headers=headers)
                                    if res.status_code == 200: st.toast(f"Đã thêm {food['name']}", icon="😋")
                                    else: st.error("Lỗi thêm giỏ")
                                except: st.error("Lỗi kết nối Cart")
            else: st.info("Không tìm thấy món nào.")

        # TAB 2: GIỎ HÀNG - GIAO DIỆN NÚT BẤM (FIX LỖI)
        with tab_cart:
            try:
                cart_res = httpx.get(f"{CART_URL}/cart", headers=headers)
                cart_items = cart_res.json() if cart_res.status_code == 200 else []
                
                if cart_items:
                    total = 0
                    for item in cart_items:
                        info = food_map.get(item['food_id'])
                        if info:
                            # Tính toán
                            sub = info['price'] * item['quantity']
                            total += sub
                            
                            # --- GIAO DIỆN DÒNG SẢN PHẨM ---
                            # Chia cột: Tên (3) | Chỉnh Số Lượng (3) | Thành tiền (2) | Xóa (1)
                            c1, c2, c3, c4 = st.columns([3, 3, 2, 1])
                            
                            # Cột 1: Tên món
                            c1.markdown(f"**{info['name']}**")
                            c1.caption(f"{info['price']:,} đ")
                            
                            # Cột 2: Nút Tăng/Giảm (FIX LỖI TẠI ĐÂY)
                            with c2:
                                cm1, cm2, cm3 = st.columns([1, 1, 1])
                                
                                # Nút Giảm ➖
                                if cm1.button("➖", key=f"dec_{item['food_id']}"):
                                    new_qty = item['quantity'] - 1
                                    if new_qty > 0:
                                        httpx.put(f"{CART_URL}/cart", json={"food_id": item['food_id'], "quantity": new_qty}, headers=headers)
                                    else:
                                        # Nếu giảm về 0 thì xóa luôn
                                        httpx.put(f"{CART_URL}/cart", json={"food_id": item['food_id'], "quantity": 0}, headers=headers)
                                    st.rerun()

                                # Hiển thị số lượng ở giữa
                                cm2.markdown(f"<div style='text-align: center; line-height: 2.3; font-weight: bold;'>{item['quantity']}</div>", unsafe_allow_html=True)

                                # Nút Tăng ➕
                                if cm3.button("➕", key=f"inc_{item['food_id']}"):
                                    new_qty = item['quantity'] + 1
                                    httpx.put(f"{CART_URL}/cart", json={"food_id": item['food_id'], "quantity": new_qty}, headers=headers)
                                    st.rerun()

                            # Cột 3: Thành tiền
                            c3.markdown(f"**{sub:,} đ**")
                            
                            # Cột 4: Nút Xóa hẳn
                            if c4.button("🗑️", key=f"del_{item['food_id']}"):
                                httpx.put(f"{CART_URL}/cart", json={"food_id": item['food_id'], "quantity": 0}, headers=headers)
                                st.rerun()
                            
                            st.divider()
                    
                    # Phần Tổng kết & Thanh toán (Giữ nguyên)
                    st.markdown(f"### Tổng: :red[{total:,} đ]")
                    if st.button("✅ THANH TOÁN", type="primary", use_container_width=True):
                        try:
                            res = httpx.post(f"{ORDER_URL}/checkout", headers=headers)
                            if res.status_code == 200:
                                st.success(f"Thành công! Mã: {res.json()['order_id']}")
                                st.balloons()
                                httpx.delete(f"{CART_URL}/cart", headers=headers)
                                time.sleep(2); st.rerun()
                            else: st.error(f"Lỗi: {res.text}")
                        except: st.error("Lỗi Order Service")
                    
                    if st.button("🗑️ Xóa hết"):
                        httpx.delete(f"{CART_URL}/cart", headers=headers); st.rerun()
                else: st.info("Giỏ hàng trống.")
            except Exception as e: st.error(f"Lỗi tải giỏ hàng: {e}")

        with tab_history:
            if st.button("🔄 Tải lại"):
                try:
                    orders = httpx.get(f"{ORDER_URL}/orders", headers=headers).json()
                    if orders:
                        df = pd.DataFrame(orders)
                        st.dataframe(df[['id', 'total_price', 'status', 'user_name']], use_container_width=True)
                    else: st.info("Chưa có đơn hàng.")
                except: st.error("Lỗi kết nối")

    else: st.error("Role không hỗ trợ")
else: st.info("👈 Vui lòng đăng nhập.")