with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(4120, 4260):
    print(f'{i+1}: {repr(lines[i])}')

