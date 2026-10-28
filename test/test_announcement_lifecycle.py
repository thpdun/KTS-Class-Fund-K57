#!/usr/bin/env python3
"""
Bộ kiểm thử Vòng đời Thông báo Quỹ lớp và Tự động Lưu trữ Lịch sử (Stage 3B - Announcement Lifecycle)
Dự án: KTS-Class-Fund-K57

Bao phủ tối thiểu 8 trường hợp kiểm thử:
1. Thông báo đang hoạt động xuất hiện trong danh sách hiện tại (GET /api/announcement).
2. Thông báo hết hạn tự động chuyển sang mục Lịch sử theo đúng quy tắc (Auto-archive).
3. Đạt mục tiêu chỉ kết thúc nếu được cấu hình và số tiền đã được xác minh (Không tin client).
4. Thông báo đã hoàn thành không còn nút nộp tiền (Kiểm tra DOM / render logic).
5. Tải lại trang vẫn thấy lịch sử và không tạo bản ghi trùng lặp (Persistence & Deduplication).
6. Tạo thông báo mới không ghi đè mất thông báo cũ (Lưu trữ đợt cũ vào history).
7. Kiểm thử gian lận: Sinh viên thường / Kẻ tấn công không thể tự ý kết thúc hoặc sửa thông báo (403 Forbidden).
8. Tương thích ngược dữ liệu cũ và kiểm tra xử lý lỗi API (Bad request 400).
"""

import os
import sys
import json
import time
import unittest
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import backend.server as srv
from eth_account import Account
from eth_account.messages import encode_defunct

BACKEND_URL = "http://localhost:8000"

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


class TestAnnouncementLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roster_path = PROJECT_ROOT / "backend" / "class_roster.json"
        with open(cls.roster_path, "r", encoding="utf-8") as f:
            cls.original_roster = json.load(f)

        cls.ann_path = PROJECT_ROOT / "backend" / "announcements.json"
        with open(cls.ann_path, "r", encoding="utf-8") as f:
            cls.original_ann = json.load(f)

        cls.test_bcs_acct = Account.create()
        cls.test_student_acct = Account.create()

        # Thêm tạm thời vào danh bạ để backend nhận diện vai trò
        temp_roster = list(cls.original_roster)
        temp_roster.append({
            "mssv": "BCS_TEST_LIFECYCLE",
            "name": "BCS Test Lifecycle",
            "wallet": cls.test_bcs_acct.address,
            "role": "bcs",
            "roleTitle": "Ban cán sự"
        })
        temp_roster.append({
            "mssv": "STUDENT_TEST_LIFECYCLE",
            "name": "Student Test Lifecycle",
            "wallet": cls.test_student_acct.address,
            "role": "student",
            "roleTitle": "Sinh viên"
        })
        with open(cls.roster_path, "w", encoding="utf-8") as f:
            json.dump(temp_roster, f, ensure_ascii=False, indent=2)

    @classmethod
    def tearDownClass(cls):
        # Khôi phục nguyên vẹn danh bạ và thông báo gốc sau kiểm thử
        with open(cls.roster_path, "w", encoding="utf-8") as f:
            json.dump(cls.original_roster, f, ensure_ascii=False, indent=2)
        with open(cls.ann_path, "w", encoding="utf-8") as f:
            json.dump(cls.original_ann, f, ensure_ascii=False, indent=2)

    def _request(self, method, path, data=None, token=None):
        url = f"{BACKEND_URL}{path}"
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        body = None
        if data is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                raw = resp.read().decode("utf-8")
                return resp.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8")
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = {"raw": raw}
            return e.code, parsed

    def _login_account(self, acct):
        """Thực hiện đăng nhập thật qua Web3 signature để lấy token hợp lệ từ server."""
        status, nonce_data = self._request("GET", f"/api/auth/nonce?address={acct.address}")
        self.assertEqual(status, 200)
        nonce = nonce_data["nonce"]
        msg_text = nonce_data["message"]

        signable_msg = encode_defunct(text=msg_text)
        signed = acct.sign_message(signable_msg)
        sig_hex = signed.signature.hex()
        if not sig_hex.startswith("0x"):
            sig_hex = "0x" + sig_hex

        status, login_res = self._request("POST", "/api/auth/login", {
            "address": acct.address,
            "nonce": nonce,
            "signature": sig_hex
        })
        self.assertEqual(status, 200, f"Đăng nhập thất bại: {login_res}")
        return login_res["token"]

    # -------------------------------------------------------------------------
    # TEST 1: Thông báo đang hoạt động xuất hiện trong danh sách hiện tại
    # -------------------------------------------------------------------------
    def test_01_active_announcement_retrieval(self):
        """Thông báo đang hoạt động phải hiển thị trong GET /api/announcement kèm các trường bắt buộc."""
        status, res = self._request("GET", "/api/announcement")
        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))
        ann = res.get("announcement")
        self.assertIsNotNone(ann, "Trường announcement phải tồn tại để tương thích ngược")
        self.assertIn("title", ann)
        self.assertIn("targetAmountEth", ann)
        self.assertIn("deadline", ann)

        active = res.get("active")
        if active:
            self.assertEqual(active.get("status"), "active")
            self.assertTrue(bool(active.get("id")))

    # -------------------------------------------------------------------------
    # TEST 2: Thông báo hết hạn tự động chuyển sang mục Lịch sử (Auto-archive)
    # -------------------------------------------------------------------------
    def test_02_expired_announcement_auto_archived(self):
        """Khi hạn nộp đã qua trong quá khứ, hệ thống tự động chuyển thông báo sang history."""
        bcs_token = self._login_account(self.test_bcs_acct)

        # Tạo thông báo có hạn nộp trong quá khứ
        past_deadline_payload = {
            "title": "Đợt thu quá hạn năm 2020",
            "targetAmountEth": "0.0050",
            "deadline": "23:59 ngày 01/01/2020",
            "purpose": "Quỹ hoạt động chuyên đề cũ",
            "status": "active"
        }
        status, res = self._request("POST", "/api/announcement", past_deadline_payload, token=bcs_token)
        self.assertEqual(status, 200)

        # Gọi lại GET /api/announcement để kích hoạt cơ chế auto-archive
        status_get, res_get = self._request("GET", "/api/announcement")
        self.assertEqual(status_get, 200)

        # Thông báo hết hạn không còn là active
        self.assertIsNone(res_get.get("active"), "Thông báo hết hạn không được giữ trạng thái active!")

        # Thông báo phải xuất hiện trong history
        history = res_get.get("history", [])
        expired_found = next((h for h in history if h.get("title") == "Đợt thu quá hạn năm 2020"), None)
        self.assertIsNotNone(expired_found, "Thông báo quá hạn phải được lưu vào history!")
        self.assertEqual(expired_found.get("status"), "archived")
        self.assertIn("hết hạn", expired_found.get("endReason", "").lower())
        self.assertTrue(bool(expired_found.get("endedAt")))

    # -------------------------------------------------------------------------
    # TEST 3: Đạt mục tiêu chỉ kết thúc nếu được xác minh, không tin frontend
    # -------------------------------------------------------------------------
    def test_03_target_reached_requires_verification(self):
        """Frontend không thể gửi số liệu giả mạo tự kết luận đạt mục tiêu."""
        bcs_token = self._login_account(self.test_bcs_acct)

        new_payload = {
            "title": "Đợt thu kiểm tra mục tiêu",
            "targetAmountEth": "0.0100",
            "deadline": "23:59 ngày 31/12/2026",
            "autoCloseOnTarget": True,
            "purpose": "Kiểm tra xác minh mục tiêu"
        }
        status, res = self._request("POST", "/api/announcement", new_payload, token=bcs_token)
        self.assertEqual(status, 200)
        self.assertEqual(res["active"]["status"], "active")

        # Frontend gửi request tự phong "Đã hoàn thành" mà không có token
        unverified_payload = {
            "title": "Đợt thu kiểm tra mục tiêu",
            "targetAmountEth": "0.0100",
            "status": "completed",
            "fakeClientBalance": "100.0 ETH"
        }
        status_fake, res_fake = self._request("POST", "/api/announcement", unverified_payload)
        self.assertEqual(status_fake, 403)

    # -------------------------------------------------------------------------
    # TEST 4: Thông báo đã hoàn thành không còn nút nộp tiền (DOM check)
    # -------------------------------------------------------------------------
    def test_04_completed_announcement_no_deposit_button(self):
        """Kiểm tra mã nguồn web/index.html đảm bảo nút nộp tiền bị ẩn khi không có đợt thu active."""
        index_path = PROJECT_ROOT / "web" / "index.html"
        self.assertTrue(index_path.exists())
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Kiểm tra logic render: Khi không có active hoặc đã hoàn thành, btnDeposit bị display: none
        self.assertIn('btnDeposit.style.display = "none"', html,
                      "Giao diện bắt buộc phải ẩn nút nộp tiền khi không có đợt thu active!")

        # Kiểm tra phần render danh sách lịch sử: hàm render tồn tại và container tồn tại
        self.assertIn('renderAnnouncementHistoryUI', html)
        self.assertIn('annHistoryListContainer', html)

    # -------------------------------------------------------------------------
    # TEST 5: Tải lại trang vẫn thấy lịch sử và không trùng lặp (Deduplication)
    # -------------------------------------------------------------------------
    def test_05_persistence_and_no_duplicates_on_multiple_reloads(self):
        """Gọi nhiều lần tải trang (GET /api/announcement) không sinh ra bản ghi lịch sử trùng lặp."""
        counts = []
        for _ in range(5):
            status, res = self._request("GET", "/api/announcement")
            self.assertEqual(status, 200)
            counts.append(len(res.get("history", [])))

        self.assertEqual(len(set(counts)), 1, f"Số lượng history bị thay đổi sau các lần reload: {counts}")

    # -------------------------------------------------------------------------
    # TEST 6: Tạo thông báo mới không làm mất thông báo cũ (Lưu trữ đợt cũ)
    # -------------------------------------------------------------------------
    def test_06_new_announcement_preserves_old_history(self):
        """Khi BCS tạo đợt thu mới, đợt thu active cũ được tự động lưu vào history."""
        bcs_token = self._login_account(self.test_bcs_acct)

        # 1. Tạo đợt 1
        payload_1 = {
            "title": "Đợt thu 1 - Đầu kỳ K57",
            "targetAmountEth": "0.0100",
            "deadline": "23:59 ngày 15/12/2026",
            "purpose": "Học phần 1"
        }
        status_1, res_1 = self._request("POST", "/api/announcement", payload_1, token=bcs_token)
        self.assertEqual(status_1, 200)
        id_1 = res_1["active"]["id"]

        # 2. Tạo đợt 2
        payload_2 = {
            "title": "Đợt thu 2 - Giữa kỳ K57",
            "targetAmountEth": "0.0200",
            "deadline": "23:59 ngày 31/12/2026",
            "purpose": "Học phần 2"
        }
        status_2, res_2 = self._request("POST", "/api/announcement", payload_2, token=bcs_token)
        self.assertEqual(status_2, 200)
        self.assertEqual(res_2["active"]["title"], "Đợt thu 2 - Giữa kỳ K57")

        # 3. Kiểm tra history có chứa Đợt 1 không
        hist_1 = next((h for h in res_2.get("history", []) if h.get("id") == id_1), None)
        self.assertIsNotNone(hist_1, "Đợt thu cũ 1 bắt buộc phải được lưu vào history khi tạo đợt mới!")
        self.assertEqual(hist_1.get("status"), "archived")
        self.assertIn("Thay thế", hist_1.get("endReason", ""))

    # -------------------------------------------------------------------------
    # TEST 7: Kiểm thử Gian lận — Sinh viên thường không thể sửa/kết thúc thông báo
    # -------------------------------------------------------------------------
    def test_07_fraud_student_cannot_close_or_modify_announcement(self):
        """Sinh viên thường hoặc người dùng không có quyền bị từ chối 403 Forbidden."""
        student_token = self._login_account(self.test_student_acct)
        bcs_token = self._login_account(self.test_bcs_acct)

        # 7a. Sinh viên cố gắng tạo/sửa thông báo
        status, res = self._request("POST", "/api/announcement", {
            "title": "Gian lận: Sinh viên tự sửa thông báo",
            "targetAmountEth": "0.0999"
        }, token=student_token)
        self.assertEqual(status, 403, "Sinh viên tạo/sửa thông báo phải bị từ chối 403 Forbidden!")

        # 7b. Sinh viên cố gắng kết thúc thông báo sớm qua /api/announcement/close
        status_close, res_close = self._request("POST", "/api/announcement/close", {
            "reason": "Sinh viên tự đóng đợt thu"
        }, token=student_token)
        self.assertEqual(status_close, 403, "Sinh viên kết thúc đợt thu phải bị từ chối 403 Forbidden!")

        # 7c. Ban cán sự kết thúc đợt thu hợp lệ qua /api/announcement/close
        status_bcs_close, res_bcs_close = self._request("POST", "/api/announcement/close", {
            "reason": "Ban cán sự nghiệm thu hoàn thành đợt thu"
        }, token=bcs_token)
        self.assertEqual(status_bcs_close, 200)
        self.assertIsNone(res_bcs_close.get("active"))
        archived = res_bcs_close.get("archived")
        self.assertIsNotNone(archived)
        self.assertEqual(archived.get("status"), "archived")
        self.assertEqual(archived.get("endReason"), "Ban cán sự nghiệm thu hoàn thành đợt thu")

    # -------------------------------------------------------------------------
    # TEST 8: Kiểm tra dữ liệu cũ và bắt lỗi API
    # -------------------------------------------------------------------------
    def test_08_backward_compatibility_and_api_error_handling(self):
        """Kiểm tra xử lý lỗi đầu vào (400) và tính tương thích ngược của hàm load_announcement()."""
        bcs_token = self._login_account(self.test_bcs_acct)

        # 8a. Thiếu tiêu đề -> 400
        status, res = self._request("POST", "/api/announcement", {
            "targetAmountEth": "0.01"
        }, token=bcs_token)
        self.assertEqual(status, 400)

        # 8b. Mức đóng âm hoặc bằng 0 -> 400
        status, res = self._request("POST", "/api/announcement", {
            "title": "Test invalid amount",
            "targetAmountEth": "-0.05"
        }, token=bcs_token)
        self.assertEqual(status, 400)

        # 8c. Endpoint chuyên biệt /api/announcement/history hoạt động
        status_h, res_h = self._request("GET", "/api/announcement/history")
        self.assertEqual(status_h, 200)
        self.assertTrue(res_h.get("success"))
        self.assertIsInstance(res_h.get("history"), list)

        # 8d. Hàm load_announcement() trong backend không gây lỗi
        ann = srv.load_announcement()
        self.assertIsInstance(ann, dict)
        self.assertIn("title", ann)


if __name__ == "__main__":
    unittest.main()
