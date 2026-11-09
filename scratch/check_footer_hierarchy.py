import re

with open('web/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

f_idx = text.find('<footer')
print('Footer at char index:', f_idx)

# Let's see lines around footer
lines = text.splitlines()
footer_line_num = -1
for i, l in enumerate(lines, 1):
    if '<footer' in l:
        footer_line_num = i
        break

print('Footer is at line:', footer_line_num)

# Let's inspect the tags opened before footer
tag_stack = []
tag_regex = re.compile(r'<(/)?([a-zA-Z0-9\-]+)([^>]*)>')

for line_no in range(1, footer_line_num):
    line = lines[line_no - 1]
    for match in tag_regex.finditer(line):
        is_closing = match.group(1) == '/'
        tag_name = match.group(2).lower()
        attrs = match.group(3)
        if tag_name in ['input', 'img', 'br', 'hr', 'meta', 'link']:
            continue
        if attrs.rstrip().endswith('/'):
            continue
        if not is_closing:
            id_m = re.search(r'id=["\'](.*?)["\']', attrs)
            cls_m = re.search(r'class=["\'](.*?)["\']', attrs)
            tag_id = id_m.group(1) if id_m else ''
            tag_cls = cls_m.group(1) if cls_m else ''
            tag_stack.append((tag_name, tag_id, tag_cls, line_no))
        else:
            # find matching tag from top of stack
            matched = False
            for idx in range(len(tag_stack) - 1, -1, -1):
                if tag_stack[idx][0] == tag_name:
                    tag_stack = tag_stack[:idx]
                    matched = True
                    break

print('\nOpen tags containing footer:')
for t in tag_stack:
    print(f'  Line {t[3]}: <{t[0]} id="{t[1]}" class="{t[2]}">')

