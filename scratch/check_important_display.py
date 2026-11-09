with open('web/styles.css', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = re.findall(r'([^\{\}]*display:[^;\}]*!important;[^\{\}]*)', text)
for m in matches:
    print(m.strip())

