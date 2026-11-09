with open('web/styles.css', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'display' in line and '!important' in line:
        print(f"{i+1}: {line.strip()[:80]}")

