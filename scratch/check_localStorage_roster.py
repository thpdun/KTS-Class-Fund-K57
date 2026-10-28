import re

with open("web/index.html", "r", encoding="utf-8") as f:
    c = f.read()

matches = [m.start() for m in re.finditer(r'kts_class_roster', c)]
for idx, m in enumerate(matches):
    start = max(0, m - 100)
    end = min(len(c), m + 150)
    print(f"=== MATCH {idx} at {m} ===")
    print(repr(c[start:end]))
