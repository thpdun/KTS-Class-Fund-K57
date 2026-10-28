import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open("web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# Check locations of:
# 1. let classRoster = [];
# 2. function lookupStudent
# 3. function updateRoleDisplay
# 4. function handleDisconnect
# 5. function loadClassRoster
# 6. function openRosterModal
# 7. function editRosterStudent
# 8. function saveRosterEntry
# 9. const actionBtn = isAdvisor
# 10. connectWallet / handleAccountChange calls to loadClassRoster

funcs = [
    "let classRoster = [];",
    "function lookupStudent",
    "function updateRoleDisplay",
    "function handleDisconnect",
    "async function loadClassRoster",
    "function openRosterModal",
    "function editRosterStudent",
    "async function saveRosterEntry",
    "const actionBtn = isAdvisor"
]

for item in funcs:
    idx = html.find(item)
    print(f"'{item}': index {idx}")
