with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'function renderFlowLedgerTable' in l:
        print(f"Line {i+1}: {l.strip()}")
        break

