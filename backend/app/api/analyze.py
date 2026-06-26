"""
Router cho luồng phân tích số liệu: /api/v1/analyze/...

Bám sát kiến trúc team:
  - Endpoint PUBLIC (không yêu cầu đăng nhập) — đã gỡ bỏ Auth Layer.
  - Chỉ điều phối: nhận file -> gọi service -> bắt ServiceError -> trả JSON.
  - KHÔNG chứa business logic (đặt trong DataAnalysisService).
"""
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import get_data_service, get_ocr_service
from app.schemas.analyze import AnalyzeResponse
from app.schemas.ocr import ImageExtractResponse
from app.services.data_srv import DataAnalysisService
from app.services.exceptions import InvalidFileError, ServiceError
from app.services.ocr_srv import GameImageToTextService
# pyrefly: ignore [missing-import]
from fastapi import HTTPException

router = APIRouter(prefix="/analyze", tags=["Analyze"])

# Giới hạn kích thước file để tránh tấn công nhồi file lớn (DoS).
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB

# Ảnh chụp màn hình thường nặng hơn CSV -> cho phép tới 10MB.
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB

# Đuôi file ảnh được chấp nhận.
ALLOWED_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".webp")


@router.post(
    "/upload",
    response_model=AnalyzeResponse,
    summary="Tải lên CSV và phân tích số liệu trận đấu",
)
async def upload_and_analyze(
    file: UploadFile = File(..., description="File CSV export từ game"),
    service: DataAnalysisService = Depends(get_data_service),
):
    """
    Nhận file CSV, phân tích và trả về kết quả cho Frontend (Vue/ECharts).

    Endpoint PUBLIC — không cần đăng nhập.

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


from typing import List

@router.post(
    "/extract-image",
    response_model=ImageExtractResponse,
    summary="Trích xuất số liệu từ nhiều ảnh chụp màn hình kết quả Bang chiến (OCR)",
)
async def extract_from_images(
    files: List[UploadFile] = File(..., description="Các ảnh chụp màn hình kết quả Bang chiến"),
    service: GameImageToTextService = Depends(get_ocr_service),
):
    """
    Nhận danh sách ảnh -> dùng Gemini OCR để bóc tách số liệu.
    Endpoint PUBLIC — không cần đăng nhập.
    Trả về mảng người chơi đã được tự động CỘNG DỒN các chỉ số nếu có tên trùng nhau.
    """
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp ít nhất 1 ảnh.")
    
    if len(files) > 35:
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ tối đa 35 ảnh cùng lúc.")

    raw_bytes_list = []
    for file in files:
        filename = (file.filename or "").lower()
        if not filename.endswith(ALLOWED_IMAGE_EXTS):
            raise HTTPException(
                status_code=400,
                detail=f"Chỉ chấp nhận ảnh: {', '.join(ALLOWED_IMAGE_EXTS)} (file: {filename})",
            )
        raw_bytes = await file.read()
        if len(raw_bytes) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail=f"Ảnh vượt quá 10MB (file: {filename})")
        raw_bytes_list.append(raw_bytes)

    try:
        return service.extract_from_bytes(raw_bytes_list)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
