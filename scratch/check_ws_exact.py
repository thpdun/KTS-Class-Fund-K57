with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i in range(4705, 4755):
    print(f'{i+1}: {repr(lines[i])}')

