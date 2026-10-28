import os
import sys
import json
import time
import urllib.request
import urllib.error
from eth_account import Account
from eth_account.messages import encode_defunct

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BACKEND_URL = "http://localhost:8000"
ROSTER_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend", "class_roster.json")

# Backup original roster
with open(ROSTER_PATH, "r", encoding="utf-8") as f:
    ORIGINAL_ROSTER = json.load(f)

# Create test wallets
test_bcs = Account.create()
test_student = Account.create()
test_outsider = Account.create()

# Add test accounts to roster for the duration of this audit script
temp_roster = list(ORIGINAL_ROSTER)
temp_roster.append({
    "mssv": "AUDIT_BCS_01",
    "name": "Audit BCS Tester",
    "wallet": test_bcs.address,
    "role": "bcs",
    "roleTitle": "Ban cán sự"
})
temp_roster.append({
    "mssv": "AUDIT_SV_01",
    "name": "Audit Student Tester",
    "wallet": test_student.address,
    "role": "student",
    "roleTitle": "Sinh viên"
})

with open(ROSTER_PATH, "w", encoding="utf-8") as f:
    json.dump(temp_roster, f, ensure_ascii=False, indent=2)

def restore_roster():
    with open(ROSTER_PATH, "w", encoding="utf-8") as f:
        json.dump(ORIGINAL_ROSTER, f, ensure_ascii=False, indent=2)

def req(method, path, data=None, token=None, extra_headers=None):
    url = f"{BACKEND_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if extra_headers:
        headers.update(extra_headers)
    
    body = json.dumps(data).encode("utf-8") if data is not None else None
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"raw": raw}
        return e.code, parsed
    except Exception as e:
        return 0, {"error": str(e)}

def login_account(acct):
    s, d = req("GET", f"/api/auth/nonce?address={acct.address}")
    if s != 200:
        return None, d
    nonce = d["nonce"]
    msg = d["message"]
    sig = acct.sign_message(encode_defunct(text=msg)).signature.hex()
    s2, d2 = req("POST", "/api/auth/login", data={
        "address": acct.address,
        "nonce": nonce,
        "signature": sig
    })
    return d2.get("token"), d2

try:
    print("=== 1. KIỂM TRA ĐĂNG NHẬP VÍ (WALLET AUTH FLOW) ===")
    
    # 1.1 Thử đăng nhập chỉ bằng cách gửi signerAddress (không nonce, không signature)
    s, r = req("POST", "/api/auth/login", data={"address": test_bcs.address, "signerAddress": test_bcs.address})
    print(f"1.1 Spoof address without signature: status={s}, error={r.get('error')}")
    assert s == 400

    # 1.2 Thử đăng nhập với nonce sai / không tồn tại
    s, r = req("POST", "/api/auth/login", data={"address": test_bcs.address, "nonce": "invalidnonce123", "signature": "0x1234"})
    print(f"1.2 Invalid nonce: status={s}, error={r.get('error')}")
    assert s == 400

    # 1.3 Thử đăng nhập với chữ ký sai
    s_n, d_n = req("GET", f"/api/auth/nonce?address={test_bcs.address}")
    s, r = req("POST", "/api/auth/login", data={"address": test_bcs.address, "nonce": d_n["nonce"], "signature": "0x" + "aa"*65})
    print(f"1.3 Corrupt signature: status={s}, error={r.get('error')}")
    assert s in [400, 401]

    # 1.4 Thử đăng nhập với địa chỉ không khớp (A ký, nhưng claim ví B)
    s_n, d_n = req("GET", f"/api/auth/nonce?address={test_bcs.address}")
    sig_student = test_student.sign_message(encode_defunct(text=d_n["message"])).signature.hex()
    s, r = req("POST", "/api/auth/login", data={"address": test_bcs.address, "nonce": d_n["nonce"], "signature": sig_student})
    print(f"1.4 Address mismatch (student signs for BCS nonce): status={s}, error={r.get('error')}")
    assert s in [400, 401]

    # 1.5 Đăng nhập hợp lệ cho BCS, Student, Stranger
    bcs_token, bcs_info = login_account(test_bcs)
    student_token, student_info = login_account(test_student)
    stranger_token, stranger_info = login_account(test_outsider)
    print(f"1.5 BCS login: role={bcs_info.get('role')}, token_len={len(bcs_token) if bcs_token else 0}")
    print(f"1.5 Student login: role={student_info.get('role')}, token_len={len(student_token) if student_token else 0}")
    print(f"1.5 Stranger login: role={stranger_info.get('role')}, token_len={len(stranger_token) if stranger_token else 0}")
    assert bcs_info.get("role") == "bcs"
    assert student_info.get("role") == "student"
    assert stranger_info.get("role") == "guest"

    # 1.6 Kiểm tra Nonce dùng lại (Replay attack)
    s_n, d_n = req("GET", f"/api/auth/nonce?address={test_bcs.address}")
    sig = test_bcs.sign_message(encode_defunct(text=d_n["message"])).signature.hex()
    s_login1, _ = req("POST", "/api/auth/login", data={"address": test_bcs.address, "nonce": d_n["nonce"], "signature": sig})
    s_login2, r_login2 = req("POST", "/api/auth/login", data={"address": test_bcs.address, "nonce": d_n["nonce"], "signature": sig})
    print(f"1.6 Replay attack with same nonce: 1st={s_login1}, 2nd={s_login2}, error={r_login2.get('error')}")
    assert s_login1 == 200 and s_login2 == 400

    # 1.7 Kiểm tra Session và Logout
    s_sess, d_sess = req("GET", "/api/auth/session", token=bcs_token)
    print(f"1.7 Session check before logout: status={s_sess}, address={d_sess.get('address')}, role={d_sess.get('role')}")
    assert s_sess == 200

    s_out, d_out = req("POST", "/api/auth/logout", token=bcs_token)
    print(f"1.7 Logout status={s_out}, message={d_out.get('message')}")
    assert s_out == 200

    s_sess2, d_sess2 = req("GET", "/api/auth/session", token=bcs_token)
    print(f"1.7 Session check after logout: status={s_sess2}, error={d_sess2.get('error')}")
    assert s_sess2 == 401

    # Login again to get a fresh bcs_token
    bcs_token, _ = login_account(test_bcs)

    print("\n=== 2. KIỂM TRA MA TRẬN PHÂN QUYỀN API NHẠY CẢM ===")
    
    # Danh sách các endpoints cần kiểm tra
    # Endpoint: GET /api/roster
    print("\n--- [GET /api/roster] ---")
    # a. Không token
    s, r = req("GET", "/api/roster")
    print(f"No token: status={s}, isAuthorized={r.get('isAuthorized')}, roster_len={len(r.get('roster', []))}")
    assert s == 200 and r.get("isAuthorized") is False and len(r.get("roster", [])) == 0

    # b. Token sai
    s, r = req("GET", "/api/roster", token="fake_invalid_token_123")
    print(f"Bad token: status={s}, isAuthorized={r.get('isAuthorized')}, roster_len={len(r.get('roster', []))}")
    assert s == 200 and r.get("isAuthorized") is False and len(r.get("roster", [])) == 0

    # c. Token sinh viên thường
    s, r = req("GET", "/api/roster", token=student_token)
    print(f"Student token: status={s}, isAuthorized={r.get('isAuthorized')}, roster_len={len(r.get('roster', []))}")
    assert s == 200 and r.get("isAuthorized") is False and len(r.get("roster", [])) == 0

    # d. Token BCS
    s, r = req("GET", "/api/roster", token=bcs_token)
    print(f"BCS token: status={s}, isAuthorized={r.get('isAuthorized')}, roster_len={len(r.get('roster', []))}")
    assert s == 200 and r.get("isAuthorized") is True and len(r.get("roster", [])) > 0

    # e. Client tự gửi query params giả mạo (?address=BCS&isAdvisor=1&isBcs=1)
    s, r = req("GET", f"/api/roster?address={test_bcs.address}&isAdvisor=1&isBcs=1")
    print(f"Spoofed query params without token: status={s}, isAuthorized={r.get('isAuthorized')}, roster_len={len(r.get('roster', []))}")
    assert s == 200 and r.get("isAuthorized") is False and len(r.get("roster", [])) == 0

    # Endpoint: GET /api/roster/check?address=...
    print("\n--- [GET /api/roster/check?address=...] ---")
    # a. Không token
    s, r = req("GET", f"/api/roster/check?address={test_student.address}")
    print(f"No token: status={s}, error={r.get('error')}")
    assert s == 401

    # b. Token sai
    s, r = req("GET", f"/api/roster/check?address={test_student.address}", token="fake_token")
    print(f"Bad token: status={s}, error={r.get('error')}")
    assert s == 401

    # c. Sinh viên tra cứu chính mình
    s, r = req("GET", f"/api/roster/check?address={test_student.address}", token=student_token)
    print(f"Student checks self: status={s}, isMember={r.get('isMember')}, student_name={r.get('student', {}).get('name')}")
    assert s == 200 and r.get("isMember") is True

    # d. Sinh viên tra cứu sinh viên khác (hoặc BCS)
    s, r = req("GET", f"/api/roster/check?address={test_bcs.address}", token=student_token)
    print(f"Student checks another (BCS): status={s}, error={r.get('error')}")
    assert s == 403

    # e. BCS tra cứu sinh viên bất kỳ
    s, r = req("GET", f"/api/roster/check?address={test_student.address}", token=bcs_token)
    print(f"BCS checks student: status={s}, isMember={r.get('isMember')}, student_name={r.get('student', {}).get('name')}")
    assert s == 200 and r.get("isMember") is True

    # Endpoint: POST /api/announcement
    print("\n--- [POST /api/announcement] ---")
    ann_payload = {
        "title": "Thông báo đợt thu mới kiểm tra bảo mật",
        "targetAmountEth": "0.01",
        "deadline": "23:59 ngày 30/11/2026",
        "purpose": "Kiểm tra quyền cập nhật thông báo",
        "status": "Đang diễn ra"
    }

    # a. Không token
    s, r = req("POST", "/api/announcement", data=ann_payload)
    print(f"No token: status={s}, error={r.get('error')}")
    assert s == 403

    # b. Token sai
    s, r = req("POST", "/api/announcement", data=ann_payload, token="fake_token")
    print(f"Bad token: status={s}, error={r.get('error')}")
    assert s == 403

    # c. Token sinh viên thường
    s, r = req("POST", "/api/announcement", data=ann_payload, token=student_token)
    print(f"Student token: status={s}, error={r.get('error')}")
    assert s == 403

    # d. Token sinh viên nhưng kèm cờ giả mạo (isAdvisor: true, signerAddress: BCS)
    spoofed_payload = dict(ann_payload)
    spoofed_payload.update({"isAdvisor": True, "isBcs": True, "signerAddress": test_bcs.address})
    s, r = req("POST", "/api/announcement", data=spoofed_payload, token=student_token)
    print(f"Student token + spoofed flags: status={s}, error={r.get('error')}")
    assert s == 403

    # e. Token BCS hợp lệ
    s, r = req("POST", "/api/announcement", data=ann_payload, token=bcs_token)
    print(f"BCS token: status={s}, success={r.get('success')}, updatedBy={r.get('announcement', {}).get('updatedBy')}")
    assert s == 200 and r.get("success") is True and r.get("announcement", {}).get("updatedBy").lower() == test_bcs.address.lower()

    # Endpoint: POST /api/roster/register
    print("\n--- [POST /api/roster/register] ---")
    reg_payload = {
        "mssv": "AUDIT_NEW_01",
        "name": "Audit New Student",
        "wallet": Account.create().address,
        "role": "student"
    }

    # a. Không token
    s, r = req("POST", "/api/roster/register", data=reg_payload)
    print(f"No token: status={s}, error={r.get('error')}")
    assert s == 403

    # b. Token sai
    s, r = req("POST", "/api/roster/register", data=reg_payload, token="bad_token")
    print(f"Bad token: status={s}, error={r.get('error')}")
    assert s == 403

    # c. Token sinh viên
    s, r = req("POST", "/api/roster/register", data=reg_payload, token=student_token)
    print(f"Student token: status={s}, error={r.get('error')}")
    assert s == 403

    # d. Token BCS hợp lệ
    s, r = req("POST", "/api/roster/register", data=reg_payload, token=bcs_token)
    print(f"BCS token: status={s}, success={r.get('success')}, message={r.get('message')}")
    assert s == 200 and r.get("success") is True

    print("\n=== 3. KIỂM TRA QUYỀN RIÊNG TƯ & LỘ LỌT DỮ LIỆU ===")
    
    # 3.1 Kiểm tra thông báo lỗi có làm lộ token, signature, hoặc MSSV/Tên không
    s_err, d_err = req("POST", "/api/roster/register", data={"bad": "payload"}, token=student_token)
    err_str = json.dumps(d_err)
    print(f"3.1 Error response check: status={s_err}, response_len={len(err_str)}")
    assert "token" not in err_str.lower() or "session" in err_str.lower()
    assert "0x" not in err_str  # No wallet exposed in error

    # 3.2 Kiểm tra response lỗi khi đăng nhập sai chữ ký
    s_err2, d_err2 = req("POST", "/api/auth/login", data={"address": test_bcs.address, "nonce": "abc", "signature": "0x123"})
    print(f"3.2 Login error check: status={s_err2}, response={d_err2}")
    assert "private" not in json.dumps(d_err2).lower()

    # 3.3 Kiểm tra CORS headers
    s_cors, _ = req("OPTIONS", "/api/roster")
    print(f"3.3 OPTIONS CORS check: status={s_cors}")
    assert s_cors == 200

    print("\n=== TOÀN BỘ CÁC BƯỚC KIỂM TRA ĐỘC LẬP HOÀN THÀNH XUẤT SẮC! ===")

finally:
    restore_roster()
    print("[Clean up] Đã khôi phục hoàn nguyên 100% backend/class_roster.json.")
