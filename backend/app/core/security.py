"""
Tiện ích bảo mật: tạo và xác thực JWT Token.

Tách riêng khỏi service để có thể tái sử dụng ở bất kỳ đâu (auth, middleware,
WebSocket...) và dễ viết unit test độc lập.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt  # PyJWT

from app.core.config import settings


class TokenError(Exception):
    """Lỗi khi token không hợp lệ / hết hạn. API layer sẽ bắt và trả về 401."""
    pass


def create_access_token(
    subject: str,
    extra_claims: Optional[Dict[str, Any]] = None,
    expires_minutes: Optional[int] = None,
) -> str:
    """
    Tạo JWT access token.

    Args:
        subject: Định danh chính của token (ở đây là key_code của license).
                 Sẽ được lưu vào claim "sub".
        extra_claims: Các thông tin bổ sung muốn nhúng vào token
                      (ví dụ: {"ip": client_ip}). Tùy chọn.
        expires_minutes: Thời gian sống của token (phút). Nếu None thì
                         lấy mặc định từ config.

    Returns:
        Chuỗi JWT đã ký.
    """
    now = datetime.now(timezone.utc)
    expire_minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": now,                                  # issued at
        "exp": now + timedelta(minutes=expire_minutes),  # expiration
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> Dict[str, Any]:
    """
    Giải mã và xác thực JWT token.

    Args:
        token: Chuỗi JWT nhận từ client (thường ở header Authorization).

    Returns:
        Payload (dict) nếu token hợp lệ.

    Raises:
        TokenError: Khi token hết hạn hoặc không hợp lệ.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenError("Token đã hết hạn")
    except jwt.PyJWTError:
        raise TokenError("Token không hợp lệ")
