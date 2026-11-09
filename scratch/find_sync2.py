with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

found = False
for i, l in enumerate(lines):
    if 'function syncRolePermissionsUI' in l:
        found = True
        print(''.join(lines[i+60:i+120]))
        break

