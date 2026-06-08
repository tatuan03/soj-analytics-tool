"""
Exception nghiệp vụ dùng chung cho tầng Service.

Service KHÔNG nên import HTTPException của FastAPI trực tiếp, để giữ business
logic độc lập với framework (dễ test, dễ tái dùng). Tầng API (router) sẽ bắt
các exception này và ánh xạ sang mã HTTP tương ứng.
"""


class ServiceError(Exception):
    """Lớp cha cho mọi lỗi nghiệp vụ. Mang theo status_code gợi ý cho API layer."""

    status_code: int = 400

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class InvalidFileError(ServiceError):
    """File upload sai định dạng / không phải CSV / không đọc được."""
    status_code = 400


class EmptyDataError(ServiceError):
    """File hợp lệ nhưng không trích được bản ghi người chơi nào."""
    status_code = 422
