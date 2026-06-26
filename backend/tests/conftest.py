"""
Cấu hình & fixture dùng chung cho pytest.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Đảm bảo import được package `app` khi chạy pytest từ thư mục backend/.
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    """TestClient của FastAPI để gọi API trong test (không cần chạy server thật)."""
    return TestClient(app)
