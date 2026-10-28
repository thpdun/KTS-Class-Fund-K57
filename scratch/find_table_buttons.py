# -*- coding: utf-8 -*-
import sys
import re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open("web/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if any(k in l for k in ['voteSpend(', 'voteRefund(', 'executeSpend(', 'executeRefund(']):
        if not 'CONTRACT_ABI' in l:
            print(f"Line {i+1}: {l.strip()[:140]}")
