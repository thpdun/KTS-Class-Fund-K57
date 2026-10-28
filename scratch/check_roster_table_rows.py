import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open("web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

idx = html.find("async function renderRosterTable")
if idx == -1:
    idx = html.find("function renderRosterTable")

print(html[idx+2000:idx+4500])
