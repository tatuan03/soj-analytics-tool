"""
Service xử lý nghiệp vụ PHÂN TÍCH SỐ LIỆU GAME.

`DataAnalysisService` đọc file CSV (định dạng export từ game, gồm nhiều
"section" theo từng bang hội) và tính toán các chỉ số Y HỆT logic frontend
(index.html) để đảm bảo số liệu khớp tuyệt đối.

Quyết định kỹ thuật: dùng module `csv` built-in thay vì pandas.
  - File giải đấu nhỏ (vài trăm dòng) -> không cần sức mạnh của pandas.
  - Giảm 1 dependency nặng cho microservice, deploy nhẹ hơn.
  - Định dạng CSV này không phải bảng phẳng (nhiều header lồng nhau theo
    section) nên pandas.read_csv cũng không dùng trực tiếp được.
Nếu sau này cần xử lý file rất lớn, có thể thay phần parse bằng pandas mà
không ảnh hưởng tới chữ ký public của service.
"""
from __future__ import annotations

import csv
import io
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.services.exceptions import EmptyDataError, InvalidFileError

# ---------------------------------------------------------------------------
# HẰNG SỐ ánh xạ tên cột gốc (tiếng Trung) trong CSV.
# Gom về một chỗ để khi game đổi tên cột, chỉ sửa tại đây.
# ---------------------------------------------------------------------------
COL_PLAYER_NAME = "玩家名字"      # Tên người chơi
COL_JOB = "职业"                  # Nghề nghiệp
COL_KILLS = "击败/清泉"           # Hạ gục (dạng "a/b", cộng dồn)
COL_ASSISTS = "助攻"              # Hỗ trợ
COL_DMG_PLAYER = "对玩家伤害"     # Sát thương lên người chơi
COL_DISARM_PLAYER = "人伤卸甲"    # Phá giáp (do đánh người)
COL_DMG_BUILDING = "对建筑伤害"   # Sát thương công trình
COL_DISARM_TOWER = "破塔卸甲"     # Phá giáp (do phá trụ)
COL_HEAL = "治疗值"               # Hồi máu
COL_DMG_TAKEN = "承受伤害"        # Nhận sát thương
COL_DEATHS = "重伤"               # Tử trận
COL_REVIVES = "复活/清泉"         # Hóa Vũ / hồi sinh (dạng "a/b", cộng dồn)
COL_FENGU = "焚骨"                # Phần Cốt

# Hệ số quy đổi tỷ lệ Hóa Vũ (lấy đúng từ frontend).
YUHUA_FACTOR = 0.0326

# Các chỉ số sẽ được tính trung bình trong summary (key = field trong PlayerStats).
_SUMMARY_METRIC_KEYS = (
    "kills", "assists", "deaths", "damage_to_players", "disarm",
    "damage_to_buildings", "heal", "damage_taken", "revives", "fengu",
    "kd", "kda", "actual_heal_rate", "yuhua_rate",
)


class _Section:
    """Một section trong CSV = 1 bang hội (header + các dòng dữ liệu)."""

    __slots__ = ("header", "rows", "camp_name")

    def __init__(self, camp_name: Optional[str] = None) -> None:
        self.header: Optional[List[str]] = None
        self.rows: List[List[str]] = []
        self.camp_name: Optional[str] = camp_name


class DataAnalysisService:
    """Đóng gói logic phân tích dữ liệu trận đấu."""

    def __init__(self, db: Session) -> None:
        # Giữ sẵn db session phòng khi cần lưu lịch sử phân tích / cache kết quả.
        self.db = db

    # ==================================================================
    # 0) HÀM TIỆN ÍCH
    # ==================================================================
    @staticmethod
    def _clean(value: Any) -> str:
        """Chuẩn hóa 1 ô: ép chuỗi, bỏ khoảng trắng và dấu nháy kép."""
        return str(value if value is not None else "").strip().replace('"', "")

    @staticmethod
    def _to_int(value: str) -> int:
        """
        Ép chuỗi sang int an toàn (mô phỏng parseInt của JS).

        Lấy phần số nguyên đứng đầu chuỗi; nếu không có thì trả 0.
        """
        value = value.strip()
        if not value:
            return 0
        sign = -1 if value[0] == "-" else 1
        digits = ""
        for ch in value.lstrip("+-"):
            if ch.isdigit():
                digits += ch
            else:
                break
        return sign * int(digits) if digits else 0

    @classmethod
    def _sum_slashed(cls, value: str) -> int:
        """
        Cộng dồn chuỗi dạng "a/b/c" -> a + b + c.

        Dùng cho cột 击败/清泉 và 复活/清泉 (giống .split('/').reduce ở frontend).
        """
        return sum(cls._to_int(part) for part in value.split("/"))

    @staticmethod
    def _round2(value: float) -> float:
        """Làm tròn 2 chữ số thập phân (khớp toFixed(2) của frontend)."""
        return round(value, 2)

    # ==================================================================
    # 1) PARSE FILE CSV  -> danh sách section theo bang hội
    # ==================================================================
    def parse_csv(self, raw_content: str) -> List[Dict[str, Any]]:
        """
        Phân tích nội dung CSV thô thành danh sách bản ghi người chơi (chưa
        tính chỉ số phái sinh ngoài các phép cộng dồn cơ bản).

        Thuật toán tách section bám sát frontend:
          - Dòng có cột đầu == "玩家名字" => dòng HEADER, định nghĩa thứ tự cột.
          - Dòng có <= 2 ô không rỗng => dòng PHÂN CÁCH (tên bang hội mới).
            "nil"/rỗng => bang hội không tên (sẽ đặt tên mặc định sau).
          - Dòng còn lại => dòng dữ liệu người chơi của section hiện tại.

        Raises:
            InvalidFileError: nội dung rỗng hoặc không parse được CSV.
        """
        if not raw_content or not raw_content.strip():
            raise InvalidFileError("File rỗng hoặc không có nội dung")

        try:
            reader = csv.reader(io.StringIO(raw_content))
            rows: List[List[str]] = list(reader)
        except (csv.Error, ValueError) as exc:
            raise InvalidFileError(f"Không đọc được CSV: {exc}") from exc

        sections: List[_Section] = []
        current: Optional[_Section] = None

        for row in rows:
            # Bỏ dòng trống hoàn toàn.
            if not row or (len(row) == 1 and not self._clean(row[0])):
                continue

            r0 = self._clean(row[0])
            r1 = self._clean(row[1]) if len(row) > 1 else ""

            # --- Dòng HEADER ---
            if r0 == COL_PLAYER_NAME:
                if current is not None and current.rows:
                    sections.append(current)
                    current = None
                if current is None:
                    current = _Section()
                current.header = [self._clean(h) for h in row]
                continue

            # --- Dòng PHÂN CÁCH bang hội (<=2 ô có dữ liệu) ---
            non_empty = sum(1 for v in row if self._clean(v))
            if non_empty <= 2:
                if current is not None and current.rows:
                    sections.append(current)
                is_nil = (r0 in ("nil", "")) and (r1 in ("nil", ""))
                camp_name = None if is_nil else (r0 or r1 or None)
                current = _Section(camp_name=camp_name)
                continue

            # --- Dòng DỮ LIỆU người chơi ---
            if current is not None and current.header and len(row) >= 2 and r0:
                current.rows.append([self._clean(v) for v in row])

        if current is not None and current.rows:
            sections.append(current)

        return self._sections_to_players(sections)

    def _sections_to_players(self, sections: List[_Section]) -> List[Dict[str, Any]]:
        """Chuyển các section đã tách thành list bản ghi người chơi phẳng."""
        default_names = ["Bang hội A", "Bang hội B", "Bang hội C", "Bang hội D"]
        players: List[Dict[str, Any]] = []

        for idx, sec in enumerate(sections):
            camp = sec.camp_name or (
                default_names[idx] if idx < len(default_names) else f"Bang hội {idx + 1}"
            )
            header = sec.header or []
            col_index = {name: i for i, name in enumerate(header)}

            def cell(row: List[str], col: str) -> str:
                """Đọc ô theo tên cột; thiếu cột -> '0' (giống frontend)."""
                i = col_index.get(col)
                if i is None or i >= len(row):
                    return "0"
                return row[i] or "0"

            for row in sec.rows:
                player_name = cell(row, COL_PLAYER_NAME)
                if not player_name:
                    continue

                players.append(
                    {
                        "camp": camp,
                        "player_name": player_name,
                        "job": cell(row, COL_JOB),
                        "kills": self._sum_slashed(cell(row, COL_KILLS)),
                        "assists": self._to_int(cell(row, COL_ASSISTS)),
                        "damage_to_players": self._to_int(cell(row, COL_DMG_PLAYER)),
                        "disarm": (
                            self._to_int(cell(row, COL_DISARM_PLAYER))
                            + self._to_int(cell(row, COL_DISARM_TOWER))
                        ),
                        "damage_to_buildings": self._to_int(cell(row, COL_DMG_BUILDING)),
                        "heal": self._to_int(cell(row, COL_HEAL)),
                        "damage_taken": self._to_int(cell(row, COL_DMG_TAKEN)),
                        "deaths": self._to_int(cell(row, COL_DEATHS)),
                        "revives": self._sum_slashed(cell(row, COL_REVIVES)),
                        "fengu": self._to_int(cell(row, COL_FENGU)),
                    }
                )

        return players

    # ==================================================================
    # 2) TÍNH CHỈ SỐ PHÁI SINH CHO TỪNG NGƯỜI CHƠI
    # ==================================================================
    def compute_player_metrics(self, player: Dict[str, Any]) -> Dict[str, Any]:
        """
        Bổ sung các chỉ số tính toán cho 1 người chơi (khớp công thức frontend):
          - KD  = kills / deaths   (deaths == 0 -> = kills)
          - KDA = (kills + assists) / deaths   (deaths == 0 -> = kills + assists)
          - actual_heal_rate = (heal - damage_taken) / heal * 100   (heal == 0 -> 0)
          - yuhua_rate = revives * 0.0326 * 100
        """
        kills = player["kills"]
        assists = player["assists"]
        deaths = player["deaths"]
        heal = player["heal"]
        taken = player["damage_taken"]
        revives = player["revives"]

        player["kd"] = float(kills) if deaths == 0 else self._round2(kills / deaths)
        player["kda"] = (
            float(kills + assists)
            if deaths == 0
            else self._round2((kills + assists) / deaths)
        )
        player["actual_heal_rate"] = (
            0.0 if heal == 0 else self._round2((heal - taken) / heal * 100)
        )
        player["yuhua_rate"] = self._round2(revives * YUHUA_FACTOR * 100)
        return player

    # ==================================================================
    # 3) TỔNG HỢP / SO SÁNH GIỮA CÁC BANG HỘI
    # ==================================================================
    def summarize_camps(self, players: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Gom người chơi theo bang hội và tính trung bình mỗi chỉ số.

        Giữ NGUYÊN thứ tự xuất hiện của bang hội (quan trọng để frontend gán
        đúng bang A/B). Dùng dict thường (Python 3.7+ giữ thứ tự insert).
        """
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for p in players:
            grouped.setdefault(p["camp"], []).append(p)

        summary: List[Dict[str, Any]] = []
        for camp, members in grouped.items():
            count = len(members)
            averages = {
                key: self._round2(sum(m[key] for m in members) / count)
                for key in _SUMMARY_METRIC_KEYS
            }
            summary.append(
                {"camp": camp, "player_count": count, "averages": averages}
            )
        return summary

    # ==================================================================
    # 4) ĐIỂM VÀO TỔNG (orchestration) - router gọi hàm này
    # ==================================================================
    def analyze(self, raw_content: str) -> Dict[str, Any]:
        """
        Nhận CSV thô -> trả về dict khớp schema AnalyzeResponse.

        Raises:
            InvalidFileError: file không hợp lệ.
            EmptyDataError: parse được nhưng không có người chơi nào.
        """
        players = self.parse_csv(raw_content)
        if not players:
            raise EmptyDataError("Không trích được dữ liệu người chơi nào từ file")

        players = [self.compute_player_metrics(p) for p in players]
        summary = self.summarize_camps(players)

        # Danh sách bang hội theo thứ tự xuất hiện.
        camps: List[str] = []
        for p in players:
            if p["camp"] not in camps:
                camps.append(p["camp"])

        return {
            "total_players": len(players),
            "camps": camps,
            "players": players,
            "summary": summary,
        }
