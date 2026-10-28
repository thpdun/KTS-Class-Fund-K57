# -*- coding: utf-8 -*-
with open("web/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

def print_range(start, end):
    print(f"\n=== Lines {start} to {end} ===")
    for i in range(start - 1, min(len(lines), end)):
        print(f"{i+1}: {lines[i].rstrip()}")

print_range(2190, 2225)
print_range(2650, 2700)
print_range(3170, 3190)
