"""
Pydantic schemas cho luồng xác thực (auth).

Tách schema (dữ liệu vào/ra qua API) khỏi model (bảng DB) là best practice:
  - Tránh lộ các field nhạy cảm của DB ra ngoài.
  - Cho phép validate dữ liệu client gửi lên một cách rõ ràng.
"""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Dữ liệu client gửi lên khi đăng nhập."""
    key_code: str = Field(..., min_length=1, description="Mã license key người dùng nhập")


class LoginResponse(BaseModel):
    """Dữ liệu trả về sau khi đăng nhập thành công."""
    access_token: str = Field(..., description="JWT token dùng cho các request sau")
    token_type: str = Field(default="bearer", description="Loại token")
    expires_at: str = Field(..., description="Thời điểm key hết hạn (ISO 8601)")
