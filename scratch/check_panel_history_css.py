with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()
with open('web/styles.css', 'r', encoding='utf-8') as f:
    css = f.read()

import re
print("index.html matches:")
for m in re.finditer(r'panel-history|panelHistory', html[:4000]):
    print(html[m.start()-20:m.start()+80])

print("styles.css matches:")
for m in re.finditer(r'panel-history|panelHistory', css):
    print(css[m.start()-20:m.start()+80])

