"""
Thiết lập kết nối database bằng SQLAlchemy.

File này cung cấp:
  - engine: kết nối tới DB (SQLite).
  - SessionLocal: factory tạo session cho mỗi request.
  - Base: lớp cha cho tất cả các model ORM.
  - get_db(): dependency cung cấp session (dùng cho Dependency Injection).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# ---------------------------------------------------------------------------
# Tạo engine kết nối DB.
# Riêng SQLite cần "check_same_thread": False vì FastAPI chạy đa luồng,
# mặc định SQLite chặn truy cập từ luồng khác luồng tạo connection.
# ---------------------------------------------------------------------------
connect_args = (
    {"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,  # tự kiểm tra connection còn sống trước khi dùng
)

# Factory tạo session. autoflush=False để kiểm soát thời điểm ghi DB rõ ràng hơn.
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# Base class cho mọi model. Tất cả bảng (license.py, ...) kế thừa từ đây.
Base = declarative_base()


def get_db():
    """
    Dependency cung cấp database session cho mỗi request.

    Cách dùng trong router:
        def login(db: Session = Depends(get_db)): ...

    Pattern try/finally đảm bảo session LUÔN được đóng dù request thành công
    hay lỗi, tránh rò rỉ connection.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Tạo toàn bộ bảng trong DB nếu chưa tồn tại.

    Sau khi gỡ Auth Layer, app hiện không còn model ORM nào nên hàm này thực
    chất chỉ tạo file DB rỗng. Giữ lại để hạ tầng DB sẵn sàng khi sau này
    DataAnalysisService cần lưu lịch sử phân tích.

    LƯU Ý: khi thêm model mới, import nó vào đây để SQLAlchemy "nhìn thấy"
    bảng trước khi create_all.
    """
    Base.metadata.create_all(bind=engine)
