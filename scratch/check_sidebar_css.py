with open('web/styles.css', 'r', encoding='utf-8') as f:
    text_styles = f.read()

with open('web/index.html', 'r', encoding='utf-8') as f:
    text_html = f.read()

import re
print("=== app-sidebar in styles.css ===")
for m in re.finditer(r'(?:^|\n)([^{}]*\bapp-sidebar\b[^{}]*)\{([^}]*)\}', text_styles):
    print(m.group(1).strip(), "-->", m.group(2).strip().replace('\n', ' '))

print("\n=== app-sidebar in index.html ===")
for m in re.finditer(r'(?:^|\n)([^{}]*\bapp-sidebar\b[^{}]*)\{([^}]*)\}', text_html[:4050]):
    print(m.group(1).strip(), "-->", m.group(2).strip().replace('\n', ' '))

