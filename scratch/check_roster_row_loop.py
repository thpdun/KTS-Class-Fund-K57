import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open("web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

idx = html.find("for (let i = 0; i < filtered.length; i++)")
print(html[idx:idx+2500])
