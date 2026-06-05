# Game Analytics Backend (FastAPI)

Backend cho hệ thống "Phân tích số liệu game", tổ chức theo mô hình
**Router → Service → Model** để dễ chia việc nhóm và dễ scale.

## Cấu trúc thư mục

```
backend/
├── app/
│   ├── main.py            # Khởi tạo app, CORS, include router
│   ├── core/
│   │   ├── config.py      # Cấu hình nạp từ .env
│   │   └── security.py    # Tạo & verify JWT
│   ├── models/            # Tầng MODEL (SQLAlchemy)
│   │   ├── database.py    # engine, session, get_db (DI), init_db
│   │   └── license.py     # bảng LicenseKey
│   ├── schemas/           # Pydantic request/response
│   │   └── auth.py
│   ├── services/          # Tầng SERVICE (business logic)
│   │   ├── auth_srv.py    # logic đăng nhập + quản lý IP
│   │   ├── data_srv.py    # << NƠI ĐIỀN THUẬT TOÁN PHÂN TÍCH >>
│   │   └── exceptions.py  # exception nghiệp vụ
│   └── api/               # Tầng ROUTER
│       ├── deps.py        # Dependency Injection dùng chung
│       └── auth.py        # /api/v1/auth/login
├── scripts/seed.py        # tạo DB + key mẫu để test
├── requirements.txt
└── .env.example
```

## Phân chia công việc gợi ý (3 người)

- **Người A — Hạ tầng & Auth:** `core/`, `models/`, `services/auth_srv.py`, `api/auth.py`.
- **Người B — Phân tích dữ liệu:** `services/data_srv.py` (điền các hàm `parse_csv`,
  `compute_player_metrics`, `summarize_camps`) + router data mới.
- **Người C — Tích hợp & Frontend:** kết nối Vue với API, quản lý license/admin, viết test.

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
# -> mở .env và đặt SECRET_KEY ngẫu nhiên

# 4. Tạo DB + key mẫu (TEST-KEY-123)
python -m scripts.seed

# 5. Chạy server
uvicorn app.main:app --reload
```

- Swagger UI: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

## Thử đăng nhập

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"key_code\": \"TEST-KEY-123\"}"
```

## Luồng kiến trúc

```
Client (Vue)
   │  POST /api/v1/auth/login { key_code }
   ▼
api/auth.py        ← validate request, bắt lỗi -> HTTP status
   │  gọi service (inject DB session qua Depends)
   ▼
services/auth_srv  ← BUSINESS LOGIC: kiểm tra status/hạn/IP, sinh JWT
   │
   ▼
models/license.py  ← truy vấn & cập nhật bảng LicenseKey (SQLAlchemy)
```
