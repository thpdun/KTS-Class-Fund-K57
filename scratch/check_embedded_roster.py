import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open("web/index.html.bak", "r", encoding="utf-8") as f:
    bak = f.read()

import re
matches = [m.start() for m in re.finditer(r'23K4300004', bak)]
for m in matches:
    print("--- 23K4300004 in bak ---")
    print(bak[m-100:m+200])

with open("web/index.html", "r", encoding="utf-8") as f:
    cur = f.read()

matches_cur = [m.start() for m in re.finditer(r'23K4300004', cur)]
for m in matches_cur:
    print("--- 23K4300004 in cur ---")
    print(cur[m-100:m+200])
