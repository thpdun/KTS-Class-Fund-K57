import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'function renderAnnouncementUI' in line or 'function updateAnnouncementProgress' in line or 'function getAnnouncementData' in line:
        print(f"Line {i+1}: {line.strip()[:100]}")
        start = max(0, i - 2)
        end = min(len(lines), i + 50)
        for j in range(start, end):
            print(f"  {j+1}: {lines[j].rstrip()}")
        print("-------------------------------")
