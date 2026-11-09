with open('web/index.html', 'r', encoding='utf-8') as f:
    text_html = f.read()

import re
matches = list(re.finditer(r'(?:^|\n)([^{}]*\bbody\b[^{}]*)\{([^}]*)\}', text_html[:4050]))
print(f"Found {len(matches)} matches")
for m in matches:
    print(m.group(1).strip(), "-->", m.group(2).strip().replace('\n', ' '))

