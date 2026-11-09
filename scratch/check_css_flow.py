with open('web/styles.css', 'r', encoding='utf-8') as f:
    css = f.read()

import re
matches = [m.start() for m in re.finditer(re.escape('flow-steps-grid'), css)]
for m in matches:
    print(css[m-20:m+200])

