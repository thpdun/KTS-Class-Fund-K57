import re

with open('web/index.html', encoding='utf-8') as f:
    content = f.read()

# Find all getElementById in script
js_part = content[content.find('<script>'):]
ids = set(re.findall(r'document\.getElementById\(["\']([^"\']+)["\']\)', js_part))
missing = []
for el_id in sorted(ids):
    pattern = f'id="{el_id}"'
    pattern_sq = f"id='{el_id}'"
    if pattern not in content and pattern_sq not in content:
        missing.append(el_id)

print(f"Total IDs referenced in JS: {len(ids)}")
print(f"Missing IDs: {len(missing)}")
if missing:
    print("Missing list:", missing)
else:
    print("ALL JAVASCRIPT DOM IDs EXIST IN HTML 100%!")
