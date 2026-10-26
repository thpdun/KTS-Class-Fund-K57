import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

checks = {
    "New Contract 0xfe3ec...": "0xfe3ec1a75503Da9ddFd44aEBE18E461686376b52" in html,
    "Roster Privacy Check": "Quyền riêng tư: Danh bạ sinh viên chỉ dành riêng" in html,
    "Dynamic Class Size (5)": "classSize" in html,
    "Close Roster Button": "closeRosterModal" in html or "btn-close" in html,
    "In-place Edit / Role update": "role" in html and "advisor" in html,
    "AI Floating Drawer": "aiChatDrawer" in html
}

print("Feature verification in current web/index.html:")
for k, v in checks.items():
    print(f"  {k}: {'[OK]' if v else '[MISSING]'}")
