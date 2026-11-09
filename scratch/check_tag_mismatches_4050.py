with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

import re

stack = []
for line_no in range(4050, 4705):
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
            if not stack:
                print(f"EXTRA CLOSING </{tag}> at line {line_no}!")
            else:
                top = stack[-1]
                if top[0] == tag:
                    # clean match
                    stack.pop()
                else:
                    print(f"MISMATCH at line {line_no}: expected </{top[0]}> (opened at {top[1]}), got </{tag}>")
                    # find it in stack
                    found = False
                    for i in range(len(stack)-1, -1, -1):
                        if stack[i][0] == tag:
                            stack = stack[:i]
                            found = True
                            break

