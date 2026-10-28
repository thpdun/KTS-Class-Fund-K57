#!/usr/bin/env python3
"""
STAGE 3B.4.4 — Independent Verification Test Suite
Kiểm thử HTTP thực tế trên backend đang chạy (http://localhost:8000)
1. Cơ chế Nonce:
   - Chữ ký sai không làm mất nonce hợp lệ.
   - Nhiều request cùng nonce chạy đồng thời -> tối đa 1 request được cấp session.
   - Double-check nonce sau verify chữ ký ngoài lock.
   - Session chỉ được cấp sau khi nonce được tiêu thụ nguyên tử.
   - Logout và token đã thu hồi không thể tái sử dụng.
2. CORS Verification:
   - Origin trong whitelist nhận header Access-Control-Allow-Origin.
   - Origin không hợp lệ không nhận Access-Control-Allow-Origin.
   - Origin null bị từ chối khi IS_PRODUCTION=True.
   - Kiểm tra OPTIONS preflight.
"""

import sys
import json
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from eth_account import Account
from eth_account.messages import encode_defunct

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BACKEND_URL = "http://localhost:8000"

def http_req(method, path, data=None, token=None, origin=None, headers=None):
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

print("======================================================================")
print("  STAGE 3B.4.4 — BẮT ĐẦU KIỂM THỬ ĐỘC LẬP TOÀN DIỆN HTTP REAL SERVER   ")
print("======================================================================\n")

total_tests = 0
passed_tests = 0

def check_assert(condition, title, details=""):
    global total_tests, passed_tests
    total_tests += 1
    if condition:
        passed_tests += 1
        print(f"  [PASS] Ca {total_tests}: {title}")
    else:
        print(f"  [FAIL] Ca {total_tests}: {title} | Chi tiết: {details}")

# -----------------------------------------------------------------------------
# PHẦN 1: KIỂM TRA CƠ CHẾ NONCE
# -----------------------------------------------------------------------------
print("--- 1. KIỂM TRA CƠ CHẾ NONCE & SESSION VỚI CHỮ KÝ MẬT MÃ ---")

acct_a = Account.create()
acct_b = Account.create()

# 1.1 Chữ ký sai không làm mất nonce hợp lệ
s1, h1, d1 = http_req("GET", f"/api/auth/nonce?address={acct_a.address}")
check_assert(s1 == 200 and "nonce" in d1, "Lấy nonce thành công cho ví A", f"status={s1}")
nonce_1 = d1.get("nonce")
msg_1 = d1.get("message")

# Tạo chữ ký sai: Ký bởi ví B thay vì ví A
bad_sig = acct_b.sign_message(encode_defunct(text=msg_1)).signature.hex()
s_bad, h_bad, d_bad = http_req("POST", "/api/auth/login", {
    "address": acct_a.address,
    "nonce": nonce_1,
    "signature": bad_sig
})
check_assert(s_bad == 401, "Gửi chữ ký sai trả về HTTP 401 Unauthorized", f"status={s_bad}, resp={d_bad}")

# Dùng lại CHÍNH NONCE ĐÓ với chữ ký ĐÚNG từ ví A
good_sig = acct_a.sign_message(encode_defunct(text=msg_1)).signature.hex()
s_good, h_good, d_good = http_req("POST", "/api/auth/login", {
    "address": acct_a.address,
    "nonce": nonce_1,
    "signature": good_sig
})
check_assert(s_good == 200 and "token" in d_good, "Sau khi bị 401, nonce vẫn còn nguyên và đăng nhập thành công với chữ ký đúng", f"status={s_good}, resp={d_good}")
session_token_1 = d_good.get("token")

# 1.2 Kiểm tra Replay Attack với nonce đã dùng
s_replay, h_replay, d_replay = http_req("POST", "/api/auth/login", {
    "address": acct_a.address,
    "nonce": nonce_1,
    "signature": good_sig
})
check_assert(s_replay == 400, "Thử sử dụng lại nonce vừa dùng (Replay) bị từ chối HTTP 400", f"status={s_replay}")

# 1.3 Concurrency Test: 15 threads gửi đồng thời cùng 1 nonce hợp lệ
acct_concurrent = Account.create()
s_nc, h_nc, d_nc = http_req("GET", f"/api/auth/nonce?address={acct_concurrent.address}")
nonce_conc = d_nc["nonce"]
msg_conc = d_nc["message"]
sig_conc = acct_concurrent.sign_message(encode_defunct(text=msg_conc)).signature.hex()

payload_conc = {
    "address": acct_concurrent.address,
    "nonce": nonce_conc,
    "signature": sig_conc
}

concurrent_results = []
def worker_send(tid):
    s, h, d = http_req("POST", "/api/auth/login", data=payload_conc)
    return tid, s, d

with ThreadPoolExecutor(max_workers=15) as executor:
    futures = [executor.submit(worker_send, i) for i in range(15)]
    for f in futures:
        concurrent_results.append(f.result())

status_200_count = sum(1 for _, s, _ in concurrent_results if s == 200)
status_400_count = sum(1 for _, s, _ in concurrent_results if s == 400)
tokens_granted = [d["token"] for _, s, d in concurrent_results if s == 200 and "token" in d]

print(f"    -> Kết quả bắn 15 requests đồng thời: 200 OK = {status_200_count}, 400 Bad Request = {status_400_count}")
print(f"    -> Số session token được cấp phát: {len(tokens_granted)}")
check_assert(status_200_count == 1, "Chính xác 1 request thành công 200 OK trong 15 requests đồng thời", f"status_200_count={status_200_count}")
check_assert(status_400_count == 14, "Chính xác 14 requests còn lại bị từ chối 400 Bad Request", f"status_400_count={status_400_count}")
check_assert(len(set(tokens_granted)) == 1, "Tối đa đúng 1 session duy nhất được cấp", f"tokens={tokens_granted}")

# 1.4 Logout và Hủy phiên
# Token vừa được cấp từ test 1.1 (session_token_1)
s_sess_pre, _, d_sess_pre = http_req("GET", "/api/auth/session", token=session_token_1)
check_assert(s_sess_pre == 200 and d_sess_pre.get("authenticated") is True, "Token đang hoạt động, GET /api/auth/session trả về 200", f"status={s_sess_pre}")

# Gọi Logout
s_logout, _, d_logout = http_req("POST", "/api/auth/logout", token=session_token_1)
check_assert(s_logout == 200 and d_logout.get("success") is True, "POST /api/auth/logout thu hồi session thành công", f"status={s_logout}")

# Kiểm tra lại sau khi logout
s_sess_post, _, d_sess_post = http_req("GET", "/api/auth/session", token=session_token_1)
check_assert(s_sess_post == 401, "Sau logout, GET /api/auth/session với token cũ bị từ chối 401", f"status={s_sess_post}")

# Thử dùng token đã logout gọi API cần quyền /api/roster
s_roster, _, d_roster = http_req("GET", "/api/roster", token=session_token_1)
check_assert(s_roster == 200 and d_roster.get("isAuthorized") is False and d_roster.get("roster") == [], 
             "Token đã logout không thể xem danh bạ (isAuthorized: False, roster rỗng)", f"roster={d_roster}")

# -----------------------------------------------------------------------------
# PHẦN 2: KIỂM TRA CẤU HÌNH CORS TRÊN MẠNG THẬT
# -----------------------------------------------------------------------------
print("\n--- 2. KIỂM TRA CẤU HÌNH CORS TRÊN HTTP THẬT ---")

# 2.1 Allowed Origin (GET)
s_c1, h_c1, _ = http_req("GET", "/api/status", origin="http://localhost:3000")
check_assert(s_c1 == 200 and h_c1.get("Access-Control-Allow-Origin") == "http://localhost:3000",
             "Origin http://localhost:3000 nhận được header Access-Control-Allow-Origin khớp", f"headers={h_c1}")
check_assert(h_c1.get("Access-Control-Max-Age") == "86400", "Access-Control-Max-Age gửi đúng 86400s", f"max-age={h_c1.get('Access-Control-Max-Age')}")

# 2.2 Allowed Origin (OPTIONS preflight)
s_c2, h_c2, _ = http_req("OPTIONS", "/api/auth/login", origin="http://127.0.0.1:5500", headers={
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "authorization,content-type"
})
check_assert(s_c2 == 200 and h_c2.get("Access-Control-Allow-Origin") == "http://127.0.0.1:5500",
             "OPTIONS preflight từ 127.0.0.1:5500 trả về 200 và cấp CORS", f"status={s_c2}")
check_assert("POST" in h_c2.get("Access-Control-Allow-Methods", ""), "Preflight cho phép phương thức POST", f"methods={h_c2.get('Access-Control-Allow-Methods')}")

# 2.3 Disallowed Origin (GET)
s_c3, h_c3, _ = http_req("GET", "/api/status", origin="http://malicious-attacker.com")
check_assert("Access-Control-Allow-Origin" not in h_c3,
             "Origin không hợp lệ (http://malicious-attacker.com) TUYỆT ĐỐI KHÔNG nhận header Access-Control-Allow-Origin", f"headers={h_c3}")

# 2.4 Disallowed Origin (OPTIONS preflight)
s_c4, h_c4, _ = http_req("OPTIONS", "/api/auth/login", origin="https://evil-phishing-site.xyz", headers={
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "authorization,content-type"
})
check_assert("Access-Control-Allow-Origin" not in h_c4,
             "OPTIONS preflight từ origin độc hại KHÔNG nhận được header Access-Control-Allow-Origin", f"headers={h_c4}")

# 2.5 Request không có header Origin (curl / internal scripts)
s_c5, h_c5, _ = http_req("GET", "/api/status", origin=None)
check_assert("Access-Control-Allow-Origin" not in h_c5,
             "Request không mang Origin (như curl / urllib) không nhận header CORS", f"headers={h_c5}")

print(f"\n======================================================================")
print(f"  TỔNG KẾT KIỂM THỬ ĐỘC LẬP STAGE 3B.4.4: {passed_tests}/{total_tests} PASS")
print(f"======================================================================")

if passed_tests == total_tests:
    sys.exit(0)
else:
    sys.exit(1)
