with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'id="panelBCS"' in l:
        print(f'panelBCS starts at {i+1}')
        for j in range(i, min(len(lines), i + 100)):
            print(f'{j+1}: {lines[j]}', end='')
        break

