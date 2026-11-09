with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if i >= 4709 and i <= 6230:
        if '<section' in l or '</section>' in l:
            print(f'{i+1}: {l.strip()[:80]}')

