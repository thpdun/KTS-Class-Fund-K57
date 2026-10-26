import sys
import re
sys.stdout.reconfigure(encoding='utf-8')

with open("web/index.html", "r", encoding="utf-8") as f:
    text = f.read()

matches = re.findall(r'(\.[a-zA-Z0-9_\-]+\s*\{[^}]*grid-template-columns:[^}]*\})', text)
print(f"Total CSS rules with grid-template-columns: {len(matches)}")
for m in matches:
    print("----------------")
    print(m)

# Also check inline styles with grid-template-columns
inline_matches = re.findall(r'(style="[^"]*grid-template-columns:[^"]*")', text)
print(f"\nTotal inline styles with grid-template-columns: {len(inline_matches)}")
for im in inline_matches:
    print("----------------")
    print(im)
