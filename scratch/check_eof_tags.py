import re

with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

tag_stack = []
tag_regex = re.compile(r'<(/)?([a-zA-Z0-9\-]+)([^>]*)>')

for line_no, line in enumerate(lines, 1):
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

print("Remaining open tags at EOF:")
for t in tag_stack:
    print(f"  Line {t[3]}: <{t[0]} id='{t[1]}' class='{t[2]}'>")

