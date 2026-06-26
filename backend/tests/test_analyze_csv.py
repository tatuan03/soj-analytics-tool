"""
Test cho luồng phân tích CSV: POST /api/v1/analyze/upload.

Kiểm tra: đường đi thành công + công thức tính, và các nhánh lỗi (sai định
dạng, không có dữ liệu).
"""
import io

from fastapi.testclient import TestClient

# CSV 2 bang hội, định dạng multi-section giống file export từ game.
SAMPLE_CSV = (
    "Thien Phu Chi Quoc,,,,,,,,,,,,\n"
    "玩家名字,职业,击败/清泉,助攻,对玩家伤害,人伤卸甲,对建筑伤害,破塔卸甲,治疗值,承受伤害,重伤,复活/清泉,焚骨\n"
    "Alice,Than Tuong,10/2,5,100000,200,5000,100,0,50000,2,3/1,10\n"
    "Bob,Thiet Y,8,3,80000,150,3000,50,0,40000,4,1,5\n"
    "Nhat Kiem,,,,,,,,,,,,\n"
    "玩家名字,职业,击败/清泉,助攻,对玩家伤害,人伤卸甲,对建筑伤害,破塔卸甲,治疗值,承受伤害,重伤,复活/清泉,焚骨\n"
    "Carol,Y Tong,2,12,20000,50,1000,0,500000,30000,1,5/2,0\n"
)


def _upload(client: TestClient, content: str, filename: str = "match.csv"):
    return client.post(
        "/api/v1/analyze/upload",
        files={"file": (filename, io.BytesIO(content.encode("utf-8")), "text/csv")},
    )


def test_upload_csv_success_and_metrics(client: TestClient) -> None:
    """Upload CSV hợp lệ -> 200 và các chỉ số tính đúng."""
    resp = _upload(client, SAMPLE_CSV)
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert data["total_players"] == 3
    assert data["camps"] == ["Thien Phu Chi Quoc", "Nhat Kiem"]

    # Alice: kills = 10+2 = 12, deaths = 2 -> KD = 6.0, KDA = (12+5)/2 = 8.5
    alice = next(p for p in data["players"] if p["player_name"] == "Alice")
    assert alice["kills"] == 12
    assert alice["kd"] == 6.0
    assert alice["kda"] == 8.5
    # yuhua_rate = (3+1) * 0.0326 * 100 = 13.04
    assert alice["yuhua_rate"] == 13.04

    # Carol: heal=500000, taken=30000 -> (500000-30000)/500000*100 = 94.0
    carol = next(p for p in data["players"] if p["player_name"] == "Carol")
    assert carol["actual_heal_rate"] == 94.0

    # Có đúng 2 bang hội trong phần summary
    assert len(data["summary"]) == 2


def test_upload_rejects_non_csv(client: TestClient) -> None:
    """File không phải .csv -> 400."""
    resp = client.post(
        "/api/v1/analyze/upload",
        files={"file": ("data.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert resp.status_code == 400


def test_upload_empty_data_returns_422(client: TestClient) -> None:
    """CSV có header nhưng không có dòng dữ liệu -> 422 (EmptyDataError)."""
    header_only = (
        "Camp X,,,\n"
        "玩家名字,职业,击败/清泉,助攻\n"
    )
    resp = _upload(client, header_only)
    assert resp.status_code == 422


def test_analyze_endpoint_is_public(client: TestClient) -> None:
    """Xác nhận endpoint KHÔNG yêu cầu token (gọi không header Authorization)."""
    resp = _upload(client, SAMPLE_CSV)
    assert resp.status_code == 200
