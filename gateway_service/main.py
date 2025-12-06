import os
import httpx
from fastapi import FastAPI, Request, Response

app = FastAPI(title="API Gateway")

# ==================================================================
# 1. ĐỌC CẤU HÌNH TỪ BIẾN MÔI TRƯỜNG (.ENV)
# ==================================================================
# Nếu không tìm thấy trong .env, sẽ dùng giá trị mặc định (tham số thứ 2)
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user_service:8001")
RESTAURANT_SERVICE_URL = os.getenv("RESTAURANT_SERVICE_URL", "http://restaurant_service:8002")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://order_service:8003")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment_service:8004")
CART_SERVICE_URL = os.getenv("CART_SERVICE_URL", "http://cart_service:8005")

# ==================================================================
# 2. HELPER FUNCTION: CHUYỂN TIẾP REQUEST
# ==================================================================
async def forward_request(service_url: str, path: str, request: Request):
    """
    Hàm nhận request từ Client và gửi sang Service đích,
    sau đó trả kết quả từ Service đích về cho Client.
    """
    client = httpx.AsyncClient()
    
    # Đọc body từ request gốc
    body = await request.body()
    
    # Tạo URL đích (Ví dụ: http://user_service:8001/login)
    # Nếu path rỗng thì không thêm dấu /
    dest_url = f"{service_url}/{path}" if path else service_url

    try:
        response = await client.request(
            method=request.method,
            url=dest_url,
            headers=request.headers,
            content=body,
            params=request.query_params
        )
        
        # Trả về nguyên vẹn phản hồi cho Client
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers)
        )
    except httpx.ConnectError:
        return Response(content="Gateway Error: Cannot connect to downstream service", status_code=503)
    except Exception as e:
        return Response(content=f"Gateway Error: {str(e)}", status_code=500)

# ==================================================================
# 3. ĐỊNH TUYẾN (ROUTING)
# ==================================================================

# --- NHÓM 1: USER SERVICE (Auth & Address) ---
# Các API: /login, /register, /verify, /users/addresses
@app.api_route("/login", methods=["POST"])
async def login_proxy(request: Request):
    return await forward_request(USER_SERVICE_URL, "login", request)

@app.api_route("/register", methods=["POST"])
async def register_proxy(request: Request):
    return await forward_request(USER_SERVICE_URL, "register", request)

@app.api_route("/verify", methods=["GET"])
async def verify_proxy(request: Request):
    return await forward_request(USER_SERVICE_URL, "verify", request)

@app.api_route("/users/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def users_general_proxy(path: str, request: Request):
    # Forward các API như /users/addresses
    return await forward_request(USER_SERVICE_URL, f"users/{path}", request)


# --- NHÓM 2: RESTAURANT SERVICE (Food, Branch, Coupon, Review) ---
# Các API: /foods, /branches, /coupons, /reviews
@app.api_route("/foods", methods=["GET", "POST"])
async def foods_root_proxy(request: Request):
    return await forward_request(RESTAURANT_SERVICE_URL, "foods", request)

@app.api_route("/foods/{path:path}", methods=["GET", "DELETE", "PUT"])
async def foods_detail_proxy(path: str, request: Request):
    return await forward_request(RESTAURANT_SERVICE_URL, f"foods/{path}", request)

@app.api_route("/branches", methods=["GET", "POST"])
async def branches_proxy(request: Request):
    return await forward_request(RESTAURANT_SERVICE_URL, "branches", request)

@app.api_route("/coupons", methods=["POST", "GET"])
async def coupons_proxy(request: Request):
    return await forward_request(RESTAURANT_SERVICE_URL, "coupons", request)

@app.api_route("/coupons/{path:path}", methods=["GET"])
async def coupons_detail_proxy(path: str, request: Request):
    return await forward_request(RESTAURANT_SERVICE_URL, f"coupons/{path}", request)

@app.api_route("/reviews", methods=["POST", "GET"])
async def reviews_proxy(request: Request):
    return await forward_request(RESTAURANT_SERVICE_URL, "reviews", request)


# --- NHÓM 3: CART SERVICE (Giỏ hàng) ---
@app.api_route("/cart", methods=["GET", "POST", "PUT", "DELETE"])
async def cart_proxy(request: Request):
    return await forward_request(CART_SERVICE_URL, "cart", request)


# --- NHÓM 4: ORDER SERVICE (Đặt hàng) ---
@app.api_route("/checkout", methods=["POST"])
async def checkout_proxy(request: Request):
    return await forward_request(ORDER_SERVICE_URL, "checkout", request)

@app.api_route("/orders", methods=["GET"])
async def orders_list_proxy(request: Request):
    return await forward_request(ORDER_SERVICE_URL, "orders", request)

@app.api_route("/orders/{path:path}", methods=["GET", "PUT"])
async def orders_detail_proxy(path: str, request: Request):
    # Forward các API như /orders/{id}/status, /orders/{id}/cancel
    return await forward_request(ORDER_SERVICE_URL, f"orders/{path}", request)


# --- NHÓM 5: PAYMENT SERVICE (Thanh toán) ---
@app.api_route("/pay", methods=["POST"])
async def pay_proxy(request: Request):
    return await forward_request(PAYMENT_SERVICE_URL, "pay", request)