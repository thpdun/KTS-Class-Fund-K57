with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'function syncRolePermissionsUI' in l:
        print(''.join(lines[i:i+60]))
        break

