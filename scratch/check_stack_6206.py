with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

import re

# Let's find what opened the divs around line 6200
stack = []
for line_no in range(1, 6206):
    line = lines[line_no - 1]
    for m in re.finditer(r'<(/)?([a-zA-Z0-9\-]+)([^>]*)>', line):
        is_closing = m.group(1) == '/'
        tag = m.group(2).lower()
        attrs = m.group(3)
        if tag in ['input', 'img', 'br', 'hr', 'meta', 'link']: continue
        if attrs.rstrip().endswith('/'): continue
        if not is_closing:
            stack.append((tag, line_no, attrs))
        else:
            for i in range(len(stack) - 1, -1, -1):
                if stack[i][0] == tag:
                    stack = stack[:i]
                    break

print("Stack right before line 6206:")
for s in stack:
    print(f"  Line {s[1]}: <{s[0]} {s[2][:60]}>")

