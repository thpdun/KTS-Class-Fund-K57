# -*- coding: utf-8 -*-
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open("web/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "app-topbar" in line and "<" in line:
        print(f"Line {i+1}:")
        for j in range(max(0, i-2), min(len(lines), i+40)):
            print(f"  {j+1}: {lines[j].rstrip()}")
        break
