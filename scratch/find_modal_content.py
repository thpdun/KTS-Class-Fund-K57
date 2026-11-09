with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'id="dapp-workspace"' in line:
        print(f'dapp-workspace at line {i+1}')
        for j in range(i, min(i+150, len(lines))):
            print(f'{j+1}: {lines[j]}', end='')
        break

