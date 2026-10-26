import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("web/index.html", "r", encoding="utf-8") as f:
    text = f.read()

sections = [
    "about",
    "workflow",
    "governance",
    "economics",
    "blockchain",
    "faq",
    "transparency",
    "dapp-workspace",
    "guestWarningBanner",
    "classAnnouncementCard",
    "walletModal",
    "announcementModal",
    "rosterModal",
    "aiChatDrawer"
]

print("Section presence in current web/index.html:")
for s in sections:
    pos = text.find(f'id="{s}"')
    if pos == -1:
        pos = text.find(f"id='{s}'")
    print(f"  {s}: position {pos}")
