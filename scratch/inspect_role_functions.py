import re
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open('web/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

funcs = [
    "selectRoleView",
    "updateRoleDisplay",
    "checkMyStudentIdentity",
    "lookupStudent",
    "handleAccountChange",
    "disconnectWallet",
    "connectWallet"
]

for fn in funcs:
    m = re.search(rf'(?:async\s+)?function\s+{fn}\s*\([^)]*\)\s*\{{', text)
    if m:
        pos = m.start()
        # print first 500 chars of function
        print(f"=== FUNCTION {fn} at index {pos} ===")
        print(text[pos:pos+450])
        print("="*50)
    else:
        print(f"FUNCTION {fn} NOT FOUND")
