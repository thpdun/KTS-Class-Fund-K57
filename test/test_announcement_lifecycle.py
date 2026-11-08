#!/usr/bin/env python3
"""
Bộ kiểm thử Vòng đời Thông báo Quỹ lớp & Lưu trữ Nguyên tử Phase 1 V4.4
Dự án: KTS-Class-Fund-K57

Đảm bảo an toàn dữ liệu tuyệt đối:
- 100% kiểm thử chạy hoàn toàn trong `tempfile.TemporaryDirectory()`.
- Khởi chạy HTTPServer cô lập trên cổng động (`127.0.0.1:0`) trỏ vào thư mục tạm.
- Tuyệt đối không tác động đến `backend/announcements.json` và `backend/class_roster.json` thật,
  kể cả khi test bị lỗi hoặc tiến trình bị dừng đột ngột giữa chừng.
"""

import concurrent.futures
import copy
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

import backend.server as srv
from backend.accounting_engine import (
    AUDIT_HASH_LIMITATION_NOTE,
    AUDIT_HASH_SPEC_VERSION,
    GENESIS_PREV_HASH,
    HASH_CHAIN_TAIL_TRUNCATION_NOTE,
    VN_TZ_KEY,
    AtomicStorageError,
    CorruptedStorageError,
    DualLayerFileLock,
    IdempotencyConflictError,
    RevisionConflictError,
    attach_record_audit_hash,
    atomic_write_json,
    classify_transaction_at_timestamp,
    compare_pre_post_migration,
    compute_file_sha256,
    compute_record_sha256,
    ensure_initial_pre_v4_backup,
    eth_to_wei_str,
    get_vn_day_bounds,
    get_vn_tz,
    migrate_v1_to_v2_store,
    parse_deadline_to_vn_timestamp,
    run_dry_run_migration_in_temp,
    safe_load_json,
    verify_json_backup_file,
    verify_record_audit_hash,
    verify_record_hash_chain,
    verify_timestamp_vn,
    wei_to_eth_str,
)
from eth_account import Account
from eth_account.messages import encode_defunct

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REAL_ANNOUNCEMENT_PATH = PROJECT_ROOT / "backend" / "announcements.json"
REAL_ROSTER_PATH = PROJECT_ROOT / "backend" / "class_roster.json"
REAL_PRE_V4_BAK_PATH = PROJECT_ROOT / "backend" / "announcements.pre_v4_migration.bak"


class IsolatedTempServerTestCase(unittest.TestCase):
    """
    Lớp cơ sở khởi tạo môi trường kiểm thử cô lập hoàn toàn trong `tempfile.TemporaryDirectory()`.
    Tuyệt đối không đọc/ghi trực tiếp vào file thật trong quá trình chạy test.
    """

    @classmethod
    def setUpClass(cls):
        # Ghi nhận SHA-256 của dữ liệu thật trước khi chạy test để chứng minh không bị thay đổi
        cls.real_ann_sha256_before = compute_file_sha256(REAL_ANNOUNCEMENT_PATH)
        cls.real_roster_sha256_before = compute_file_sha256(REAL_ROSTER_PATH)

        # Tạo thư mục tạm cô lập cho toàn bộ test class
        cls._temp_dir_obj = tempfile.TemporaryDirectory(prefix="kts_phase1_test_")
        cls.temp_dir = Path(cls._temp_dir_obj.name).resolve()
        cls.temp_ann_path = cls.temp_dir / "announcements.json"
        cls.temp_roster_path = cls.temp_dir / "class_roster.json"

        # Sao chép dữ liệu mẫu ban đầu sang thư mục tạm (chỉ đọc từ file thật)
        cls.fixture_ann_bytes = REAL_ANNOUNCEMENT_PATH.read_bytes()
        shutil.copy2(REAL_ANNOUNCEMENT_PATH, cls.temp_ann_path)
        shutil.copy2(REAL_ROSTER_PATH, cls.temp_roster_path)

        cls.test_bcs_acct = Account.create()
        cls.test_bcs2_acct = Account.create()
        cls.test_student_acct = Account.create()

        with open(cls.temp_roster_path, "r", encoding="utf-8") as f:
            temp_roster = json.load(f)

        temp_roster.append({
            "mssv": "BCS_TEST_LIFECYCLE",
            "name": "BCS Test Lifecycle",
            "wallet": cls.test_bcs_acct.address,
            "role": "bcs",
            "roleTitle": "Ban cán sự",
        })
        temp_roster.append({
            "mssv": "BCS2_TEST_LIFECYCLE",
            "name": "BCS 2 Test Lifecycle",
            "wallet": cls.test_bcs2_acct.address,
            "role": "bcs",
            "roleTitle": "Ban cán sự",
        })
        temp_roster.append({
            "mssv": "STUDENT_TEST_LIFECYCLE",
            "name": "Student Test Lifecycle",
            "wallet": cls.test_student_acct.address,
            "role": "student",
            "roleTitle": "Sinh viên",
        })
        cls.fixture_roster_bytes = json.dumps(temp_roster, ensure_ascii=False, indent=2).encode("utf-8")
        cls.temp_roster_path.write_bytes(cls.fixture_roster_bytes)

        # Cấu hình đường dẫn dữ liệu của backend trỏ vào thư mục tạm
        os.environ["ANNOUNCEMENT_FILE_PATH"] = str(cls.temp_ann_path)
        os.environ["CLASS_ROSTER_FILE_PATH"] = str(cls.temp_roster_path)
        srv.ANNOUNCEMENT_FILE = cls.temp_ann_path
        srv.ROSTER_FILE = cls.temp_roster_path

        # Khởi chạy HTTPServer cô lập trên cổng động (ephemeral port)
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), srv.AIChatRequestHandler)
        cls.port = cls.httpd.server_address[1]
        cls.backend_url = f"http://127.0.0.1:{cls.port}"
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.httpd.shutdown()
            cls.httpd.server_close()
        finally:
            cls._temp_dir_obj.cleanup()

        # Kiểm chứng bắt buộc: Dữ liệu thật không bị thay đổi dù chỉ 1 byte
        ann_sha_after = compute_file_sha256(REAL_ANNOUNCEMENT_PATH)
        roster_sha_after = compute_file_sha256(REAL_ROSTER_PATH)
        assert ann_sha_after == cls.real_ann_sha256_before, "LỖI NGHIÊM TRỌNG: announcements.json thật bị thay đổi!"
        assert roster_sha_after == cls.real_roster_sha256_before, "LỖI NGHIÊM TRỌNG: class_roster.json thật bị thay đổi!"

    def setUp(self):
        # Đảm bảo biến môi trường luôn trỏ vào thư mục tạm của class hiện tại
        os.environ["ANNOUNCEMENT_FILE_PATH"] = str(self.temp_ann_path)
        os.environ["CLASS_ROSTER_FILE_PATH"] = str(self.temp_roster_path)
        srv.ANNOUNCEMENT_FILE = self.temp_ann_path
        srv.ROSTER_FILE = self.temp_roster_path

        # Khôi phục trạng thái dữ liệu mẫu sạch trước MỖI test case (W5: Cô lập hoàn toàn giữa các test)
        with DualLayerFileLock(self.temp_ann_path):
            for extra_file in self.temp_dir.glob("announcements*.bak"):
                try:
                    extra_file.unlink()
                except OSError:
                    pass
            self.temp_ann_path.write_bytes(self.fixture_ann_bytes)

        with DualLayerFileLock(self.temp_roster_path):
            for extra_file in self.temp_dir.glob("class_roster*.bak"):
                try:
                    extra_file.unlink()
                except OSError:
                    pass
            self.temp_roster_path.write_bytes(self.fixture_roster_bytes)

    def _request(self, method: str, path: str, data=None, token: str = None):
        url = f"{self.backend_url}{path}"
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
            "signature": sig_hex,
        })
        self.assertEqual(status, 200, f"Đăng nhập thất bại: {login_res}")
        return login_res["token"]


# =============================================================================
# NHÓM 1: KIỂM THỬ VÒNG ĐỜI THÔNG BÁO (CHẠY TRÊN THƯ MỤC TẠM)
# =============================================================================

class TestAnnouncementLifecycle(IsolatedTempServerTestCase):
    def test_01_active_announcement_retrieval(self):
        """Thông báo trả về từ GET /api/announcement có đầy đủ trường tương thích ngược và revision."""
        status, res = self._request("GET", "/api/announcement")
        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))
        self.assertGreaterEqual(res.get("revision", 0), 1)
        self.assertEqual(res.get("timezone"), "Asia/Ho_Chi_Minh")
        ann = res.get("announcement")
        self.assertIsNotNone(ann)
        self.assertIn("title", ann)
        self.assertIn("targetAmountEth", ann)
        self.assertIn("deadline", ann)

    def test_02_expired_announcement_auto_archived(self):
        """Khi hạn nộp đã qua trong quá khứ, hệ thống tự động chuyển sang trạng thái expired và đưa vào history."""
        bcs_token = self._login_account(self.test_bcs_acct)

        past_deadline_payload = {
            "title": "Đợt thu quá hạn năm 2020",
            "targetAmountEth": "0.0050",
            "deadline": "23:59 ngày 01/01/2020",
            "purpose": "Quỹ hoạt động chuyên đề cũ",
            "status": "active",
        }
        status, res = self._request("POST", "/api/announcement", past_deadline_payload, token=bcs_token)
        self.assertEqual(status, 200)

        status_get, res_get = self._request("GET", "/api/announcement")
        self.assertEqual(status_get, 200)
        self.assertIsNone(res_get.get("active"), "Thông báo hết hạn không được giữ trạng thái active!")

        history = res_get.get("history", [])
        expired_found = next((h for h in history if h.get("title") == "Đợt thu quá hạn năm 2020"), None)
        self.assertIsNotNone(expired_found, "Thông báo quá hạn phải được lưu vào history!")
        self.assertEqual(expired_found.get("status"), "expired")
        self.assertIn("hết hạn", expired_found.get("endReason", "").lower())
        self.assertTrue(bool(expired_found.get("endedAt")))

    def test_03_target_reached_requires_verification(self):
        """Frontend không thể gửi số liệu giả mạo tự kết luận đạt mục tiêu mà không có quyền."""
        bcs_token = self._login_account(self.test_bcs_acct)

        new_payload = {
            "title": "Đợt thu kiểm tra mục tiêu",
            "targetAmountEth": "0.0100",
            "deadline": "23:59 ngày 31/12/2026",
            "autoCloseOnTarget": True,
            "purpose": "Kiểm tra xác minh mục tiêu",
        }
        status, res = self._request("POST", "/api/announcement", new_payload, token=bcs_token)
        self.assertEqual(status, 200)
        self.assertEqual(res["active"]["status"], "active")

        unverified_payload = {
            "title": "Đợt thu kiểm tra mục tiêu",
            "targetAmountEth": "0.0100",
            "status": "completed",
            "fakeClientBalance": "100.0 ETH",
        }
        status_fake, _ = self._request("POST", "/api/announcement", unverified_payload)
        self.assertEqual(status_fake, 403)

    def test_04_completed_announcement_no_deposit_button(self):
        """Kiểm tra mã nguồn web/index.html đảm bảo nút nộp tiền bị ẩn khi không có đợt thu active."""
        index_path = PROJECT_ROOT / "web" / "index.html"
        self.assertTrue(index_path.exists())
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn('btnDeposit.style.display = "none"', html)
        self.assertIn("renderAnnouncementHistoryUI", html)
        self.assertIn("annHistoryListContainer", html)

    def test_05_persistence_and_no_duplicates_on_multiple_reloads(self):
        """Gọi nhiều lần tải trang (GET /api/announcement) không sinh ra bản ghi lịch sử trùng lặp."""
        counts = []
        for _ in range(5):
            status, res = self._request("GET", "/api/announcement")
            self.assertEqual(status, 200)
            counts.append(len(res.get("history", [])))

        self.assertEqual(len(set(counts)), 1, f"Số lượng history bị thay đổi sau các lần reload: {counts}")

    def test_06_new_announcement_preserves_old_history(self):
        """Khi BCS tạo đợt thu mới, đợt thu cũ vẫn giữ active độc lập (nhiều active cùng lúc) trừ khi chủ động đóng."""
        bcs_token = self._login_account(self.test_bcs_acct)

        payload_1 = {
            "title": "Đợt thu 1 - Đầu kỳ K57",
            "targetAmountEth": "0.0100",
            "deadline": "23:59 ngày 15/12/2026",
            "purpose": "Học phần 1",
        }
        status_1, res_1 = self._request("POST", "/api/announcement", payload_1, token=bcs_token)
        self.assertEqual(status_1, 200)
        id_1 = res_1["announcement"]["id"]

        payload_2 = {
            "title": "Đợt thu 2 - Giữa kỳ K57",
            "targetAmountEth": "0.0200",
            "deadline": "23:59 ngày 31/12/2026",
            "purpose": "Học phần 2",
        }
        status_2, res_2 = self._request("POST", "/api/announcement", payload_2, token=bcs_token)
        self.assertEqual(status_2, 200)
        id_2 = res_2["announcement"]["id"]

        # Yêu cầu mới: Cho phép nhiều active đồng thời, không tự động đóng đợt cũ khi tạo đợt mới
        active_ids = [a["id"] for a in res_2.get("activeNotifications", [])]
        self.assertIn(id_1, active_ids, "Đợt thu 1 phải vẫn còn active!")
        self.assertIn(id_2, active_ids, "Đợt thu 2 phải có trạng thái active!")

        # Khi BCS chủ động kết thúc đợt 1 qua ID: đợt 1 vào history, đợt 2 vẫn active
        status_close, res_close = self._request("POST", "/api/announcement/close", {
            "id": id_1,
            "reason": "Ban cán sự chủ động kết thúc đợt 1"
        }, token=bcs_token)
        self.assertEqual(status_close, 200)
        hist_1 = next((h for h in res_close.get("history", []) if h.get("id") == id_1), None)
        self.assertIsNotNone(hist_1)
        self.assertEqual(hist_1.get("status"), "archived")

        # Đợt 2 vẫn tiếp tục active
        active_after = [a["id"] for a in res_close.get("activeNotifications", [])]
        self.assertIn(id_2, active_after)
        self.assertNotIn(id_1, active_after)

    def test_07_fraud_student_cannot_close_or_modify_announcement(self):
        """Sinh viên thường hoặc người dùng không có quyền bị từ chối 403 Forbidden (độc lập thứ tự chạy)."""
        student_token = self._login_account(self.test_student_acct)
        bcs_token = self._login_account(self.test_bcs_acct)

        # Khởi tạo một đợt thu đang mở với hạn nộp tương lai để kiểm thử độc lập hoàn toàn với test_06
        status_init, res_init = self._request("POST", "/api/announcement", {
            "title": "Đợt thu kiểm thử phân quyền đóng/sửa",
            "targetAmountEth": "0.0150",
            "deadline": "23:59 ngày 31/12/2026",
            "purpose": "Kiểm thử chống gian lận phân quyền",
        }, token=bcs_token)
        self.assertEqual(status_init, 200)
        self.assertIsNotNone(res_init.get("active"))

        status, _ = self._request("POST", "/api/announcement", {
            "title": "Gian lận: Sinh viên tự sửa thông báo",
            "targetAmountEth": "0.0999",
        }, token=student_token)
        self.assertEqual(status, 403)

        status_close, _ = self._request("POST", "/api/announcement/close", {
            "reason": "Sinh viên tự đóng đợt thu",
        }, token=student_token)
        self.assertEqual(status_close, 403)

        status_bcs_close, res_bcs_close = self._request("POST", "/api/announcement/close", {
            "reason": "Ban cán sự nghiệm thu hoàn thành đợt thu",
        }, token=bcs_token)
        self.assertEqual(status_bcs_close, 200)
        self.assertIsNone(res_bcs_close.get("active"))
        archived = res_bcs_close.get("archived")
        self.assertIsNotNone(archived)
        self.assertEqual(archived.get("status"), "archived")

    def test_08_backward_compatibility_and_api_error_handling(self):
        """Kiểm tra xử lý lỗi đầu vào (400) và tính tương thích ngược của hàm load_announcement()."""
        bcs_token = self._login_account(self.test_bcs_acct)

        status, _ = self._request("POST", "/api/announcement", {
            "targetAmountEth": "0.01",
        }, token=bcs_token)
        self.assertEqual(status, 400)

        status, _ = self._request("POST", "/api/announcement", {
            "title": "Test invalid amount",
            "targetAmountEth": "-0.05",
        }, token=bcs_token)
        self.assertEqual(status, 400)

        status_h, res_h = self._request("GET", "/api/announcement/history")
        self.assertEqual(status_h, 200)
        self.assertTrue(res_h.get("success"))
        self.assertIsInstance(res_h.get("history"), list)

        ann = srv.load_announcement()
        self.assertIsInstance(ann, dict)
        self.assertIn("title", ann)


# =============================================================================
# NHÓM 2: KIỂM THỬ CHUYÊN SÂU PHASE 1 V4.4 (TIMEZONE, OVERLAP, ATOMIC, HASH, MIGRATION)
# =============================================================================

class TestPhase1V44AccountingEngineAndStorage(IsolatedTempServerTestCase):
    # -------------------------------------------------------------------------
    # D.1: Múi giờ Asia/Ho_Chi_Minh (ZoneInfo)
    # -------------------------------------------------------------------------
    def test_p1_01_timezone_asia_ho_chi_minh_and_day_bounds(self):
        """Kiểm tra ZoneInfo('Asia/Ho_Chi_Minh'), đầu ngày, cuối ngày, thời hạn và chống sai lệch năm."""
        tz = get_vn_tz()
        self.assertIsInstance(tz, ZoneInfo)
        self.assertEqual(tz.key, "Asia/Ho_Chi_Minh")

        # Kiểm tra mốc 02/11/2026
        bounds = get_vn_day_bounds(2026, 11, 2)
        self.assertEqual(bounds["startOfDayTs"], 1793552400)      # 2026-11-02 00:00:00+07:00
        self.assertEqual(bounds["deadlineMinuteTs"], 1793638740)  # 2026-11-02 23:59:00+07:00
        self.assertEqual(bounds["endOfDayTs"], 1793638799)        # 2026-11-02 23:59:59+07:00

        # Kiểm tra chuyển đổi chuỗi tiếng Việt sang Unix timestamp
        ts_nov2 = parse_deadline_to_vn_timestamp("23:59 ngày 2/11/2026")
        self.assertEqual(ts_nov2, 1793638740)
        rev_nov2 = verify_timestamp_vn(ts_nov2, 2026, 11, 2, 23, 59, 0)
        self.assertTrue(rev_nov2["matches"])

        ts_nov30 = parse_deadline_to_vn_timestamp("23:59 ngày 30/11/2026")
        self.assertEqual(ts_nov30, 1796057940)
        rev_nov30 = verify_timestamp_vn(ts_nov30, 2026, 11, 30, 23, 59, 0)
        self.assertTrue(rev_nov30["matches"])

        # Kiểm tra ngày đơn lẻ DD/MM/YYYY mặc định về 23:59:59+07:00
        ts_date_only = parse_deadline_to_vn_timestamp("02/11/2026")
        self.assertEqual(ts_date_only, 1793638799)

        # Kiểm chứng giá trị 1762102740 thuộc năm 2025 (2025-11-02 23:59:00+07:00), KHÔNG khớp năm 2026
        wrong_check = verify_timestamp_vn(1762102740, 2026, 11, 2, 23, 59, 0)
        self.assertFalse(wrong_check["matches"])
        self.assertEqual(wrong_check["actual"]["year"], 2025)

    # -------------------------------------------------------------------------
    # D.2: Chính sách phân loại giao dịch tại giây biên trùng nhau (1793619753)
    # -------------------------------------------------------------------------
    def test_p1_02_same_second_overlap_and_boundary_classification(self):
        """
        Mô phỏng giao dịch có block.timestamp tại giây biên trùng nhau (1793619753)
        giữa ann-k57-hk1 và ann-20261102114233:
        - Không tự ý sửa timestamp gốc (cả hai giữ nguyên 1793619753).
        - Không mất dữ liệu, không phân bổ trùng vào 2 đợt.
        - Đánh dấu PROVISIONAL_PENDING_REVIEW và needsBoundaryReview = True.
        """
        dry_res = run_dry_run_migration_in_temp(REAL_ANNOUNCEMENT_PATH, reference_now_ts=1793700000)
        campaigns = dry_res["afterData"]["campaigns"]

        # Xác nhận dữ liệu gốc không bị sửa cứng thành 1793619752
        self.assertEqual(campaigns["ann-k57-hk1"]["effectiveEndTimestamp"], 1793619753)
        self.assertEqual(campaigns["ann-20261102114233"]["startTimestamp"], 1793619753)
        # Thiết lập mốc kết thúc đợt 2 đúng hạn chót 1793638740 để kiểm tra trường hợp 5 & 6 (sau hạn chót)
        campaigns["ann-20261102114233"]["effectiveEndTimestamp"] = 1793638740

        # 1. Giao dịch tại đúng giây trùng nhau 1793619753
        c_shared = classify_transaction_at_timestamp(1793619753, campaigns)
        self.assertEqual(c_shared["assignedBucket"], "campaign")
        self.assertEqual(c_shared["campaignId"], "ann-20261102114233")
        self.assertEqual(c_shared["allocatedCampaignCount"], 1)
        self.assertEqual(c_shared["classificationStatus"], "PROVISIONAL_PENDING_REVIEW")
        self.assertTrue(c_shared["needsBoundaryReview"])
        self.assertEqual(c_shared["boundaryReason"], "SHARED_SECOND_CAMPAIGN_TRANSITION")
        self.assertEqual(c_shared["candidateCampaignIds"], ["ann-k57-hk1", "ann-20261102114233"])

        # 2. Giao dịch tại 1793619752 (1 giây trước mốc chuyển giao) -> thuộc ann-k57-hk1, có cờ biên ±12s
        c_before = classify_transaction_at_timestamp(1793619752, campaigns)
        self.assertEqual(c_before["campaignId"], "ann-k57-hk1")
        self.assertEqual(c_before["allocatedCampaignCount"], 1)
        self.assertTrue(c_before["needsBoundaryReview"])
        self.assertEqual(c_before["boundaryReason"], "WITHIN_12S_END_BOUNDARY")

        # 3. Giao dịch tại 1793619754 (1 giây sau mốc chuyển giao) -> thuộc ann-20261102114233, có cờ biên ±12s
        c_after = classify_transaction_at_timestamp(1793619754, campaigns)
        self.assertEqual(c_after["campaignId"], "ann-20261102114233")
        self.assertEqual(c_after["allocatedCampaignCount"], 1)
        self.assertTrue(c_after["needsBoundaryReview"])
        self.assertEqual(c_after["boundaryReason"], "WITHIN_12S_START_BOUNDARY")

        # 4. Giao dịch ở giữa đợt thu (cách xa biên > 12s) -> CONFIRMED_IN_CAMPAIGN, needsBoundaryReview = False
        c_mid = classify_transaction_at_timestamp(1793625000, campaigns)
        self.assertEqual(c_mid["campaignId"], "ann-20261102114233")
        self.assertFalse(c_mid["needsBoundaryReview"])
        self.assertEqual(c_mid["classificationStatus"], "CONFIRMED_IN_CAMPAIGN")

        # 5. Giao dịch tại 1793638741 (1 giây sau hạn chót 1793638740 của đợt 2) -> Ngoài đợt thu + chờ đối soát biên
        c_post_dl = classify_transaction_at_timestamp(1793638741, campaigns)
        self.assertEqual(c_post_dl["assignedBucket"], "voluntaryContributions")
        self.assertIsNone(c_post_dl["campaignId"])
        self.assertEqual(c_post_dl["allocatedCampaignCount"], 0)
        self.assertTrue(c_post_dl["needsBoundaryReview"])
        self.assertEqual(c_post_dl["classificationStatus"], "VOLUNTARY_PENDING_BOUNDARY_REVIEW")
        self.assertIn("ann-20261102114233", c_post_dl["candidateCampaignIds"])

        # 6. Giao dịch ngoài đợt thu cách xa biên (> 12s sau hạn chót) -> VOLUNTARY_CONFIRMED
        c_far_vol = classify_transaction_at_timestamp(1793640000, campaigns)
        self.assertEqual(c_far_vol["assignedBucket"], "voluntaryContributions")
        self.assertIsNone(c_far_vol["campaignId"])
        self.assertFalse(c_far_vol["needsBoundaryReview"])
        self.assertEqual(c_far_vol["classificationStatus"], "VOLUNTARY_CONFIRMED")

    # -------------------------------------------------------------------------
    # D.3: File Lock, Atomic Write 7 bước, Tiến trình dừng giữa chừng & Phục hồi Backup
    # -------------------------------------------------------------------------
    def test_p1_03_atomic_write_crash_recovery_and_corrupted_backup_rejection(self):
        """
        Kiểm thử:
        1. Tiến trình bị dừng giữa lúc ghi (.tmp) không làm hỏng file chính.
        2. Ghi JSON không hợp lệ bị chặn trước khi chạm vào file chính.
        3. Khi file chính bị hỏng, tự động xác minh và khôi phục từ .bak hợp lệ.
        4. Khi cả file chính và .bak đều bị hỏng, dừng ngay và ném CorruptedStorageError
           (tuyệt đối không phục hồi từ backup lỗi và không tự sinh dữ liệu mới).
        """
        with tempfile.TemporaryDirectory(prefix="kts_atomic_test_") as tmp_dir:
            target = Path(tmp_dir) / "store.json"
            bak = target.with_name("store.json.bak")

            initial_payload = {
                "revision": 1,
                "active": {"id": "ann-1", "title": "Đợt 1", "status": "active"},
                "history": [],
            }
            atomic_write_json(target, initial_payload)

            # Cập nhật lên revision 2 để tạo bản .bak (chứa revision 1)
            rev2_payload = {
                "revision": 2,
                "active": {"id": "ann-2", "title": "Đợt 2", "status": "active"},
                "history": [{"id": "ann-1", "title": "Đợt 1", "status": "archived"}],
            }
            atomic_write_json(target, rev2_payload)
            self.assertTrue(bak.exists())

            # 1. Mô phỏng tiến trình bị dừng đột ngột ngay sau khi ghi .tmp (trước os.replace)
            rev3_payload = {
                "revision": 3,
                "active": {"id": "ann-3", "title": "Đợt 3", "status": "active"},
                "history": [],
            }
            with self.assertRaises(RuntimeError):
                atomic_write_json(target, rev3_payload, simulate_crash_after_tmp_write=True)

            # File chính vẫn nguyên vẹn ở revision 2!
            loaded_after_crash, meta_crash = safe_load_json(target)
            self.assertFalse(meta_crash["recoveredFromBackup"])
            self.assertEqual(loaded_after_crash["revision"], 2)
            self.assertEqual(loaded_after_crash["active"]["id"], "ann-2")

            # 2. Thử ghi dữ liệu sai cấu trúc (không phải dict hợp lệ) -> bị từ chối
            with self.assertRaises(AtomicStorageError):
                atomic_write_json(target, ["invalid_root_list"])

            # 3. Làm hỏng file chính (ghi chuỗi JSON cụt) -> safe_load_json tự động phục hồi từ .bak đã xác minh
            target.write_text("{corrupted_json_truncated...", encoding="utf-8")
            recovered_data, rec_meta = safe_load_json(target)
            self.assertTrue(rec_meta["recoveredFromBackup"])
            self.assertEqual(recovered_data["revision"], 1)
            self.assertEqual(recovered_data["active"]["id"], "ann-1")

            # 4. Làm hỏng cả file chính lẫn file .bak -> Phải DỪNG và ném CorruptedStorageError
            target.write_text("{corrupted_primary", encoding="utf-8")
            bak.write_text("{corrupted_backup", encoding="utf-8")
            with self.assertRaises(CorruptedStorageError):
                safe_load_json(target)

    def test_p1_04_concurrent_writes_and_optimistic_concurrency_409_and_idempotency(self):
        """
        Kiểm thử:
        1. Hai yêu cầu ghi đồng thời với cùng expectedRevision: đúng 1 yêu cầu thành công (200),
           yêu cầu còn lại nhận HTTP 409 Conflict.
        2. Gửi lại cùng clientRequestId (Idempotency): trả về HTTP 200 (idempotentReplay=True),
           không tạo bản ghi trùng và không tăng revision.
        3. Chế độ mode='edit' cập nhật thông tin đợt hiện tại mà không đẩy vào history.
        """
        bcs_token = self._login_account(self.test_bcs_acct)

        # Lấy revision hiện tại
        st_get, res_get = self._request("GET", "/api/announcement")
        self.assertEqual(st_get, 200)
        base_rev = res_get["revision"]

        # Tạo 1 đợt thu mới với clientRequestId và expectedRevision
        req_id_1 = "req-phase1-idempotent-001"
        payload_create = {
            "mode": "create",
            "expectedRevision": base_rev,
            "clientRequestId": req_id_1,
            "title": "Đợt thu K57 Kiểm thử Idempotency",
            "targetAmountEth": "0.015",
            "deadline": "23:59 ngày 25/12/2026",
            "purpose": "Kiểm thử chống ghi trùng",
        }
        st1, res1 = self._request("POST", "/api/announcement", payload_create, token=bcs_token)
        self.assertEqual(st1, 200)
        self.assertFalse(res1.get("idempotentReplay"))
        rev_after_create = res1["revision"]
        self.assertEqual(rev_after_create, base_rev + 1)

        # Gửi lại đúng request trên (cùng clientRequestId) -> Phải trả về 200 idempotentReplay=True, không tăng revision
        st1_replay, res1_replay = self._request("POST", "/api/announcement", payload_create, token=bcs_token)
        self.assertEqual(st1_replay, 200)
        self.assertTrue(res1_replay.get("idempotentReplay"))
        self.assertEqual(res1_replay["revision"], rev_after_create)

        # Kiểm thử mode="edit" với expectedRevision đúng
        payload_edit = {
            "mode": "edit",
            "expectedRevision": rev_after_create,
            "clientRequestId": "req-phase1-edit-002",
            "title": "Đợt thu K57 Đã Chỉnh Sửa Tiêu Đề",
            "targetAmountEth": "0.015",
            "deadline": "23:59 ngày 28/12/2026",
            "purpose": "Đã cập nhật hạn nộp",
        }
        st_edit, res_edit = self._request("POST", "/api/announcement", payload_edit, token=bcs_token)
        self.assertEqual(st_edit, 200)
        self.assertEqual(res_edit["active"]["id"], res1["active"]["id"])
        self.assertEqual(res_edit["active"]["title"], "Đợt thu K57 Đã Chỉnh Sửa Tiêu Đề")
        rev_after_edit = res_edit["revision"]
        self.assertEqual(rev_after_edit, rev_after_create + 1)

        # Kiểm thử 2 request ghi đồng thời (race condition) cùng dùng expectedRevision = rev_after_edit
        def send_concurrent_update(idx: int):
            return self._request(
                "POST",
                "/api/announcement",
                {
                    "mode": "edit",
                    "expectedRevision": rev_after_edit,
                    "clientRequestId": f"req-concurrent-{idx}",
                    "title": f"Concurrent Edit #{idx}",
                    "targetAmountEth": "0.02",
                    "deadline": "23:59 ngày 30/12/2026",
                },
                token=bcs_token,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(send_concurrent_update, 1)
            f2 = executor.submit(send_concurrent_update, 2)
            r1 = f1.result()
            r2 = f2.result()

        statuses = sorted([r1[0], r2[0]])
        self.assertEqual(
            statuses,
            [200, 409],
            f"Hai yêu cầu đồng thời cùng expectedRevision phải có đúng 1 cái 200 và 1 cái 409: {r1}, {r2}",
        )

    # -------------------------------------------------------------------------
    # D.4: Hash kiểm toán (recordSha256 & previousRecordHash)
    # -------------------------------------------------------------------------
    def test_p1_05_audit_hash_and_hash_chain_verification(self):
        """Kiểm tra tính toán recordSha256, liên kết chuỗi previousRecordHash và phát hiện giả mạo."""
        self.assertIn("SINGLE_HASH_LIMITATION", AUDIT_HASH_LIMITATION_NOTE)

        rec1 = attach_record_audit_hash(
            {"id": "adj-001", "txHash": "0xabc", "toCampaignId": "ann-k57-hk1"},
            previous_record_hash=GENESIS_PREV_HASH,
            seq=1,
        )
        rec2 = attach_record_audit_hash(
            {"id": "adj-002", "txHash": "0xdef", "toCampaignId": "ann-20261102114233"},
            previous_record_hash=rec1["recordSha256"],
            seq=2,
        )

        self.assertTrue(verify_record_audit_hash(rec1))
        self.assertTrue(verify_record_audit_hash(rec2))
        chain_ok, chain_err = verify_record_hash_chain([rec1, rec2])
        self.assertTrue(chain_ok, f"Chuỗi hash hợp lệ nhưng báo lỗi: {chain_err}")

        # Giả mạo nội dung rec1 mà không tính lại chuỗi -> verify_record_hash_chain phải phát hiện
        tampered_rec1 = copy.deepcopy(rec1)
        tampered_rec1["toCampaignId"] = "tampered-campaign"
        ok_tamper, err_tamper = verify_record_hash_chain([tampered_rec1, rec2])
        self.assertFalse(ok_tamper)
        self.assertIn("recordSha256", err_tamper)

        # Giả mạo rec1 VÀ tự tính lại recordSha256 của rec1 -> bị phát hiện tại mắt xích previousRecordHash của rec2!
        rehashed_tampered_rec1 = attach_record_audit_hash(
            tampered_rec1,
            previous_record_hash=GENESIS_PREV_HASH,
            seq=1,
        )
        ok_chain_break, err_chain_break = verify_record_hash_chain([rehashed_tampered_rec1, rec2])
        self.assertFalse(ok_chain_break)
        self.assertIn("previousRecordHash", err_chain_break)

    # -------------------------------------------------------------------------
    # C.1–C.4: Sao lưu bất biến và Migration thử nghiệm Schema V2 trên thư mục tạm
    # -------------------------------------------------------------------------
    def test_p1_06_initial_backup_immutability_and_dry_run_migration(self):
        """
        Kiểm tra:
        1. Bản sao lưu ban đầu không bao giờ bị ghi đè trong các lần chạy tiếp theo.
        2. Migration thử nghiệm trên bản sao trong thư mục tạm bảo toàn 100% dữ liệu của
           ann-k57-hk1 và ann-20261102114233 (chuyển sang expired).
        """
        with tempfile.TemporaryDirectory(prefix="kts_backup_test_") as tmp_dir:
            src_copy = Path(tmp_dir) / "announcements.json"
            bak_copy = Path(tmp_dir) / "announcements.pre_v4_migration.bak"
            shutil.copy2(REAL_ANNOUNCEMENT_PATH, src_copy)

            # Lần 1: Tạo mới backup
            res_first = ensure_initial_pre_v4_migration_res = ensure_initial_pre_v4_backup(src_copy, bak_copy)
            self.assertTrue(res_first["createdNow"])
            self.assertFalse(res_first["overwritten"])
            self.assertTrue(res_first["isValidJson"])
            first_sha = res_first["backupSha256"]

            # Thay đổi file nguồn trong thư mục tạm rồi gọi lại ensure_initial_pre_v4_backup
            modified_v1 = json.loads(src_copy.read_text(encoding="utf-8"))
            if modified_v1.get("active"):
                modified_v1["active"]["title"] = "Tiêu đề đã bị sửa sau khi backup"
            elif modified_v1.get("history"):
                modified_v1["history"][0]["title"] = "Tiêu đề đã bị sửa sau khi backup"
            src_copy.write_text(json.dumps(modified_v1, ensure_ascii=False, indent=2), encoding="utf-8")

            # Lần 2: Tuyệt đối KHÔNG ghi đè bản backup ban đầu
            res_second = ensure_initial_pre_v4_backup(src_copy, bak_copy)
            self.assertFalse(res_second["createdNow"])
            self.assertFalse(res_second["overwritten"])
            self.assertEqual(res_second["backupSha256"], first_sha)

        # Kiểm tra dry-run migration từ bản gốc
        dry_run = run_dry_run_migration_in_temp(REAL_ANNOUNCEMENT_PATH, reference_now_ts=1793700000)
        comp = dry_run["comparison"]
        self.assertTrue(comp["allPreserved"])
        self.assertEqual(comp["beforeCount"], 2)
        self.assertEqual(comp["afterCount"], 2)
        self.assertTrue(comp["hashChainValid"])

        after_v2 = dry_run["afterData"]
        self.assertEqual(after_v2["schemaVersion"], 2)
        self.assertIsNone(after_v2["active"])
        self.assertIn(after_v2["campaigns"]["ann-20261102114233"]["status"], ["archived", "expired"])
        self.assertEqual(after_v2["campaigns"]["ann-k57-hk1"]["status"], "archived")

    # =========================================================================
    # PHASE 1.1 – KIỂM THỬ CHUYÊN SÂU CHO 5 CẢNH BÁO (W1 -> W5) & MIGRATION FIELDS
    # =========================================================================

    def test_p11_w1_no_auto_fallback_to_v1_backup(self):
        """
        W1: safe_load_json() chỉ tự động khôi phục từ <target>.bak hợp lệ.
        Tuyệt đối KHÔNG tự động fallback về announcements.pre_v4_migration.bak
        khi cả file chính và <target>.bak đều hỏng hoặc thiếu.
        """
        with tempfile.TemporaryDirectory(prefix="kts_w1_test_") as tmp_dir:
            tmp_path = Path(tmp_dir)
            primary = tmp_path / "announcements.json"
            rolling_bak = tmp_path / "announcements.json.bak"
            pre_v4_bak = tmp_path / "announcements.pre_v4_migration.bak"

            # Tạo bản sao lưu gốc V1 hợp lệ trong cùng thư mục tạm
            shutil.copy2(REAL_ANNOUNCEMENT_PATH, pre_v4_bak)

            # Ghi dữ liệu giả lập vào primary và tạo rolling backup
            v2_rev1 = {
                "revision": 10,
                "active": {"id": "ann-v2-10", "title": "Đợt Rev 10", "status": "active"},
                "history": [],
            }
            v2_rev2 = {
                "revision": 11,
                "active": {"id": "ann-v2-11", "title": "Đợt Rev 11", "status": "active"},
                "history": [],
            }
            atomic_write_json(primary, v2_rev1)
            atomic_write_json(primary, v2_rev2)
            self.assertTrue(rolling_bak.exists())

            # Trường hợp 1: Primary bị hỏng nhưng rolling .bak còn tốt -> Khôi phục từ .bak (Rev 10), KHÔNG dùng pre_v4_bak
            primary.write_text("{broken_primary_json", encoding="utf-8")
            recovered, meta = safe_load_json(primary)
            self.assertTrue(meta["recoveredFromBackup"])
            self.assertEqual(Path(meta["backupSource"]).name, "announcements.json.bak")
            self.assertEqual(recovered["revision"], 10)
            self.assertEqual(recovered["active"]["id"], "ann-v2-10")

            # Trường hợp 2: Cả primary và rolling .bak đều bị hỏng, dù pre_v4_bak hợp lệ vẫn phải ném CorruptedStorageError!
            primary.write_text("{broken_primary_json", encoding="utf-8")
            rolling_bak.write_text("{broken_rolling_bak_json", encoding="utf-8")
            self.assertTrue(pre_v4_bak.exists())

            with self.assertRaises(CorruptedStorageError) as ctx:
                safe_load_json(primary)
            self.assertIn("backup V1", str(ctx.exception))

            # Đảm bảo file primary không bị ghi đè tự động bằng dữ liệu V1 từ pre_v4_bak
            self.assertEqual(primary.read_text(encoding="utf-8"), "{broken_primary_json")

    def test_p11_w2_concurrent_roster_registrations_preserve_all_updates(self):
        """
        W2: Bọc toàn bộ chu trình đọc - kiểm tra - sửa - ghi của POST /api/roster/register
        trong DualLayerFileLock(get_roster_file()). Kiểm thử nhiều luồng đăng ký đồng thời
        không bị mất cập nhật (lost update) và không bị deadlock.
        """
        bcs_token = self._login_account(self.test_bcs_acct)
        num_concurrent = 10
        new_students = []
        for i in range(num_concurrent):
            acct = Account.create()
            new_students.append({
                "mssv": f"SV_CONCURRENT_{i:02d}",
                "name": f"Sinh viên Đồng Thời {i:02d}",
                "wallet": acct.address,
                "role": "student",
            })

        barrier = threading.Barrier(num_concurrent)

        def register_worker(student_payload):
            barrier.wait(timeout=5)
            return self._request("POST", "/api/roster/register", student_payload, token=bcs_token)

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(register_worker, s) for s in new_students]
            results = [f.result(timeout=10) for f in futures]

        for status, body in results:
            self.assertEqual(status, 200, f"Đăng ký đồng thời thất bại: {body}")
            self.assertTrue(body.get("success"))

        # Kiểm tra danh bạ sau khi tất cả luồng hoàn tất: phải bảo toàn đủ 10 sinh viên mới
        st_roster, res_roster = self._request("GET", "/api/roster", token=bcs_token)
        self.assertEqual(st_roster, 200)
        roster_list = res_roster.get("roster", [])
        registered_mssvs = {item.get("mssv") for item in roster_list}

        for s in new_students:
            self.assertIn(
                s["mssv"],
                registered_mssvs,
                f"Mất dữ liệu đăng ký đồng thời cho sinh viên {s['mssv']}!",
            )

    def test_p11_w3_hash_chain_all_10_cases(self):
        """
        W3: Kiểm thử đầy đủ 10 trường hợp bắt buộc của verify_record_hash_chain():
        1. Chuỗi hợp lệ.
        2. Sửa nội dung một bản ghi.
        3. Xóa bản ghi ở giữa.
        4. Đảo thứ tự hai bản ghi.
        5. Sửa seq.
        6. Cắt mất bản ghi cuối (phát hiện qua expected_tail_hash / expected_length).
        7. Sai expected_tail_hash.
        8. Sai expected_length.
        9. Chuỗi rỗng.
        10. Bản ghi thiếu trường bắt buộc.
        """
        self.assertIn("TAIL_TRUNCATION_LIMITATION", HASH_CHAIN_TAIL_TRUNCATION_NOTE)

        r1 = attach_record_audit_hash(
            {"id": "rec-1", "txHash": "0x111", "amountWei": "10000000000000000"},
            previous_record_hash=GENESIS_PREV_HASH,
            seq=1,
        )
        r2 = attach_record_audit_hash(
            {"id": "rec-2", "txHash": "0x222", "amountWei": "20000000000000000"},
            previous_record_hash=r1["recordSha256"],
            seq=2,
        )
        r3 = attach_record_audit_hash(
            {"id": "rec-3", "txHash": "0x333", "amountWei": "30000000000000000"},
            previous_record_hash=r2["recordSha256"],
            seq=3,
        )
        valid_chain = [r1, r2, r3]
        tail_hash = r3["recordSha256"]

        # Case 1: Chuỗi hợp lệ (kèm expected_tail_hash và expected_length)
        ok_1, err_1 = verify_record_hash_chain(
            valid_chain,
            expected_tail_hash=tail_hash,
            expected_length=3,
        )
        self.assertTrue(ok_1, f"Case 1 thất bại: {err_1}")
        self.assertIsNone(err_1)

        # Case 2: Sửa nội dung một bản ghi
        chain_case2 = copy.deepcopy(valid_chain)
        chain_case2[1]["amountWei"] = "99999999999999999"
        ok_2, err_2 = verify_record_hash_chain(chain_case2)
        self.assertFalse(ok_2)
        self.assertIn("recordSha256", err_2)

        # Case 3: Xóa bản ghi ở giữa ([r1, r3])
        chain_case3 = [copy.deepcopy(r1), copy.deepcopy(r3)]
        ok_3, err_3 = verify_record_hash_chain(chain_case3)
        self.assertFalse(ok_3)
        self.assertIn("seq", err_3)

        # Case 4: Đảo thứ tự hai bản ghi ([r2, r1, r3])
        chain_case4 = [copy.deepcopy(r2), copy.deepcopy(r1), copy.deepcopy(r3)]
        ok_4, err_4 = verify_record_hash_chain(chain_case4)
        self.assertFalse(ok_4)

        # Case 5: Sửa seq (kể cả khi tự tính lại recordSha256 cho seq giả mạo)
        r2_forged_seq = attach_record_audit_hash(
            {"id": "rec-2", "txHash": "0x222", "amountWei": "20000000000000000"},
            previous_record_hash=r1["recordSha256"],
            seq=99,
        )
        ok_5, err_5 = verify_record_hash_chain([copy.deepcopy(r1), r2_forged_seq])
        self.assertFalse(ok_5)
        self.assertIn("seq", err_5)

        # Case 6: Cắt mất bản ghi cuối ([r1, r2]) -> phát hiện qua expected_tail_hash hoặc expected_length
        truncated_chain = [copy.deepcopy(r1), copy.deepcopy(r2)]
        ok_6a, err_6a = verify_record_hash_chain(truncated_chain, expected_tail_hash=tail_hash)
        self.assertFalse(ok_6a)
        self.assertIn("expected_tail_hash", err_6a)

        ok_6b, err_6b = verify_record_hash_chain(truncated_chain, expected_length=3)
        self.assertFalse(ok_6b)
        self.assertIn("expected_length", err_6b)

        # Case 7: Sai expected_tail_hash trên chuỗi đầy đủ
        ok_7, err_7 = verify_record_hash_chain(valid_chain, expected_tail_hash="f" * 64)
        self.assertFalse(ok_7)
        self.assertIn("expected_tail_hash", err_7)

        # Case 8: Sai expected_length trên chuỗi đầy đủ
        ok_8, err_8 = verify_record_hash_chain(valid_chain, expected_length=5)
        self.assertFalse(ok_8)
        self.assertIn("expected_length", err_8)

        # Case 9: Chuỗi rỗng ([])
        ok_9_empty, err_9_empty = verify_record_hash_chain([], expected_length=0, expected_tail_hash=GENESIS_PREV_HASH)
        self.assertTrue(ok_9_empty, f"Chuỗi rỗng hợp lệ báo lỗi: {err_9_empty}")
        ok_9_nonempty_exp, err_9_nonempty_exp = verify_record_hash_chain([], expected_length=1)
        self.assertFalse(ok_9_nonempty_exp)
        self.assertIn("expected_length", err_9_nonempty_exp)
        ok_9_tail_exp, err_9_tail_exp = verify_record_hash_chain([], expected_tail_hash=tail_hash)
        self.assertFalse(ok_9_tail_exp)
        self.assertIn("expected_tail_hash", err_9_tail_exp)

        # Case 10: Bản ghi thiếu từng trường bắt buộc (seq, previousRecordHash, hashSpecVersion, recordSha256)
        for req_field in ("seq", "previousRecordHash", "hashSpecVersion", "recordSha256"):
            broken_rec = copy.deepcopy(r1)
            del broken_rec[req_field]
            self.assertFalse(verify_record_audit_hash(broken_rec))
            ok_10, err_10 = verify_record_hash_chain([broken_rec])
            self.assertFalse(ok_10)
            self.assertIn(req_field, err_10)

    def test_p11_w4_client_request_id_context_validation_5_cases(self):
        """
        W4: Kiểm thử đầy đủ 5 trường hợp của clientRequestId gắn với (action, actor):
        1. Cùng ID + cùng action + cùng actor -> 200 OK (idempotentReplay=True).
        2. Cùng ID + khác action -> 409 Conflict (IDEMPOTENCY_CONTEXT_MISMATCH).
        3. Cùng ID + khác actor -> 409 Conflict (IDEMPOTENCY_CONTEXT_MISMATCH).
        4. ID mới -> 200 OK (thực thi mới, tăng revision).
        5. Request thất bại không làm thay đổi revision hoặc dữ liệu.
        """
        bcs1_token = self._login_account(self.test_bcs_acct)
        bcs2_token = self._login_account(self.test_bcs2_acct)

        st_get, res_get = self._request("GET", "/api/announcement")
        self.assertEqual(st_get, 200)
        base_rev = res_get["revision"]

        shared_req_id = "req-w4-context-check-001"
        create_payload = {
            "mode": "create",
            "expectedRevision": base_rev,
            "clientRequestId": shared_req_id,
            "title": "Đợt thu W4 Context Original",
            "targetAmountEth": "0.025",
            "deadline": "23:59 ngày 25/12/2026",
            "purpose": "Kiểm thử ngữ cảnh clientRequestId",
        }

        # Khởi tạo lần đầu bởi BCS 1 với action = create_announcement
        st_init, res_init = self._request("POST", "/api/announcement", create_payload, token=bcs1_token)
        self.assertEqual(st_init, 200)
        self.assertFalse(res_init.get("idempotentReplay"))
        rev_after_create = res_init["revision"]
        self.assertEqual(rev_after_create, base_rev + 1)

        # Case 1: Cùng ID + cùng action (create) + cùng actor (BCS 1) -> 200 Replay
        st_c1, res_c1 = self._request("POST", "/api/announcement", create_payload, token=bcs1_token)
        self.assertEqual(st_c1, 200)
        self.assertTrue(res_c1.get("idempotentReplay"))
        self.assertEqual(res_c1["revision"], rev_after_create)
        self.assertEqual(res_c1["active"]["title"], "Đợt thu W4 Context Original")

        # Case 2: Cùng ID + KHÁC action (mode='edit' và action='close') bởi cùng BCS 1 -> 409 Conflict
        edit_with_same_id = {
            "mode": "edit",
            "expectedRevision": rev_after_create,
            "clientRequestId": shared_req_id,
            "title": "Tiêu đề giả mạo qua ID cũ",
            "targetAmountEth": "0.099",
            "deadline": "23:59 ngày 25/12/2026",
        }
        st_c2_edit, res_c2_edit = self._request("POST", "/api/announcement", edit_with_same_id, token=bcs1_token)
        self.assertEqual(st_c2_edit, 409)
        self.assertEqual(res_c2_edit.get("code"), "IDEMPOTENCY_CONTEXT_MISMATCH")
        self.assertEqual(res_c2_edit.get("savedAction"), "create_announcement")
        self.assertEqual(res_c2_edit.get("actualAction"), "edit_announcement")

        close_with_same_id = {
            "expectedRevision": rev_after_create,
            "clientRequestId": shared_req_id,
            "reason": "Đóng đợt thu nhưng dùng lại ID của lệnh create",
        }
        st_c2_close, res_c2_close = self._request("POST", "/api/announcement/close", close_with_same_id, token=bcs1_token)
        self.assertEqual(st_c2_close, 409)
        self.assertEqual(res_c2_close.get("code"), "IDEMPOTENCY_CONTEXT_MISMATCH")
        self.assertEqual(res_c2_close.get("savedAction"), "create_announcement")
        self.assertEqual(res_c2_close.get("actualAction"), "close_announcement")

        # Case 3: Cùng ID + cùng action (create) nhưng KHÁC actor (BCS 2 gửi) -> 409 Conflict
        st_c3, res_c3 = self._request("POST", "/api/announcement", create_payload, token=bcs2_token)
        self.assertEqual(st_c3, 409)
        self.assertEqual(res_c3.get("code"), "IDEMPOTENCY_CONTEXT_MISMATCH")

        # Case 5: Xác nhận các request thất bại ở Case 2 & Case 3 KHÔNG làm thay đổi revision hoặc dữ liệu
        st_check, res_check = self._request("GET", "/api/announcement")
        self.assertEqual(st_check, 200)
        self.assertEqual(res_check["revision"], rev_after_create)
        self.assertEqual(res_check["active"]["title"], "Đợt thu W4 Context Original")
        self.assertEqual(res_check["active"]["targetAmountEth"], "0.025")

        # Case 4: ID mới hợp lệ -> 200 OK, thực thi chỉnh sửa thành công và tăng revision
        new_id_payload = {
            "mode": "edit",
            "expectedRevision": rev_after_create,
            "clientRequestId": "req-w4-context-new-002",
            "title": "Đợt thu W4 Đã Cập Nhật Hợp Lệ",
            "targetAmountEth": "0.030",
            "deadline": "23:59 ngày 28/12/2026",
        }
        st_c4, res_c4 = self._request("POST", "/api/announcement", new_id_payload, token=bcs2_token)
        self.assertEqual(st_c4, 200)
        self.assertFalse(res_c4.get("idempotentReplay"))
        self.assertEqual(res_c4["revision"], rev_after_create + 1)
        self.assertEqual(res_c4["active"]["title"], "Đợt thu W4 Đã Cập Nhật Hợp Lệ")

    def test_p11_w5_migration_critical_fields_updated_at_and_end_reason(self):
        """
        Kiểm tra compare_pre_post_migration() đối chiếu đầy đủ cả updatedAt và endReason:
        - Giải thích rõ quy tắc AUTO_EXPIRE_RULE khi endReason của đợt thu quá hạn chuyển từ None sang lý do hết hạn.
        - Phát hiện ngay nếu updatedAt hoặc endReason bị thay đổi sai quy tắc.
        """
        dry_run = run_dry_run_migration_in_temp(REAL_ANNOUNCEMENT_PATH, reference_now_ts=1793700000)
        comp = dry_run["comparison"]
        self.assertIn("updatedAt", comp["criticalFieldsChecked"])
        self.assertIn("endReason", comp["criticalFieldsChecked"])
        self.assertTrue(comp["allPreserved"])

        details_by_id = {d["id"]: d for d in comp["campaignComparisons"]}
        d_hk1 = details_by_id["ann-k57-hk1"]
        d_nov2 = details_by_id["ann-20261102114233"]

        self.assertTrue(d_hk1["fieldChecks"]["updatedAt"]["matched"])
        self.assertTrue(d_hk1["fieldChecks"]["endReason"]["matched"])
        self.assertTrue(d_nov2["fieldChecks"]["updatedAt"]["matched"])
        self.assertTrue(d_nov2["fieldChecks"]["endReason"]["matched"])
        if "migrationRuleExplanation" in d_nov2["fieldChecks"]["endReason"]:
            self.assertIn("AUTO_EXPIRE_RULE", d_nov2["fieldChecks"]["endReason"]["migrationRuleExplanation"])

        # Giả lập làm sai lệch updatedAt hoặc endReason sau migration -> compare_pre_post_migration phải báo False
        v1_raw = json.loads(REAL_ANNOUNCEMENT_PATH.read_text(encoding="utf-8"))
        v2_tampered = copy.deepcopy(dry_run["afterData"])
        v2_tampered["campaigns"]["ann-k57-hk1"]["updatedAt"] = "2099-01-01T00:00:00+07:00"
        comp_bad_updated = compare_pre_post_migration(v1_raw, v2_tampered)
        self.assertFalse(comp_bad_updated["allPreserved"])

        v2_tampered_reason = copy.deepcopy(dry_run["afterData"])
        v2_tampered_reason["campaigns"]["ann-k57-hk1"]["endReason"] = "Lý do bị sửa trái phép"
        comp_bad_reason = compare_pre_post_migration(v1_raw, v2_tampered_reason)
        self.assertFalse(comp_bad_reason["allPreserved"])


class TestMultipleActiveNotificationLifecycleAndHistoryScenarios(IsolatedTempServerTestCase):
    """
    Bộ kiểm thử bắt buộc theo yêu cầu TASK: FIX NOTIFICATION HISTORY & MULTIPLE ACTIVE NOTIFICATIONS.
    Bao gồm đủ 10 kịch bản kiểm thử quy định tại Mục 3 và Mục 6, kết hợp kiểm thử gian lận theo AGENTS.md.
    """

    def test_01_create_multiple_active_notifications_simultaneously(self):
        """Kịch bản 1: Tạo 3 thông báo A, B, C đều có trạng thái active -> Hệ thống ghi nhận cả 3 active đồng thời."""
        bcs_token = self._login_account(self.test_bcs_acct)

        res_a = self._request("POST", "/api/announcement", {
            "title": "Thông báo A - Quỹ học tập",
            "targetAmountEth": "0.0100",
            "deadline": "23:59 ngày 20/12/2026",
            "purpose": "Mua giáo trình và tài liệu",
        }, token=bcs_token)[1]

        res_b = self._request("POST", "/api/announcement", {
            "title": "Thông báo B - Quỹ ngoại khóa",
            "targetAmountEth": "0.0200",
            "deadline": "23:59 ngày 25/12/2026",
            "purpose": "Tổ chức teambuilding",
        }, token=bcs_token)[1]

        res_c = self._request("POST", "/api/announcement", {
            "title": "Thông báo C - Quỹ thể thao",
            "targetAmountEth": "0.0150",
            "deadline": "23:59 ngày 30/12/2026",
            "purpose": "Giải bóng đá K57",
        }, token=bcs_token)[1]

        id_a = res_a["announcement"]["id"]
        id_b = res_b["announcement"]["id"]
        id_c = res_c["announcement"]["id"]

        _, res_get = self._request("GET", "/api/announcement")
        active_list = res_get.get("activeNotifications", [])
        active_ids = [a["id"] for a in active_list]

        self.assertIn(id_a, active_ids, "Thông báo A phải ở trạng thái active!")
        self.assertIn(id_b, active_ids, "Thông báo B phải ở trạng thái active!")
        self.assertIn(id_c, active_ids, "Thông báo C phải ở trạng thái active!")
        self.assertGreaterEqual(len(active_list), 3, "Hệ thống phải cho phép ít nhất 3 thông báo active cùng lúc!")

    def test_02_edit_notification_b_only_preserves_a_and_c(self):
        """Kịch bản 2: Chỉnh sửa thông tin thông báo B -> Chỉ B thay đổi; A và C giữ nguyên trạng thái và thông tin."""
        bcs_token = self._login_account(self.test_bcs_acct)

        # Tạo A, B, C
        id_a = self._request("POST", "/api/announcement", {
            "title": "Đợt A gốc",
            "targetAmountEth": "0.0100",
            "deadline": "23:59 ngày 20/12/2026",
        }, token=bcs_token)[1]["announcement"]["id"]

        id_b = self._request("POST", "/api/announcement", {
            "title": "Đợt B gốc",
            "targetAmountEth": "0.0200",
            "deadline": "23:59 ngày 25/12/2026",
        }, token=bcs_token)[1]["announcement"]["id"]

        id_c = self._request("POST", "/api/announcement", {
            "title": "Đợt C gốc",
            "targetAmountEth": "0.0300",
            "deadline": "23:59 ngày 30/12/2026",
        }, token=bcs_token)[1]["announcement"]["id"]

        # Chỉ sửa B
        st_edit, res_edit = self._request("POST", "/api/announcement", {
            "mode": "edit",
            "id": id_b,
            "title": "Đợt B đã sửa tiêu đề",
            "targetAmountEth": "0.0250",
            "deadline": "23:59 ngày 28/12/2026",
            "purpose": "Mục đích B mới",
        }, token=bcs_token)
        self.assertEqual(st_edit, 200)

        # Kiểm tra A và C hoàn toàn không bị ảnh hưởng
        _, res_get = self._request("GET", "/api/announcement")
        active_map = {n["id"]: n for n in res_get.get("activeNotifications", [])}

        self.assertEqual(active_map[id_b]["title"], "Đợt B đã sửa tiêu đề")
        self.assertEqual(active_map[id_b]["targetAmountEth"], "0.0250")
        self.assertEqual(active_map[id_a]["title"], "Đợt A gốc")
        self.assertEqual(active_map[id_a]["targetAmountEth"], "0.0100")
        self.assertEqual(active_map[id_c]["title"], "Đợt C gốc")
        self.assertEqual(active_map[id_c]["targetAmountEth"], "0.0300")

    def test_03_notification_b_expires_independently(self):
        """Kịch bản 3: Thông báo B đến hạn nộp -> Tự động chuyển B sang expired; A và C vẫn active."""
        bcs_token = self._login_account(self.test_bcs_acct)

        id_a = self._request("POST", "/api/announcement", {
            "title": "Đợt A còn hạn dài",
            "targetAmountEth": "0.0100",
            "deadline": "23:59 ngày 20/12/2028",
        }, token=bcs_token)[1]["announcement"]["id"]

        id_b = self._request("POST", "/api/announcement", {
            "title": "Đợt B quá hạn",
            "targetAmountEth": "0.0200",
            "deadline": "23:59 ngày 01/01/2021",  # Hạn trong quá khứ
        }, token=bcs_token)[1]["announcement"]["id"]

        id_c = self._request("POST", "/api/announcement", {
            "title": "Đợt C còn hạn dài",
            "targetAmountEth": "0.0300",
            "deadline": "23:59 ngày 30/12/2028",
        }, token=bcs_token)[1]["announcement"]["id"]

        # Gọi đọc store để kích hoạt quy tắc auto-expire
        _, res_get = self._request("GET", "/api/announcement")
        active_ids = [n["id"] for n in res_get.get("activeNotifications", [])]
        history_map = {n["id"]: n for n in res_get.get("history", [])}

        self.assertNotIn(id_b, active_ids, "Đợt B quá hạn không được nằm trong activeNotifications!")
        self.assertIn(id_a, active_ids, "Đợt A phải giữ nguyên trạng thái active!")
        self.assertIn(id_c, active_ids, "Đợt C phải giữ nguyên trạng thái active!")

        self.assertIn(id_b, history_map, "Đợt B phải được chuyển sang history!")
        self.assertEqual(history_map[id_b]["status"], "expired")
        self.assertIn("quá thời hạn", history_map[id_b]["endReason"].lower())

    def test_04_revoke_notification_a_preserves_c(self):
        """Kịch bản 4: Ban cán sự thu hồi thông báo A -> A chuyển sang revoked; C vẫn giữ nguyên active."""
        bcs_token = self._login_account(self.test_bcs_acct)

        id_a = self._request("POST", "/api/announcement", {
            "title": "Đợt A bị thu hồi",
            "targetAmountEth": "0.0100",
            "deadline": "23:59 ngày 20/12/2028",
        }, token=bcs_token)[1]["announcement"]["id"]

        id_c = self._request("POST", "/api/announcement", {
            "title": "Đợt C đang diễn ra",
            "targetAmountEth": "0.0300",
            "deadline": "23:59 ngày 30/12/2028",
        }, token=bcs_token)[1]["announcement"]["id"]

        # Thu hồi A qua endpoint /api/announcement/revoke
        st_rev, res_rev = self._request("POST", "/api/announcement/revoke", {
            "id": id_a,
            "reason": "Ban cán sự thu hồi do sai kế hoạch thực hiện",
        }, token=bcs_token)
        self.assertEqual(st_rev, 200)

        _, res_get = self._request("GET", "/api/announcement")
        active_ids = [n["id"] for n in res_get.get("activeNotifications", [])]
        history_map = {n["id"]: n for n in res_get.get("history", [])}

        self.assertNotIn(id_a, active_ids, "Đợt A không còn trong activeNotifications!")
        self.assertIn(id_c, active_ids, "Đợt C vẫn giữ nguyên trạng thái active!")
        self.assertIn(id_a, history_map, "Đợt A phải nằm trong lịch sử!")
        self.assertEqual(history_map[id_a]["status"], "revoked")
        self.assertEqual(history_map[id_a]["endReason"], "Ban cán sự thu hồi do sai kế hoạch thực hiện")

    def test_05_archive_notification_c_leaves_zero_active(self):
        """Kịch bản 5: Ban cán sự kết thúc đợt C -> C chuyển sang archived; không còn đợt nào active."""
        bcs_token = self._login_account(self.test_bcs_acct)

        id_c = self._request("POST", "/api/announcement", {
            "title": "Đợt C duy nhất đang mở",
            "targetAmountEth": "0.0200",
            "deadline": "23:59 ngày 30/12/2028",
        }, token=bcs_token)[1]["announcement"]["id"]

        # Đóng đợt C
        st_close, _ = self._request("POST", "/api/announcement/close", {
            "id": id_c,
            "reason": "Hoàn thành chỉ tiêu đợt C",
        }, token=bcs_token)
        self.assertEqual(st_close, 200)

        # Đóng tất cả các đợt khác nếu còn để đảm bảo active rỗng
        _, res_get = self._request("GET", "/api/announcement")
        for rem in res_get.get("activeNotifications", []):
            self._request("POST", "/api/announcement/close", {"id": rem["id"]}, token=bcs_token)

        _, res_after = self._request("GET", "/api/announcement")
        self.assertEqual(len(res_after.get("activeNotifications", [])), 0)
        self.assertIsNone(res_after.get("active"))

    def test_06_create_notification_d_preserves_all_previous_history(self):
        """Kịch bản 6: Tạo thông báo mới D -> D có trạng thái active; history giữ nguyên A, B, C đúng trạng thái."""
        bcs_token = self._login_account(self.test_bcs_acct)

        # 1. Tạo A và thu hồi
        id_a = self._request("POST", "/api/announcement", {
            "title": "Đợt A chuỗi kiểm thử",
            "targetAmountEth": "0.0100",
            "deadline": "23:59 ngày 31/12/2028",
        }, token=bcs_token)[1]["announcement"]["id"]
        self._request("POST", "/api/announcement/revoke", {"id": id_a, "reason": "Hủy đợt A"}, token=bcs_token)

        # 2. Tạo B quá hạn để tự chuyển expired
        id_b = self._request("POST", "/api/announcement", {
            "title": "Đợt B chuỗi kiểm thử",
            "targetAmountEth": "0.0150",
            "deadline": "23:59 ngày 01/01/2020",
        }, token=bcs_token)[1]["announcement"]["id"]
        self._request("GET", "/api/announcement")

        # 3. Tạo C và chủ động đóng (archived)
        id_c = self._request("POST", "/api/announcement", {
            "title": "Đợt C chuỗi kiểm thử",
            "targetAmountEth": "0.0200",
            "deadline": "23:59 ngày 31/12/2028",
        }, token=bcs_token)[1]["announcement"]["id"]
        self._request("POST", "/api/announcement/close", {"id": id_c, "reason": "Đóng đợt C"}, token=bcs_token)

        # 4. Tạo thông báo mới D
        res_d = self._request("POST", "/api/announcement", {
            "title": "Đợt D mới tinh",
            "targetAmountEth": "0.0500",
            "deadline": "23:59 ngày 31/12/2029",
            "purpose": "Kinh phí học kỳ tới",
        }, token=bcs_token)[1]
        id_d = res_d["announcement"]["id"]

        # Đối chiếu kết quả
        _, res_final = self._request("GET", "/api/announcement")
        active_ids = [n["id"] for n in res_final.get("activeNotifications", [])]
        history_map = {n["id"]: n for n in res_final.get("history", [])}

        self.assertIn(id_d, active_ids)
        self.assertEqual(history_map[id_a]["status"], "revoked")
        self.assertEqual(history_map[id_b]["status"], "expired")
        self.assertEqual(history_map[id_c]["status"], "archived")

    def test_07_system_restart_persistence(self):
        """Kịch bản 7: Khởi động lại hệ thống -> Toàn bộ trạng thái và lịch sử được giữ nguyên chính xác."""
        bcs_token = self._login_account(self.test_bcs_acct)

        res_n = self._request("POST", "/api/announcement", {
            "title": "Đợt lưu trữ bền vững",
            "targetAmountEth": "0.0330",
            "deadline": "23:59 ngày 20/12/2028",
        }, token=bcs_token)[1]
        test_id = res_n["announcement"]["id"]

        # Đọc trực tiếp từ file trên đĩa để mô phỏng máy chủ khởi động lại đọc từ cold storage
        store_on_disk = srv.load_announcements_store()
        all_ids = [n["id"] for n in store_on_disk.get("notifications", [])]
        self.assertIn(test_id, all_ids)

        found = next(n for n in store_on_disk["notifications"] if n["id"] == test_id)
        self.assertEqual(found["title"], "Đợt lưu trữ bền vững")
        self.assertEqual(found["targetAmountEth"], "0.0330")
        self.assertEqual(found["status"], "active")

    def test_08_idempotent_auto_expire_no_duplicates(self):
        """Kịch bản 8: Gọi hàm kiểm tra hết hạn nhiều lần liên tiếp không nhân bản history."""
        # Gọi GET /api/announcement và GET /api/announcement/history 10 lần liên tục
        counts = []
        for _ in range(10):
            st, res = self._request("GET", "/api/announcement")
            self.assertEqual(st, 200)
            counts.append(len(res.get("history", [])))

        self.assertEqual(len(set(counts)), 1, f"Số lượng history phải hoàn toàn cố định: {counts}")

    def test_09_timezone_asia_ho_chi_minh_accuracy(self):
        """Kịch bản 9: Kiểm thử tự động kiểm tra thời hạn theo múi giờ Asia/Ho_Chi_Minh."""
        deadline_str = "23:59 ngày 31/12/2026"
        ts = parse_deadline_to_vn_timestamp(deadline_str)
        self.assertIsNotNone(ts)

        # Chuyển đổi ngược lại sang thời gian Việt Nam
        dt = datetime.fromtimestamp(ts, tz=get_vn_tz())
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 12)
        self.assertEqual(dt.day, 31)
        self.assertEqual(dt.hour, 23)
        self.assertEqual(dt.minute, 59)
        self.assertEqual(str(dt.tzinfo), "Asia/Ho_Chi_Minh")

    def test_10_fraud_unauthorized_student_cannot_mutate_or_close(self):
        """Kịch bản 10 (Gian lận): Sinh viên không có quyền cố gắng tạo, sửa hoặc đóng thông báo -> 403 Forbidden."""
        student_token = self._login_account(self.test_student_acct)
        bcs_token = self._login_account(self.test_bcs_acct)

        # 1. Ban cán sự tạo thông báo hợp lệ
        id_legit = self._request("POST", "/api/announcement", {
            "title": "Thông báo hợp lệ của BCS",
            "targetAmountEth": "0.0100",
            "deadline": "23:59 ngày 31/12/2028",
        }, token=bcs_token)[1]["announcement"]["id"]

        # 2. Sinh viên gian lận cố gắng tạo thông báo mới
        st_fraud_create, res_fraud_create = self._request("POST", "/api/announcement", {
            "title": "Thông báo giả mạo của sinh viên",
            "targetAmountEth": "0.9999",
        }, token=student_token)
        self.assertEqual(st_fraud_create, 403, "Sinh viên tạo thông báo phải bị từ chối 403!")

        # 3. Sinh viên gian lận cố gắng sửa thông báo của BCS
        st_fraud_edit, _ = self._request("POST", "/api/announcement", {
            "mode": "edit",
            "id": id_legit,
            "title": "Bị sinh viên sửa trái phép",
            "targetAmountEth": "0.0001",
        }, token=student_token)
        self.assertEqual(st_fraud_edit, 403, "Sinh viên sửa thông báo phải bị từ chối 403!")

        # 4. Sinh viên gian lận cố gắng kết thúc sớm thông báo của BCS
        st_fraud_close, _ = self._request("POST", "/api/announcement/close", {
            "id": id_legit,
            "reason": "Sinh viên tự ý hủy đợt thu",
        }, token=student_token)
        self.assertEqual(st_fraud_close, 403, "Sinh viên đóng thông báo phải bị từ chối 403!")

        # 5. Sinh viên gian lận cố gắng thu hồi thông báo của BCS
        st_fraud_revoke, _ = self._request("POST", "/api/announcement/revoke", {
            "id": id_legit,
            "reason": "Sinh viên tự ý thu hồi",
        }, token=student_token)
        self.assertEqual(st_fraud_revoke, 403, "Sinh viên thu hồi thông báo phải bị từ chối 403!")

        # 6. Xác minh dữ liệu thông báo hợp lệ không bị thay đổi một byte nào
        _, res_check = self._request("GET", f"/api/announcement?id={id_legit}")
        legit_item = res_check.get("notification")
        self.assertEqual(legit_item["title"], "Thông báo hợp lệ của BCS")
        self.assertEqual(legit_item["targetAmountEth"], "0.0100")
        self.assertEqual(legit_item["status"], "active")

    def test_11_target_ids_preservation_hk1_and_nov2(self):
        """Xác minh 2 mục tiêu ID: ann-k57-hk1 (trong history) và ann-20261102114233 (chuyển sang expired vì quá hạn)."""
        raw = json.loads(REAL_ANNOUNCEMENT_PATH.read_text(encoding="utf-8"))
        store_v3, report = srv.migrate_to_notifications_store(raw)

        all_ids = {n["id"] for n in store_v3.get("notifications", [])}
        self.assertIn("ann-k57-hk1", all_ids, "ann-k57-hk1 phải được lưu giữ an toàn!")
        self.assertIn("ann-20261102114233", all_ids, "ann-20261102114233 phải được lưu giữ an toàn!")

        # Kích hoạt auto-expire
        srv.expire_due_notifications(store_v3)

        item_hk1 = next(n for n in store_v3["notifications"] if n["id"] == "ann-k57-hk1")
        item_nov2 = next(n for n in store_v3["notifications"] if n["id"] == "ann-20261102114233")

        # ann-k57-hk1 nằm trong history
        self.assertIn(item_hk1["status"], ["archived", "completed", "expired"])

        # ann-20261102114233 trong announcements.json gốc có status="archived" (hoặc expired nếu còn active)
        self.assertIn(item_nov2["status"], ["archived", "expired"])
        self.assertTrue(bool(item_nov2["endedAt"]))
        self.assertIn("quá thời hạn", item_nov2["endReason"].lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
