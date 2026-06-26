"""
Pydantic schemas cho luồng TRÍCH XUẤT DỮ LIỆU TỪ ẢNH (OCR).

File MỚI hoàn toàn — không đụng tới schemas/analyze.py của luồng CSV.

Tên field được đặt KHỚP với mô hình dữ liệu người chơi mà luồng phân tích CSV
đang dùng (player_name, job, kills, assists, camp) để dữ liệu bóc từ ảnh có thể
chảy thẳng vào cùng pipeline phân tích. Hai field bổ sung (level, supplies) là
thông tin chỉ có trên ảnh kết quả Bang chiến.
"""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class ExtractedPlayer(BaseModel):
    """Một người chơi được bóc tách từ ảnh kết quả."""

    camp: str = Field(default="", description="Bang (Trái/Phải)")
    player_name: str = Field(..., description="Tên nhân vật (Tên)")
    job: str = Field(default="", description="Môn phái")
    kills: int = Field(default=0, description="Hạ gục")
    assists: int = Field(default=0, description="Hỗ trợ")
    supplies: int = Field(default=0, description="Vật tư")
    damage_to_players: int = Field(default=0, description="Sát thương lên người")
    damage_to_buildings: int = Field(default=0, description="Sát thương lên công trình")
    healing: int = Field(default=0, description="Trị liệu")
    damage_taken: int = Field(default=0, description="Nhận sát thương")
    deaths: int = Field(default=0, description="Tử trận")
    revives: int = Field(default=0, description="Hồi sinh")


class ImageExtractResponse(BaseModel):
    """Kết quả trả về cho endpoint extract-image."""

    total_players: int = Field(..., description="Tổng số người chơi bóc tách được")
    image_width: int = Field(..., description="Chiều rộng thực tế của ảnh (px)")
    image_height: int = Field(..., description="Chiều cao thực tế của ảnh (px)")
    scale_x: float = Field(..., description="Tỷ lệ co giãn trục X so với ảnh gốc chuẩn")
    scale_y: float = Field(..., description="Tỷ lệ co giãn trục Y so với ảnh gốc chuẩn")
    players: List[ExtractedPlayer] = Field(..., description="Danh sách người chơi")
