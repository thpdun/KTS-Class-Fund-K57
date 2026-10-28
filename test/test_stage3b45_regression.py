#!/usr/bin/env python3
"""
STAGE 3B.4.5 — Comprehensive Nonce Validation & Regression Test Suite
Dự án: KTS-Class-Fund-K57

Bao phủ 8 trường hợp kiểm thử hồi quy bắt buộc:
A. Sinh nonce thành công (HTTP thật).
B. Chữ ký sai trả về 401; nonce còn hạn vẫn dùng được với chữ ký đúng (HTTP thật).
C. Concurrency: 20 luồng đồng thời -> Đúng 1 request 200, 19 request 400, duy nhất 1 session được cấp (HTTP thật).
D. Nonce hết hạn trước khi đăng nhập bị từ chối 400 (Mô phỏng thời gian handler).
E. Nonce hết hạn TRONG THỜI GIAN xác minh chữ ký bị từ chối ở bước kiểm tra cuối 400 (Mô phỏng thời gian có kiểm soát).
F. Nonce đã dùng không thể replay 400 (HTTP thật).
G. Logout vô hiệu hóa session, không thể tái sử dụng token 401 (HTTP thật).
H. CORS Whitelist và kiểm soát Origin không bị hồi quy (HTTP thật).
"""

import unittest
import json
import time
import sys
import io
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

from eth_account import Account
from eth_account.messages import encode_defunct

import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import backend.server as srv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BACKEND_URL = "http://localhost:8000"

def do_http(method, path, data=None, token=None, origin=None, headers=None):
    url = f"{BACKEND_URL}{path}"
    req_headers = {}
    if headers:
        req_headers.update(headers)
    if origin:
        req_headers["Origin"] = origin
    if token:
        req_headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    if data is not None and "Content-Type" not in req_headers:
        req_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_headers = dict(resp.headers)
            raw = resp.read().decode("utf-8")
            return resp.status, resp_headers, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        resp_headers = dict(e.headers)
        raw = e.read().decode("utf-8")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"raw": raw}
        return e.code, resp_headers, parsed
    except Exception as e:
        return 0, {}, {"error": str(e)}


class MockSocket:
    """Mock socket để kiểm thử trực tiếp handler AIChatRequestHandler trong tiến trình test."""
    def __init__(self, raw_bytes):
        self.rfile = io.BytesIO(raw_bytes)
        self.output = io.BytesIO()

    def makefile(self, mode, *args, **kwargs):
        if 'r' in mode:
            return self.rfile
        return self.output

    def sendall(self, b):
        self.output.write(b)


class DummyServer:
    pass


def execute_in_process_post(path, data):
    body = json.dumps(data).encode("utf-8")
    req_text = (
        f"POST {path} HTTP/1.1\r\n"
        f"Host: localhost\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Content-Type: application/json\r\n\r\n"
    ).encode("utf-8") + body

    sock = MockSocket(req_text)
    handler = srv.AIChatRequestHandler(sock, ("127.0.0.1", 9999), DummyServer())
    raw_res = sock.output.getvalue().decode("utf-8", errors="replace")

    parts = raw_res.split("\r\n\r\n", 1)
    header_part = parts[0]
    body_part = parts[1] if len(parts) > 1 else "{}"

    status_line = header_part.split("\r\n")[0]
    status_code = int(status_line.split(" ")[1])

    try:
        parsed_body = json.loads(body_part)
    except Exception:
        parsed_body = {"raw": body_part}

    return status_code, parsed_body


class TestStage3B45Regression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acct_a = Account.create()
        cls.acct_b = Account.create()

    # -------------------------------------------------------------------------
    # TRƯỜNG HỢP A: Sinh nonce thành công
    # -------------------------------------------------------------------------
    def test_A_nonce_generation_success(self):
        """[HTTP thật] GET /api/auth/nonce trả về 200, nonce 32 ký tự hex, message chuẩn, hạn 300s."""
        status, headers, body = do_http("GET", f"/api/auth/nonce?address={self.acct_a.address}")
        self.assertEqual(status, 200)
        self.assertTrue(body.get("success"))
        self.assertEqual(body.get("address"), self.acct_a.address.lower())
        nonce = body.get("nonce")
        self.assertTrue(bool(nonce) and len(nonce) == 32)
        self.assertIn("KTS-Class-Fund-K57 Authentication", body.get("message", ""))
        self.assertEqual(body.get("expiresIn"), 300)

    # -------------------------------------------------------------------------
    # TRƯỜNG HỢP B: Chữ ký sai không làm mất nonce hợp lệ
    # -------------------------------------------------------------------------
    def test_B_invalid_signature_does_not_consume_nonce(self):
        """[HTTP thật] Chữ ký sai trả về 401; dùng lại chính nonce đó với chữ ký đúng trả về 200."""
        # 1. Lấy nonce cho ví A
        status, _, body = do_http("GET", f"/api/auth/nonce?address={self.acct_a.address}")
        self.assertEqual(status, 200)
        nonce = body["nonce"]
        msg = body["message"]

        # 2. Ký bằng ví B (chữ ký sai người ký)
        bad_sig = self.acct_b.sign_message(encode_defunct(text=msg)).signature.hex()
        status_bad, _, body_bad = do_http("POST", "/api/auth/login", {
            "address": self.acct_a.address,
            "nonce": nonce,
            "signature": bad_sig
        })
        self.assertEqual(status_bad, 401, "Chữ ký sai phải trả về HTTP 401 Unauthorized")
        self.assertFalse(body_bad.get("success"))

        # 3. Ký lại bằng ví A (chữ ký chuẩn) với CÙNG NONCE ĐÓ
        good_sig = self.acct_a.sign_message(encode_defunct(text=msg)).signature.hex()
        status_good, _, body_good = do_http("POST", "/api/auth/login", {
            "address": self.acct_a.address,
            "nonce": nonce,
            "signature": good_sig
        })
        self.assertEqual(status_good, 200, "Sau khi bị 401, nonce còn hạn vẫn dùng được với chữ ký đúng")
        self.assertTrue(body_good.get("success"))
        self.assertTrue(bool(body_good.get("token")))

    # -------------------------------------------------------------------------
    # TRƯỜNG HỢP C: Concurrency - 20 requests đồng thời chỉ cấp đúng 1 session
    # -------------------------------------------------------------------------
    def test_C_concurrent_requests_grant_at_most_one_session(self):
        """[HTTP thật] 20 luồng đồng thời dùng cùng 1 nonce: Đúng 1 request 200, 19 request 400, duy nhất 1 session."""
        acct_conc = Account.create()
        status, _, body = do_http("GET", f"/api/auth/nonce?address={acct_conc.address}")
        self.assertEqual(status, 200)
        nonce = body["nonce"]
        msg = body["message"]
        sig = acct_conc.sign_message(encode_defunct(text=msg)).signature.hex()

        payload = {
            "address": acct_conc.address,
            "nonce": nonce,
            "signature": sig
        }

        results = []
        def worker(idx):
            s, h, b = do_http("POST", "/api/auth/login", data=payload)
            return idx, s, b

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            for f in futures:
                results.append(f.result())

        status_200 = [b for _, s, b in results if s == 200]
        status_400 = [b for _, s, b in results if s == 400]

        self.assertEqual(len(status_200), 1, "Chính xác đúng 1 request thành công HTTP 200")
        self.assertEqual(len(status_400), 19, "Chính xác 19 requests bị từ chối HTTP 400")

        # Kiểm tra tính hợp lệ của session duy nhất được cấp
        granted_token = status_200[0]["token"]
        self.assertTrue(bool(granted_token))
        s_sess, _, b_sess = do_http("GET", "/api/auth/session", token=granted_token)
        self.assertEqual(s_sess, 200)
        self.assertTrue(b_sess.get("authenticated"))
        self.assertEqual(b_sess.get("address"), acct_conc.address.lower())

    # -------------------------------------------------------------------------
    # TRƯỜNG HỢP D: Nonce hết hạn trước khi đăng nhập bị từ chối (bước 1.3)
    # -------------------------------------------------------------------------
    def test_D_expired_nonce_before_login_rejected(self):
        """[Mô phỏng thời gian handler] Nonce có expires_at trong quá khứ bị từ chối ở bước 1.3 với HTTP 400."""
        acct = Account.create()
        nonce = "test_expired_before_login_9999"
        addr = acct.address.lower()

        # Nạp nonce đã hết hạn 10s trước vào ACTIVE_NONCES
        with srv.AUTH_MUTEX:
            srv.ACTIVE_NONCES[nonce] = {
                "address": addr,
                "expires_at": time.time() - 10,
                "used": False,
                "created_at": time.time() - 310
            }

        msg = srv.generate_auth_message(addr, nonce)
        sig = acct.sign_message(encode_defunct(text=msg)).signature.hex()

        status, body = execute_in_process_post("/api/auth/login", {
            "address": addr,
            "nonce": nonce,
            "signature": sig
        })

        self.assertEqual(status, 400, "Nonce hết hạn trước login phải trả về HTTP 400")
        err_msg = body.get("error", "").lower()
        self.assertTrue("hết hạn" in err_msg or "không tồn tại" in err_msg, f"Thông báo lỗi phải thể hiện nonce không hợp lệ: {err_msg}")
        self.assertNotIn(nonce, srv.ACTIVE_NONCES, "Nonce hết hạn phải bị xóa khỏi ACTIVE_NONCES")

    # -------------------------------------------------------------------------
    # TRƯỜNG HỢP E: Nonce hết hạn TRONG THỜI GIAN xác minh chữ ký (bước 1.6)
    # -------------------------------------------------------------------------
    def test_E_nonce_expires_during_signature_verification_rejected_at_final_check(self):
        """
        [Mô phỏng thời gian có kiểm soát]
        Kịch bản kiểm thử:
        - Tại Bước 1.1: Nonce còn hạn (expires_at = T0 + 5).
        - Tại Bước 1.5: Thao tác xác minh chữ ký diễn ra, thời gian giả lập được tăng vọt qua mốc expires_at.
        - Tại Bước 1.6: Server re-check expires_at dưới AUTH_MUTEX -> Phát hiện quá hạn -> Trả về HTTP 400!
        - Không có session nào được tạo, nonce bị tiêu hủy.
        """
        acct = Account.create()
        nonce = "test_expire_during_sig_atomic"
        addr = acct.address.lower()

        t0 = 1000000.0  # Mốc thời gian giả định ban đầu

        # Cấu hình nonce có hạn đến t0 + 5 giây
        with srv.AUTH_MUTEX:
            srv.ACTIVE_NONCES[nonce] = {
                "address": addr,
                "expires_at": t0 + 5.0,
                "used": False,
                "created_at": t0
            }

        msg = srv.generate_auth_message(addr, nonce)
        sig = acct.sign_message(encode_defunct(text=msg)).signature.hex()

        simulated_time = t0
        def get_simulated_time():
            return simulated_time

        orig_recover = Account.recover_message
        def delayed_recover(*args, **kwargs):
            nonlocal simulated_time
            # Nhảy vọt thời gian sang t0 + 10 giây (vượt quá expires_at = t0 + 5)
            simulated_time = t0 + 10.0
            return orig_recover(*args, **kwargs)

        sessions_before = len(srv.ACTIVE_SESSIONS)

        # Chặn time.time và Account.recover_message trong module srv
        orig_time = srv.time.time
        orig_account_recover = srv.Account.recover_message
        try:
            srv.time.time = get_simulated_time
            srv.Account.recover_message = delayed_recover

            status, body = execute_in_process_post("/api/auth/login", {
                "address": addr,
                "nonce": nonce,
                "signature": sig
            })
        finally:
            srv.time.time = orig_time
            srv.Account.recover_message = orig_account_recover

        # Kiểm chứng nghiêm ngặt
        self.assertEqual(status, 400, "Nonce hết hạn trong lúc xác thực chữ ký phải bị từ chối 400 ở bước 1.6")
        self.assertIn("hết hạn trong lúc xác thực", body.get("error", "").lower())
        self.assertNotIn(nonce, srv.ACTIVE_NONCES, "Nonce hết hạn phải bị hủy khỏi ACTIVE_NONCES")
        self.assertEqual(len(srv.ACTIVE_SESSIONS), sessions_before, "Tuyệt đối không cấp session nào khi nonce hết hạn")

    # -------------------------------------------------------------------------
    # TRƯỜNG HỢP F: Nonce đã dùng không thể replay
    # -------------------------------------------------------------------------
    def test_F_used_nonce_cannot_replay(self):
        """[HTTP thật] Gửi lại một nonce đã đăng nhập thành công bị từ chối HTTP 400."""
        acct = Account.create()
        status, _, body = do_http("GET", f"/api/auth/nonce?address={acct.address}")
        nonce = body["nonce"]
        msg = body["message"]
        sig = acct.sign_message(encode_defunct(text=msg)).signature.hex()

        # Login lần 1 -> 200
        s1, _, b1 = do_http("POST", "/api/auth/login", {"address": acct.address, "nonce": nonce, "signature": sig})
        self.assertEqual(s1, 200)

        # Login lần 2 (Replay) -> 400
        s2, _, b2 = do_http("POST", "/api/auth/login", {"address": acct.address, "nonce": nonce, "signature": sig})
        self.assertEqual(s2, 400)
        self.assertFalse(b2.get("success"))

    # -------------------------------------------------------------------------
    # TRƯỜNG HỢP G: Logout vô hiệu hóa session
    # -------------------------------------------------------------------------
    def test_G_logout_invalidates_session(self):
        """[HTTP thật] Sau khi logout, session token cũ bị từ chối 401 trên /api/auth/session và /api/roster."""
        acct = Account.create()
        status, _, body = do_http("GET", f"/api/auth/nonce?address={acct.address}")
        nonce = body["nonce"]
        sig = acct.sign_message(encode_defunct(text=body["message"])).signature.hex()

        # Login
        s_log, _, b_log = do_http("POST", "/api/auth/login", {"address": acct.address, "nonce": nonce, "signature": sig})
        token = b_log["token"]

        # Kiểm tra đang active -> 200
        s_chk1, _, b_chk1 = do_http("GET", "/api/auth/session", token=token)
        self.assertEqual(s_chk1, 200)
        self.assertTrue(b_chk1.get("authenticated"))

        # Logout -> 200
        s_out, _, b_out = do_http("POST", "/api/auth/logout", token=token)
        self.assertEqual(s_out, 200)

        # Kiểm tra sau logout -> 401
        s_chk2, _, b_chk2 = do_http("GET", "/api/auth/session", token=token)
        self.assertEqual(s_chk2, 401)

    # -------------------------------------------------------------------------
    # TRƯỜNG HỢP H: CORS Whitelist & Origin Security không bị hồi quy
    # -------------------------------------------------------------------------
    def test_H_cors_and_role_permissions_no_regression(self):
        """[HTTP thật] Whitelist CORS nhận đúng header; origin lạ không nhận CORS; preflight 200."""
        # 1. Allowed origin GET
        s_get, h_get, _ = do_http("GET", "/api/status", origin="http://localhost:3000")
        self.assertEqual(s_get, 200)
        self.assertEqual(h_get.get("Access-Control-Allow-Origin"), "http://localhost:3000")
        self.assertEqual(h_get.get("Access-Control-Max-Age"), "86400")

        # 2. Allowed origin OPTIONS preflight
        s_opt, h_opt, _ = do_http("OPTIONS", "/api/auth/login", origin="http://127.0.0.1:5500", headers={
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type"
        })
        self.assertEqual(s_opt, 200)
        self.assertEqual(h_opt.get("Access-Control-Allow-Origin"), "http://127.0.0.1:5500")
        self.assertIn("POST", h_opt.get("Access-Control-Allow-Methods", ""))

        # 3. Disallowed origin GET
        s_dis, h_dis, _ = do_http("GET", "/api/status", origin="http://hacker-c2.net")
        self.assertEqual(s_dis, 200)
        self.assertNotIn("Access-Control-Allow-Origin", h_dis, "Origin lạ không được nhận CORS header")


if __name__ == "__main__":
    unittest.main()
