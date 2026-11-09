with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if '<footer' in line:
        footer_line = i + 1
        print(f"Footer is at line {footer_line}")
        break

# Trace opening tags from line 4050 (<div class="app-main">) to footer_line
stack = []
for i in range(4049, footer_line - 1):
    line = lines[i]
    import re
    tokens = re.findall(r'<(/?[a-zA-Z0-9\-]+)[^>]*>', line)
    for t in tokens:
        if t.startswith('/'):
            tag = t[1:].lower()
            if stack and stack[-1][0] == tag:
                stack.pop()
        elif not t.endswith('/'):
            tag = t.lower()
            if tag not in ['img', 'br', 'hr', 'input', 'meta', 'link']:
                stack.append((tag, i+1, line.strip()[:60]))

print("Unclosed tags before <footer class='site-footer'>:")
for s in stack:
    print(f"Line {s[1]}: <{s[0]}> ({s[2]})")

