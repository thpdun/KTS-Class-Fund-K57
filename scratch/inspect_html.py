with open('web/index.html', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        l = line.strip().lower()
        if '<style' in l or '</style>' in l or '<body' in l or '</body' in l or '<script' in l or '</script>' in l:
            print(f"{i+1}: {line.strip()[:80]}")

