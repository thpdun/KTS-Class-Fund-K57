with open('web/styles.css', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(2045, 2085):
    print(f'{i+1}: {lines[i]}', end='')

