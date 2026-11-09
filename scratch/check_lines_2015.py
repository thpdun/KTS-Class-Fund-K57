with open('web/styles.css', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(2005, 2045):
    print(f'{i+1}: {lines[i]}', end='')

