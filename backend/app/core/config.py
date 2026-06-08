"""
Cấu hình tập trung cho toàn bộ ứng dụng.

Mọi giá trị được nạp & validate từ biến môi trường (file .env) thông qua
pydantic-settings. Sau khi PIVOT mở public, đã gỡ toàn bộ cấu hình liên quan
tới JWT/SECRET_KEY/license (không còn cơ chế auth).
"""
from enum import Enum
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


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
