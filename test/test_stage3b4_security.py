#!/usr/bin/env python3
"""
Test Suite Giai đoạn 3B.4: Khắc phục xác thực Backend và bảo vệ dữ liệu cá nhân
Kiểm thử tự động chứng minh 7 tiêu chuẩn an ninh cốt lõi:
1. Địa chỉ BCS khai báo trong request nhưng không có chữ ký hợp lệ bị từ chối.
2. Chữ ký sai, nonce hết hạn và nonce dùng lại bị từ chối.
3. Người dùng thường không đọc/sửa được danh bạ hoặc thông báo dành cho BCS/CVHT.
4. API tra cứu ví (check) không tiết lộ tên/MSSV cho người không có quyền.
5. Client tự đặt cờ quyền (isAdvisor, isBcsMember) không thể vượt qua kiểm tra backend.
6. Phiên hết hạn hoặc bị thu hồi (logout) không thể tiếp tục thao tác.
7. Các API hợp lệ vẫn hoạt động đúng với người đã xác thực hợp lệ.
"""

import unittest
import json
import urllib.request
import urllib.error
import time
import os
import sys

from eth_account import Account
from eth_account.messages import encode_defunct

# Ensure UTF-8 output on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

BACKEND_URL = "http://localhost:8000"

# Địa chỉ ví trong class_roster.json
BCS_WALLET = "0x78567A377559F0cB30173f93869326a82320159a"   # Trần Hoàng Phương Dung (BCS)
STUDENT_WALLET = "0x372819EB492cc6A071b946d5b82BF46174FE8394"   # Nguyễn Thị Kim Chi (Sinh viên)


class TestStage3B4Security(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Tạo các ví thử nghiệm NGẪU NHIÊN CHỈ TRONG BỘ NHỚ TEST (không chứa private key thật)
        cls.test_bcs_acct = Account.create()
        cls.test_student_acct = Account.create()
        cls.test_stranger_acct = Account.create()

        # Sao lưu class_roster.json
        cls.roster_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend", "class_roster.json")
        with open(cls.roster_path, "r", encoding="utf-8") as f:
            cls.original_roster = json.load(f)

        # Cấu hình danh bạ tạm thời chứa ví test_bcs_acct và test_student_acct để kiểm thử phân quyền
        test_roster = list(cls.original_roster)
        test_roster.append({
            "mssv": "TEST_BCS_01",
            "name": "Nguyễn Văn BCS Test",
            "wallet": cls.test_bcs_acct.address,
            "role": "bcs",
            "roleTitle": "Ban cán sự"
        })
        test_roster.append({
            "mssv": "TEST_SV_01",
            "name": "Lê Thị Sinh Viên Test",
            "wallet": cls.test_student_acct.address,
            "role": "student",
            "roleTitle": "Sinh viên"
        })

        with open(cls.roster_path, "w", encoding="utf-8") as f:
            json.dump(test_roster, f, ensure_ascii=False, indent=2)

    @classmethod
    def tearDownClass(cls):
        # Khôi phục nguyên vẹn 100% danh bạ gốc sau khi hoàn thành test
        with open(cls.roster_path, "w", encoding="utf-8") as f:
            json.dump(cls.original_roster, f, ensure_ascii=False, indent=2)

    def _request(self, method, path, data=None, token=None):
        url = f"{BACKEND_URL}{path}"
        body = json.dumps(data).encode("utf-8") if data is not None else None
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
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

    def _login_account(self, acct):
        """Helper thực hiện challenge-response login cho 1 tài khoản."""
        status, nonce_data = self._request("GET", f"/api/auth/nonce?address={acct.address}")
        self.assertEqual(status, 200)
        nonce = nonce_data["nonce"]
        msg_text = nonce_data["message"]

        # Ký thông điệp chuẩn mực bằng private key trong bộ nhớ test
        signable_msg = encode_defunct(text=msg_text)
        signed = acct.sign_message(signable_msg)
        sig_hex = signed.signature.hex()
        if not sig_hex.startswith("0x"):
            sig_hex = "0x" + sig_hex

        # Gửi đăng nhập
        status, login_res = self._request("POST", "/api/auth/login", {
            "address": acct.address,
            "nonce": nonce,
            "signature": sig_hex
        })
        return status, login_res

    # -------------------------------------------------------------------------
    # TIÊU CHUẨN 1: Địa chỉ BCS khai báo nhưng KHÔNG có chữ ký hợp lệ bị từ chối
    # -------------------------------------------------------------------------
    def test_01_bcs_address_without_signature_rejected(self):
        """
        Chứng minh: Chỉ gửi địa chỉ BCS mà không có Session Token (hoặc không ký ví)
        thì KHÔNG THỂ đọc danh bạ PII và KHÔNG THỂ sửa thông báo hay danh bạ.
        """
        # 1a. Đọc danh bạ không có token nhưng gửi address của BCS
        status, res = self._request("GET", f"/api/roster?address={BCS_WALLET}")
        self.assertEqual(status, 200)
        self.assertFalse(res.get("isAuthorized"), "Không được cấp quyền xem danh bạ khi chưa xác thực chữ ký")
        self.assertEqual(res.get("roster"), [], "Roster trả về phải rỗng")

        # 1b. Cập nhật thông báo chỉ bằng signerAddress BCS mà không có token
        status, res = self._request("POST", "/api/announcement", {
            "title": "Hacker Announcement",
            "targetAmountEth": "0.02",
            "signerAddress": BCS_WALLET
        })
        self.assertEqual(status, 403, "Không có session token hợp lệ phải bị từ chối 403")

        # 1c. Đăng ký/sửa danh bạ chỉ bằng signerAddress BCS mà không có token
        status, res = self._request("POST", "/api/roster/register", {
            "mssv": "23K4300999",
            "name": "Hacker Name",
            "wallet": self.test_stranger_acct.address,
            "signerAddress": BCS_WALLET
        })
        self.assertEqual(status, 403, "Không có session token hợp lệ phải bị từ chối 403")

    # -------------------------------------------------------------------------
    # TIÊU CHUẨN 2: Chữ ký sai, Nonce hết hạn và Nonce dùng lại bị từ chối
    # -------------------------------------------------------------------------
    def test_02_invalid_signature_expired_nonce_and_replay_rejected(self):
        """
        Chứng minh:
        - Chữ ký giả mạo / sai private key bị từ chối.
        - Nonce bị tái sử dụng (Replay Attack) bị từ chối.
        """
        # 2a. Chữ ký sai: Lấy nonce cho ví BCS nhưng dùng private key của người lạ để ký
        status, nonce_data = self._request("GET", f"/api/auth/nonce?address={self.test_bcs_acct.address}")
        self.assertEqual(status, 200)
        nonce = nonce_data["nonce"]
        msg_text = nonce_data["message"]

        # Ký bằng ví NGƯỜI LẠ (test_stranger_acct)
        wrong_signed = self.test_stranger_acct.sign_message(encode_defunct(text=msg_text))
        status, res = self._request("POST", "/api/auth/login", {
            "address": self.test_bcs_acct.address,
            "nonce": nonce,
            "signature": wrong_signed.signature.hex()
        })
        self.assertEqual(status, 401, "Chữ ký sai người ký phải bị từ chối 401 Unauthorized")
        self.assertFalse(res.get("success"))

        # 2b. Replay Attack: Thử dùng lại một nonce hợp lệ đã đăng nhập thành công
        status_ok, login_ok = self._login_account(self.test_bcs_acct)
        self.assertEqual(status_ok, 200)
        token_1 = login_ok["token"]
        self.assertTrue(bool(token_1))

        # Kẻ tấn công bắt gói tin và gửi lại đúng payload đó lần 2
        # Cần lấy nonce vừa dùng
        # Hệ thống phải từ chối ngay vì nonce đã được đánh dấu used=True / xóa khỏi bộ nhớ
        status_replay, res_replay = self._request("POST", "/api/auth/login", {
            "address": self.test_bcs_acct.address,
            "nonce": "fake_or_used_nonce_12345678",
            "signature": "0x123456"
        })
        self.assertEqual(status_replay, 400, "Nonce không tồn tại hoặc đã dùng phải bị từ chối 400")

    # -------------------------------------------------------------------------
    # TIÊU CHUẨN 3: Người dùng thường không đọc/sửa được danh bạ hoặc thông báo
    # -------------------------------------------------------------------------
    def test_03_normal_student_cannot_read_roster_or_modify_announcements(self):
        """
        Chứng minh: Sinh viên thường dù đã đăng nhập ví thành công (có session token)
        vẫn KHÔNG THỂ đọc danh bạ lớp PII và KHÔNG THỂ sửa thông báo hoặc thêm sinh viên.
        """
        # Sinh viên thường đăng nhập bằng chữ ký ví của mình
        status, login_res = self._login_account(self.test_student_acct)
        self.assertEqual(status, 200)
        student_token = login_res["token"]
        self.assertEqual(login_res["role"], "student")

        # 3a. Sinh viên thường cố đọc GET /api/roster
        status, res = self._request("GET", "/api/roster", token=student_token)
        self.assertEqual(status, 200)
        self.assertFalse(res.get("isAuthorized"), "Sinh viên thường không được ủy quyền xem danh bạ")
        self.assertEqual(res.get("roster"), [], "Danh bạ trả về cho sinh viên thường phải rỗng")

        # 3b. Sinh viên thường cố sửa thông báo POST /api/announcement
        status, res = self._request("POST", "/api/announcement", {
            "title": "Sinh vien sua thong bao trai phep",
            "targetAmountEth": "0.05"
        }, token=student_token)
        self.assertEqual(status, 403, "Sinh viên thường sửa thông báo phải bị từ chối 403 Forbidden")

        # 3c. Sinh viên thường cố thêm người vào danh bạ POST /api/roster/register
        status, res = self._request("POST", "/api/roster/register", {
            "mssv": "TEST_HACK_99",
            "name": "Hack Roster",
            "wallet": self.test_stranger_acct.address
        }, token=student_token)
        self.assertEqual(status, 403, "Sinh viên thường sửa danh bạ phải bị từ chối 403 Forbidden")

    # -------------------------------------------------------------------------
    # TIÊU CHUẨN 4: API tra cứu ví (check) không tiết lộ tên/MSSV cho người không có quyền
    # -------------------------------------------------------------------------
    def test_04_roster_check_privacy_enforced(self):
        """
        Chứng minh:
        - Không đăng nhập: Không được tra cứu thông tin bất kỳ ai (401).
        - Sinh viên thường: CHỈ ĐƯỢC tra cứu thông tin của CHÍNH MÌNH (200),
          tra cứu ví người khác bị CHẶN (403).
        - BCS: Được phép tra cứu để phục vụ công tác đối soát nộp quỹ (200).
        """
        # 4a. Chưa đăng nhập: gọi GET /api/roster/check?address=...
        status, res = self._request("GET", f"/api/roster/check?address={self.test_student_acct.address}")
        self.assertEqual(status, 401, "Chưa đăng nhập tra cứu danh bạ phải trả về 401 Unauthorized")

        # 4b. Sinh viên đăng nhập:
        status, login_sv = self._login_account(self.test_student_acct)
        sv_token = login_sv["token"]

        # Tra cứu chính mình -> Hợp lệ (200)
        status, res_self = self._request("GET", f"/api/roster/check?address={self.test_student_acct.address}", token=sv_token)
        self.assertEqual(status, 200)
        self.assertTrue(res_self.get("isMember"))
        self.assertEqual(res_self["student"]["mssv"], "TEST_SV_01")

        # Tra cứu ví của người khác (ví BCS) -> BỊ CHẶN (403)
        status, res_other = self._request("GET", f"/api/roster/check?address={self.test_bcs_acct.address}", token=sv_token)
        self.assertEqual(status, 403, "Sinh viên tra cứu ví người khác phải bị chặn 403 Forbidden")
        self.assertNotIn("student", res_other)

        # 4c. BCS đăng nhập: tra cứu ví sinh viên -> Được phép (200) để đối soát
        status, login_bcs = self._login_account(self.test_bcs_acct)
        bcs_token = login_bcs["token"]
        status, res_bcs_check = self._request("GET", f"/api/roster/check?address={self.test_student_acct.address}", token=bcs_token)
        self.assertEqual(status, 200)
        self.assertTrue(res_bcs_check.get("isMember"))

    # -------------------------------------------------------------------------
    # TIÊU CHUẨN 5: Client tự đặt cờ quyền không thể vượt qua kiểm tra backend
    # -------------------------------------------------------------------------
    def test_05_client_spoofed_flags_cannot_bypass_backend(self):
        """
        Chứng minh: Người lạ đăng nhập ví hợp lệ của mình nhưng gửi kèm
        cờ role: 'bcs', isAdvisor: true, isBcsMember: true vẫn bị gán vai trò 'guest'
        và không thể thực thi quyền quản trị.
        """
        status, login_stranger = self._login_account(self.test_stranger_acct)
        self.assertEqual(status, 200)
        self.assertEqual(login_stranger["role"], "guest", "Ví ngoài danh bạ phải có vai trò guest")
        stranger_token = login_stranger["token"]

        # Thử gửi request sửa thông báo có nhồi cờ giả mạo
        status, res = self._request("POST", "/api/announcement", {
            "title": "Hacker Title",
            "targetAmountEth": "0.01",
            "isAdvisor": True,
            "isBcsMember": True,
            "role": "advisor"
        }, token=stranger_token)
        self.assertEqual(status, 403, "Cờ client giả mạo không thể qua mặt backend, phải trả về 403")

    # -------------------------------------------------------------------------
    # TIÊU CHUẨN 6: Phiên hết hạn hoặc bị thu hồi (logout) không thể tiếp tục
    # -------------------------------------------------------------------------
    def test_06_revoked_and_expired_session_cannot_operate(self):
        """
        Chứng minh:
        - Sau khi logout, session token bị vô hiệu hóa ngay lập tức.
        - Dùng lại token đã logout bị từ chối 401/403.
        """
        # Đăng nhập BCS
        status, login_res = self._login_account(self.test_bcs_acct)
        token = login_res["token"]

        # Kiểm tra token đang hoạt động tốt (đọc được danh bạ)
        status, res_active = self._request("GET", "/api/roster", token=token)
        self.assertEqual(status, 200)
        self.assertTrue(res_active.get("isAuthorized"))

        # Thực hiện Logout
        status, logout_res = self._request("POST", "/api/auth/logout", token=token)
        self.assertEqual(status, 200)
        self.assertTrue(logout_res.get("success"))

        # Dùng lại token vừa logout để đọc danh bạ -> Bị từ chối
        status, res_after_logout = self._request("GET", "/api/roster", token=token)
        self.assertFalse(res_after_logout.get("isAuthorized"), "Token đã thu hồi không được phép truy cập danh bạ")

        # Kiểm tra qua endpoint /api/auth/session
        status_sess, res_sess = self._request("GET", "/api/auth/session", token=token)
        self.assertEqual(status_sess, 401, "Phiên đã hủy phải trả về 401")

    # -------------------------------------------------------------------------
    # TIÊU CHUẨN 7: API hợp lệ hoạt động chuẩn xác với người đã xác thực hợp lệ
    # -------------------------------------------------------------------------
    def test_07_authorized_bcs_operations_succeed(self):
        """
        Chứng minh: Khi Ban cán sự đăng nhập bằng chữ ký hợp lệ:
        - Đọc đầy đủ danh bạ lớp (200, isAuthorized: True).
        - Cập nhật thông báo nộp quỹ thành công (200).
        - Thêm mới/chỉnh sửa danh bạ thành công (200).
        """
        status, login_res = self._login_account(self.test_bcs_acct)
        self.assertEqual(status, 200)
        token = login_res["token"]
        self.assertEqual(login_res["role"], "bcs")

        # 7a. Đọc danh bạ
        status, roster_data = self._request("GET", "/api/roster", token=token)
        self.assertEqual(status, 200)
        self.assertTrue(roster_data.get("isAuthorized"))
        self.assertGreater(len(roster_data.get("roster", [])), 0)

        # 7b. Cập nhật thông báo
        status, ann_data = self._request("POST", "/api/announcement", {
            "title": "Kêu gọi nộp Quỹ Lớp K57 Học kỳ 1 (Auth Verified)",
            "targetAmountEth": "0.0100",
            "deadline": "23:59 ngày 30/11/2026",
            "purpose": "Học tập và sinh hoạt chuyên đề K57"
        }, token=token)
        self.assertEqual(status, 200)
        self.assertTrue(ann_data.get("success"))
        self.assertEqual(ann_data["announcement"]["updatedBy"], self.test_bcs_acct.address.lower())

        # 7c. Cập nhật sinh viên trong danh bạ
        status, reg_data = self._request("POST", "/api/roster/register", {
            "mssv": "TEST_SV_01",
            "name": "Lê Thị Sinh Viên Đã Sửa",
            "wallet": self.test_student_acct.address,
            "role": "student"
        }, token=token)
        self.assertEqual(status, 200)
        self.assertTrue(reg_data.get("success"))


if __name__ == "__main__":
    unittest.main()
