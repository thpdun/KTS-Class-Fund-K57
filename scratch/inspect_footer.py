import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

with open("web/index.html", "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find('<footer')
footer_end = text.find('</footer>', pos) + len('</footer>')
print("=== FOOTER HTML ===")
print(text[pos:footer_end])

print("\n=== FOOTER CSS ===")
footer_css = re.findall(r'(\.[a-zA-Z0-9_\-\s,.:]*footer[^}]*\{[^}]*\})', text, re.IGNORECASE)
for fc in footer_css:
    print(fc)

# Also check surrounding layout of footer
print("\n=== AFTER FOOTER ===")
print(text[footer_end:footer_end+500])
