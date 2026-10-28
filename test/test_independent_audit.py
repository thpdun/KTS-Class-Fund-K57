#!/usr/bin/env python3
"""
Kiểm thử độc lập sau Giai đoạn 3B.3 - KTS-Class-Fund-K57
Audit độc lập: Xác thực API, Phân quyền thông tin, và Rò rỉ PII
"""

import unittest
import json
import urllib.request
import urllib.error
import os
import sys

# Ensure UTF-8 output on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

BACKEND_URL = "http://localhost:8000"

# Các địa chỉ ví trong class_roster.json
BCS_WALLET = "0x78567A377559F0cB30173f93869326a82320159a"  # Trần Hoàng Phương Dung (BCS)
STUDENT_WALLET = "0x372819EB492cc6A071b946d5b82BF46174FE8394"  # Nguyễn Thị Kim Chi (Sinh viên thường)
ATTACKER_WALLET = "0x9999999999999999999999999999999999999999"  # Ví người lạ/tấn công ngoài danh bạ
ADVISOR_ENV_WALLET = os.environ.get("ADVISOR_ADDRESS", "").strip().lower()


class TestIndependentApiAudit(unittest.TestCase):
    """
    Kiểm tra 1: Xác thực API & Phân quyền trên backend/server.py
    """

    def _send_request(self, method, path, data=None):
        url = f"{BACKEND_URL}{path}"
        body = json.dumps(data).encode("utf-8") if data is not None else None
        headers = {"Content-Type": "application/json"} if data is not None else {}
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                return resp.status, resp_data
        except urllib.error.HTTPError as e:
            try:
                err_data = json.loads(e.read().decode("utf-8"))
            except Exception:
                err_data = {"error": str(e)}
            return e.code, err_data

    # -------------------------------------------------------------------------
    # TRƯỜNG HỢP 1: Không gửi địa chỉ người dùng
    # -------------------------------------------------------------------------
    def test_case_1_missing_address(self):
        print("\n--- Trường hợp 1: Không gửi địa chỉ người dùng ---")

        # 1a. GET /api/roster không có tham số address
        status, data = self._send_request("GET", "/api/roster")
        print(f"GET /api/roster (no addr): status={status}, isAuthorized={data.get('isAuthorized')}, roster_len={len(data.get('roster', []))}")
        self.assertEqual(status, 200)
        self.assertFalse(data.get("isAuthorized"))
        self.assertEqual(data.get("roster"), [])

        # 1b. POST /api/announcement không gửi signerAddress
        status, data = self._send_request("POST", "/api/announcement", {
            "title": "Audit Test",
            "targetAmountEth": "0.01"
        })
        print(f"POST /api/announcement (no signer): status={status}, success={data.get('success')}")
        self.assertEqual(status, 403, "Không có signerAddress phải trả về 403")

        # 1c. POST /api/roster/register không gửi signerAddress
        status, data = self._send_request("POST", "/api/roster/register", {
            "mssv": "23K4300999",
            "name": "Audit Test",
            "wallet": ATTACKER_WALLET
        })
        print(f"POST /api/roster/register (no signer): status={status}, success={data.get('success')}")
        self.assertEqual(status, 403, "Không có signerAddress phải trả về 403")

    # -------------------------------------------------------------------------
    # TRƯỜNG HỢP 2: Gửi địa chỉ của BCS nhưng KHÔNG có chữ ký xác thực
    # -------------------------------------------------------------------------
    def test_case_2_bcs_address_without_signature(self):
        print("\n--- Trường hợp 2: Gửi địa chỉ BCS nhưng KHÔNG có chữ ký ---")

        # 2a. GET /api/roster?address=BCS_WALLET
        # Vì backend chỉ so sánh chuỗi address trong danh bạ, nó trả về TOÀN BỘ danh bạ!
        status, data = self._send_request("GET", f"/api/roster?address={BCS_WALLET}")
        roster = data.get("roster", [])
        print(f"GET /api/roster?address={BCS_WALLET}: status={status}, isAuthorized={data.get('isAuthorized')}, roster_count={len(roster)}")
        
        # ĐÁNH GIÁ LỖ HỔNG: Kẻ tấn công chỉ cần biết địa chỉ ví công khai của BCS là crawl được toàn bộ danh bạ lớp!
        vulnerability_detected = (data.get("isAuthorized") is True and len(roster) > 0)
        print(f"  [LỖ HỔNG XÁC THỰC GET /api/roster]: {vulnerability_detected} (Bất kỳ ai cũng có thể giả mạo query param address)")
        self.assertTrue(vulnerability_detected, "Backend cho phép xem toàn bộ danh bạ chỉ bằng query param địa chỉ ví mà không cần chữ ký!")

        # 2b. POST /api/announcement với signerAddress=BCS_WALLET (không có chữ ký)
        status, data = self._send_request("POST", "/api/announcement", {
            "title": "Kêu gọi nộp Quỹ Lớp Học kỳ 1 - Khóa K57 Kinh tế Số",
            "targetAmountEth": "0.01",
            "signerAddress": BCS_WALLET
        })
        print(f"POST /api/announcement (signer=BCS, no sig): status={status}, success={data.get('success')}")
        ann_vulnerability = (status == 200 and data.get("success") is True)
        print(f"  [LỖ HỔNG XÁC THỰC POST /api/announcement]: {ann_vulnerability} (Kẻ tấn công có thể sửa thông báo quỹ lớp bằng cách gửi signerAddress là ví BCS)")

    # -------------------------------------------------------------------------
    # TRƯỜNG HỢP 3: Gửi cờ isBcsMember: true hoặc isAdvisor: true
    # -------------------------------------------------------------------------
    def test_case_3_client_flags_spoofing(self):
        print("\n--- Trường hợp 3: Gửi cờ isBcsMember: true hoặc isAdvisor: true ---")

        # 3a. Gửi cờ với ví ngoài danh bạ
        status, data = self._send_request("POST", "/api/announcement", {
            "title": "Hacker Announcement",
            "targetAmountEth": "0.05",
            "signerAddress": ATTACKER_WALLET,
            "isAdvisor": True,
            "isBcsMember": True,
            "role": "bcs"
        })
        print(f"POST /api/announcement (attacker + spoofed flags): status={status}")
        self.assertEqual(status, 403, "Cờ client-side boolean phải bị bỏ qua, trả về 403")

        # 3b. GET /api/roster với ví ngoài danh bạ và cờ giả mạo
        status, data = self._send_request("GET", f"/api/roster?address={ATTACKER_WALLET}&isAdvisor=1&isBcs=1")
        print(f"GET /api/roster (attacker + spoofed flags): isAuthorized={data.get('isAuthorized')}, roster_len={len(data.get('roster', []))}")
        self.assertFalse(data.get("isAuthorized"))
        self.assertEqual(data.get("roster"), [])

    # -------------------------------------------------------------------------
    # TRƯỜNG HỢP 4: Giả mạo signerAddress thành địa chỉ BCS / Cố vấn
    # -------------------------------------------------------------------------
    def test_case_4_spoofed_signer_address(self):
        print("\n--- Trường hợp 4: Giả mạo signerAddress thành địa chỉ BCS/Cố vấn ---")

        # Giả mạo thêm sinh viên vào danh bạ qua POST /api/roster/register
        # Người gửi là Attacker (không sở hữu private key của BCS), nhưng gửi JSON body có signerAddress: BCS_WALLET
        spoofed_payload = {
            "mssv": "23K4300999",
            "name": "Sinh Vien Test Audit",
            "wallet": ATTACKER_WALLET,
            "role": "student",
            "signerAddress": BCS_WALLET  # Giả mạo ví BCS!
        }
        # Backup roster trước khi test
        roster_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend", "class_roster.json")
        with open(roster_path, "r", encoding="utf-8") as rf:
            original_roster = rf.read()

        try:
            status, data = self._send_request("POST", "/api/roster/register", spoofed_payload)
            print(f"POST /api/roster/register (spoofed BCS signer): status={status}, success={data.get('success')}")

            # Đánh giá: Backend chấp nhận request vì chỉ check is_authorized_viewer(signer)
            # mà không có chữ ký mã hóa (cryptographic signature)
            if status == 200 and data.get("success"):
                print("  [LỖ HỔNG XÁC THỰC NGHIÊM TRỌNG]: Backend tin tưởng signerAddress mà không đòi hỏi chữ ký xác thực quyền sở hữu ví (Proof of Possession)!")
        finally:
            # Khôi phục nguyên vẹn danh bạ gốc sau khi kiểm thử
            with open(roster_path, "w", encoding="utf-8") as wf:
                wf.write(original_roster)

    # -------------------------------------------------------------------------
    # TRƯỜNG HỢP 5: Kiểm tra cơ chế chữ ký (Signature, Nonce, Expiration)
    # -------------------------------------------------------------------------
    def test_case_5_signature_verification_mechanism(self):
        print("\n--- Trường hợp 5: Cơ chế xác thực chữ ký (Signature, Nonce, Expiration) ---")
        
        # Đọc backend/server.py xem có hàm xác thực chữ ký (ec_recover, eth_account, web3) nào không
        with open("backend/server.py", "r", encoding="utf-8") as f:
            server_code = f.read()

        has_signature_lib = any(lib in server_code for lib in ["eth_account", "web3", "ecrecover", "w3.eth.account"])
        has_nonce_handling = "nonce" in server_code.lower()
        has_timestamp_validation = "timestamp" in server_code.lower()

        print(f"  Thư viện khôi phục chữ ký (eth_account/web3): {has_signature_lib}")
        print(f"  Cơ chế kiểm tra Nonce chống replay attack: {has_nonce_handling}")
        print(f"  Cơ chế kiểm tra thời hạn chữ ký: {has_timestamp_validation}")

        # Khẳng định: Cơ chế chữ ký CHƯA ĐƯỢC TRIỂN KHAI trên backend
        self.assertFalse(has_signature_lib, "Backend hiện tại chưa tích hợp thư viện xác thực chữ ký Ethereum")

    # -------------------------------------------------------------------------
    # TRƯỜNG HỢP 6: Người đã xác thực địa chỉ nhưng không có quyền
    # -------------------------------------------------------------------------
    def test_case_6_authenticated_normal_student_without_privilege(self):
        print("\n--- Trường hợp 6: Địa chỉ sinh viên thường (không có quyền BCS/CVHT) ---")

        # 6a. Sinh viên thường gọi GET /api/roster
        status, data = self._send_request("GET", f"/api/roster?address={STUDENT_WALLET}")
        print(f"GET /api/roster (student addr): isAuthorized={data.get('isAuthorized')}, roster_len={len(data.get('roster', []))}")
        self.assertEqual(status, 200)
        self.assertFalse(data.get("isAuthorized"))
        self.assertEqual(data.get("roster"), [])

        # 6b. Sinh viên thường gọi POST /api/announcement
        status, data = self._send_request("POST", "/api/announcement", {
            "title": "Hacker Announcement",
            "targetAmountEth": "0.05",
            "signerAddress": STUDENT_WALLET
        })
        print(f"POST /api/announcement (student addr): status={status}")
        self.assertEqual(status, 403)

        # 6c. Sinh viên thường gọi POST /api/roster/register
        status, data = self._send_request("POST", "/api/roster/register", {
            "mssv": "23K4300999",
            "name": "Audit Test",
            "wallet": ATTACKER_WALLET,
            "signerAddress": STUDENT_WALLET
        })
        print(f"POST /api/roster/register (student addr): status={status}")
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
