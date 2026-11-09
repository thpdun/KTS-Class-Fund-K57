with open('web/index.html', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'FLOW 1' in line or 'flow-step-box' in line:
            print(f"{i+1}: {line.strip()[:100]}")

