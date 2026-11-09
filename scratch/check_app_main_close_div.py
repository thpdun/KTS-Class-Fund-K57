with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

depth = 0
found = False
for i in range(4049, len(lines)):
    line = lines[i]
    opens = line.count('<div')
    closes = line.count('</div')
    depth += opens - closes
    if depth == 0:
        print(f"app-main (started at line 4050) closes at line {i+1}")
        found = True
        break

if not found:
    print(f"app-main never closes! final depth: {depth}")

