import sys
import re

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open("web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

matches = [m.start() for m in re.finditer(r'loadClassRoster\(', html)]
print(f"Total loadClassRoster calls: {len(matches)}")
for m in matches:
    print("--- CALL ---")
    print(html[m-80:m+150])
