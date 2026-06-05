"""
Service xử lý nghiệp vụ xác thực (đăng nhập bằng license key).

Toàn bộ business logic nằm ở đây, KHÔNG dính tới FastAPI:
  - Router chỉ gọi vào service và nhận kết quả/exception.
  - Service chỉ làm việc với DB session + model.
Cách tách lớp này giúp 3 thành viên làm song song: 1 người lo API, 1 người lo
service, 1 người lo thuật toán phân tích (data_srv) mà ít đụng độ nhau.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.models.license import LicenseKey, LicenseStatus
from app.services.exceptions import (
    InvalidKeyError,
    IpLimitExceededError,
    KeyInactiveError,
)


class AuthService:
    """Đóng gói logic đăng nhập / xác thực license key."""

    def __init__(self, db: Session):
        # Nhận session qua constructor (Dependency Injection từ router).
        self.db = db

    # ------------------------------------------------------------------
    # API CHÍNH của service
    # ------------------------------------------------------------------
    def login(self, key_code: str, client_ip: str) -> dict:
        """
        Xử lý đăng nhập bằng license key.

        Luồng:
          1. Tìm key trong DB.
          2. Kiểm tra trạng thái ACTIVE.
          3. Kích hoạt lần đầu (đặt expires_at) nếu chưa có.
          4. Kiểm tra hết hạn.
          5. Quản lý danh sách IP (tối đa MAX_IPS_PER_KEY).
          6. Sinh và trả về JWT token.

        Args:
            key_code: Mã key người dùng nhập.
            client_ip: IP thực của client (router trích từ request).

        Returns:
            dict gồm access_token, token_type, expires_at.

        Raises:
            InvalidKeyError: key không tồn tại.
            KeyInactiveError: key bị khóa hoặc hết hạn.
            IpLimitExceededError: vượt số IP cho phép.
        """
        license_key = self._get_key_or_raise(key_code)

        self._ensure_active(license_key)
        self._ensure_activated(license_key)   # đặt expires_at nếu là lần đầu
        self._ensure_not_expired(license_key)
        self._register_ip(license_key, client_ip)

        # Lưu mọi thay đổi (expires_at, registered_ips) trong 1 transaction.
        self.db.commit()
        self.db.refresh(license_key)

        # Nhúng IP vào token để các API sau có thể đối chiếu nếu cần.
        token = create_access_token(
            subject=license_key.key_code,
            extra_claims={"ip": client_ip},
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_at": license_key.expires_at.isoformat()
            if license_key.expires_at
            else "",
        }

    # ------------------------------------------------------------------
    # Các bước nội bộ (tách nhỏ để dễ đọc + dễ test từng phần)
    # ------------------------------------------------------------------
    def _get_key_or_raise(self, key_code: str) -> LicenseKey:
        """Tra cứu key trong DB, raise nếu không tồn tại."""
        license_key = (
            self.db.query(LicenseKey)
            .filter(LicenseKey.key_code == key_code)
            .first()
        )
        if license_key is None:
            raise InvalidKeyError("Key không tồn tại hoặc không hợp lệ")
        return license_key

    def _ensure_active(self, license_key: LicenseKey) -> None:
        """Kiểm tra status phải là ACTIVE."""
        if license_key.status != LicenseStatus.ACTIVE.value:
            raise KeyInactiveError("Key đã bị vô hiệu hóa")

    def _ensure_activated(self, license_key: LicenseKey) -> None:
        """
        Kích hoạt lần đầu: nếu expires_at chưa được set, tính từ thời điểm
        đăng nhập đầu tiên + duration_days. Đây là mô hình "key kích hoạt khi
        dùng lần đầu" (phổ biến cho license bán ra).

        Nếu nhóm muốn key đếm hạn ngay từ lúc tạo, hãy bỏ bước này và set
        expires_at lúc seed/tạo key.
        """
        if license_key.expires_at is None:
            now = datetime.now(timezone.utc)
            license_key.expires_at = now + timedelta(days=license_key.duration_days)

    def _ensure_not_expired(self, license_key: LicenseKey) -> None:
        """Kiểm tra key chưa hết hạn theo thời gian thực."""
        if license_key.is_expired():
            # Đồng bộ trạng thái trong DB để admin nhìn thấy.
            license_key.status = LicenseStatus.EXPIRED.value
            self.db.commit()
            raise KeyInactiveError("Key đã hết hạn")

    def _register_ip(self, license_key: LicenseKey, client_ip: str) -> None:
        """
        Quản lý danh sách IP đăng ký:
          - IP đã có -> cho qua (đăng nhập lại trên thiết bị cũ).
          - IP mới + còn slot -> thêm vào.
          - IP mới + đã đủ MAX_IPS_PER_KEY -> chặn (raise 403).
        """
        ips = license_key.get_ips()

        if client_ip in ips:
            return  # thiết bị đã đăng ký trước đó, không làm gì thêm

        if len(ips) >= settings.MAX_IPS_PER_KEY:
            raise IpLimitExceededError(
                f"Key đã đạt giới hạn {settings.MAX_IPS_PER_KEY} địa chỉ IP"
            )

        ips.append(client_ip)
        license_key.set_ips(ips)
