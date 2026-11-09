with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

import re
matches = [m.start() for m in re.finditer(r'site-footer', html)]
for m in matches:
    line_no = html[:m].count('\n') + 1
    print(f"Line {line_no}: {html[m-20:m+80]}")

