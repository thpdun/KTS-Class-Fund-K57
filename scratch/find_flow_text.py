with open('web/index.html', 'r', encoding='utf-8') as f:
    c = f.read()

import re
matches = [m.start() for m in re.finditer(re.escape('Mỗi luồng tiền trong hệ thống'), c)]
print('Matches count:', len(matches))
lines = c.splitlines()
for m in matches:
    line_no = c[:m].count('\n') + 1
    print(f'Line {line_no}')

