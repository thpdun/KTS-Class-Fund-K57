with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start = None
for i, line in enumerate(lines):
    if 'function syncRolePermissionsUI(' in line:
        start = i
        break

if start is not None:
    for j in range(start, min(start + 80, len(lines))):
        print(f'{j+1}: {lines[j]}', end='')

