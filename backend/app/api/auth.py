"""
Router cho luồng xác thực: /api/v1/auth/...

Tầng API chỉ làm 3 việc:
  1. Nhận & validate request (qua Pydantic schema).
  2. Gọi service xử lý nghiệp vụ.
  3. Bắt exception nghiệp vụ -> ánh xạ sang mã HTTP, rồi trả JSON.
KHÔNG đặt business logic ở đây.
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_auth_service, get_client_ip
from app.schemas.auth import LoginRequest, LoginResponse
from app.services.auth_srv import AuthService
from app.services.exceptions import ServiceError
from fastapi import HTTPException

# prefix gắn ở đây để URL cuối là: /api/v1/auth/login (prefix /api/v1 set ở main.py)
router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=LoginResponse, summary="Đăng nhập bằng license key")
def login(
    payload: LoginRequest,
    client_ip: str = Depends(get_client_ip),
    service: AuthService = Depends(get_auth_service),
):
    """
    Đăng nhập bằng license key.

    - **key_code**: mã key người dùng nhập.
    - IP client được tự động trích từ request (không cần client gửi).

    Trả về JWT token nếu hợp lệ.
    """
    try:
        result = service.login(key_code=payload.key_code, client_ip=client_ip)
        return result
    except ServiceError as exc:
        # Ánh xạ exception nghiệp vụ -> HTTP. status_code do service quyết định.
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
