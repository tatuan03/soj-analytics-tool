# Hướng dẫn Cài đặt – Chạy – Test hệ thống "Phân tích số liệu Bang chiến"

Tài liệu này dành cho người mới tiếp nhận dự án. Làm theo đúng thứ tự là chạy được.

---

## 1. Tổng quan hệ thống

Hệ thống gồm **2 phần độc lập**:

| Phần | Vị trí | Vai trò |
|------|--------|---------|
| **Frontend** | `index.html` (+ thư mục `*_files`) | Giao diện web: tải CSV, vẽ biểu đồ ECharts. Chạy hoàn toàn ở trình duyệt. |
| **Backend** | `backend/` (FastAPI) | API phân tích CSV và trích xuất số liệu từ ảnh (OCR). |

> **Lưu ý quan trọng:** Frontend hiện tại tự phân tích CSV ngay trong trình duyệt
> (dùng PapaParse), **chưa gọi sang Backend**. Backend là API riêng, phục vụ tích
> hợp về sau hoặc cho client khác. Hai phần có thể chạy/test riêng rẽ.

Hệ thống đã **mở public hoàn toàn** — không còn đăng nhập, license key hay JWT.

---

## 2. Yêu cầu môi trường

- **Python 3.11+** (bắt buộc cho Backend).
- **Trình duyệt web** hiện đại (Chrome/Edge/Firefox) cho Frontend.
- **Kết nối Internet** khi mở Frontend (do tải thư viện Vue/ECharts từ CDN).
- **Tesseract OCR** (tùy chọn) — chỉ cần nếu dùng tính năng trích xuất từ ảnh.

---

## 3. Chạy FRONTEND (giao diện web)

Frontend là file tĩnh. Cách đơn giản và ổn định nhất là phục vụ qua HTTP server:

```bash
# Đứng ở thư mục chứa index.html
python -m http.server 8080
```

Mở trình duyệt: <http://127.0.0.1:8080/index.html>

Hoặc nhanh hơn: nhấp đúp mở thẳng `index.html` (cần Internet để tải thư viện CDN).

**Cách dùng:** kéo–thả (hoặc bấm chọn) file CSV xuất từ game vào ô tải lên →
hệ thống tự phân tích và vẽ biểu đồ radar so sánh giữa các bang hội.

---

## 4. Cài đặt & chạy BACKEND (API)

Tất cả lệnh dưới đây chạy trong thư mục `backend/`.

### 4.1. Tạo môi trường ảo & cài thư viện

**Windows (PowerShell):**
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS / Linux:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4.2. Tạo file cấu hình `.env`

```powershell
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
```
Mở `.env` chỉnh `BACKEND_CORS_ORIGINS` nếu Frontend chạy ở origin khác.

### 4.3. (Tùy chọn) Tạo schema database bằng migration

```bash
alembic upgrade head
```
> App hiện không bắt buộc có bảng nào (đã gỡ license). Bước này chỉ cần khi
> bạn muốn quản lý schema chuẩn chỉnh bằng Alembic.

### 4.4. Chạy server

```bash
uvicorn app.main:app --reload
```

- Tài liệu API (Swagger UI): <http://127.0.0.1:8000/docs>
- Kiểm tra sống: <http://127.0.0.1:8000/health> → `{"status":"ok",...}`

---

## 5. Cài Tesseract OCR (chỉ cho tính năng trích xuất từ ảnh)

Tính năng `/analyze/extract-image` cần **binary Tesseract** (không cài qua pip được).

- **Windows:** tải installer tại <https://github.com/UB-Mannheim/tesseract/wiki>,
  khi cài nhớ tích thêm gói ngôn ngữ **Vietnamese (vie)**. Nếu Tesseract không
  nằm trong PATH, thêm vào đầu `app/services/ocr_srv.py`:
  ```python
  pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
  ```
- **Ubuntu/Debian:**
  ```bash
  sudo apt-get install tesseract-ocr tesseract-ocr-vie
  ```

> Nếu CHƯA cài Tesseract: app vẫn chạy bình thường, riêng endpoint trích xuất ảnh
> sẽ trả lỗi **503** với thông điệp hướng dẫn (không làm chết các API khác).
>
> Ngoài ra cần bỏ ảnh icon môn phái mẫu (PNG) vào `backend/app/assets/icons/`
> theo hướng dẫn trong file README ở thư mục đó. Tọa độ bounding box trong
> `ocr_srv.py` đang là STUB, cần hiệu chỉnh theo ảnh thật trước khi dùng.

---

## 6. Thử nhanh các API

**Phân tích CSV:**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyze/upload ^
  -F "file=@duong-dan/match.csv"
```

**Trích xuất từ ảnh (cần Tesseract):**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyze/extract-image ^
  -F "file=@duong-dan/screenshot.png"
```

Hoặc test trực quan ngay trên Swagger UI tại `/docs` (nút **Try it out**).

---

## 7. Chạy TEST tự động

Bộ test dùng `pytest`, gọi API qua TestClient (không cần chạy server thật).

```powershell
cd backend
.venv\Scripts\Activate.ps1            # nếu chưa kích hoạt venv
pip install -r requirements-dev.txt   # cài pytest + httpx
pytest
```

Kết quả mong đợi: **9 passed**.

```
tests/test_analyze_csv.py ....   # 4 test: phân tích CSV + công thức + nhánh lỗi
tests/test_ocr.py .....          # 5 test: scale ảnh, template matching, lỗi ảnh, pipeline
```

**Ghi chú:**
- Các test OCR **tự động bỏ qua (skip)** nếu máy chưa cài OpenCV.
- Test pipeline OCR **giả lập (mock) Tesseract** nên chạy được kể cả khi chưa
  cài binary Tesseract.

Chạy 1 file / 1 test cụ thể:
```bash
pytest tests/test_analyze_csv.py
pytest tests/test_ocr.py::test_template_matching_detects_faction
```

---

## 8. Cấu trúc thư mục Backend

```
backend/
├── app/
│   ├── main.py              # Khởi tạo FastAPI, CORS, include router
│   ├── core/config.py       # Cấu hình nạp từ .env
│   ├── models/database.py   # engine, session, get_db (DI)
│   ├── schemas/             # Pydantic: analyze.py (CSV), ocr.py (ảnh)
│   ├── services/
│   │   ├── data_srv.py      # Phân tích CSV (KD, KDA, tỷ lệ trị liệu...)
│   │   ├── ocr_srv.py       # OCR + OpenCV template matching
│   │   └── exceptions.py    # Exception nghiệp vụ
│   ├── api/
│   │   ├── analyze.py       # /analyze/upload (CSV) + /analyze/extract-image (ảnh)
│   │   └── deps.py          # Dependency Injection
│   └── assets/icons/        # Icon môn phái mẫu cho template matching
├── alembic/                 # Database migrations
├── tests/                   # Test tự động (pytest)
├── requirements.txt         # Thư viện chạy thật
├── requirements-dev.txt     # Thư viện cho dev/test
└── .env.example             # Mẫu cấu hình
```

---

## 9. Xử lý sự cố thường gặp

| Hiện tượng | Nguyên nhân & cách xử lý |
|-----------|--------------------------|
| `ModuleNotFoundError` khi chạy | Chưa kích hoạt venv hoặc chưa `pip install -r requirements.txt`. |
| Frontend không vẽ biểu đồ | Mất Internet (thư viện CDN không tải được). Dùng `python -m http.server`. |
| API ảnh trả **503** | Chưa cài binary Tesseract — xem mục 5. |
| Cột "Môn phái" luôn là "Không xác định" | Chưa có icon mẫu trong `app/assets/icons/`, hoặc tọa độ bbox chưa khớp ảnh. |
| Lỗi CORS khi gọi API từ web | Thêm origin của Frontend vào `BACKEND_CORS_ORIGINS` trong `.env`. |
| Cảnh báo `on_event is deprecated` | Chỉ là cảnh báo của FastAPI, không ảnh hưởng vận hành. |

---

## 10. Tóm tắt API

| Method | Endpoint | Mô tả | Auth |
|--------|----------|-------|------|
| GET | `/health` | Kiểm tra server sống | Không |
| POST | `/api/v1/analyze/upload` | Phân tích file CSV | Không (public) |
| POST | `/api/v1/analyze/extract-image` | Trích xuất số liệu từ ảnh (OCR) | Không (public) |
```
