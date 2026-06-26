# Game Analytics Backend (FastAPI)

Backend cho hệ thống "Phân tích số liệu game", tổ chức theo mô hình
**Router → Service → Model** để dễ chia việc nhóm và dễ scale.

> **Pivot:** Hệ thống đã được mở **PUBLIC hoàn toàn** — gỡ bỏ License Key, JWT
> và IP Tracking để tối ưu trải nghiệm, tập trung vào sức mạnh phân tích CSV.

## Cấu trúc thư mục

```
backend/
├── app/
│   ├── main.py            # Khởi tạo app, CORS, include router
│   ├── core/
│   │   └── config.py      # Cấu hình nạp từ .env
│   ├── models/            # Tầng MODEL (SQLAlchemy)
│   │   └── database.py    # engine, session, get_db (DI), init_db
│   ├── schemas/           # Pydantic request/response
│   │   └── analyze.py     # contract dữ liệu cho Frontend
│   ├── schemas/           # Pydantic: analyze.py (CSV), ocr.py (ảnh)
│   ├── services/          # Tầng SERVICE (business logic)
│   │   ├── data_srv.py    # << THUẬT TOÁN PHÂN TÍCH CSV >>
│   │   ├── ocr_srv.py     # OCR + OpenCV template matching (trích xuất ảnh)
│   │   └── exceptions.py  # exception nghiệp vụ
│   ├── api/               # Tầng ROUTER
│   │   ├── deps.py        # Dependency Injection dùng chung
│   │   └── analyze.py     # /analyze/upload (CSV) + /analyze/extract-image (ảnh)
│   └── assets/icons/      # Icon môn phái mẫu cho template matching
├── alembic/               # Database migrations
├── tests/                 # Test tự động (pytest)
├── requirements.txt       # Thư viện chạy thật
├── requirements-dev.txt   # Thư viện cho dev/test
└── .env.example
```

> Hướng dẫn cài đặt – chạy – test đầy đủ (cả Frontend) xem ở `../HUONG_DAN.md`.

## Phân chia công việc gợi ý (3 người)

- **Người A — Hạ tầng & API:** `core/`, `models/`, `api/`, CORS, deploy.
- **Người B — Phân tích dữ liệu:** `services/data_srv.py` (`parse_csv`,
  `compute_player_metrics`, `summarize_camps`) + `schemas/analyze.py`.
- **Người C — Tích hợp & Frontend:** kết nối Vue với API, biểu đồ ECharts, viết test.

## Cài đặt & chạy

```bash
# 1. Tạo môi trường ảo
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 2. Cài thư viện
pip install -r requirements.txt

# 3. Tạo file cấu hình
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux

# 4. (Tùy chọn) Áp dụng migration tạo schema DB
alembic upgrade head

# 5. Chạy server
uvicorn app.main:app --reload
```

- Swagger UI: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

## Chạy test

```bash
pip install -r requirements-dev.txt
pytest
```
Mong đợi: **9 passed**. Test OCR tự skip nếu thiếu OpenCV; phần Tesseract được mock.

## Thử phân tích CSV (không cần đăng nhập)

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyze/upload ^
  -F "file=@duong-dan/toi/match.csv"
```

## Luồng kiến trúc

```
Client (Vue)
   │  POST /api/v1/analyze/upload  (multipart: file CSV)   — PUBLIC, không token
   ▼
api/analyze.py     ← nhận file, validate, bắt ServiceError -> HTTP status
   │  gọi service (inject DB session qua Depends)
   ▼
services/data_srv  ← BUSINESS LOGIC: parse CSV, tính KD/KDA/tỷ lệ trị liệu...
   │
   ▼
schemas/analyze.py ← trả JSON chuẩn cho Frontend vẽ ECharts
```
