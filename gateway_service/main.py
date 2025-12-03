import httpx
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# --- CẤU HÌNH CORS (Để Frontend gọi được) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ĐỊNH NGHĨA ĐỊA CHỈ CÁC SERVICE CON (Trong mạng Docker) ---
USER_SERVICE = "http://user_service:8001"
RESTAURANT_SERVICE = "http://restaurant_service:8002"
ORDER_SERVICE = "http://order_service:8003"
CART_SERVICE = "http://cart_service:8005"

# --- HÀM CHUYỂN TIẾP REQUEST (PROXY) ---
# gateway_service/main.py

async def forward_request(service_url: str, path: str, request: Request):
    client = httpx.AsyncClient()
    
    target_url = f"{service_url}/{path}"
    
    params = dict(request.query_params)
    try:
        body = await request.json()
    except:
        body = None 

    # --- SỬA QUAN TRỌNG TẠI ĐÂY ---
    # Loại bỏ 'host' VÀ 'content-length' để Gateway tự tính toán lại độ dài gói tin
    headers = {
        k: v for k, v in request.headers.items() 
        if k.lower() not in ['host', 'content-length']
    }

    try:
        resp = await client.request(
            method=request.method,
            url=target_url,
            params=params,
            json=body,
            headers=headers,
            timeout=10.0
        )
        
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=dict(resp.headers)
        )
    except Exception as e:
        return Response(content=f"Gateway Error: {str(e)}", status_code=500)
    finally:
        await client.aclose()

# --- ĐỊNH TUYẾN (ROUTING) ---
# Quy tắc: Xem đầu đường dẫn là gì để chọn Service

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def gateway_router(path: str, request: Request):
    
    # 1. Nhóm USER (Login, Register)
    if path in ["login", "register"] or path.startswith("users"):
        return await forward_request(USER_SERVICE, path, request)
    
    # 2. Nhóm RESTAURANT (Món ăn & Chi nhánh)
    # --- THÊM: or path.startswith("branches") ---
    elif path.startswith("foods") or path.startswith("seller") or path.startswith("branches"):
        return await forward_request(RESTAURANT_SERVICE, path, request)
    
    # 3. Nhóm ORDER (Đơn hàng)
    elif path.startswith("orders") or path == "checkout":
        return await forward_request(ORDER_SERVICE, path, request)
    
    # 4. Nhóm CART (Giỏ hàng)
    elif path.startswith("cart"):
        return await forward_request(CART_SERVICE, path, request)
        
    else:
        raise HTTPException(status_code=404, detail="Không tìm thấy đường dẫn này trên Gateway")