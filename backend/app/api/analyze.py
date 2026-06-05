"""
Router cho luồng phân tích số liệu: /api/v1/analyze/...

Bám sát kiến trúc team:
  - Route được bảo vệ bằng JWT qua dependency get_current_user.
  - Chỉ điều phối: nhận file -> gọi service -> bắt ServiceError -> trả JSON.
  - KHÔNG chứa business logic (đặt trong DataAnalysisService).
"""
from typing import Any, Dict

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import get_current_user, get_data_service
from app.schemas.analyze import AnalyzeResponse
from app.services.data_srv import DataAnalysisService
from app.services.exceptions import InvalidFileError, ServiceError
from fastapi import HTTPException

router = APIRouter(prefix="/analyze", tags=["Analyze"])

# Giới hạn kích thước file để tránh tấn công nhồi file lớn (DoS).
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post(
    "/upload",
    response_model=AnalyzeResponse,
    summary="Tải lên CSV và phân tích số liệu trận đấu",
)
async def upload_and_analyze(
    file: UploadFile = File(..., description="File CSV export từ game"),
    service: DataAnalysisService = Depends(get_data_service),
    current_user: Dict[str, Any] = Depends(get_current_user),  # yêu cầu JWT hợp lệ
):
    """
    Nhận file CSV, phân tích và trả về kết quả cho Frontend (Vue/ECharts).

    Yêu cầu: header `Authorization: Bearer <token>` hợp lệ.

    Trả về:
      - total_players, camps, players[], summary[] (xem schema AnalyzeResponse).
    """
    # --- Validate sơ bộ phần thuộc về HTTP layer (không phải business logic) ---
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .csv")

    raw_bytes = await file.read()
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File vượt quá 5MB")

    # Giải mã nội dung. CSV game có thể là UTF-8 (kèm BOM) hoặc GBK.
    raw_content = _decode_bytes(raw_bytes)

    # --- Gọi service xử lý nghiệp vụ ---
    try:
        return service.analyze(raw_content)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


def _decode_bytes(raw_bytes: bytes) -> str:
    """
    Giải mã bytes -> str, thử lần lượt các encoding phổ biến.

    File export game tiếng Trung thường là utf-8-sig (UTF-8 có BOM) hoặc GBK.
    Tách thành hàm riêng để dễ test và mở rộng.
    """
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    # Phương án cuối: bỏ qua ký tự lỗi để vẫn parse được phần còn lại.
    raise InvalidFileError("Không giải mã được nội dung file (encoding không hỗ trợ)")
