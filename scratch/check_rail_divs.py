with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

import re

stack = []
for line_no in range(4620, 4705):
    line = lines[line_no - 1]
    for m in re.finditer(r'<(/)?([a-zA-Z0-9\-]+)([^>]*)>', line):
        is_closing = m.group(1) == '/'
        tag = m.group(2).lower()
        attrs = m.group(3)
        if tag in ['input', 'img', 'br', 'hr', 'meta', 'link']: continue
        if attrs.rstrip().endswith('/'): continue
        if not is_closing:
            stack.append((tag, line_no, attrs))
            print(f"  +{tag} line {line_no}: {attrs[:30]}")
        else:
            top = stack.pop() if stack else None
            print(f"  -{tag} line {line_no} (closed {top[0]} from {top[1]})")

