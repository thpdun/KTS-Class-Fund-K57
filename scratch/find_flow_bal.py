with open('web/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'flowBalClassFund', text)]
for idx in matches:
    print(text[idx-40:idx+60].replace('\n', ' '))

