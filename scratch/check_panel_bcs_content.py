with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(4920, min(5115, len(lines))):
    print(f'{i+1}: {lines[i]}', end='')

