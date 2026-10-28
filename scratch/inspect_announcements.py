import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if any(k in line for k in ['renderAnnouncementUI', 'updateAnnouncementProgress', 'renderPendingActions']):
        print(f"Line {i+1}: {line.strip()[:100]}")
        start = max(0, i - 5)
        end = min(len(lines), i + 35)
        for j in range(start, end):
            print(f"  {j+1}: {lines[j].rstrip()}")
        print("========================")
