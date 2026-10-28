import sys, re
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

with open('web/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Search for Phuong Dung
print("=== PHƯƠNG DUNG SEARCH ===")
for m in re.finditer(r'[^\n]*Phương Dung[^\n]*', text, re.IGNORECASE):
    print(m.group(0).strip())

# Search for DEFAULT_ROSTER or CLASS_ROSTER
print("\n=== ROSTER DEFINITIONS ===")
for m in re.finditer(r'(?:const|let|var)\s+(?:DEFAULT_ROSTER|CLASS_ROSTER|classRoster|rosterData)\s*=\s*(\[[\s\S]*?\]);', text):
    print("Found roster var definition:")
    print(m.group(0)[:500])
    print("...")

# Search for renderRosterTable
print("\n=== RENDER ROSTER TABLE FUNCTION ===")
m_fn = re.search(r'function\s+renderRosterTable\s*\([^\)]*\)\s*\{([\s\S]*?)\n\s*function\s+', text)
if m_fn:
    print(m_fn.group(0)[:1500])
else:
    print("renderRosterTable function not matched with regex pattern")
