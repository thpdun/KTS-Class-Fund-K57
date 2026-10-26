import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('web/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

for target in ['inputModalContract', 'roleViewStudent']:
    for i, line in enumerate(text.splitlines()):
        if target in line:
            print(f'{target} at line {i+1}: {line.strip()[:100]}')
