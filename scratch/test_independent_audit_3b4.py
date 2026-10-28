import sys
import json
import time
import urllib.request
import urllib.error
from eth_account import Account
from eth_account.messages import encode_defunct

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:8000"

print("=" * 70)
print("BẮT ĐẦU ĐỢT KIỂM TRA ĐỘC LẬP BẢO MẬT STAGE 3B.4.1")
print("=" * 70)

# 1. Tạo ví thử nghiệm
bcs_account = Account.create()
student_account = Account.create()
outsider_account = Account.create()
advisor_account = Account.from_key("0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d") # Test account for 0x36fd4887e9d1eca4ae5062a745cc2c6182b77060

# We need a known student in roster, or we can check who is in backend/class_roster.json
with open("backend/class_roster.json", "r", encoding="utf-8") as f:
    roster_data = json.load(f)

# Find first BCS and first Student in roster
known_bcs = next((s for s in roster_data if s.get("role") == "bcs"), None)
known_student = next((s for s in roster_data if s.get("role") == "student"), None)

print(f"Known BCS in roster: {known_bcs['name']} ({known_bcs['wallet'][:10]}...)")
print(f"Known Student in roster: {known_student['name']} ({known_student['wallet'][:10]}...)")

# Helper HTTP request
def make_request(path, method="GET", data=None, token=None, extra_headers=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if extra_headers:
        headers.update(extra_headers)

    req_data = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"raw": body}
        return e.code, parsed
    except Exception as e:
        return 0, {"error": str(e)}

def login_wallet(account):
    # Step 1: get nonce
    status, res = make_request(f"/api/auth/nonce?address={account.address}")
    assert status == 200, f"Nonce failed: {res}"
    nonce = res["nonce"]
    message = res["message"]

    # Step 2: sign
    msg_defunct = encode_defunct(text=message)
    sig = account.sign_message(msg_defunct).signature.hex()

    # Step 3: login
    status, res = make_request("/api/auth/login", method="POST", data={
        "address": account.address,
        "nonce": nonce,
        "signature": sig
    })
    return status, res

# Let's register a known test student and BCS temporarily or test with created accounts
# Since server checks roster for roles:
# Let's login with outsider, and see their role
status, outsider_login = login_wallet(outsider_account)
print(f"Outsider login status: {status}, role: {outsider_login.get('role')}")
outsider_token = outsider_login.get("token")

# How can we test BCS login with real signature?
# We can create a test BCS account and temporarily add it to roster, OR use existing advisor key if we have private key for known advisor?
# Wait! Do we have the private key for known_bcs? We don't! But we can test login with a known private key, or add test BCS via register if authorized, OR test using our test suite's pattern.
# Wait! In test_stage3b4_security.py, how did it test?
# In test_stage3b4_security.py, it temporarily added a test wallet to class_roster.json!
# But user constraint:
# 'Không sửa mã nguồn trong lượt kiểm tra này.'
# 'Không xóa hoặc thay đổi dữ liệu danh bạ thật ngoài phạm vi cần thiết; sao lưu trước khi sửa dữ liệu hoặc cấu trúc lưu trữ.'
# Wait, can we test without modifying class_roster.json?
# Let's check: What is ADVISOR_ADDRESS?
# In backend/server.py:
# ADVISOR_ADDRESS = os.environ.get("ADVISOR_ADDRESS", "0x36fd4887e9d1eca4ae5062a745cc2c6182b77060").lower()
# But we don't have the private key for 0x36fd4887e9d1eca4ae5062a745cc2c6182b77060!
# Wait, let's see if we can login with student or outsider.
