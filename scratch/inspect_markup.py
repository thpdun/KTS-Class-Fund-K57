import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

body_line = 0
for idx, l in enumerate(lines):
    if '<body' in l:
        body_line = idx
        break

print(f"Body starts at line: {body_line + 1}")
for i in range(body_line, min(body_line + 80, len(lines))):
    print(f"{i+1}: {lines[i]}", end="")
