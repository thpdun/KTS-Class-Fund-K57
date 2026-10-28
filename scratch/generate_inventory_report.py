import re
import sys
import json

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Separate markup and script
m_script_start = re.search(r'<script(?![^>]*src=)[^>]*>', html)
m_script_end = re.search(r'</script>', html[m_script_start.end():])

idx_script_start = m_script_start.start()
idx_script_end = m_script_start.end() + m_script_end.end()

script = html[idx_script_start:idx_script_end]
markup = html[:idx_script_start] + "\n<!-- SPLIT -->\n" + html[idx_script_end:]

# 1. Blocks & Sections
sections = []
for m in re.finditer(r'<(section|aside|footer|header|nav|div\s+class="[^"]*(?:modal|ai-fab-container|ai-chat-drawer)[^"]*")[^>]*id="([^"]+)"[^>]*>', markup):
    tag = m.group(1).split()[0]
    sid = m.group(2)
    snippet = markup[m.start():m.start()+600]
    h_m = re.search(r'<(?:h[1-6]|div\s+class="[^"]*title[^"]*")[^>]*>([\s\S]*?)</(?:h[1-6]|div)>', snippet)
    h_text = re.sub(r'<[^>]+>', '', h_m.group(1)).strip() if h_m else ""
    sections.append({"tag": tag, "id": sid, "heading": h_text})

# 2. All HTML IDs with their tag and approximate line number
html_id_details = []
for line_no, line in enumerate(html.splitlines(), 1):
    # Only if line is outside script block
    # Check if line_no is outside script
    pass

html_ids_all = re.findall(r'id="([^"]+)"', markup)
unique_html_ids = sorted(list(set(html_ids_all)))

# 3. JS accessed IDs
js_get_elem = set(re.findall(r'getElementById\(["\']([^"\']+)["\']\)', script))
js_query_id = set(re.findall(r'querySelector\(["\']#([^"\', .:\s>]+)["\']\)', script))
all_js_ids = js_get_elem.union(js_query_id)

# 4. Onclicks
onclicks = []
for m in re.finditer(r'<([a-zA-Z0-9_-]+)([^>]*?)onclick="([^"]+)"([^>]*)>', markup):
    attrs = m.group(2) + " " + m.group(4)
    id_m = re.search(r'id="([^"]+)"', attrs)
    elem_id = id_m.group(1) if id_m else "(none)"
    onclicks.append({
        "tag": m.group(1),
        "id": elem_id,
        "onclick": m.group(3).strip()
    })

# Also find onclicks created dynamically in JS
js_dynamic_onclicks = re.findall(r'onclick\s*=\s*["\']([^"\']+)["\']', script)

# 5. addEventListener in script
listeners = []
for m in re.finditer(r'([a-zA-Z0-9_$.]+)\.addEventListener\(["\']([^"\']+)["\']\s*,\s*([^,\)]+)', script):
    listeners.append({
        "target": m.group(1),
        "event": m.group(2),
        "handler": m.group(3).strip()
    })

# Check IDs match
ids_in_html_not_in_js = sorted(list(set(unique_html_ids) - all_js_ids))
ids_in_js_not_in_html = sorted(list(all_js_ids - set(unique_html_ids)))

print(f"Total Unique HTML IDs: {len(unique_html_ids)}")
print(f"Total JS Accessed IDs: {len(all_js_ids)}")
print(f"IDs in HTML not in JS: {len(ids_in_html_not_in_js)}")
print(f"IDs in JS not in HTML: {len(ids_in_js_not_in_html)}")
print(f"List of IDs in JS not in HTML: {ids_in_js_not_in_html}")

report = {
    "sections": sections,
    "unique_html_ids_count": len(unique_html_ids),
    "unique_html_ids": unique_html_ids,
    "js_accessed_ids_count": len(all_js_ids),
    "js_accessed_ids": sorted(list(all_js_ids)),
    "ids_not_in_js": ids_in_html_not_in_js,
    "ids_in_js_not_in_html": ids_in_js_not_in_html,
    "onclicks_markup": onclicks,
    "dynamic_onclicks_js": sorted(list(set(js_dynamic_onclicks))),
    "listeners": listeners
}

with open("scratch/detailed_inventory.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print("Updated inventory saved to scratch/detailed_inventory.json successfully.")
