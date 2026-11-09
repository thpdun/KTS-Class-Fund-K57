with open('web/styles.css', 'r', encoding='utf-8') as f:
    css_text = f.read()

import re
print("Matches in styles.css for panelHistory:")
for m in re.finditer(r'.*panelHistory.*', css_text):
    print(m.group(0))

print("\nMatches in styles.css for flow-steps-grid:")
for m in re.finditer(r'.*flow-steps-grid.*', css_text):
    print(m.group(0))

