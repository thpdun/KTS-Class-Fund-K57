with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(5250, 5350):
    if 'id=' in lines[i]:
        print(f'{i+1}: {lines[i].strip()[:90]}')

