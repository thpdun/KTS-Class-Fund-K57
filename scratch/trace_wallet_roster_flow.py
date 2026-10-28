import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open("web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# Let's inspect updateRoleDisplay in web/index.html
def show_func(name):
    idx = html.find(f"function {name}")
    if idx == -1:
        idx = html.find(f"async function {name}")
    if idx == -1:
        print(f"=== {name}: NOT FOUND ===")
        return
    # Find next function or 2000 chars
    end = html.find("function ", idx + 10)
    if end == -1 or end - idx > 2500:
        end = idx + 2500
    print(f"=== {name} ===")
    print(html[idx:end])

show_func("updateRoleDisplay")
show_func("connectWallet")
show_func("handleDisconnect")
show_func("loadClassRoster")
show_func("saveRosterEntry")
show_func("editRosterStudent")
show_func("renderAnnouncementUI")
