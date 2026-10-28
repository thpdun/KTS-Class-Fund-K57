import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open("web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

idx = html.find("function handleAccountChange")
if idx == -1:
    idx = html.find("async function handleAccountChange")
print(html[idx:idx+2000])
