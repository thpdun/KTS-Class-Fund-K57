import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open("web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

idx = html.find("function checkMyStudentIdentity")
if idx == -1:
    idx = html.find("async function checkMyStudentIdentity")
print("=== checkMyStudentIdentity ===")
print(html[idx:idx+1500])
