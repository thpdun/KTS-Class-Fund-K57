with open('web/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'quy tắc kinh tế chuẩn mực', text)]
print("Matches in web/index.html:", len(matches))
for idx in matches:
    print(text[idx-50:idx+100])

