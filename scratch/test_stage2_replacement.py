import re

with open('web/index.html', 'r', encoding='utf-8') as f:
    orig_html = f.read()

with open('scratch/js_ids.txt', 'r', encoding='utf-8') as f:
    js_ids = [line.strip() for line in f if line.strip()]

print(f"Total IDs to verify: {len(js_ids)}")
# Check that all IDs currently exist
missing = [i for i in js_ids if f'id="{i}"' not in orig_html and f"id='{i}'" not in orig_html]
print(f"Initially missing: {len(missing)}")
if missing:
    print("Missing IDs:", missing)

