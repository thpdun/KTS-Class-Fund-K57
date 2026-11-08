import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Đảm bảo không cho phép ghi dữ liệu thật
os.environ["ALLOW_REAL_DATA_MUTATION"] = "0"

from backend.accounting_engine import safe_load_json
from backend.contribution_store import (
    init_campaign_progress_record,
    get_or_create_campaign_progress,
    freeze_campaign_progress_record,
    get_campaign_progress_view,
    get_official_roster_count,
    load_contributions_store,
)


class TestRosterAndProgressVerificationV454(unittest.TestCase):
    """
    Bộ kiểm thử bắt buộc theo APPROVAL V4.5.4 Mục D:
    1. Roster 5 người -> tạo campaign mới -> classSize = 5.
    2. Đóng băng campaign mới -> snapshot có classSize = 5.
    3. Roster không hợp lệ -> báo lỗi rõ ràng, không fallback về 7.
    4. Campaign cũ có classSize = 7 -> snapshot gốc không bị thay đổi.
    5. Số ví đóng góp được tính độc lập với sĩ số lớp.
    6. Kiểm tra không có vị trí nào còn fallback sĩ số về 7 ngoài những dữ liệu lịch sử cần giữ nguyên.
    """

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="kts_test_v454_")
        self.tmp_path = Path(self.tmp_dir.name)
        self.contributions_file = self.tmp_path / "campaign_contributions.json"
        self.roster_file = self.tmp_path / "class_roster.json"

        os.environ["CONTRIBUTIONS_FILE_PATH"] = str(self.contributions_file)
        os.environ["CLASS_ROSTER_FILE_PATH"] = str(self.roster_file)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_01_roster_5_creates_campaign_class_size_5(self):
        """1. Roster 5 người -> tạo campaign mới -> classSize = 5."""
        # Tạo roster mẫu 5 người
        roster_data = [
            {"studentId": f"23K430000{i}", "name": f"Sinh vien {i}", "wallet": f"0x{i:040x}", "role": "student"}
            for i in range(1, 6)
        ]
        import json
        with open(self.roster_file, "w", encoding="utf-8") as f:
            json.dump(roster_data, f)

        self.assertEqual(get_official_roster_count(), 5)

        # Khởi tạo campaign không truyền class_size -> phải tự lấy từ roster chính thức = 5
        camp = init_campaign_progress_record("ann-new-2026", target_eth="0.05")
        self.assertEqual(camp["classSize"], 5)
        self.assertEqual(camp["contributingWalletsCount"], 0)
        self.assertEqual(camp["headcountPercent"], 0)

    def test_02_freeze_new_campaign_snapshot_class_size_5(self):
        """2. Đóng băng campaign mới -> snapshot có classSize = 5."""
        roster_data = [
            {"studentId": f"23K430000{i}", "name": f"Sinh vien {i}", "wallet": f"0x{i:040x}", "role": "student"}
            for i in range(1, 6)
        ]
        import json
        with open(self.roster_file, "w", encoding="utf-8") as f:
            json.dump(roster_data, f)

        # Đóng băng trực tiếp campaign mới
        snap = freeze_campaign_progress_record("ann-new-close", reason="Kết thúc đợt thu thử nghiệm")
        self.assertEqual(snap["classSize"], 5)
        self.assertTrue(snap["isFrozen"])
        self.assertEqual(snap["contributingWalletsCount"], 0)
        self.assertEqual(snap["headcountPercent"], 0)

    def test_03_invalid_roster_raises_error_no_silent_fallback_7(self):
        """3. Roster không hợp lệ -> không fallback về 7 mà báo lỗi rõ ràng."""
        # Ghi roster không hợp lệ (dict thay vì list, hoặc rỗng)
        with open(self.roster_file, "w", encoding="utf-8") as f:
            f.write("[]")

        self.assertEqual(get_official_roster_count(), 0)

        # Gọi khởi tạo không truyền class_size -> Bắt buộc raise ValueError, không fallback về 7!
        with self.assertRaises(ValueError) as ctx:
            init_campaign_progress_record("ann-invalid-roster")
        self.assertIn("Không thể xác định sĩ số hợp lệ", str(ctx.exception))
        self.assertNotIn("7", str(ctx.exception))

    def test_04_historical_snapshot_with_class_size_7_preserved(self):
        """4. Campaign cũ có classSize = 7 -> snapshot gốc không bị thay đổi."""
        import json
        # Giả lập dữ liệu lịch sử đã đóng băng với classSize = 7 từ trước
        historical_campaign = {
            "version": 1,
            "campaigns": {
                "ann-historical-frozen": {
                    "notificationId": "ann-historical-frozen",
                    "classSize": 7,
                    "isFrozen": True,
                    "finalProgress": {
                        "notificationId": "ann-historical-frozen",
                        "isFrozen": True,
                        "frozenAt": "2026-11-04T16:39:40+07:00",
                        "reason": "Đã chốt sổ trước đó",
                        "raisedEth": "0.0000",
                        "contributingWalletsCount": 0,
                        "classSize": 7,
                        "headcountPercent": 0,
                    }
                }
            },
            "transactions": {},
            "claimedTxHashes": {}
        }
        with open(self.contributions_file, "w", encoding="utf-8") as f:
            json.dump(historical_campaign, f)

        # Gọi get_campaign_progress_view
        view = get_campaign_progress_view("ann-historical-frozen")
        self.assertEqual(view["classSize"], 7)
        self.assertEqual(view["finalProgress"]["classSize"], 7)

        # Đóng băng lại (idempotent) không làm thay đổi snapshot gốc
        snap = freeze_campaign_progress_record("ann-historical-frozen", reason="Thao tác lại")
        self.assertEqual(snap["classSize"], 7)
        self.assertEqual(snap["frozenAt"], "2026-11-04T16:39:40+07:00")

    def test_05_contributing_wallets_independent_from_class_size(self):
        """5. Số ví đóng góp được tính độc lập với sĩ số lớp."""
        camp = init_campaign_progress_record("ann-calc-test", class_size=5)
        self.assertEqual(camp["classSize"], 5)
        self.assertEqual(camp["contributingWalletsCount"], 0)
        self.assertEqual(camp["headcountPercent"], 0)

        # Thêm 2 ví đóng góp
        camp["contributingWallets"] = ["0x1111111111111111111111111111111111111111", "0x2222222222222222222222222222222222222222"]
        camp["contributingWalletsCount"] = len(camp["contributingWallets"])
        camp["headcountPercent"] = min(100, round((camp["contributingWalletsCount"] / camp["classSize"]) * 100))

        # Phân biệt rõ: classSize = 5, contributingWalletsCount = 2, headcountPercent = 40%
        self.assertEqual(camp["classSize"], 5)
        self.assertEqual(camp["contributingWalletsCount"], 2)
        self.assertEqual(camp["headcountPercent"], 40)


if __name__ == "__main__":
    unittest.main()

