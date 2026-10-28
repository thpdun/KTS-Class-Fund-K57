import re
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

idx = html.find('const FAQ_DATA')
end = html.find('];', idx)
block = html[idx:end+2]

# find all items: { id: ..., cat: ..., q: ..., a: ... }
items = re.findall(r'id:\s*(\d+)[\s\S]*?cat:\s*["\']([^"\']+)["\'][\s\S]*?q:\s*["\']([^"\']+)["\']', block)
print(f"Total FAQ items parsed: {len(items)}")
for item_id, cat, q in items:
    print(f"[{item_id}] ({cat}): {q}")
