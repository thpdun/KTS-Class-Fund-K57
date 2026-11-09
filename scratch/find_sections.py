with open('web/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.splitlines()
targets = ['id="workflow"', 'id="governance"', 'id="economics"', 'id="blockchain"', 'id="faq"']
for t in targets:
    for i, l in enumerate(lines):
        if t in l:
            print(f'{t} at line {i+1}')
