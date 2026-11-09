with open('web/styles.css', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(2065, 2090):
    print(f'{i+1}: {lines[i]}', end='')

