with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'function selectRoleView' in l:
        print(''.join(lines[i:i+40]))
        break

