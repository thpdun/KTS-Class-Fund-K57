import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'classRoster' in line:
        print(f"Line {i+1}: {line.strip()[:100]}")
