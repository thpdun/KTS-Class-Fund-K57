with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(6205, min(len(lines), 6250)):
    print(f'{i+1}: {repr(lines[i])}')

