# -*- coding: utf-8 -*-
import re

with open("web/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
for i, line in enumerate(lines):
    if "overflow" in line.lower():
        print(f"Line {i+1}: {line.strip()[:100]}")
