with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if '<body' in line or '<div class="app-main"' in line or '<main' in line or '</main>' in line or '<footer' in line or '</aside>' in line or '<aside' in line:
        print(f'{i+1}: {line.strip()[:100]}')

