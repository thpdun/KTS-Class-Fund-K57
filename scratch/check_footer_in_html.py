with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

import re
matches = [m.start() for m in re.finditer(r'site-footer|footer', html[:7000])] # in style tags
for m in matches:
    print(html[m-20:m+200])
    print("="*40)

