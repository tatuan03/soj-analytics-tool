"""
Các dependency dùng chung cho tầng API (Dependency Injection của FastAPI).

Sau khi PIVOT mở public, ứng dụng không còn cơ chế auth/JWT/IP tracking.
File này chỉ còn factory tạo service đã inject sẵn DB session.
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.services.data_srv import DataAnalysisService


def get_data_service(db: Session = Depends(get_db)) -> DataAnalysisService:
    """Cung cấp DataAnalysisService đã được inject sẵn DB session."""
    return DataAnalysisService(db)
