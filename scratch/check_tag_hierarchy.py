with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

tag_stack = []
for i, l in enumerate(lines):
    if i > 6220:
        break
    import re
    tokens = re.findall(r'<(/?[a-zA-Z0-9\-]+)([^>]*)>', l)
    for tag, attrs in tokens:
        tag = tag.lower()
        if tag in ['img', 'br', 'hr', 'input', 'link', 'meta']:
            continue
        if tag.startswith('/'):
            closing = tag[1:]
            if tag_stack and tag_stack[-1][0] == closing:
                tag_stack.pop()
            else:
                # mismatch
                pass
        else:
            # check self-closing
            if not attrs.endswith('/'):
                tag_id = re.search(r'id=["\'](.*?)["\']', attrs)
                tag_cls = re.search(r'class=["\'](.*?)["\']', attrs)
                desc = f"{tag}"
                if tag_id: desc += f"#{tag_id.group(1)}"
                if tag_cls: desc += f".{tag_cls.group(1).split()[0]}"
                tag_stack.append((tag, i+1, desc))

print("Active tags at line 6214:")
for t, line_num, desc in tag_stack:
    print(f"  Line {line_num}: <{desc}>")

