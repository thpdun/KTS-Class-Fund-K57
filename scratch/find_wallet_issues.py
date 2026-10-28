import sys
import re

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open("web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# Split into HTML markup and JS script
idx_script = html.find("<script>")
markup = html[:idx_script]
script = html[idx_script:]

print("=== CHECKING BUTTONS AND WALLET ELEMENTS IN MARKUP ===")
for elem_id in [
    "btnConnectWallet", "walletBtnText", "btnSwitchWallet", "btnDisconnectWallet",
    "networkBadge", "networkDot", "networkText",
    "quickRoleBadge", "quickStudentIdentity", "quickWalletAccount",
    "sidebarUserIdentity", "sidebarRoleBadge", "sidebarWalletShort",
    "sidebarRosterBadge", "rosterCountBadge",
    "guestWarningBanner", "rosterAdminSection"
]:
    in_markup = f'id="{elem_id}"' in markup or f"id='{elem_id}'" in markup
    print(f"ID: {elem_id:<25} In Markup: {in_markup}")

print("\n=== CHECKING HOW WALLET IS CONNECTED AND UPDATED IN JS ===")
# Find connectWallet implementation
start_cw = script.find("async function connectWallet")
if start_cw == -1:
    start_cw = script.find("function connectWallet")
end_cw = script.find("async function switchAccount", start_cw)
if end_cw == -1:
    end_cw = start_cw + 2000
print("--- connectWallet snippet ---")
print(script[start_cw:start_cw+1500])

# Find where userAddress is set and what functions are called right after
matches = [m.start() for m in re.finditer(r'userAddress\s*=\s*(?:accounts\[0\]|account|signerAddr)', script)]
for m in matches:
    print("\n--- userAddress assignment & next 30 lines ---")
    print(script[m:m+600])
