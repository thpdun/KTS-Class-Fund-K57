with open('web/styles.css', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if '.site-footer' in line or 'footer-strip' in line:
        print(f"{i+1}: {line.strip()[:80]}")

