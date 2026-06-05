"""
Các dependency dùng chung cho tầng API (Dependency Injection của FastAPI).

Gom về một chỗ để các router tái sử dụng: lấy DB session, lấy IP client,
khởi tạo service, xác thực token...
"""
from typing import Any, Dict

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import TokenError, verify_token
from app.models.database import get_db
from app.services.auth_srv import AuthService
from app.services.data_srv import DataAnalysisService


# ---------------------------------------------------------------------------
# IP CLIENT
# ---------------------------------------------------------------------------
def get_real_ip(request: Request) -> str:
    """
    Đọc IP thật của client một cách an toàn khi chạy sau reverse proxy (Nginx).

    Thứ tự ưu tiên:
      1. Header `X-Forwarded-For` (do Nginx set). Có thể là chuỗi nhiều IP
         "client, proxy1, proxy2" -> lấy IP ĐẦU TIÊN (IP gốc của client).
      2. Header `X-Real-IP` (một số cấu hình Nginx dùng header này).
      3. Fallback: `request.client.host` (IP kết nối trực tiếp).

    CẢNH BÁO BẢO MẬT:
      `X-Forwarded-For` do client gửi nên CÓ THỂ bị giả mạo nếu app KHÔNG
      đứng sau proxy tin cậy. Trong production, Nginx phải GHI ĐÈ header này.
      Cấu hình Nginx tham khảo:
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Real-IP $remote_addr;
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first_ip = forwarded.split(",")[0].strip()
        if first_ip:
            return first_ip

    real_ip = request.headers.get("x-real-ip")
    if real_ip and real_ip.strip():
        return real_ip.strip()

    return request.client.host if request.client else "unknown"


# Giữ alias cũ để code auth hiện tại không bị vỡ (get_client_ip == get_real_ip).
def get_client_ip(request: Request) -> str:
    """Alias tương thích ngược. Khuyến nghị dùng get_real_ip cho code mới."""
    return get_real_ip(request)


# ---------------------------------------------------------------------------
# SERVICE FACTORIES (inject sẵn DB session)
# ---------------------------------------------------------------------------
def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Cung cấp AuthService đã được inject sẵn DB session."""
    return AuthService(db)


def get_data_service(db: Session = Depends(get_db)) -> DataAnalysisService:
    """Cung cấp DataAnalysisService đã được inject sẵn DB session."""
    return DataAnalysisService(db)


# ---------------------------------------------------------------------------
# XÁC THỰC JWT
# ---------------------------------------------------------------------------
def get_current_payload(authorization: str = Header(default="")) -> Dict[str, Any]:
    """
    Xác thực JWT từ header Authorization và trả về payload đã giải mã.

    Raises:
        HTTPException 401 nếu thiếu/sai/hết hạn token.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thiếu hoặc sai định dạng token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ", 1)[1].strip()
    try:
        return verify_token(token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    payload: Dict[str, Any] = Depends(get_current_payload),
) -> Dict[str, Any]:
    """
    Dependency bảo vệ route cho các API cần đăng nhập (vd: /analyze/upload).

    Bóc tách thông tin "người dùng hiện tại" từ payload JWT. Hiện tại định danh
    chính là `key_code` (claim "sub"), kèm IP đã nhúng lúc đăng nhập (claim "ip").

    Returns:
        Dict gồm {"key_code": ..., "ip": ...} cùng toàn bộ payload gốc.

    Raises:
        HTTPException 401 nếu token thiếu claim bắt buộc.
    """
    key_code = payload.get("sub")
    if not key_code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không chứa thông tin người dùng hợp lệ",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "key_code": key_code,
        "ip": payload.get("ip"),
        "raw": payload,
    }
