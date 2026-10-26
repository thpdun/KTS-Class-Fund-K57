import re
import json

with open("web/index.html.bak", "r", encoding="utf-8") as f:
    content = f.read()

# Separate HTML part before <script>
script_pos = content.find("<script>")
html_part = content[:script_pos]
js_part = content[script_pos:]

html_ids = sorted(list(set(re.findall(r'id=["\']([a-zA-Z0-9_\-]+)["\']', html_part))))
js_ids = sorted(list(set(re.findall(r'getElementById\(["\']([a-zA-Z0-9_\-]+)["\']\)', js_part))))

print(f"Total HTML IDs in markup: {len(html_ids)}")
print(f"Total IDs accessed by getElementById in JS: {len(js_ids)}")

missing_in_html = [id_name for id_name in js_ids if id_name not in html_ids]
print(f"IDs accessed in JS but not in HTML: {missing_in_html}")

with open("scratch/all_ids.json", "w", encoding="utf-8") as out:
    json.dump({
        "html_ids": html_ids,
        "js_accessed_ids": js_ids
    }, out, indent=2, ensure_ascii=False)

print("Saved to scratch/all_ids.json")
