import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open("web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

import re
for elem_id in [
    "quickRoleBadge", "quickStudentIdentity", "quickWalletAccount", "quickNetworkStatus",
    "sidebarUserIdentity", "sidebarRoleBadge", "sidebarWalletShort", "sidebarRosterBadge",
    "studentIdentityName", "userRoleBadge", "userWalletAddress", "walletBtnText"
]:
    count = html.count(f'id="{elem_id}"')
    js_refs = html.count(f'"{elem_id}"')
    print(f"{elem_id:<25} In HTML: {count} | In JS: {js_refs - count}")
