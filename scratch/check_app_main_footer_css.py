with open('web/styles.css', 'r', encoding='utf-8') as f:
    css = f.read()

import re
matches = re.findall(r'(\.app-main\b[^{]*\{[^}]*\})', css)
for m in matches:
    print(m)

matches2 = re.findall(r'(\.site-footer\b[^{]*\{[^}]*\})', css)
for m in matches2:
    print(m)

matches3 = re.findall(r'(\.footer-strip-container\b[^{]*\{[^}]*\})', css)
for m in matches3:
    print(m)

