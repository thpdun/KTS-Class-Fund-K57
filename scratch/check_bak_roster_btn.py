import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open("web/index.html.bak", "r", encoding="utf-8") as f:
    bak = f.read()

# Find where openRosterModal button was in bak
idx = bak.find("openRosterModal")
while idx != -1:
    print("--- BAK BUTTON/CALL ---")
    print(bak[idx-100:idx+250])
    idx = bak.find("openRosterModal", idx + 1)
