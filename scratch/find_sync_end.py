with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'function syncRolePermissionsUI' in l:
        print(f"Line {i+1}: {l.strip()}")
        print(''.join(lines[i+125:i+145]))
        break

