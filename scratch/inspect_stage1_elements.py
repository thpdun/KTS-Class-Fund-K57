import re
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print('Total lines in web/index.html:', len(lines))

for i, l in enumerate(lines):
    if any(k in l for k in ['<header', 'id="appSidebar"', 'id="hero"', 'id="classAnnouncementCard"', 'id="metricClassFund"', 'btnBannerQuickDeposit', 'roleViewStudent', ':root']):
        print(f"Line {i+1}: {l.strip()[:100]}")
