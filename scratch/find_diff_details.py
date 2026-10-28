import sys
import re

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open("web/index.html.bak", "r", encoding="utf-8") as f:
    bak = f.read()

with open("web/index.html", "r", encoding="utf-8") as f:
    cur = f.read()

# Let's inspect where wallet address and user info was shown in bak
print("=== WALLET / IDENTITY ELEMENTS IN BAK ===")
for m in re.finditer(r'<[^>]+(?:wallet|address|account|identity|mssv|role)[^>]*id=["\']([^"\']+)["\'][^>]*>', bak, re.IGNORECASE):
    print(m.group(0))

print("\n=== WALLET / IDENTITY ELEMENTS IN CUR ===")
for m in re.finditer(r'<[^>]+(?:wallet|address|account|identity|mssv|role)[^>]*id=["\']([^"\']+)["\'][^>]*>', cur, re.IGNORECASE):
    print(m.group(0))

# Check where walletBtnText or connect buttons are
print("\n=== WALLET BUTTONS IN BAK ===")
for m in re.finditer(r'<[^>]+(?:connect|wallet)[^>]*>', bak, re.IGNORECASE):
    if "btn" in m.group(0).lower():
        print(m.group(0))

print("\n=== WALLET BUTTONS IN CUR ===")
for m in re.finditer(r'<[^>]+(?:connect|wallet)[^>]*>', cur, re.IGNORECASE):
    if "btn" in m.group(0).lower():
        print(m.group(0))
