import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'flowLedgerTableBody' in line:
        print(f"Line {i+1}:")
        start = max(0, i - 25)
        end = min(len(lines), i + 15)
        for j in range(start, end):
            print(f"  {j+1}: {lines[j].rstrip()}")
