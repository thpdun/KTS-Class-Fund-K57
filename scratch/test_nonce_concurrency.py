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
test_acct = Account.create()

def make_req(method, path, data=None):
    url = f"{BACKEND_URL}{path}"
    headers = {"Content-Type": "application/json"}
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

print("=== KIỂM THỬ ĐỒNG THỜI NONCE (CONCURRENT NONCE LOGIN TEST) ===")

# Step 1: Lấy 1 nonce duy nhất
s, d = make_req("GET", f"/api/auth/nonce?address={test_acct.address}")
assert s == 200
nonce = d["nonce"]
message = d["message"]
sig = test_acct.sign_message(encode_defunct(text=message)).signature.hex()

payload = {
    "address": test_acct.address,
    "nonce": nonce,
    "signature": sig
}

# Step 2: Gửi đồng thời 10 requests cùng một lúc với cùng một payload
results = []
def send_login(req_id):
    s_code, r_data = make_req("POST", "/api/auth/login", data=payload)
    return req_id, s_code, r_data

print("Đang bắn đồng thời 10 requests với cùng 1 nonce...")
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(send_login, i) for i in range(10)]
    for f in futures:
        results.append(f.result())

successes = [r for r in results if r[1] == 200]
fails = [r for r in results if r[1] == 400]

print(f"Tổng số request: {len(results)}")
print(f"Số request thành công (HTTP 200): {len(successes)}")
print(f"Số request bị từ chối (HTTP 400): {len(fails)}")

for r in results:
    print(f"Req {r[0]}: status={r[1]}, error={r[2].get('error', 'None (Success)')}")

if len(successes) == 1 and len(fails) == 9:
    print("\n=> KẾT QUẢ THỰC TẾ TRÊN HTTPServer HIỆN TẠI: PASS!")
    print("Chỉ duy nhất 1 request đăng nhập thành công. 9 requests đồng thời còn lại đều bị từ chối 400.")
else:
    print(f"\n=> PHÁT HIỆN LỖ HỔNG CONCURRENCY! Số request thành công: {len(successes)}")
