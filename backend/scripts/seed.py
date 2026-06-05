"""
Script tạo dữ liệu mẫu để test nhanh.

Chạy từ thư mục backend/:
    python -m scripts.seed

Sẽ tạo bảng (nếu chưa có) và thêm 1 license key mẫu: "TEST-KEY-123".
"""
from app.models.database import SessionLocal, init_db
from app.models.license import LicenseKey, LicenseStatus

SAMPLE_KEY = "TEST-KEY-123"


def run() -> None:
    init_db()
    db = SessionLocal()
    try:
        existing = (
            db.query(LicenseKey).filter(LicenseKey.key_code == SAMPLE_KEY).first()
        )
        if existing:
            print(f"Key '{SAMPLE_KEY}' đã tồn tại, bỏ qua.")
            return

        key = LicenseKey(
            key_code=SAMPLE_KEY,
            duration_days=30,
            status=LicenseStatus.ACTIVE.value,
            registered_ips="[]",
            expires_at=None,  # None = sẽ kích hoạt khi đăng nhập lần đầu
        )
        db.add(key)
        db.commit()
        print(f"Đã tạo key mẫu: {SAMPLE_KEY} (hiệu lực 30 ngày kể từ lần đăng nhập đầu)")
    finally:
        db.close()


if __name__ == "__main__":
    run()
