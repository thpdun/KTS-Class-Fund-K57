with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()[:4050]

for i, line in enumerate(lines):
    if 'panelHistory' in line or 'panel-history' in line or 'role-panel' in line:
        print(f"{i+1}: {line.strip()[:100]}")

