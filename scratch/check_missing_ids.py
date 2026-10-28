import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open('web/index.html', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'inputModalContract' in line or 'roleViewStudent' in line:
            print(f"Line {i+1}: {line.strip()}")
