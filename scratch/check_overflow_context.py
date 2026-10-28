# -*- coding: utf-8 -*-
with open("web/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

overflow_lines = [139, 261, 634, 761, 891, 934, 1209, 1562, 1613, 1785, 1919, 1973, 2284, 2703, 3052, 5253]

for ln in overflow_lines:
    start = max(0, ln - 10)
    end = min(len(lines), ln + 10)
    print(f"\n=================== CONTEXT FOR LINE {ln} ===================")
    for idx in range(start, end):
        prefix = "-> " if idx + 1 == ln else "   "
        print(f"{prefix}{idx+1}: {lines[idx].rstrip()}")
