import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("web/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, l in enumerate(lines):
    if "mục tiêu" in l.lower():
        print(f"L{idx+1}: {l.strip()[:140]}")
