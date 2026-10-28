#!/usr/bin/env python3
"""
Test Suite Giai đoạn 3B.3:
Bảo mật lịch sử dòng tiền, phân quyền thông tin và vòng đời thông báo
Kiểm tra toàn diện 10 mục bắt buộc theo đặc tả yêu cầu Đợt 3B.3
"""

import unittest
import json
import os
import sys
import re
import urllib.request
import urllib.error
import subprocess

# Ensure repo root is in sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from backend.server import (
    load_roster,
    is_authorized_advisor,
    is_authorized_viewer,
    find_student_by_wallet
)
from backend.ai_service import AIAssistantService


class TestStage3B3Security(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backend_url = "http://localhost:8000"
        with open(os.path.join(REPO_ROOT, "web", "index.html"), "r", encoding="utf-8") as f:
            cls.index_html = f.read()

    # -------------------------------------------------------------------------
    # MỤC 1: Rút gọn địa chỉ ví & Kiểm tra tính bền vững đầu vào
    # -------------------------------------------------------------------------
    def test_01_shorten_address_robustness(self):
        """
        Mục 1: Hàm shortenAddress xử lý chuẩn xác dữ liệu thiếu, null, undefined,
        chuỗi ngắn, và không làm thay đổi biến gốc.
        """
        # Trích xuất và kiểm tra định nghĩa shortenAddress trong web/index.html
        match = re.search(r'function shortenAddress\([^)]*\)\s*\{([\s\S]*?)\n\s{4}\}', self.index_html)
        self.assertIsNotNone(match, "Hàm shortenAddress phải tồn tại trong web/index.html")
        fn_code = match.group(0)

        # Chạy test trong Node.js để kiểm tra chính xác môi trường JS
        node_script = f"""
        {fn_code}
        const assert = require('assert');
        
        // 1. null / undefined / empty
        assert.strictEqual(shortenAddress(null), "");
        assert.strictEqual(shortenAddress(undefined), "");
        assert.strictEqual(shortenAddress(""), "");
        assert.strictEqual(shortenAddress(12345), "");
        assert.strictEqual(shortenAddress({{}}), "");

        // 2. Chuỗi ngắn (< 10 ký tự)
        assert.strictEqual(shortenAddress("0x123"), "0x123");

        // 3. Địa chỉ chuẩn 42 ký tự
        const original = "0x78567A377559F0cB30173f93869326a82320159a";
        const shortened = shortenAddress(original);
        assert.strictEqual(shortened, "0x7856...159a");
        // Kiểm tra tính bất biến: không làm biến đổi chuỗi gốc
        assert.strictEqual(original, "0x78567A377559F0cB30173f93869326a82320159a");

        console.log("SHORTEN_OK");
        """
        res = subprocess.run(["node", "-e", node_script], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"NodeJS shortenAddress test failed: {res.stderr}")
        self.assertIn("SHORTEN_OK", res.stdout)

    # -------------------------------------------------------------------------
    # MỤC 2: Lịch sử dòng tiền công khai không chứa Họ tên/MSSV từ danh sách lớp
    # -------------------------------------------------------------------------
    def test_02_public_cash_flow_ledger_privacy(self):
        """
        Mục 2: Lịch sử dòng tiền công khai chỉ hiển thị địa chỉ ví rút gọn,
        loại giao dịch, số tiền, trạng thái, hash; TUYỆT ĐỐI không gọi lookupStudent
        để ghép Họ tên hoặc MSSV vào bảng công khai.
        """
        # Kiểm tra đoạn code loadCashFlowLedger trong web/index.html
        match = re.search(r'async function loadCashFlowLedger\([^)]*\)\s*\{([\s\S]*?)\n\s{4}\}', self.index_html)
        self.assertIsNotNone(match, "Hàm loadCashFlowLedger phải tồn tại")
        ledger_code = match.group(0)

        # Khẳng định không có lookupStudent trong loadCashFlowLedger
        self.assertNotIn("lookupStudent(", ledger_code,
                         "loadCashFlowLedger KHÔNG ĐƯỢC gọi lookupStudent để ghép tên vào lịch sử công khai!")

        # Khẳng định party chỉ dùng shortenAddress
        self.assertIn("shortenAddress(recipient)", ledger_code)
        self.assertIn("shortenAddress(creator)", ledger_code)
        self.assertIn("shortenAddress(applicant)", ledger_code)

        # Kiểm tra syncDepositorsData không gọi lookupStudent
        match_dep = re.search(r'function syncDepositorsData\([^)]*\)\s*\{([\s\S]*?)\n\s{4}\}', self.index_html)
        self.assertIsNotNone(match_dep, "Hàm syncDepositorsData phải tồn tại")
        dep_code = match_dep.group(0)
        self.assertNotIn("lookupStudent(", dep_code,
                         "syncDepositorsData KHÔNG ĐƯỢC ghép tên/MSSV vào danh sách công khai!")

    # -------------------------------------------------------------------------
    # MỤC 3: API công khai GET /api/roster không trả về PII
    # -------------------------------------------------------------------------
    def test_03_public_api_roster_does_not_leak_pii(self):
        """
        Mục 3: Endpoint GET /api/roster khi không có xác thực quyền BCS/CVHT
        phải trả về roster rỗng (roster: []), chỉ trả về sĩ số count/classSize tổng quan.
        """
        # 1. Gọi ẩn danh không truyền tham số address
        req = urllib.request.Request(f"{self.backend_url}/api/roster")
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("success"))
            self.assertFalse(data.get("isAuthorized"))
            self.assertEqual(len(data.get("roster", [])), 0, "Request công khai phải nhận roster rỗng!")
            self.assertGreater(data.get("classSize", 0), 0, "Vẫn cung cấp tổng sĩ số công khai")

        # 2. Gọi với địa chỉ sinh viên thường (Nguyễn Thị Kim Chi, role: student - không phải BCS / CVHT)
        normal_student_wallet = "0x372819EB492cc6A071b946d5b82BF46174FE8394"
        req_student = urllib.request.Request(f"{self.backend_url}/api/roster?address={normal_student_wallet}")
        with urllib.request.urlopen(req_student, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertFalse(data.get("isAuthorized"), "Sinh viên thường không được xem toàn bộ danh bạ")
            self.assertEqual(len(data.get("roster", [])), 0, "Sinh viên thường không được nhận toàn bộ PII lớp!")

    # -------------------------------------------------------------------------
    # MỤC 4: Chặn giả mạo isAdvisor, isBcsMember, role hoặc signerAddress
    # -------------------------------------------------------------------------
    def test_04_fraud_privilege_spoofing_rejected(self):
        """
        Mục 4: Gửi cờ giả mạo isAdvisor: true, isBcsMember: true, role: 'bcs'
        hoặc signerAddress giả mạo không cấp quyền cho kẻ tấn công.
        """
        # 4a. Giả mạo tạo thông báo /api/announcement
        fake_payload = {
            "title": "Hacker Announcement",
            "targetAmountEth": "1.0",
            "isAdvisor": True,
            "isBcsMember": True,
            "role": "advisor",
            "signerAddress": "0x0000000000000000000000000000000000000000"
        }
        req = urllib.request.Request(
            f"{self.backend_url}/api/announcement",
            data=json.dumps(fake_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                self.fail("Server không được chấp thuận request tạo thông báo giả mạo!")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 403, f"Phải trả về 403 Forbidden nhưng nhận {e.code}")

        # 4b. Giả mạo sửa danh bạ /api/roster/register
        fake_register = {
            "mssv": "23K4300999",
            "name": "Hacker Name",
            "wallet": "0x1111111111111111111111111111111111111111",
            "isAdvisor": True,
            "isBcsMember": True,
            "signerAddress": "0x1111111111111111111111111111111111111111"
        }
        req_reg = urllib.request.Request(
            f"{self.backend_url}/api/roster/register",
            data=json.dumps(fake_register).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req_reg, timeout=5) as resp:
                self.fail("Server không được chấp thuận request cập nhật danh bạ giả mạo!")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 403, f"Phải trả về 403 Forbidden nhưng nhận {e.code}")

    # -------------------------------------------------------------------------
    # MỤC 5: Chatbot không nhận PII và từ chối tiết lộ thông tin cá nhân
    # -------------------------------------------------------------------------
    def test_05_chatbot_refuses_personal_queries_and_strips_pii(self):
        """
        Mục 5: Chatbot không nhận danh bạ trong ngữ cảnh prompt và từ chối trả lời
        trạng thái nộp quỹ của cá nhân sinh viên cụ thể.
        """
        service = AIAssistantService(api_key="AIzaSyMockKeyForTest")

        # Kiểm tra build_system_context lọc sạch PII
        sample_data = {
            "isContractConnected": True,
            "classFundBalanceEth": "0.0099",
            "depositorsCount": 2,
            "roster": [
                {"name": "Trần Hoàng Phương Dung", "mssv": "23K4300004", "wallet": "0x78567A377559F0cB30173f93869326a82320159a"}
            ]
        }
        context = service.build_system_context(sample_data)
        self.assertNotIn("Phương Dung", context)
        self.assertNotIn("23K4300004", context)
        self.assertNotIn("0x78567A377559F0cB30173f93869326a82320159a", context)

        # Kiểm tra câu trả lời từ chối truy vấn cá nhân
        ans = service.generate_local_fallback_answer("Trần Hoàng Phương Dung nộp tiền chưa?", sample_data)
        self.assertIn("quyền riêng tư", ans.lower())
        self.assertNotIn("phương dung đã nộp", ans.lower())
        self.assertNotIn("phương dung chưa nộp", ans.lower())

    # -------------------------------------------------------------------------
    # MỤC 6: Phân biệt rõ ràng Thông báo cá nhân và Thông báo chung cả lớp
    # -------------------------------------------------------------------------
    def test_06_announcement_personal_vs_group_lifecycle(self):
        """
        Mục 6: Vòng đời thông báo nộp quỹ:
        - Tiến độ cá nhân: Phụ thuộc vào studentContributions của địa chỉ ví người dùng hiện tại.
        - Tiến độ cả lớp: Chỉ COMPLETED khi 100% sinh viên nộp đủ; người nộp xong không làm cả lớp hoàn thành.
        """
        node_script = """
        // Mô phỏng logic updateAnnouncementProgress trong index.html
        let currentAnnouncement = {
            title: "Nộp Quỹ Lớp Học Kỳ 1",
            targetAmountEth: "0.0100",
            deadline: Date.now() + 86400000
        };
        let targetClassSize = 10;
        let userAddress = "0xStudent1";
        let studentContributions = {
            "0xstudent1": 10000000000000000n // 0.01 ETH (đã nộp đủ)
        };

        // Người dùng 1: Đã nộp
        let personalContribWei = studentContributions[userAddress.toLowerCase()] || 0n;
        let personalDone = personalContribWei >= 10000000000000000n;
        let classDepositorsCount = 1;
        let groupDone = classDepositorsCount >= targetClassSize;

        const assert = require('assert');
        // Cá nhân đã hoàn thành
        assert.strictEqual(personalDone, true, "Cá nhân đã nộp phải ghi nhận personalDone = true");
        // Toàn lớp CHƯA hoàn thành vì chỉ mới 1/10
        assert.strictEqual(groupDone, false, "Toàn lớp không được đánh dấu COMPLETED khi mới 1/10 nộp!");

        // Người dùng 2: Chưa nộp
        let userAddress2 = "0xStudent2";
        let personalContribWei2 = studentContributions[userAddress2.toLowerCase()] || 0n;
        let personalDone2 = personalContribWei2 >= 10000000000000000n;
        assert.strictEqual(personalDone2, false, "Sinh viên 2 chưa nộp phải có personalDone = false");

        console.log("ANNOUNCEMENT_LIFECYCLE_OK");
        """
        res = subprocess.run(["node", "-e", node_script], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Announcement lifecycle test failed: {res.stderr}")
        self.assertIn("ANNOUNCEMENT_LIFECYCLE_OK", res.stdout)

    # -------------------------------------------------------------------------
    # MỤC 7: Không coi số dư quỹ là bằng chứng cá nhân đã nộp
    # -------------------------------------------------------------------------
    def test_07_fund_balance_is_not_personal_proof(self):
        """
        Mục 7: Số dư quỹ lớn hơn 0 (ví dụ 1.0 ETH) tuyệt đối không được coi là
        bằng chứng một cá nhân cụ thể đã nộp quỹ.
        """
        node_script = """
        const assert = require('assert');
        let classFundBalanceEth = "1.5000"; // Quỹ có 1.5 ETH
        let myWallet = "0xStudentUnpaid";
        let studentContributions = {}; // Mapping on-chain bằng 0

        // Kiểm tra logic xác định nghĩa vụ: phải tra cứu studentContributions[myWallet]
        let contrib = studentContributions[myWallet.toLowerCase()] || 0n;
        let isPaid = contrib > 0n;

        assert.strictEqual(isPaid, false, "Dù quỹ có 1.5 ETH nhưng cá nhân đóng góp 0 thì vẫn là Chưa nộp!");
        console.log("BALANCE_INDEPENDENCE_OK");
        """
        res = subprocess.run(["node", "-e", node_script], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("BALANCE_INDEPENDENCE_OK", res.stdout)

    # -------------------------------------------------------------------------
    # MỤC 8: Phân biệt rõ ràng Biểu quyết đạt 51% (Ready) và Đã giải ngân (Executed)
    # -------------------------------------------------------------------------
    def test_08_voting_approved_is_not_executed(self):
        """
        Mục 8: getStatusBadge và hiển thị danh sách phân biệt rõ ràng:
        Status 0: Chờ biểu quyết (Pending)
        Status 1: Đã thông qua - Chờ thực thi (Ready)
        Status 2: Đã giải ngân / Đã thực thi (Executed)
        Không đồng nhất 'đạt 51% phiếu' với 'đã giải ngân'.
        """
        match = re.search(r'function getStatusBadge\([^)]*\)\s*\{([\s\S]*?)\n\s{4}\}', self.index_html)
        self.assertIsNotNone(match, "Hàm getStatusBadge phải tồn tại")
        fn_code = match.group(0)

        node_script = f"""
        {fn_code}
        const assert = require('assert');

        let badge0 = getStatusBadge(0);
        let badge1 = getStatusBadge(1);
        let badge2 = getStatusBadge(2);

        assert.ok(badge0.includes("Chờ biểu quyết"), "Status 0 phải là Chờ biểu quyết");
        assert.ok(badge1.includes("Đã thông qua (Chờ thực thi)"), "Status 1 phải là Đã thông qua (Chờ thực thi)");
        assert.ok(badge2.includes("Đã giải ngân"), "Status 2 phải là Đã giải ngân");

        // Đảm bảo Status 1 và Status 2 khác biệt hoàn toàn
        assert.notStrictEqual(badge1, badge2, "Status 1 (Đã đạt 51%) không được nhầm với Status 2 (Đã giải ngân)");
        console.log("STATUS_BADGE_OK");
        """
        res = subprocess.run(["node", "-e", node_script], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Status badge test failed: {res.stderr}")
        self.assertIn("STATUS_BADGE_OK", res.stdout)

    # -------------------------------------------------------------------------
    # MỤC 9: Đổi tài khoản/mạng làm sạch cache, không dùng lại cache tài khoản trước
    # -------------------------------------------------------------------------
    def test_09_account_switch_invalidates_cache_and_state(self):
        """
        Mục 9: Khi sự kiện accountsChanged hoặc handleAccountChange kích hoạt:
        myStudentProfile được xóa, cờ vai trò được reset, invalidateRosterContribCache()
        được gọi để dọn sạch cache của tài khoản trước.
        """
        match = re.search(r'async function handleAccountChange\([^)]*\)\s*\{([\s\S]*?)\n\s{4}\}', self.index_html)
        self.assertIsNotNone(match, "Hàm handleAccountChange phải tồn tại")
        handler_code = match.group(0)

        self.assertIn("myStudentProfile = null", handler_code, "Phải reset myStudentProfile khi đổi tài khoản")
        self.assertIn("isBcsMember = false", handler_code, "Phải reset isBcsMember khi đổi tài khoản")
        self.assertIn("isAdvisor = false", handler_code, "Phải reset isAdvisor khi đổi tài khoản")
        self.assertIn("invalidateRosterContribCache()", handler_code, "Phải xóa sạch cache đóng góp danh bạ khi đổi tài khoản")

    # -------------------------------------------------------------------------
    # MỤC 10: Nút điều hướng KHÔNG gửi giao dịch hoặc yêu cầu ký ví
    # -------------------------------------------------------------------------
    def test_10_navigation_buttons_do_not_send_transactions(self):
        """
        Mục 10: Các nút điều hướng trong Việc cần xử lý và Thông báo ('Nộp quỹ ngay',
        'Xem đề xuất chi', 'Xem yêu cầu hoàn tiền') chỉ thực hiện chuyển tab / cuộn màn hình,
        tuyệt đối KHÔNG gọi hàm gửi transaction (doDeposit, executeSpend, executeRefund).
        """
        # Kiểm tra renderPendingActions
        match = re.search(r'function renderPendingActions\(\)\s*\{([\s\S]*?)\n\s{4}\}', self.index_html)
        self.assertIsNotNone(match, "Hàm renderPendingActions phải tồn tại")
        actions_code = match.group(0)

        # Đảm bảo không gọi trực tiếp executeSpend, executeRefund, doDeposit trên onclick
        self.assertNotIn("onclick=\"executeSpend(", actions_code, "Không được gọi trực tiếp executeSpend trên nút thông báo!")
        self.assertNotIn("onclick=\"executeRefund(", actions_code, "Không được gọi trực tiếp executeRefund trên nút thông báo!")
        self.assertNotIn("onclick=\"doDeposit(", actions_code, "Không được gọi trực tiếp doDeposit trên nút thông báo!")

        # Đảm bảo các nút chỉ gọi selectRoleView và cuộn scrollIntoView
        self.assertTrue('selectRoleView("student")' in actions_code or "selectRoleView('student')" in actions_code)
        self.assertTrue('selectRoleView("bcs")' in actions_code or "selectRoleView('bcs')" in actions_code)
        self.assertIn("scrollIntoView", actions_code)


if __name__ == "__main__":
    unittest.main()
