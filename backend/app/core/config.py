"""
Cấu hình tập trung cho toàn bộ ứng dụng (Production-hardened).

Mọi giá trị được nạp & VALIDATE từ biến môi trường (file .env) thông qua
pydantic-settings. Nhờ vậy:
  - 3 thành viên dùng cấu hình khác nhau mà không sửa code.
  - Sai cấu hình nguy hiểm (vd SECRET_KEY mặc định ở production) sẽ chặn
    server khởi động ngay, thay vì âm thầm chạy với cấu hình không an toàn.
"""
from enum import Enum
from functools import lru_cache
from typing import List

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Các giá trị placeholder KHÔNG được phép dùng ở môi trường production.
# "CHANGE_ME" giữ lại để tương thích yêu cầu/tài liệu cũ; thêm 1 dev-key mặc
# định đủ dài để team chạy được ngay ở local mà không cần .env.
_DEFAULT_SECRET = "CHANGE_ME"
_DEV_SECRET = "dev-insecure-secret-key-do-not-use-in-prod-00000"  # >= 32 ký tự
_INSECURE_SECRETS = {_DEFAULT_SECRET, _DEV_SECRET}
_MIN_SECRET_LENGTH = 32


class Environment(str, Enum):
    """Các môi trường chạy ứng dụng."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    # ---- Thông tin chung ----
    PROJECT_NAME: str = "Game Analytics API"
    API_V1_PREFIX: str = "/api/v1"

    # Môi trường hiện tại. Đặt ENVIRONMENT=production trong .env khi deploy.
    ENVIRONMENT: Environment = Environment.DEVELOPMENT

    # ---- Database ----
    DATABASE_URL: str = "sqlite:///./game_analytics.db"

    # ---- JWT ----
    # Mặc định dùng dev-key (đủ dài) để chạy local không cần .env.
    # Ở production BẮT BUỘC ghi đè bằng key ngẫu nhiên thật.
    SECRET_KEY: str = _DEV_SECRET
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 giờ

    # ---- License ----
    MAX_IPS_PER_KEY: int = 3

    # ---- CORS ----
    # Trong .env ghi dạng: http://localhost:5173,http://localhost:3000
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION

    @property
    def cors_origins(self) -> List[str]:
        """Tách chuỗi origin (phân tách bằng dấu phẩy) thành list cho middleware."""
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]

    # ------------------------------------------------------------------
    # VALIDATE cấu hình nhạy cảm. Chạy sau khi mọi field đã nạp xong.
    # ------------------------------------------------------------------
    @model_validator(mode="after")
    def _validate_secret_key(self) -> "Settings":
        """
        Đảm bảo SECRET_KEY an toàn:
          - LUÔN yêu cầu độ dài >= 32 ký tự (đủ entropy cho HS256).
          - Ở PRODUCTION: không cho phép bất kỳ key mặc định/dev nào
            (CHANGE_ME hoặc dev-key) -> buộc phải đặt key thật.

        Vi phạm -> raise ValueError -> pydantic biến thành ValidationError,
        server KHÔNG khởi động được. Đây là hành vi mong muốn (fail fast).
        """
        if self.is_production and self.SECRET_KEY in _INSECURE_SECRETS:
            raise ValueError(
                "SECRET_KEY đang để giá trị mặc định/dev ở môi trường "
                "PRODUCTION. Hãy đặt SECRET_KEY ngẫu nhiên trong .env "
                "(gợi ý: python -c \"import secrets; print(secrets.token_hex(32))\")."
            )

        if len(self.SECRET_KEY) < _MIN_SECRET_LENGTH:
            raise ValueError(
                f"SECRET_KEY quá ngắn ({len(self.SECRET_KEY)} ký tự). "
                f"Cần tối thiểu {_MIN_SECRET_LENGTH} ký tự."
            )

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Trả về một instance Settings duy nhất (cache lại để khỏi đọc .env nhiều lần)."""
    return Settings()


# Instance dùng chung: from app.core.config import settings
settings = get_settings()
