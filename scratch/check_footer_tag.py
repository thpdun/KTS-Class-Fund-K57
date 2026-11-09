with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if '<footer' in line:
        print(f'{i+1}: {line.strip()[:100]}')
        for j in range(i, min(i+40, len(lines))):
            print(f'{j+1}: {lines[j]}', end='')

