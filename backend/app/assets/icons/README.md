# Icon môn phái mẫu (Template Matching)

Thư mục này chứa ảnh icon mẫu của từng môn phái, dùng cho `cv2.matchTemplate`
trong `app/services/ocr_srv.py` để nhận diện phái từ ảnh kết quả Bang chiến.

## Cách thêm icon

1. Crop sát phần icon môn phái từ ảnh game (nền càng gọn càng tốt).
2. Lưu thành file PNG, đặt tên đúng theo mapping trong
   `FACTION_ICON_TEMPLATES` (biến trong `ocr_srv.py`). Ví dụ:
   - `long_ngam.png`  -> "Long Ngâm"
   - `to_van.png`     -> "Tố Vấn"
   - `thiet_y.png`    -> "Thiết Y"
   - ...

## Lưu ý

- Icon nên được crop ở cùng cỡ tương đối với ô icon trên giao diện (service tự
  resize template về cỡ ROI nếu cần, nhưng crop chuẩn sẽ cho độ khớp cao hơn).
- Nếu thư mục chưa có icon nào, service vẫn chạy bình thường nhưng cột môn phái
  sẽ trả về "Không xác định".
- Đây là dữ liệu STUB: tọa độ bounding box và danh sách phái trong `ocr_srv.py`
  cần được hiệu chỉnh (calibrate) theo ảnh thật trước khi dùng production.
