with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

import re

for line_no in range(4680, 4715):
    print(f"{line_no}: {lines[line_no - 1]}", end='')

