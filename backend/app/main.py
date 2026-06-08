"""
Điểm khởi tạo ứng dụng FastAPI.

Chịu trách nhiệm "lắp ráp" toàn hệ thống:
  - Tạo app.
  - Cấu hình CORS cho phép Frontend (Vue) gọi sang.
  - Đăng ký (include) các router.
  - Khởi tạo DB lúc startup.

Chạy local:
    uvicorn app.main:app --reload
Tài liệu API tự sinh: http://127.0.0.1:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analyze
from app.core.config import settings
from app.models.database import init_db

# ---------------------------------------------------------------------------
# Khởi tạo app
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Backend API cho hệ thống phân tích số liệu game.",
)

# ---------------------------------------------------------------------------
# CORS: cho phép Frontend Vue (chạy ở origin khác) gọi API.
# Origin được cấu hình trong .env (BACKEND_CORS_ORIGINS).
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,   # ví dụ: http://localhost:5173
    allow_credentials=True,
    allow_methods=["*"],                   # GET, POST, PUT, DELETE...
    allow_headers=["*"],                   # cho phép gửi Authorization, Content-Type...
)


# ---------------------------------------------------------------------------
# Sự kiện khởi động.
#
# CHÚ Ý migration: từ giai đoạn 2 dùng Alembic để quản lý schema.
#   - DEV: cho phép init_db() (create_all) để chạy nhanh không cần migrate.
#   - PRODUCTION/STAGING: KHÔNG auto create_all. Schema phải áp bằng lệnh
#     `alembic upgrade head` trong quy trình deploy (an toàn, có version).
# ---------------------------------------------------------------------------
@app.on_event("startup")
def on_startup() -> None:
    if not settings.is_production:
        init_db()


# ---------------------------------------------------------------------------
# Health check: tiện kiểm tra server sống và test CORS từ frontend.
# ---------------------------------------------------------------------------
@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "service": settings.PROJECT_NAME}


# ---------------------------------------------------------------------------
# Đăng ký router. Mỗi nhóm tính năng = 1 router, include tại đây.
# Ứng dụng mở PUBLIC: không còn router auth/login.
# ---------------------------------------------------------------------------
app.include_router(analyze.router, prefix=settings.API_V1_PREFIX)
