"""
Service TRÍCH XUẤT DỮ LIỆU TỪ ẢNH chụp màn hình kết quả Bang chiến.

Phương pháp: AI Vision (Gemini API) thay thế cho Traditional OCR (pytesseract/cv2).
"""
from __future__ import annotations

import io
import json
import logging
import os
import concurrent.futures
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
load_dotenv()
from typing import Dict

import google.generativeai as genai
from PIL import Image

from app.services.exceptions import ServiceError

logger = logging.getLogger(__name__)

# ===========================================================================
# EXCEPTIONS riêng cho OCR (kế thừa ServiceError sẵn có để router bắt thống nhất)
# ===========================================================================
class OcrUnavailableError(ServiceError):
    """Lỗi khi gọi API Gemini (thiếu key, limit, lỗi mạng)."""
    status_code = 503


class ImageDecodeError(ServiceError):
    """Không decode được ảnh (file hỏng / không phải ảnh)."""
    status_code = 400


class GameImageToTextService:
    """
    Bóc tách số liệu Bang chiến từ ảnh chụp màn hình bằng Gemini API.
    """

    def __init__(self) -> None:
        """
        Khởi tạo dịch vụ và cấu hình Gemini API Key.
        """
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY chưa được thiết lập. Tính năng OCR sẽ báo lỗi 503 khi sử dụng.")
        else:
            genai.configure(api_key=api_key)

    def extract_from_bytes(self, raw_bytes_list: list[bytes]) -> dict:
        """
        Nhận danh sách bytes ảnh -> decode -> bóc tách qua Gemini -> trả dict gộp.
        """
        images = []
        for raw_bytes in raw_bytes_list:
            try:
                image = Image.open(io.BytesIO(raw_bytes))
                if image.mode in ('RGBA', 'P'):
                    image = image.convert('RGB')
                images.append(image)
            except Exception as exc:
                raise ImageDecodeError(f"Không decode được ảnh bằng Pillow: {exc}")

        return self.extract_batch(images)

    def extract_batch(self, images: list[Image.Image]) -> dict:
        if not os.environ.get("GEMINI_API_KEY"):
            raise OcrUnavailableError("Chưa cấu hình GEMINI_API_KEY trong biến môi trường.")

        prompt = """Bạn là một chuyên gia trích xuất dữ liệu từ hình ảnh bảng xếp hạng game. Yêu cầu trả về kết quả CHỈ dưới định dạng JSON.

Bảng dữ liệu luôn được chia làm 2 phe rõ ràng: Bảng bên Trái (Màu xanh) và Bảng bên Phải (Màu đỏ). Tên Phe nằm ở trên cùng của mỗi bảng tương ứng.

ĐỐI VỚI MỖI NGƯỜI CHƠI, HÃY TRÍCH XUẤT CÁC THÔNG TIN SAU:

Tên Phe: Lấy ở trên cùng của bảng tương ứng (Trái hoặc Phải).

Tên Người Chơi: Chữ màu trắng.

Môn Phái: Xác định dựa vào HÌNH DÁNG vũ khí/biểu tượng bên trong icon nhỏ nằm ngay bên trái Tên Người Chơi:

Cây thương / Lá cờ = Huyết hà

Đèn lồng / Quyền trượng = Cửu linh

Thanh kiếm = Long Ngâm

Dải lụa / Bông hoa = Tố vấn

Đao cong = Toái Mộng

Cây đàn / Chiếc quạt = Thần tương

Cái khiên / Bộ giáp = Thiết y

QUY TẮC ĐỌC CỘT CHỈ SỐ (QUAN TRỌNG TỐI CAO):
Hãy nhìn vào Menu dọc ở cạnh phải của màn hình để biết chữ của Tab nào đang SÁNG MÀU lên. Từ đó, áp dụng quy tắc đọc chỉ số từ TRÁI sang PHẢI:

CỘT ĐẦU TIÊN (Có icon Ngôi Sao): Luôn là cấp độ (thường hiển thị số 69). TUYỆT ĐỐI BỎ QUA cột này, không đưa vào JSON.

Nếu Tab "Chiến Lược" sáng: Cột 2 là 'kills', Cột 3 là 'assists', Cột 4 là 'supplies'.

Nếu Tab "Sát Thương" sáng: Cột 2 là 'damage_to_players', Cột 3 là 'damage_to_buildings'.

Nếu Tab "Trị Liệu" sáng: Cột 2 là 'healing', Cột 3 là 'damage_taken'.

Nếu Tab "Trọng Thương" sáng: Cột 2 là 'deaths', Cột 3 là 'revives'.

Các cột chỉ số không thuộc Tab đang sáng hãy mặc định gán giá trị bằng 0.

QUY TẮC XỬ LÝ SỐ LIỆU:

Nếu số liệu có chữ "vạn" (ví dụ: "628 vạn", "1365 vạn"), hãy nhân số đó với 10,000 và trả về kiểu số nguyên (ví dụ: 6280000, 13650000).

Nếu ô số liệu trống hoặc là dấu gạch ngang (-), gán giá trị bằng 0.

Tất cả các chỉ số phải là kiểu dữ liệu số (Number/Integer), không để trong dấu ngoặc kép.

CẤU TRÚC JSON ĐẦU RA BẮT BUỘC:
{
"players": [
{
"camp": "Tên Phe",
"player_name": "Tên người chơi",
"job": "Môn phái",
"kills": 0,
"assists": 0,
"supplies": 0,
"damage_to_players": 0,
"damage_to_buildings": 0,
"healing": 0,
"damage_taken": 0,
"deaths": 0,
"revives": 0
}
]
}"""

        try:
            model = genai.GenerativeModel(
                'gemini-2.5-flash',
                generation_config={"response_mime_type": "application/json"}
            )
            
            merged_players = {}

            def process_image(img):
                try:
                    response = model.generate_content([prompt, img])
                    data = json.loads(response.text)
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict):
                        return data.get("players", [])
                except Exception as e:
                    logger.error(f"Lỗi khi xử lý ảnh: {e}")
                return []

            with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(images) if images else 1)) as executor:
                results = executor.map(process_image, images)

            for players in results:
                for p in players:
                    if not isinstance(p, dict):
                        continue
                    p_name = str(p.get("player_name", "")).strip()
                    if not p_name:
                        continue
                    
                    if p_name not in merged_players:
                        merged_players[p_name] = {
                            "camp": p.get("camp", ""),
                            "player_name": p_name,
                            "job": p.get("job", ""),
                            "kills": 0, "assists": 0, "supplies": 0,
                            "damage_to_players": 0, "damage_to_buildings": 0,
                            "healing": 0, "damage_taken": 0,
                            "deaths": 0, "revives": 0
                        }
                    
                    for key in ["kills", "assists", "supplies", "damage_to_players", "damage_to_buildings",
                                "healing", "damage_taken", "deaths", "revives"]:
                        val = p.get(key, 0)
                        if isinstance(val, (int, float)) and val > 0:
                            merged_players[p_name][key] = max(merged_players[p_name][key], val)
                            
                    if not merged_players[p_name]["job"] or merged_players[p_name]["job"] == "Không xác định":
                        if p.get("job") and p.get("job") != "Không xác định":
                            merged_players[p_name]["job"] = p.get("job")
                            
                    if not merged_players[p_name]["camp"]:
                        merged_players[p_name]["camp"] = p.get("camp", "")
                        
            final_players = list(merged_players.values())
            
            return {
                "total_players": len(final_players),
                "image_width": images[0].width if images else 0,
                "image_height": images[0].height if images else 0,
                "scale_x": 1.0,
                "scale_y": 1.0,
                "players": final_players,
            }
            
        except Exception as exc:
            logger.error(f"Lỗi khi gọi Gemini API: {exc}")
            raise OcrUnavailableError(f"Lỗi phân tích OCR bằng Gemini API: {exc}")
