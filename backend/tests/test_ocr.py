"""
Test cho luồng OCR: service GameImageToTextService + endpoint extract-image.

Các test cần OpenCV sẽ tự bỏ qua (skip) nếu máy chưa cài cv2/numpy.
Phần đọc chữ của Tesseract được giả lập (mock) để test toàn bộ pipeline mà
không cần cài binary Tesseract.
"""
import pytest
from fastapi.testclient import TestClient

# Bỏ qua toàn bộ file này nếu thiếu cv2/numpy (giữ test suite chạy được mọi máy).
cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")
pytest.importorskip("pytesseract")

from app.services.ocr_srv import (  # noqa: E402
    BASE_HEIGHT,
    BASE_WIDTH,
    ROWS_PER_SIDE,
    BoundingBox,
    GameImageToTextService,
    ImageDecodeError,
)


def test_bounding_box_scaled() -> None:
    """Tỷ lệ co giãn áp dụng đúng cho bounding box (resolution independence)."""
    box = BoundingBox(x=100, y=200, w=50, h=40)
    scaled = box.scaled(1280 / BASE_WIDTH, 720 / BASE_HEIGHT)
    assert scaled.x == round(100 * 1280 / 1920)  # 67
    assert scaled.y == round(200 * 720 / 1080)   # 133


def test_template_matching_detects_faction(tmp_path) -> None:
    """matchTemplate nhận đúng môn phái khi icon trùng template."""
    icon = np.zeros((48, 48), dtype=np.uint8)
    cv2.circle(icon, (24, 24), 18, 255, -1)
    cv2.rectangle(icon, (5, 5), (20, 20), 128, -1)
    cv2.imwrite(str(tmp_path / "long_ngam.png"), icon)

    svc = GameImageToTextService(icon_dir=tmp_path, match_threshold=0.6)

    canvas = np.zeros((BASE_HEIGHT, BASE_WIDTH, 3), dtype=np.uint8)
    canvas[300:348, 70:118] = cv2.cvtColor(icon, cv2.COLOR_GRAY2BGR)
    gray = cv2.cvtColor(canvas, cv2.COLOR_BGR2GRAY)

    roi = svc._crop(gray, BoundingBox(70, 300, 48, 48))
    assert svc._detect_faction(roi) == "Long Ngâm"

    # Vùng trống -> không khớp
    empty = svc._crop(gray, BoundingBox(800, 800, 48, 48))
    assert svc._detect_faction(empty) == "Không xác định"


def test_decode_invalid_image_raises() -> None:
    """Bytes không phải ảnh -> ImageDecodeError."""
    svc = GameImageToTextService()
    with pytest.raises(ImageDecodeError):
        svc.extract_from_bytes(b"this-is-not-an-image")


def test_full_extract_with_mocked_tesseract(monkeypatch, tmp_path) -> None:
    """
    Giả lập pytesseract để test toàn bộ pipeline extract() mà không cần binary.

    - Ô số (config có whitelist) -> trả "123".
    - Ô chữ -> trả "TestPlayer".
    """
    import app.services.ocr_srv as ocr

    def fake_image_to_string(image, lang=None, config="") -> str:
        return "123" if "whitelist" in config else "TestPlayer"

    monkeypatch.setattr(ocr.pytesseract, "image_to_string", fake_image_to_string)

    svc = GameImageToTextService(icon_dir=tmp_path)  # tmp_path rỗng -> không có icon
    canvas = np.zeros((BASE_HEIGHT, BASE_WIDTH, 3), dtype=np.uint8)
    _, png = cv2.imencode(".png", canvas)

    result = svc.extract_from_bytes(png.tobytes())

    # 2 bên x ROWS_PER_SIDE hàng, mock luôn trả dữ liệu -> không hàng nào bị bỏ.
    assert result["total_players"] == 2 * ROWS_PER_SIDE
    assert result["image_width"] == BASE_WIDTH
    assert result["scale_x"] == 1.0

    first = result["players"][0]
    assert first["camp"] == "Bang Trái"
    assert first["player_name"] == "TestPlayer"
    assert first["kills"] == 123
    assert first["job"] == "Không xác định"  # chưa có icon mẫu


def test_extract_image_endpoint_rejects_non_image(client: TestClient) -> None:
    """Endpoint từ chối file không phải ảnh -> 400."""
    resp = client.post(
        "/api/v1/analyze/extract-image",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400
