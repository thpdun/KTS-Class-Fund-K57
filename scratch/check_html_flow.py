with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

import re
matches = [m.start() for m in re.finditer(re.escape('flow-steps-grid'), html)]
for m in matches:
    print(html[m-50:m+200])

