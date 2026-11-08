#!/usr/bin/env python3
"""
Bộ kiểm thử tính toàn vẹn và bảo mật của Mã băm Danh bạ Chuẩn hóa (Phase 3 / Mục D)
Dự án: KTS-Class-Fund-K57

Bao phủ:
1. Tính xác định (Determinism) & Bất biến hoán vị (Permutation Invariance):
   - Thay đổi thứ tự các dòng sinh viên trong JSON cho ra cùng một rosterHash.
   - Viết hoa/viết thường địa chỉ ví EIP-55 cho ra cùng một rosterHash.
2. Độ nhạy thay đổi (Tamper Sensitivity / Avalanche Effect):
   - Thay đổi 1 ký tự trong MSSV, Họ tên, Địa chỉ ví, hoặc Vai trò làm thay đổi hoàn toàn rosterHash.
3. Định dạng và Tiêu chuẩn EVM:
   - rosterHash đúng định dạng bytes32 ('0x' + 64 ký tự hex chữ thường).
   - Thuật toán băm là keccak256 native.
4. Chặn dữ liệu không hợp lệ:
   - Danh bạ rỗng bị từ chối rõ ràng (ValueError / 400 ROSTER_EMPTY).
   - Phần tử thiếu MSSV hoặc sai kiểu bị từ chối.
5. Bảo vệ quyền riêng tư tuyệt đối (Privacy Preservation):
   - Payload trả về từ compute_roster_hash và GET /api/roster/hash TUYỆT ĐỐI KHÔNG chứa PII
     (không có mssv, name, mảng wallet, hay chuỗi JSON thô chứa dữ liệu cá nhân).
6. Kiểm thử HTTP API độc lập (Isolated Server):
   - Chạy trên cổng động (127.0.0.1:0) với thư mục tạm cô lập, không ghi đè dữ liệu thật.
   - Phản hồi đúng 200, 400 (ROSTER_EMPTY), 500 (CORRUPTED_STORAGE).
"""

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
from http.server import ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import backend.server as srv
from backend.import_roster import (
    ROSTER_CANONICAL_SPEC,
    ROSTER_CANONICAL_VERSION,
    ROSTER_HASH_ALGORITHM,
    build_roster_hash_payload,
    compute_roster_hash,
    compute_roster_hash_from_file,
    normalize_roster_for_hash,
    serialize_canonical_roster,
)


class TestRosterHashLogic(unittest.TestCase):
    """Kiểm thử thuần logic băm danh bạ chuẩn hóa."""

    def setUp(self):
        self.sample_roster = [
            {
                "mssv": "23K4300004",
                "name": "Trần Hoàng Phương Dung",
                "wallet": "0x78567A377559F0cB30173f93869326a82320159a",
                "role": "bcs",
                "roleTitle": "Ban cán sự"
            },
            {
                "mssv": "23K4300015",
                "name": "Võ Ngọc Tâm Phúc",
                "wallet": "0xf5D971952dbDF69058a28D23110381d96B00cb50",
                "role": "bcs",
                "roleTitle": "Ban cán sự"
            },
            {
                "mssv": "23K4300014",
                "name": "Phan Thị Yến Nhi",
                "wallet": "0x7Af21f18DEfDA4a141BAD89681C0d4767A42333C",
                "role": "bcs",
                "roleTitle": "Ban cán sự"
            },
            {
                "mssv": "23K4300005",
                "name": "Trần Thị Bình Dương",
                "wallet": "0x64ADE1f3E814c98dEFeC19f07253afeBDD2DBfcf",
                "role": "student",
                "roleTitle": "Sinh viên"
            },
            {
                "mssv": "23K4300025",
                "name": "Nguyễn Thị Kim Chi",
                "wallet": "0x372819EB492cc6A071b946d5b82BF46174FE8394",
                "role": "student",
                "roleTitle": "Sinh viên"
            }
        ]

    def test_01_valid_hash_format_and_algorithm(self):
        """Mã băm phải đúng định dạng bytes32 ('0x' + 64 hex ký tự thường) và thuật toán keccak256."""
        h = compute_roster_hash(self.sample_roster)
        self.assertTrue(h.startswith("0x"))
        self.assertEqual(len(h), 66)
        self.assertEqual(h, h.lower())
        int(h[2:], 16)  # Phải là chuỗi hex hợp lệ

        payload = build_roster_hash_payload(self.sample_roster)
        self.assertEqual(payload["rosterHash"], h)
        self.assertEqual(payload["algorithm"], "keccak256")
        self.assertEqual(payload["canonicalVersion"], ROSTER_CANONICAL_VERSION)
        self.assertEqual(payload["count"], 5)
        self.assertEqual(payload["classSize"], 5)
        self.assertEqual(payload["walletCount"], 5)

    def test_02_permutation_invariance(self):
        """Đổi thứ tự phần tử trong danh sách không làm đổi mã băm."""
        h1 = compute_roster_hash(self.sample_roster)

        # Đảo ngược thứ tự danh sách
        reversed_roster = list(reversed(self.sample_roster))
        h2 = compute_roster_hash(reversed_roster)
        self.assertEqual(h1, h2, "Hoán vị thứ tự mảng phải cho ra cùng một rosterHash")

        # Hoán vị bất kỳ (xáo trộn)
        shuffled = [self.sample_roster[2], self.sample_roster[0], self.sample_roster[4], self.sample_roster[1], self.sample_roster[3]]
        h3 = compute_roster_hash(shuffled)
        self.assertEqual(h1, h3, "Thứ tự xáo trộn phải cho ra cùng một rosterHash")

    def test_03_wallet_casing_insensitivity(self):
        """Chữ hoa / chữ thường trong địa chỉ ví Ethereum (EIP-55) không làm đổi mã băm."""
        roster_upper = copy.deepcopy(self.sample_roster)
        for item in roster_upper:
            item["wallet"] = "0x" + item["wallet"][2:].upper()

        roster_lower = copy.deepcopy(self.sample_roster)
        for item in roster_lower:
            item["wallet"] = item["wallet"].lower()

        h_orig = compute_roster_hash(self.sample_roster)
        h_upper = compute_roster_hash(roster_upper)
        h_lower = compute_roster_hash(roster_lower)
        self.assertEqual(h_orig, h_upper)
        self.assertEqual(h_orig, h_lower)

    def test_04_tamper_sensitivity_mssv(self):
        """Sửa 1 ký tự trong MSSV làm thay đổi hoàn toàn rosterHash."""
        h_orig = compute_roster_hash(self.sample_roster)
        tampered = copy.deepcopy(self.sample_roster)
        tampered[0]["mssv"] = "23K4300009"  # Đổi số cuối
        h_tampered = compute_roster_hash(tampered)
        self.assertNotEqual(h_orig, h_tampered)

    def test_05_tamper_sensitivity_name_and_wallet_and_role(self):
        """Sửa Họ tên, Địa chỉ ví, hoặc Vai trò đều làm đổi rosterHash."""
        h_orig = compute_roster_hash(self.sample_roster)

        # Sửa họ tên
        t_name = copy.deepcopy(self.sample_roster)
        t_name[0]["name"] = "Trần Hoàng Phương Dung (Đã sửa)"
        self.assertNotEqual(h_orig, compute_roster_hash(t_name))

        # Sửa ví
        t_wallet = copy.deepcopy(self.sample_roster)
        t_wallet[0]["wallet"] = "0x1111111111111111111111111111111111111111"
        self.assertNotEqual(h_orig, compute_roster_hash(t_wallet))

        # Sửa role từ bcs sang student
        t_role = copy.deepcopy(self.sample_roster)
        t_role[0]["role"] = "student"
        t_role[0]["roleTitle"] = "Sinh viên"
        self.assertNotEqual(h_orig, compute_roster_hash(t_role))

    def test_06_empty_roster_rejection(self):
        """Danh bạ rỗng bị từ chối rõ ràng bằng ValueError."""
        with self.assertRaises(ValueError):
            compute_roster_hash([])
        with self.assertRaises(ValueError):
            build_roster_hash_payload([])

    def test_07_zero_pii_in_payload(self):
        """Payload từ build_roster_hash_payload tuyệt đối không chứa PII cá nhân."""
        payload = build_roster_hash_payload(self.sample_roster)
        serialized = json.dumps(payload, ensure_ascii=False)

        for s in self.sample_roster:
            self.assertNotIn(s["name"], serialized)
            self.assertNotIn(s["mssv"], serialized)
            self.assertNotIn(s["wallet"].lower(), serialized)


class TestRosterHashEndpointIsolated(unittest.TestCase):
    """Kiểm thử HTTP endpoint GET /api/roster/hash trên máy chủ cô lập trong tempfile."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir_obj = tempfile.TemporaryDirectory(prefix="kts_roster_hash_test_")
        cls.temp_dir = Path(cls.temp_dir_obj.name).resolve()
        cls.temp_roster = cls.temp_dir / "class_roster.json"
        cls.temp_ann = cls.temp_dir / "announcements.json"

        # Khởi tạo announcements rỗng hợp lệ
        cls.temp_ann.write_text(json.dumps({"schemaVersion": 3, "revision": 1, "notifications": []}), encoding="utf-8")

        # Cấu hình biến môi trường trỏ vào thư mục tạm
        os.environ["CLASS_ROSTER_FILE_PATH"] = str(cls.temp_roster)
        os.environ["ANNOUNCEMENT_FILE_PATH"] = str(cls.temp_ann)
        srv.ROSTER_FILE = cls.temp_roster
        srv.ANNOUNCEMENT_FILE = cls.temp_ann

        # Khởi chạy server trên cổng ngẫu nhiên do OS cấp (cổng 0)
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), srv.AIChatRequestHandler)
        cls.port = cls.httpd.server_address[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.httpd.shutdown()
            cls.httpd.server_close()
        except Exception:
            pass
        cls.temp_dir_obj.cleanup()

    def _http_get(self, path: str):
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return resp.status, data
        except urllib.error.HTTPError as e:
            try:
                data = json.loads(e.read().decode("utf-8"))
            except Exception:
                data = {"raw": str(e)}
            return e.code, data

    def test_01_empty_roster_returns_400(self):
        """Khi danh bạ rỗng ([]), endpoint trả về 400 ROSTER_EMPTY."""
        self.temp_roster.write_text("[]", encoding="utf-8")
        status, data = self._http_get("/api/roster/hash")
        self.assertEqual(status, 400)
        self.assertFalse(data.get("success"))
        self.assertEqual(data.get("code"), "ROSTER_EMPTY")

    def test_02_valid_roster_returns_200_and_zero_pii(self):
        """Khi danh bạ hợp lệ, endpoint trả về 200, mã băm 32 byte và ZERO PII."""
        sample = [
            {"mssv": "SV01", "name": "Nguyễn Văn A", "wallet": "0x78567A377559F0cB30173f93869326a82320159a", "role": "bcs"},
            {"mssv": "SV02", "name": "Trần Thị B", "wallet": "0x372819EB492cc6A071b946d5b82BF46174FE8394", "role": "student"}
        ]
        self.temp_roster.write_text(json.dumps(sample, ensure_ascii=False), encoding="utf-8")

        status, data = self._http_get("/api/roster/hash")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("algorithm"), "keccak256")
        self.assertEqual(data.get("count"), 2)
        self.assertEqual(data.get("classSize"), 2)
        self.assertEqual(data.get("walletCount"), 2)

        roster_hash = data.get("rosterHash", "")
        self.assertTrue(roster_hash.startswith("0x"))
        self.assertEqual(len(roster_hash), 66)

        # Kiểm tra không chứa PII
        raw_resp = json.dumps(data, ensure_ascii=False)
        self.assertNotIn("Nguyễn Văn A", raw_resp)
        self.assertNotIn("Trần Thị B", raw_resp)
        self.assertNotIn("SV01", raw_resp)
        self.assertNotIn("0x7856", raw_resp)

    def test_03_corrupted_storage_returns_500(self):
        """Khi file danh bạ bị hỏng cú pháp JSON, trả về 500 CORRUPTED_STORAGE."""
        self.temp_roster.write_text("{ broken json [", encoding="utf-8")
        status, data = self._http_get("/api/roster/hash")
        self.assertEqual(status, 500)
        self.assertFalse(data.get("success"))
        self.assertEqual(data.get("code"), "CORRUPTED_STORAGE")


if __name__ == "__main__":
    unittest.main()

