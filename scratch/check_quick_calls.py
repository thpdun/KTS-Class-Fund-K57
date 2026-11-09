with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'handleQuickAction' in l or 'openActionModal' in l:
        print(f'{i+1}: {l.strip()[:100]}')

