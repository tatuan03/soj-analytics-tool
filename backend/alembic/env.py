"""
Môi trường chạy migration của Alembic — đã cấu hình sẵn cho dự án.

Điểm tùy biến quan trọng so với template gốc:
  1. Thêm thư mục gốc dự án vào sys.path để import được package `app`.
  2. Lấy DATABASE_URL từ app.core.config.settings (1 nguồn sự thật, không
     hardcode URL trong alembic.ini).
  3. target_metadata = Base.metadata của dự án -> bật autogenerate migration.
     LƯU Ý: phải import các module model để chúng đăng ký bảng vào metadata.
"""
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# (1) Đảm bảo import được package `app` (env.py nằm trong backend/alembic/).
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.core.config import settings          # noqa: E402
from app.models.database import Base          # noqa: E402

# (3) Import model để đăng ký bảng vào Base.metadata TRƯỚC khi autogenerate.
#     Thêm dòng import cho mỗi file model mới của dự án.
from app.models import license                # noqa: E402,F401

# ---------------------------------------------------------------------------
# Cấu hình logging chuẩn của Alembic.
# ---------------------------------------------------------------------------
config = context.config

# (2) Nạp URL database từ settings của dự án (ghi đè giá trị trong alembic.ini).
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata mục tiêu cho autogenerate.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Chạy migration ở chế độ 'offline' (chỉ sinh SQL, không cần kết nối DB).

    Hữu ích khi muốn xuất script SQL để DBA review trước khi áp dụng.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # render_as_batch: cần thiết cho SQLite khi ALTER TABLE.
        render_as_batch=url.startswith("sqlite"),
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Chạy migration ở chế độ 'online' (kết nối DB thật và áp dụng thay đổi)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        is_sqlite = connection.dialect.name == "sqlite"
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # SQLite không hỗ trợ ALTER TABLE đầy đủ -> dùng batch mode.
            render_as_batch=is_sqlite,
            compare_type=True,  # phát hiện đổi kiểu cột khi autogenerate
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
