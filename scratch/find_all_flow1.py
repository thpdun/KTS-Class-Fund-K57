with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'FLOW 1: THU NẠP QUỸ' in l:
        print(f"Line {i+1}")

