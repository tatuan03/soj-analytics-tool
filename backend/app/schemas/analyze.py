"""
Pydantic schemas cho luồng phân tích số liệu (analyze).

Đây là HỢP ĐỒNG DỮ LIỆU (data contract) giữa Backend và Frontend (Vue/ECharts).
Frontend chỉ cần hứng đúng cấu trúc này để vẽ bảng + biểu đồ radar, không phải
tự tính lại bất kỳ chỉ số nào.

Quy ước đặt tên field: dùng tiếng Anh (snake_case) cho API ổn định, kèm comment
ánh xạ sang cột gốc tiếng Trung trong CSV.
"""
from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field


class PlayerStats(BaseModel):
    """Số liệu đầy đủ của một người chơi sau khi đã tính toán các chỉ số."""

    # ---- Định danh ----
    camp: str = Field(..., description="Bang hội (所属帮会)")
    player_name: str = Field(..., description="Tên người chơi (玩家名字)")
    job: str = Field(..., description="Nghề nghiệp (职业)")

    # ---- Chỉ số thô (tổng hợp từ CSV) ----
    kills: int = Field(..., description="Hạ gục (击败/清泉, cộng dồn các phần)")
    assists: int = Field(..., description="Hỗ trợ (助攻)")
    deaths: int = Field(..., description="Tử trận (重伤)")
    damage_to_players: int = Field(..., description="Sát thương lên người chơi (对玩家伤害)")
    disarm: int = Field(..., description="Phá giáp (人伤卸甲 + 破塔卸甲)")
    damage_to_buildings: int = Field(..., description="Sát thương lên công trình (对建筑伤害)")
    heal: int = Field(..., description="Hồi máu (治疗值)")
    damage_taken: int = Field(..., description="Nhận sát thương (承受伤害)")
    revives: int = Field(..., description="Số lần Hóa Vũ (复活/清泉, cộng dồn)")
    fengu: int = Field(..., description="Phần Cốt (焚骨)")

    # ---- Chỉ số tính toán ----
    kd: float = Field(..., description="KD = kills / deaths")
    kda: float = Field(..., description="KDA = (kills + assists) / deaths")
    actual_heal_rate: float = Field(
        ..., description="Tỷ lệ trị liệu thực tế (%) = (heal - damage_taken) / heal * 100"
    )
    yuhua_rate: float = Field(
        ..., description="Tỷ lệ Hóa Vũ (%) = revives * 0.0326 * 100"
    )


class CampSummary(BaseModel):
    """Tổng hợp trung bình của một bang hội (phục vụ biểu đồ radar so sánh)."""

    camp: str = Field(..., description="Tên bang hội")
    player_count: int = Field(..., description="Số người chơi trong bang hội")
    # Trung bình từng chỉ số: key = tên chỉ số, value = giá trị trung bình.
    averages: Dict[str, float] = Field(
        ..., description="Giá trị trung bình mỗi chỉ số của bang hội"
    )


class AnalyzeResponse(BaseModel):
    """Response tổng cho endpoint upload + phân tích."""

    total_players: int = Field(..., description="Tổng số người chơi đã phân tích")
    camps: List[str] = Field(..., description="Danh sách bang hội (theo thứ tự xuất hiện)")
    players: List[PlayerStats] = Field(..., description="Chi tiết từng người chơi")
    summary: List[CampSummary] = Field(..., description="Tổng hợp trung bình theo bang hội")
