import sys
import re
import json

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open("web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# Locate main inline script
m_script = re.search(r'<script(?![^>]*src=)[^>]*>', html)
if not m_script:
    raise ValueError("Inline script not found!")

idx_script = m_script.start()
markup = html[:idx_script]
script = html[idx_script:]

# 1. Blocks / Sections in markup
# Find all top-level sections, headers, asides, modals, main content blocks
sections = []
for m in re.finditer(r'<(section|header|nav|aside|footer|div\s+class="[^"]*modal[^"]*")[^>]*id="([^"]+)"[^>]*>', markup):
    tag = m.group(1).split()[0]
    elem_id = m.group(2)
    # find near heading if any
    start_pos = m.start()
    sample = markup[start_pos:start_pos+600]
    title_m = re.search(r'<h[1-6][^>]*>([\s\S]*?)</h[1-6]>', sample)
    title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip() if title_m else ""
    sections.append({"tag": tag, "id": elem_id, "title": title})

# 2. All HTML IDs in markup
html_ids = re.findall(r'id="([^"]+)"', markup)
unique_html_ids = sorted(list(set(html_ids)))
print(f"Total HTML IDs in markup: {len(html_ids)} (Unique: {len(unique_html_ids)})")

# 3. All IDs accessed in Script
js_get_elem = set(re.findall(r'getElementById\(["\']([^"\']+)["\']\)', script))
js_query_id = set(re.findall(r'querySelector\(["\']#([^"\', .:\s>]+)["\']\)', script))
all_js_ids = js_get_elem.union(js_query_id)
print(f"Total JS accessed IDs: {len(all_js_ids)}")

# 4. Check IDs match
ids_in_html_not_in_js = sorted(list(set(unique_html_ids) - all_js_ids))
ids_in_js_not_in_html = sorted(list(all_js_ids - set(unique_html_ids)))
print(f"IDs in HTML not in JS: {len(ids_in_html_not_in_js)}")
print(f"IDs in JS not in HTML: {len(ids_in_js_not_in_html)}")

# 5. All inline onclick attributes in markup
onclicks = []
for m in re.finditer(r'<([a-zA-Z0-9_-]+)([^>]*?)onclick="([^"]+)"([^>]*)>', markup):
    tag = m.group(1)
    attrs = m.group(2) + " " + m.group(4)
    id_m = re.search(r'id="([^"]+)"', attrs)
    elem_id = id_m.group(1) if id_m else "(no id)"
    onclick_fn = m.group(3).strip()
    onclicks.append({"tag": tag, "id": elem_id, "onclick": onclick_fn})
print(f"Total onclick elements in HTML: {len(onclicks)}")

# 6. All addEventListener in script
listeners = []
for m in re.finditer(r'(?:document\.getElementById\(["\']([^"\']+)["\']\)|([a-zA-Z0-9_$]+))\s*\.addEventListener\(["\']([^"\']+)["\']\s*,\s*([^,\)]+)', script):
    elem = m.group(1) or m.group(2)
    ev = m.group(3)
    handler = m.group(4).strip()
    listeners.append({"element": elem, "event": ev, "handler": handler})
print(f"Total addEventListener calls in script: {len(listeners)}")

# 7. Check FAQs in markup & script
faq_questions_markup = re.findall(r'<div class="faq-question"[^>]*>([\s\S]*?)</div>', markup)
print(f"FAQs in markup: {len(faq_questions_markup)}")

# 8. All global JS functions defined
js_funcs = re.findall(r'(?:function\s+([a-zA-Z0-9_$]+)\s*\(|window\.([a-zA-Z0-9_$]+)\s*=|(?:async\s+)?function\s+([a-zA-Z0-9_$]+)\s*\()', script)
all_funcs = set()
for f in js_funcs:
    for item in f:
        if item:
            all_funcs.add(item)
print(f"Total JS functions defined: {len(all_funcs)}")

output_data = {
    "sections": sections,
    "total_unique_html_ids": len(unique_html_ids),
    "html_ids": unique_html_ids,
    "total_js_ids": len(all_js_ids),
    "js_accessed_ids": sorted(list(all_js_ids)),
    "ids_in_html_not_in_js": ids_in_html_not_in_js,
    "ids_in_js_not_in_html": ids_in_js_not_in_html,
    "onclicks": onclicks,
    "listeners": listeners,
    "faq_questions": [re.sub(r'<[^>]+>', '', q).strip() for q in faq_questions_markup],
    "js_functions": sorted(list(all_funcs))
}

with open("scratch/inventory_data.json", "w", encoding="utf-8") as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)

print("Saved complete inventory to scratch/inventory_data.json successfully.")
