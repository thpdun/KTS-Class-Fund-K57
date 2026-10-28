# -*- coding: utf-8 -*-
"""
Find all references to logo in web/index.html
"""
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open("web/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines in web/index.html: {len(lines)}")
for i, line in enumerate(lines):
    if "logo" in line.lower():
        print(f"Line {i+1}: {line.strip()[:140]}")
