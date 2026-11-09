with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i in range(4750, 4775):
    print(f'{i+1}: {repr(lines[i])}')

