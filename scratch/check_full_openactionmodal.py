with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(16340, 16465):
    print(f'{i+1}: {lines[i]}', end='')

