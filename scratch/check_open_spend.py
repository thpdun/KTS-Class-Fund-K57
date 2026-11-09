with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(16375, 16420):
    print(f'{i+1}: {lines[i]}', end='')

