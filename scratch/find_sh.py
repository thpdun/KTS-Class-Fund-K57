import re, sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    if 'section-header' in line:
        print(f"Line {i}: {line.strip()[:100]}")
