with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()[:4050]

for i, line in enumerate(lines):
    if 'sidebar' in line.lower() and ('{' in line or ':' in line):
        print(f"{i+1}: {line.strip()[:80]}")

