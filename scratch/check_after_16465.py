with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(16465, min(16510, len(lines))):
    print(f'{i+1}: {lines[i]}', end='')

