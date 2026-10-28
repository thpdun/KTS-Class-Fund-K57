import re
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open('web/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

funcs = [
    "renderBcsSpendTable",
    "renderBcsRefundTable",
    "renderStudentRefundTable"
]

for fn in funcs:
    m = re.search(rf'function\s+{fn}\s*\([^)]*\)\s*\{{', text)
    if m:
        pos = m.start()
        print(f"=== {fn} at {pos} ===")
        print(text[pos:pos+1200])
        print("="*50)
    else:
        print(f"{fn} NOT FOUND")
