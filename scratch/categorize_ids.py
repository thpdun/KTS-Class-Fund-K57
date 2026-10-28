import json
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open("scratch/detailed_inventory.json", "r", encoding="utf-8") as f:
    d = json.load(f)

unique_ids = d["unique_html_ids"]
js_ids = set(d["js_accessed_ids"])
markup_onclicks = d["onclicks_markup"]
dynamic_onclicks = d["dynamic_onclicks_js"]
listeners = d["listeners"]

print(f"Total HTML Unique IDs: {len(unique_ids)}")
print(f"Total JS Accessed IDs: {len(js_ids)}")
print(f"Total Markup Onclicks: {len(markup_onclicks)}")
print(f"Total Dynamic Onclicks: {len(dynamic_onclicks)}")
print(f"Total Listeners: {len(listeners)}")

# Categorize IDs
# Group 1: Header / Navbar / Network / Wallet Bar
# Group 2: Hero & Class Announcement & 6 Metrics
# Group 3: DApp Workspace (Role Tabs & Panels: Student, BCS, Advisor, History)
# Group 4: Cash Flow & Public Ledgers (4 Flows, Depositors, Spend, Refund)
# Group 5: Governance & Rules (51% quorum, R1-R11, 99/1 split)
# Group 6: Workflow & Process Timelines (Process 1 & 2)
# Group 7: FAQ Section
# Group 8: Transparency & System Diagnostics Terminal
# Group 9: Modals (Wallet, Announcement, Roster, General)
# Group 10: AI Chat Floating Widget

def categorize_id(elem_id):
    lid = elem_id.lower()
    if 'ai' in lid or 'fab' in lid:
        return 'AI Assistant Widget'
    if 'modal' in lid or 'roster' in lid or 'announcementform' in lid:
        return 'Modals & Overlays'
    if 'terminal' in lid or 'console' in lid:
        return 'Transparency & Terminal'
    if 'faq' in lid:
        return 'FAQ Section'
    if 'metric' in lid or 'announcement' in lid or 'hero' in lid:
        return 'Hero, Metrics & Announcement'
    if 'flow' in lid or 'ledger' in lid or 'spend' in lid or 'refund' in lid or 'deposit' in lid or 'table' in lid or 'tx' in lid:
        return 'Cash Flow & Public Ledger'
    if 'panel' in lid or 'role' in lid or 'tab' in lid or 'btnrole' in lid or 'dapp' in lid:
        return 'Role Workspace (DApp)'
    if 'nav' in lid or 'sidebar' in lid or 'wallet' in lid or 'network' in lid or 'account' in lid or 'connect' in lid:
        return 'Navigation, Header & Wallet Bar'
    if 'rule' in lid or 'gov' in lid or 'eco' in lid or 'split' in lid or 'quorum' in lid:
        return 'Governance & Economics'
    return 'General / Layout / Info'

categorized = {}
for elem_id in unique_ids:
    cat = categorize_id(elem_id)
    categorized.setdefault(cat, []).append(elem_id)

for cat, ids in sorted(categorized.items()):
    print(f"\n### {cat} ({len(ids)} IDs)")
    for i in ids:
        used = "JS" if i in js_ids else "Markup only"
        print(f"  - `{i}`: [{used}]")
