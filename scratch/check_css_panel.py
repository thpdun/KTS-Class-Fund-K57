with open('web/styles.css', 'r', encoding='utf-8') as f:
    text = f.read()

import re
for m in re.finditer(r'([^{}]*(?:role-panel|panel-history|panelHistory|flow-steps-grid)[^{}]*)\{([^}]*)\}', text):
    print(m.group(0))

