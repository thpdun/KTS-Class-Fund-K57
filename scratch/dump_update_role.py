import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open("web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

idx = html.find("function updateRoleDisplay")
idx_end = html.find("function promptSwitchSepoliaModal", idx)
if idx_end == -1:
    idx_end = html.find("async function connectWallet", idx)
if idx_end == -1:
    idx_end = html.find("function ", idx + 30)

print(repr(html[idx:idx_end]))
