with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, l in enumerate(lines):
    if 'id="dapp-workspace"' in l or "id='dapp-workspace'" in l:
        print(f"Found on line {i+1}")
        for j in range(max(0, i - 5), min(len(lines), i + 40)):
            print(f'{j+1}: {lines[j]}', end='')
        break

