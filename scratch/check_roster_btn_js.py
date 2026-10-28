import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open("web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

idx = html.find('itemRosterModalBtn')
while idx != -1:
    print("--- OCCURRENCE ---")
    print(html[idx-100:idx+250])
    idx = html.find('itemRosterModalBtn', idx + 1)

