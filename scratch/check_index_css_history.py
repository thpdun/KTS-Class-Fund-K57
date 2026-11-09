with open('web/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = re.findall(r'([^{}]*panel-history[^{}]*\{[^}]*\})', text)
for m in matches:
    print(m)

