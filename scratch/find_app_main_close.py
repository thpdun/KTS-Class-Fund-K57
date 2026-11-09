with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

import re

# Let's trace when <div class="app-main"> was closed!
stack = []
for line_no in range(3909, 6275):
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
                    closed_tag = stack[i]
                    if 'app-main' in closed_tag[2]:
                        print(f"app-main (opened at line {closed_tag[1]}) was CLOSED at line {line_no} by </{tag}>!")
                    stack = stack[:i]
                    break

