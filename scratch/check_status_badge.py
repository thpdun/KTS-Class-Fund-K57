import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'function getStatusBadge' in line:
        print(f"Line {i+1}:")
        for j in range(i, min(len(lines), i + 25)):
            print(f"  {j+1}: {lines[j].rstrip()}")
