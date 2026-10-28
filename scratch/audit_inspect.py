import re

with open("web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

def extract_fn(name):
    m = re.search(rf'((?:async\s+)?function\s+{name}\s*\([^{{]*\{{[\s\S]*?\n\s{{4}}\}})', html)
    return m.group(1) if m else f"// NOT FOUND: {name}"

fns = ["loadClassRoster", "renderRosterTable", "openRosterModal", "syncDepositorsData", "updateAnnouncementProgress"]

with open("scratch/audit_inspected_fns.js", "w", encoding="utf-8") as out:
    for fn in fns:
        out.write(f"\n// ==================== {fn} ====================\n")
        out.write(extract_fn(fn))
        out.write("\n")

print("Extracted functions to scratch/audit_inspected_fns.js")
