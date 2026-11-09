with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'id="panelStudent"' in l:
        print(f'panelStudent: line {i+1}')
    if 'id="panelBCS"' in l:
        print(f'panelBCS: line {i+1}')
    if 'id="panelAdvisor"' in l:
        print(f'panelAdvisor: line {i+1}')
    if 'id="panelHistory"' in l:
        print(f'panelHistory: line {i+1}')

