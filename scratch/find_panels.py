with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if any(pid in line for pid in ['id="panelStudent"', 'id="panelBCS"', 'id="panelAdvisor"', 'id="panelHistory"']):
        print(f'{i+1}: {line.strip()[:100]}')

