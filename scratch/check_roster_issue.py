import sys
import re
import difflib

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

with open("web/index.html.bak", "r", encoding="utf-8") as f:
    bak = f.read()

with open("web/index.html", "r", encoding="utf-8") as f:
    cur = f.read()

print("Bak total len:", len(bak), "Cur total len:", len(cur))

# Check for rosterModal
print("rosterModal in bak:", "rosterModal" in bak)
print("rosterModal in cur:", "rosterModal" in cur)

# Find where rosterModal is in cur
idx_rm_cur = cur.find('id="rosterModal"')
print("idx of rosterModal in cur:", idx_rm_cur)
if idx_rm_cur != -1:
    print("cur snippet around rosterModal:")
    print(cur[idx_rm_cur - 50:idx_rm_cur + 250])

# Check for buttons that open rosterModal
buttons_bak = re.findall(r'<[^>]+(?:openRosterModal|rosterModal)[^>]*>', bak)
buttons_cur = re.findall(r'<[^>]+(?:openRosterModal|rosterModal)[^>]*>', cur)
print("Buttons/triggers in bak:", len(buttons_bak), buttons_bak)
print("Buttons/triggers in cur:", len(buttons_cur), buttons_cur)

# Extract scripts
def extract_script(text):
    m = re.findall(r'<script(?:\s+type="[^"]*")?>([\s\S]*?)</script>', text)
    # Filter out external CDNs (they have no inner script or are short)
    long_scripts = [s for s in m if len(s.strip()) > 100]
    return "\n".join(long_scripts)

s_bak = extract_script(bak)
s_cur = extract_script(cur)

print("JS bak len:", len(s_bak), "JS cur len:", len(s_cur))
with open("scratch/js_bak.js", "w", encoding="utf-8") as f:
    f.write(s_bak)
with open("scratch/js_cur.js", "w", encoding="utf-8") as f:
    f.write(s_cur)

# Check functions in js_cur vs js_bak
roster_funcs_bak = re.findall(r'function\s+([a-zA-Z0-9_]+)\s*\(', s_bak)
roster_funcs_cur = re.findall(r'function\s+([a-zA-Z0-9_]+)\s*\(', s_cur)

print("Functions in bak:", len(roster_funcs_bak))
print("Functions in cur:", len(roster_funcs_cur))

missing_funcs = set(roster_funcs_bak) - set(roster_funcs_cur)
print("Missing functions in cur:", missing_funcs)
