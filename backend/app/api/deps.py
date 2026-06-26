"""
Các dependency dùng chung cho tầng API (Dependency Injection của FastAPI).

Sau khi PIVOT mở public, ứng dụng không còn cơ chế auth/JWT/IP tracking.
File này chỉ còn factory tạo service đã inject sẵn DB session.
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.services.data_srv import DataAnalysisService
from app.services.ocr_srv import GameImageToTextService


def get_data_service(db: Session = Depends(get_db)) -> DataAnalysisService:
    """Cung cấp DataAnalysisService đã được inject sẵn DB session."""
    return DataAnalysisService(db)


def get_ocr_service() -> GameImageToTextService:
    """
    Cung cấp GameImageToTextService cho luồng trích xuất ảnh.

    Service này không cần DB session. Import GameImageToTextService an toàn kể
    cả khi thiếu cv2/pytesseract (module bọc import phòng thủ) — chỉ khi GỌI
    mới báo lỗi 503.
    """
    return GameImageToTextService()
