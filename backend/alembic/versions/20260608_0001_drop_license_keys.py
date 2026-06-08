"""drop license_keys table (pivot: gỡ bỏ Auth Layer)

Revision ID: 0001_drop_license_keys
Revises:
Create Date: 2026-06-08

Sau khi pivot mở public, bảng license_keys không còn được dùng. Migration này
DROP bảng đó. Dùng "DROP TABLE IF EXISTS" để an toàn cả khi DB chưa từng tạo
bảng (vd DB mới tinh) lẫn khi DB cũ đã có bảng.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_drop_license_keys"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # IF EXISTS: chạy được trên cả SQLite và PostgreSQL, idempotent.
    op.execute("DROP TABLE IF EXISTS license_keys")


def downgrade() -> None:
    # Tái tạo lại bảng theo đúng schema gốc của model LicenseKey (đã xóa).
    op.create_table(
        "license_keys",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key_code", sa.String(length=64), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("registered_ips", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_license_keys_key_code", "license_keys", ["key_code"], unique=True
    )
    op.create_index("ix_license_keys_id", "license_keys", ["id"], unique=False)
