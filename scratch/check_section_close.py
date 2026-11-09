with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if '</section>' in line and i > 4700 and i < 6000:
        print(f'{i+1}: {line.strip()[:100]}')

