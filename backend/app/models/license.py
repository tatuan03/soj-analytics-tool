"""
Model ORM cho bảng LicenseKey (khóa bản quyền / key đăng nhập).

Một "license key" cấp quyền truy cập hệ thống trong một khoảng thời gian
(duration_days) và bị giới hạn số IP được đăng ký (chống share key tràn lan).
"""
import enum
import json
from datetime import datetime, timezone
from typing import List

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class LicenseStatus(str, enum.Enum):
    """Trạng thái của một license key."""
    ACTIVE = "ACTIVE"      # Đang hoạt động
    DISABLED = "DISABLED"  # Bị admin khóa thủ công
    EXPIRED = "EXPIRED"    # Hết hạn (có thể cập nhật bằng job định kỳ)


class LicenseKey(Base):
    __tablename__ = "license_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Mã key người dùng nhập để đăng nhập. Unique + index để tra cứu nhanh.
    key_code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    # Số ngày hiệu lực kể từ lúc kích hoạt (dùng để tính/đặt expires_at).
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)

    # Trạng thái. Lưu dạng chuỗi để dễ đọc trực tiếp trong DB.
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=LicenseStatus.ACTIVE.value
    )

    # Danh sách IP đã đăng ký, lưu dưới dạng chuỗi JSON (ví dụ: ["1.2.3.4"]).
    # SQLite không có kiểu mảng native nên dùng Text + helper get/set bên dưới.
    registered_ips: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    # Thời điểm hết hạn. Có thể None nếu key chưa được kích hoạt lần đầu.
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # ----------------------------------------------------------------------
    # Helper methods: thao tác registered_ips như một list thay vì chuỗi JSON.
    # Giúp service layer code sạch hơn, không phải json.loads/dumps thủ công.
    # ----------------------------------------------------------------------
    def get_ips(self) -> List[str]:
        """Đọc danh sách IP đã đăng ký dưới dạng list."""
        try:
            ips = json.loads(self.registered_ips or "[]")
            return ips if isinstance(ips, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    def set_ips(self, ips: List[str]) -> None:
        """Ghi đè danh sách IP (tự serialize về chuỗi JSON)."""
        self.registered_ips = json.dumps(ips)

    def is_expired(self) -> bool:
        """Kiểm tra key đã hết hạn theo thời gian thực hay chưa."""
        if self.expires_at is None:
            return False
        # So sánh ở UTC để tránh lệch múi giờ.
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)

    def __repr__(self) -> str:  # hỗ trợ debug/log
        return f"<LicenseKey id={self.id} key_code={self.key_code} status={self.status}>"
