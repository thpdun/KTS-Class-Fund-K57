import re
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open("web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

m_script = re.search(r'<script(?![^>]*src=)[^>]*>', html)
idx_script_start = m_script.start()
m_script_end = re.search(r'</script>', html[idx_script_start:])
idx_script_end = idx_script_start + m_script_end.end()

markup = html[:idx_script_start] + html[idx_script_end:]
script = html[idx_script_start:idx_script_end]

target_ids = [
    "panelStudent",
    "panelBCS",
    "panelAdvisor",
    "panelHistory",
    "aiChatDrawer",
    "aiFabToggle",
    "btnDepositAction",
    "btnCreateRefundAction",
    "btnCreateSpendAction",
    "btnWithdrawFeeAction",
    "btnSetBcsAction"
]

print("=== VERIFYING TARGET IDS ===")
for tid in target_ids:
    in_markup = f'id="{tid}"' in markup
    in_script_gid = f'"{tid}"' in script or f"'{tid}'" in script
    print(f"ID: `{tid}`")
    print(f"  - In HTML Markup: {in_markup}")
    print(f"  - In JavaScript: {in_script_gid}")
    # find where in script it's accessed
    uses = re.findall(rf'[a-zA-Z0-9_$.]+\([\'"]{tid}[\'"]\)', script)
    print(f"  - Script calls: {uses}")

print("\n=== VERIFYING roleViewStudent vs panelStudent ===")
print("roleViewStudent in markup:", 'id="roleViewStudent"' in markup)
print("roleViewStudent in script:", '"roleViewStudent"' in script or "'roleViewStudent'" in script)
for line_no, line in enumerate(script.splitlines(), 1):
    if "roleViewStudent" in line:
        print(f"  Script line {line_no}: {line.strip()}")
