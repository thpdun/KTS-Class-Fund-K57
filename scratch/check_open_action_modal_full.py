with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'function openActionModal' in l:
        for j in range(i, min(len(lines), i + 80)):
            print(f'{j+1}: {lines[j]}', end='')
        break

