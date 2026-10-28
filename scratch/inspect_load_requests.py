import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if re.search(r'allFlowItems\s*=', line) or 'allFlowItems.push' in line or 'loadSpendRequests' in line or 'loadRefundRequests' in line:
        print(f"Line {i+1}: {line.strip()[:100]}")
        start = max(0, i - 5)
        end = min(len(lines), i + 25)
        for j in range(start, end):
            print(f"  {j+1}: {lines[j].rstrip()}")
        print("-------------------")
