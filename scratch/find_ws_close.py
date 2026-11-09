with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if '</section>' in l and i > 4710 and i < 9500:
        print(f'{i+1}: {l.strip()[:60]}')

