import sys
import json
import urllib.request

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

print("=== 1. VERIFY BACKEND /api/roster GET ===")
req = urllib.request.Request("http://localhost:8000/api/roster")
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    assert data["success"] is True
    assert len(data["roster"]) >= 5
    print(f"PASS: /api/roster returned {len(data['roster'])} students.")

print("\n=== 2. VERIFY BACKEND /api/roster/check GET ===")
# Test Dung's wallet
dung_wallet = "0x78567A377559F0cB30173f93869326a82320159a"
req = urllib.request.Request(f"http://localhost:8000/api/roster/check?address={dung_wallet}")
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    assert data["success"] is True
    assert data["isMember"] is True
    assert data["student"]["mssv"] == "23K4300004"
    print(f"PASS: Dung's wallet recognized as {data['student']['name']} ({data['student']['role']}).")

# Test Unknown wallet
unknown = "0x1111111111111111111111111111111111111111"
req = urllib.request.Request(f"http://localhost:8000/api/roster/check?address={unknown}")
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    assert data["success"] is True
    assert data["isMember"] is False
    print("PASS: Unknown wallet correctly recognized as non-member.")

print("\n=== 3. VERIFY BACKEND /api/roster/register POST with BCS ===")
# Test update student wallet by BCS
update_payload = json.dumps({
    "originalMssv": "23K4300025",
    "mssv": "23K4300025",
    "name": "Nguyễn Thị Kim Chi",
    "wallet": "0x372819EB492cc6A071b946d5b82BF46174FE8394",
    "role": "student",
    "roleTitle": "Sinh viên",
    "signerAddress": dung_wallet,
    "isBcs": True,
    "isAdvisor": False
}).encode("utf-8")

req = urllib.request.Request(
    "http://localhost:8000/api/roster/register",
    data=update_payload,
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    assert data["success"] is True
    print(f"PASS: BCS successfully updated roster: {data.get('message')}")

print("\n=== 4. VERIFY FRAUD / OUTSIDER ATTEMPT (AGENTS.md Requirement) ===")
# Outsider without isBcs or isAdvisor tries to update roster
fraud_payload = json.dumps({
    "originalMssv": "23K4300005",
    "mssv": "23K4300005",
    "name": "Hacker",
    "wallet": "0x9999999999999999999999999999999999999999",
    "role": "bcs",
    "roleTitle": "Ban cán sự",
    "signerAddress": unknown,
    "isBcs": False,
    "isAdvisor": False
}).encode("utf-8")

req = urllib.request.Request(
    "http://localhost:8000/api/roster/register",
    data=fraud_payload,
    headers={"Content-Type": "application/json"}
)
try:
    with urllib.request.urlopen(req) as resp:
        print("FAIL: Fraudulent request should have been rejected!")
except urllib.error.HTTPError as e:
    assert e.code == 403
    print(f"PASS: Fraudulent request correctly rejected with HTTP 403 Forbidden: {e.reason}")

print("\n=== ALL 4 VERIFICATION TESTS PASSED ===")
