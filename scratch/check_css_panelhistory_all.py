with open('web/styles.css', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = re.findall(r'([^{}]*panelHistory[^{}]*\{[^}]*\})', text)
print("Matches in styles.css for panelHistory:")
for m in matches:
    print(m)

matches2 = re.findall(r'([^{}]*panel-history[^{}]*\{[^}]*\})', text)
print("\nMatches in styles.css for panel-history:")
for m in matches2:
    print(m)

