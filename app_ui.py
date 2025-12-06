import streamlit as st
import httpx
import time
import pandas as pd

# --- CẤU HÌNH API ---
GATEWAY_URL = "http://localhost:8000"

# --- KHỞI TẠO SESSION ---
if 'token' not in st.session_state: st.session_state['token'] = None
if 'user_role' not in st.session_state: st.session_state['user_role'] = ""
if 'user_name' not in st.session_state: st.session_state['user_name'] = ""
if 'branch_id' not in st.session_state: st.session_state['branch_id'] = None

st.set_page_config(page_title="Micro Food App", page_icon="🍔", layout="wide")

# --- CSS TÙY CHỈNH ---
st.markdown("""
<style>
    .food-card { border: 1px solid #ddd; border-radius: 10px; padding: 15px; margin-bottom: 10px; background: white; }
    .price-tag { color: #e44d26; font-weight: bold; font-size: 1.1rem; }
    .old-price { text-decoration: line-through; color: #888; font-size: 0.9rem; margin-right: 5px; }
    .discount-badge { background-color: #ff4b4b; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; }
    .role-badge { background-color: #f0f2f6; padding: 5px 10px; border-radius: 5px; font-weight: bold; }
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
# SIDEBAR: LOGIN / REGISTER
# ==========================================
with st.sidebar:
    st.title("Micro Food 🚀")
    if st.session_state['token'] is None:
        tab_login, tab_register = st.tabs(["🔐 Login", "📝 Register"])
        
        # --- LOGIN ---
        with tab_login:
            email = st.text_input("Email", value="seller_1@gmail.com")
            pwd = st.text_input("Pass", type="password", value="123")
            if st.button("Đăng nhập"):
                try:
                    res = httpx.post(f"{GATEWAY_URL}/login", json={"email": email, "password": pwd})
                    if res.status_code == 200:
                        data = res.json()
                        st.session_state['token'] = data['access_token']
                        st.session_state['user_role'] = data['role']
                        st.session_state['user_name'] = email.split('@')[0]
                        st.session_state['branch_id'] = data.get('branch_id')
                        st.rerun()
                    else: st.error(res.text)
                except Exception as e: st.error(f"Err: {e}")
        
        # --- REGISTER (ĐÃ KHÔI PHỤC) ---
        with tab_register:
            with st.form("reg_form"):
                st.write("Tạo tài khoản Buyer mới")
                new_name = st.text_input("Họ tên")
                new_email = st.text_input("Email Đăng Ký")
                new_pass = st.text_input("Mật khẩu", type="password")
                confirm_pass = st.text_input("Nhập lại mật khẩu", type="password")
                
                if st.form_submit_button("Đăng ký ngay"):
                    if new_pass != confirm_pass:
                        st.error("Mật khẩu không khớp!")
                    else:
                        try:
                            # Mặc định role là Buyer
                            payload = {"name": new_name, "email": new_email, "password": new_pass, "role": "buyer"}
                            res = httpx.post(f"{GATEWAY_URL}/register", json=payload)
                            if res.status_code == 200:
                                st.success("Đăng ký thành công! Hãy chuyển sang Tab Login.")
                            else:
                                st.error(f"Lỗi: {res.text}")
                        except Exception as e:
                            st.error(f"Lỗi Gateway: {e}")

    else:
        st.success(f"Hi, {st.session_state['user_name']}")
        st.markdown(f"Role: **{st.session_state['user_role'].upper()}**")
        if st.button("Logout"):
            st.session_state['token'] = None; st.rerun()

# ==========================================
# MAIN APP
# ==========================================
if st.session_state['token']:
    # Thêm tiền tố Bearer cho chuẩn giao thức
    headers = {"Authorization": f"Bearer {st.session_state['token']}"}

    # --- SELLER ---
    if st.session_state['user_role'] == 'seller':
        st.header("👨‍🍳 Kênh Người Bán")
        
        # Check xem có Branch ID chưa
        if not st.session_state['branch_id']:
            st.warning("⚠️ User này là Seller nhưng chưa được gán vào Chi nhánh nào (Database).")
            st.stop()

        tabs = st.tabs(["Thêm Món", "Thực Đơn", "Đơn Hàng"])
        
        with tabs[0]: # Thêm Món
            with st.form("add"):
                st.write(f"Thêm món vào Chi nhánh ID: {st.session_state['branch_id']}")
                name = st.text_input("Tên món")
                price = st.number_input("Giá gốc", step=1000)
                discount = st.number_input("Giảm giá (%)", min_value=0, max_value=100, value=0)
                if st.form_submit_button("Lưu"):
                    payload = {
                        "name": name, "price": price, 
                        "branch_id": st.session_state['branch_id'],
                        "discount": discount
                    }
                    try:
                        res = httpx.post(f"{GATEWAY_URL}/foods", json=payload, headers=headers)
                        if res.status_code == 200:
                            st.success("Đã thêm!"); time.sleep(1); st.rerun()
                        else: st.error(f"Lỗi: {res.text}")
                    except Exception as e: st.error(f"Kết nối lỗi: {e}")
        
        with tabs[1]: # Thực Đơn
            try:
                res = httpx.get(f"{GATEWAY_URL}/foods", params={"branch_id": st.session_state['branch_id']})
                if res.status_code == 200:
                    for f in res.json():
                        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                        c1.write(f"**{f['name']}**")
                        c2.write(f"{f['price']:,}đ")
                        c3.write(f"-{f['discount']}%")
                        if c4.button("Xóa", key=f"d_{f['id']}"):
                            httpx.delete(f"{GATEWAY_URL}/foods/{f['id']}", headers=headers)
                            st.rerun()
                else: st.info("Chưa có món ăn nào.")
            except: st.error("Không tải được thực đơn.")

        with tabs[2]: # Đơn hàng (Cũ - Chưa nâng cấp)
            st.info("Chức năng quản lý đơn hàng sẽ được nâng cấp ở Bước 4.")

    # --- BUYER (Logic Mới) ---
    elif st.session_state['user_role'] == 'buyer':
        st.header("😋 Bạn muốn ăn gì hôm nay?")
        
        tab_home, tab_cart = st.tabs(["🏠 Trang Chủ", "🛒 Giỏ Hàng"])

        # 1. TRANG CHỦ (TÌM KIẾM & GỘP NHÓM)
        with tab_home:
            # Gọi API Search mới
            try:
                res = httpx.get(f"{GATEWAY_URL}/foods/search")
                foods = res.json() if res.status_code == 200 else []
            except: foods = []

            if foods:
                cols = st.columns(3)
                for i, f in enumerate(foods):
                    with cols[i % 3]:
                        with st.container(border=True):
                            st.image(get_food_image(f['name']), use_container_width=True)
                            st.subheader(f['name'])
                            
                            # Hiển thị khoảng giá
                            if f['min_price'] == f['max_price']:
                                st.write(f"💰 **{int(f['min_price']):,} đ**")
                            else:
                                st.write(f"💰 **{int(f['min_price']):,} đ - {int(f['max_price']):,} đ**")
                            
                            st.caption(f"Đang bán tại {f['branch_count']} chi nhánh")
                            
                            # Nút xem chi tiết
                            if st.button("Xem nơi bán", key=f"v_{f['name']}"):
                                st.session_state['viewing_food'] = f['name']

            # --- MODAL/EXPANDER: HIỆN DANH SÁCH QUÁN ---
            if 'viewing_food' in st.session_state:
                st.divider()
                st.markdown(f"### 🏪 Các quán bán: :orange[{st.session_state['viewing_food']}]")
                
                # Gọi API lấy options
                try:
                    opt_res = httpx.get(f"{GATEWAY_URL}/foods/options", params={"name": st.session_state['viewing_food']})
                    options = opt_res.json()
                    
                    for opt in options:
                        c1, c2, c3 = st.columns([2, 2, 1])
                        c1.markdown(f"**{opt['branch_name']}**")
                        
                        # Logic hiển thị giá giảm
                        with c2:
                            if opt['discount'] > 0:
                                st.markdown(f"""
                                    <span class='old-price'>{int(opt['original_price']):,}đ</span>
                                    <span class='price-tag'>{int(opt['final_price']):,}đ</span>
                                    <span class='discount-badge'>-{opt['discount']}%</span>
                                """, unsafe_allow_html=True)
                            else:
                                st.markdown(f"**{int(opt['final_price']):,} đ**")
                        
                        if c3.button("Thêm ➕", key=f"add_c_{opt['food_id']}"):
                            # Thêm vào giỏ
                            # --- UPDATE: Gửi kèm branch_id ---
                            cart_res = httpx.post(f"{GATEWAY_URL}/cart", 
                                                json={
                                                    "food_id": opt['food_id'], 
                                                    "quantity": 1, 
                                                    "branch_id": opt['branch_id'] # <--- QUAN TRỌNG
                                                }, 
                                                headers=headers)
                            if cart_res.status_code == 200:
                                st.toast("Đã thêm vào giỏ!", icon="✅")
                            else:
                                st.error("Lỗi: " + cart_res.text)

                    if st.button("Đóng danh sách"):
                        del st.session_state['viewing_food']
                        st.rerun()
                except Exception as e: st.error(f"Lỗi tải options: {e}")

        # 2. GIỎ HÀNG (ĐÃ NÂNG CẤP)
        with tab_cart:
            try:
                # 1. Lấy dữ liệu giỏ hàng từ Cart Service
                cart_res = httpx.get(f"{GATEWAY_URL}/cart", headers=headers)
                
                if cart_res.status_code == 200:
                    cart_items = cart_res.json()
                    
                    if not cart_items:
                        st.info("🛒 Giỏ hàng của bạn đang trống. Hãy ra Trang chủ chọn món nhé!")
                    else:
                        # 2. Lấy thông tin chi tiết món ăn từ Restaurant Service
                        # (Vì Cart Service chỉ lưu food_id, không lưu tên/ảnh)
                        
                        # Lấy branch_id từ món đầu tiên (Quy tắc 1 giỏ - 1 quán)
                        current_branch_id = cart_items[0]['branch_id']
                        
                        # Gọi API lấy menu của quán đó để map thông tin
                        food_res = httpx.get(f"{GATEWAY_URL}/foods", params={"branch_id": current_branch_id})
                        if food_res.status_code == 200:
                            # Tạo dictionary để tra cứu nhanh: {food_id: food_info}
                            food_map = {f['id']: f for f in food_res.json()}
                            
                            st.success(f"Đang đặt món tại Chi nhánh ID: {current_branch_id}")
                            st.divider()

                            total_bill = 0
                            
                            for item in cart_items:
                                f_id = item['food_id']
                                qty = item['quantity']
                                info = food_map.get(f_id)

                                if info:
                                    # Tính giá sau giảm
                                    discount = info.get('discount', 0)
                                    final_price = info['price'] * (1 - discount/100)
                                    item_total = final_price * qty
                                    total_bill += item_total

                                    # Hiển thị giao diện từng dòng
                                    with st.container(border=True):
                                        c1, c2, c3, c4 = st.columns([1, 3, 2, 1])
                                        
                                        with c1:
                                            st.image(get_food_image(info['name']), use_container_width=True)
                                        
                                        with c2:
                                            st.markdown(f"**{info['name']}**")
                                            if discount > 0:
                                                st.caption(f"Giá gốc: ~~{int(info['price']):,}đ~~")
                                                st.markdown(f":red[**{int(final_price):,}đ**] (Giảm {discount}%)")
                                            else:
                                                st.markdown(f"**{int(final_price):,}đ**")
                                        
                                        with c3:
                                            # Nút tăng giảm số lượng
                                            col_minus, col_num, col_plus = st.columns([1, 1, 1])
                                            if col_minus.button("➖", key=f"dec_{f_id}"):
                                                new_qty = qty - 1
                                                httpx.put(f"{GATEWAY_URL}/cart", json={"food_id": f_id, "quantity": new_qty}, headers=headers)
                                                st.rerun()
                                                
                                            col_num.write(f"**SL: {qty}**")
                                            
                                            if col_plus.button("➕", key=f"inc_{f_id}"):
                                                new_qty = qty + 1
                                                # Lưu ý: Backend Cart Service đang dùng PUT để update, body chỉ cần food_id & quantity
                                                httpx.put(f"{GATEWAY_URL}/cart", json={"food_id": f_id, "quantity": new_qty}, headers=headers)
                                                st.rerun()
                                        
                                        with c4:
                                            st.write(f"**{int(item_total):,}đ**")
                                            if st.button("🗑️", key=f"del_cart_{f_id}"):
                                                httpx.put(f"{GATEWAY_URL}/cart", json={"food_id": f_id, "quantity": 0}, headers=headers)
                                                st.rerun()

                            st.divider()
                            # Phần Tổng tiền & Thanh toán
                            col_total, col_btn = st.columns([2, 1])
                            col_total.markdown(f"### Tổng cộng: :red[{int(total_bill):,} đ]")
                            
                            with col_btn:
                                if st.button("🚀 ĐẶT HÀNG NGAY", type="primary", use_container_width=True):
                                    with st.spinner("Đang xử lý đơn hàng..."):
                                        try:
                                            # Gọi API Checkout của Order Service
                                            checkout_res = httpx.post(f"{GATEWAY_URL}/checkout", headers=headers)
                                            if checkout_res.status_code == 200:
                                                order_id = checkout_res.json().get('order_id')
                                                st.success(f"🎉 Đặt thành công! Mã đơn: #{order_id}")
                                                st.balloons()
                                                time.sleep(2)
                                                # Chuyển qua tab Lịch sử (cần user tự bấm qua hoặc reload)
                                                st.rerun()
                                            else:
                                                st.error(f"Lỗi đặt hàng: {checkout_res.text}")
                                        except Exception as e:
                                            st.error(f"Lỗi kết nối: {e}")
                                            
                            if st.button("Xóa sạch giỏ hàng"):
                                httpx.delete(f"{GATEWAY_URL}/cart", headers=headers)
                                st.rerun()
                                
                        else:
                            st.warning("Không tải được thông tin món ăn từ Server.")
                else:
                    st.error("Lỗi tải giỏ hàng (Token hết hạn hoặc lỗi Server)")
            except Exception as e:
                st.error(f"Lỗi hiển thị: {e}")