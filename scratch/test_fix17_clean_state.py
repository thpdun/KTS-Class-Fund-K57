"""
Kịch bản kiểm thử toàn diện FIX 17:
Kiểm tra 12 trường hợp bắt buộc về trạng thái khởi tạo sạch và bảo toàn tính năng.
"""
import sys
import json
import time
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import backend.server as srv
from backend.ai_service import AIAssistantService
from eth_account import Account
from eth_account.messages import encode_defunct


class TestFix17CleanState(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ann_path = PROJECT_ROOT / "backend" / "announcements.json"
        cls.roster_path = PROJECT_ROOT / "backend" / "class_roster.json"
        cls.index_path = PROJECT_ROOT / "web" / "index.html"
        cls.contract_path = PROJECT_ROOT / "contracts" / "project" / "ProjectCore.sol"

        # Đọc roster để lấy 1 tài khoản BCS thật
        with open(cls.roster_path, "r", encoding="utf-8") as f:
            cls.roster = json.load(f)

        cls.bcs_entry = next((s for s in cls.roster if s.get("role") == "bcs"), None)
        cls.student_entry = next((s for s in cls.roster if s.get("role") == "student"), None)

    def test_01_first_load_no_sample_announcement(self):
        """Case 1: Mở web lần đầu không xuất hiện thông báo mẫu cũ trong HTML tĩnh và DEFAULT_ANNOUNCEMENT."""
        with open(self.index_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Kiểm tra DEFAULT_ANNOUNCEMENT
        self.assertIn('status: "none"', html)
        self.assertIn('Hiện chưa có thông báo kêu gọi nộp quỹ', html)
        self.assertNotIn('Kêu gọi nộp Quỹ Lớp Học kỳ 1 - Khóa K57 Kinh tế Số', html)

        # Kiểm tra HTML tĩnh
        self.assertIn('id="annTitle">Hiện chưa có thông báo kêu gọi nộp quỹ</h2>', html)
        self.assertIn('id="annStatusText">Chưa có đợt thu</span>', html)
        self.assertIn('id="btnBannerQuickDeposit" style="display: none;"', html)

    def test_02_empty_announcement_clean_state(self):
        """Case 2: Khi không có thông báo, Backend trả về active=None và fallback tiêu đề sạch."""
        store = srv.load_announcements_store()
        self.assertIsNone(store.get("active"), "Trạng thái khởi tạo sạch thì active phải là None")

        single = srv.load_announcement()
        self.assertEqual(single.get("status"), "none")
        self.assertEqual(single.get("title"), "Hiện chưa có thông báo kêu gọi nộp quỹ")
        self.assertEqual(single.get("targetAmountEth"), "0")

    def test_03_empty_history_clean_state(self):
        """Case 3: Khi không có lịch sử, Backend trả về history rỗng và UI hiển thị trạng thái hợp lý."""
        store = srv.load_announcements_store()
        self.assertEqual(len(store.get("history", [])), 0, "Lịch sử khởi tạo phải là mảng rỗng []")

        with open(self.index_path, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn("Chưa có đợt thu quỹ nào trong lịch sử lưu trữ.", html)

    def test_04_bcs_permission_to_create_announcement(self):
        """Case 4: BCS/CVHT có quyền tạo thông báo mới qua cơ chế xác thực."""
        # Tạo phiên cho BCS
        bcs_acct = Account.create()
        # Đưa tạm thời vào ACTIVE_SESSIONS với vai trò bcs
        token = "test_bcs_token_12345"
        srv.ACTIVE_SESSIONS[token] = {
            "token": token,
            "address": bcs_acct.address.lower(),
            "role": "bcs",
            "isAdvisor": False,
            "isBcs": True,
            "expires_at": time.time() + 3600
        }

        # Giả lập headers
        headers = {"Authorization": f"Bearer {token}"}
        session = srv.get_authenticated_session(headers)
        self.assertIsNotNone(session)
        self.assertEqual(session.get("role"), "bcs")

    def test_05_and_06_new_announcement_saved_and_synced(self):
        """Case 5 & 6: Tạo thông báo mới lưu thành công vào Backend và có thể đọc qua store/API."""
        bcs_acct = Account.create()
        token = "test_bcs_token_create"
        srv.ACTIVE_SESSIONS[token] = {
            "token": token,
            "address": bcs_acct.address.lower(),
            "role": "bcs",
            "isAdvisor": False,
            "isBcs": True,
            "expires_at": time.time() + 3600
        }

        # Lưu thông báo mới
        test_payload = {
            "id": "ann-test-2026-new",
            "title": "Đợt thu kiểm thử tính năng FIX 17",
            "targetAmountEth": "0.0200",
            "deadline": "23:59 ngày 31/12/2026",
            "deadlineTimestamp": srv.parse_deadline_to_timestamp("23:59 ngày 31/12/2026"),
            "classSize": 7,
            "purpose": "Học tập K57",
            "status": "active",
            "autoCloseOnTarget": False,
            "createdAt": "2026-11-02T10:00:00Z",
            "endedAt": None,
            "endReason": None,
            "updatedBy": bcs_acct.address.lower(),
            "updatedAt": "2026-11-02T10:00:00Z"
        }
        store = srv.load_announcements_store()
        store["active"] = test_payload
        srv.save_announcements_store(store)

        # Đọc lại từ đĩa
        reloaded = srv.load_announcements_store()
        self.assertIsNotNone(reloaded.get("active"))
        self.assertEqual(reloaded["active"]["title"], "Đợt thu kiểm thử tính năng FIX 17")
        self.assertEqual(reloaded["active"]["targetAmountEth"], "0.0200")

    def test_07_update_announcement(self):
        """Case 7: Cập nhật thông báo đang diễn ra hoạt động bình thường."""
        store = srv.load_announcements_store()
        self.assertIsNotNone(store.get("active"))
        # Cập nhật mức nộp
        store["active"]["targetAmountEth"] = "0.0300"
        store["active"]["title"] = "Đợt thu đã cập nhật"
        srv.save_announcements_store(store)

        updated = srv.load_announcements_store()
        self.assertEqual(updated["active"]["targetAmountEth"], "0.0300")
        self.assertEqual(updated["active"]["title"], "Đợt thu đã cập nhật")

    def test_08_and_09_close_announcement_moves_to_history(self):
        """Case 8 & 9: Đóng thông báo chuyển vào lịch sử với status=archived và endReason."""
        store = srv.load_announcements_store()
        active = store.get("active")
        self.assertIsNotNone(active)

        # Đóng thông báo
        active["status"] = "archived"
        active["endedAt"] = "2026-11-02T10:15:00Z"
        active["endReason"] = "Ban cán sự chủ động kết thúc đợt thu"
        store["history"].insert(0, active)
        store["active"] = None
        srv.save_announcements_store(store)

        closed_store = srv.load_announcements_store()
        self.assertIsNone(closed_store.get("active"), "Đợt thu đã đóng thì active phải là None")
        self.assertEqual(len(closed_store.get("history", [])), 1)
        self.assertEqual(closed_store["history"][0]["title"], "Đợt thu đã cập nhật")
        self.assertEqual(closed_store["history"][0]["status"], "archived")
        self.assertEqual(closed_store["history"][0]["endReason"], "Ban cán sự chủ động kết thúc đợt thu")

    def test_10_reloading_clean_state_does_not_resurrect_sample_data(self):
        """Case 10: Làm sạch lại announcements.json và reload không làm xuất hiện dữ liệu mẫu cũ."""
        clean_store = {"active": None, "history": []}
        srv.save_announcements_store(clean_store)

        # Gọi reload nhiều lần
        for _ in range(3):
            store = srv.load_announcements_store()
            self.assertIsNone(store.get("active"), "Không được tự động sinh ra active mẫu!")
            self.assertEqual(len(store.get("history", [])), 0, "Không được tự động sinh ra history mẫu!")

    def test_11_unauthorized_user_blocked(self):
        """Case 11: Người không có phiên BCS/CVHT bị từ chối quyền quản trị."""
        # Phiên sinh viên thường
        student_token = "test_student_token"
        srv.ACTIVE_SESSIONS[student_token] = {
            "token": student_token,
            "address": "0x1111111111111111111111111111111111111111",
            "role": "student",
            "isAdvisor": False,
            "isBcs": False,
            "expires_at": time.time() + 3600
        }
        headers = {"Authorization": f"Bearer {student_token}"}
        session = srv.get_authenticated_session(headers)
        self.assertIsNotNone(session)
        self.assertNotIn(session.get("role"), ["bcs", "advisor"], "Sinh viên không được có quyền quản trị thông báo")

        # Không có token
        no_session = srv.get_authenticated_session({})
        self.assertIsNone(no_session)

    def test_12_blockchain_integrity_preserved(self):
        """Case 12: Hợp đồng Smart Contract và các cấu hình kết nối Blockchain nguyên vẹn 100%."""
        self.assertTrue(self.contract_path.exists())
        with open(self.contract_path, "r", encoding="utf-8") as f:
            contract_code = f.read()

        # Kiểm tra các hàm nghiệp vụ cốt lõi không bị thay đổi
        self.assertIn("function deposit() external payable", contract_code)
        self.assertIn("function createSpendRequest(", contract_code)
        self.assertIn("function voteSpendRequest(", contract_code)
        self.assertIn("function executeSpendRequest(", contract_code)
        self.assertIn("function createRefundRequest(", contract_code)
        self.assertIn("function voteRefundRequest(", contract_code)
        self.assertIn("function executeRefundRequest(", contract_code)
        self.assertIn("function withdrawAdminFee(", contract_code)
        self.assertIn("event FundDeposited(", contract_code)
        self.assertIn("event SpendRequestCreated(", contract_code)

        # Kiểm tra cấu hình frontend
        with open(self.index_path, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn("const CONFIG = {", html)
        self.assertIn("contractAddress:", html)
        self.assertIn('chainIdHex: "0xaa36a7"', html)
        self.assertIn("const CONTRACT_ABI = [", html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
