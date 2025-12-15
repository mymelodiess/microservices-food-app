import httpx
import os
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# --- CẤU HÌNH CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CẤU HÌNH URL DỊCH VỤ ---
USER_SERVICE_URL = "http://user_service:8001"
RESTAURANT_SERVICE_URL = "http://restaurant_service:8002"
ORDER_SERVICE_URL = "http://order_service:8003"
PAYMENT_SERVICE_URL = "http://payment_service:8004"
CART_SERVICE_URL = "http://cart_service:8005"
NOTIFICATION_SERVICE_URL = "http://notification_service:8006"

# --- HÀM PROXY ---
async def forward_request(service_url: str, path: str, request: Request):
    client = httpx.AsyncClient()
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)
    params = dict(request.query_params)
    
    try:
        body = await request.body()
        url = f"{service_url}/{path}"
        
        response = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            params=params,
            content=body
        )
        
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers)
        )
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail=f"Service Unavailable: {service_url}")
    except Exception as e:
        print(f"Gateway Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Gateway Error")

# ==========================================
# CÁC ROUTES ĐỊNH TUYẾN
# ==========================================

# 1. RESTAURANT SERVICE (Foods, Coupons, Branches, Static)
@app.api_route("/foods", methods=["GET", "POST"])
async def foods_root(req: Request):
    return await forward_request(RESTAURANT_SERVICE_URL, "foods", req)

@app.api_route("/foods/search", methods=["GET"])
async def foods_search(req: Request):
    return await forward_request(RESTAURANT_SERVICE_URL, "foods/search", req)

@app.api_route("/foods/{path:path}", methods=["GET", "PUT", "DELETE"])
async def foods_path(path: str, req: Request):
    return await forward_request(RESTAURANT_SERVICE_URL, f"foods/{path}", req)

@app.api_route("/branches", methods=["GET", "POST"])
async def branches_root(req: Request):
    return await forward_request(RESTAURANT_SERVICE_URL, "branches", req)

@app.api_route("/branches/{path:path}", methods=["GET"])
async def branches_path(path: str, req: Request):
    return await forward_request(RESTAURANT_SERVICE_URL, f"branches/{path}", req)

@app.api_route("/coupons", methods=["GET", "POST"])
async def coupons_root(req: Request):
    return await forward_request(RESTAURANT_SERVICE_URL, "coupons", req)

# [QUAN TRỌNG: SỬA LỖI XÓA COUPON TẠI ĐÂY]
@app.api_route("/coupons/{path:path}", methods=["GET", "PUT", "DELETE"])
async def coupons_path(path: str, req: Request):
    return await forward_request(RESTAURANT_SERVICE_URL, f"coupons/{path}", req)

@app.api_route("/static/{path:path}", methods=["GET"])
async def static_files(path: str, req: Request):
    return await forward_request(RESTAURANT_SERVICE_URL, f"static/{path}", req)

# 2. ORDER SERVICE
@app.api_route("/checkout", methods=["POST"])
async def checkout(req: Request):
    return await forward_request(ORDER_SERVICE_URL, "checkout", req)

@app.api_route("/orders", methods=["GET"])
async def orders_root(req: Request):
    return await forward_request(ORDER_SERVICE_URL, "orders", req)

@app.api_route("/orders/{path:path}", methods=["GET", "PUT", "DELETE"])
async def orders_path(path: str, req: Request):
    return await forward_request(ORDER_SERVICE_URL, f"orders/{path}", req)

# 3. PAYMENT SERVICE
@app.api_route("/pay", methods=["POST"])
async def pay(req: Request):
    return await forward_request(PAYMENT_SERVICE_URL, "pay", req)

@app.api_route("/payment-methods", methods=["GET", "POST"])
async def payment_methods(req: Request):
    return await forward_request(PAYMENT_SERVICE_URL, "payment-methods", req)

# 4. USER & AUTH
@app.api_route("/login", methods=["POST"])
async def login(req: Request):
    return await forward_request(USER_SERVICE_URL, "login", req)

@app.api_route("/register", methods=["POST"])
async def register(req: Request):
    return await forward_request(USER_SERVICE_URL, "register", req)

@app.api_route("/verify", methods=["GET"])
async def verify(req: Request):
    return await forward_request(USER_SERVICE_URL, "verify", req)

@app.api_route("/users/{path:path}", methods=["GET", "POST", "PUT"])
async def users_path(path: str, req: Request):
    return await forward_request(USER_SERVICE_URL, f"users/{path}", req)

# 5. CART & NOTIFICATION
@app.api_route("/cart", methods=["GET", "POST", "PUT", "DELETE"])
async def cart_root(req: Request):
    return await forward_request(CART_SERVICE_URL, "cart", req)

@app.api_route("/notify", methods=["POST"])
async def notify(req: Request):
    return await forward_request(NOTIFICATION_SERVICE_URL, "notify", req)