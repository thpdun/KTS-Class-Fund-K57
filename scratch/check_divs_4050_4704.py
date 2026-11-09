with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

import re

div_stack = []
for line_no in range(4050, 4705):
    line = lines[line_no - 1]
    for m in re.finditer(r'<(/)?div([^>]*)>', line):
        is_closing = m.group(1) == '/'
        attrs = m.group(2)
        if not is_closing:
            div_stack.append((line_no, attrs))
        else:
            if div_stack:
                popped = div_stack.pop()
                if not div_stack:
                    print(f"ROOT DIV {popped[1][:30]} (opened at {popped[0]}) was CLOSED at line {line_no}!")

print(f"Unclosed divs at 4704: {len(div_stack)}")

