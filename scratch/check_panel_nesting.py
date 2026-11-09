with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Check tags between line 4706 and line 5472
stack = []
for i in range(4705, 5473):
    line = lines[i]
    # Simple tag tracer for divs
    opens = line.count('<div')
    closes = line.count('</div')
    for _ in range(opens):
        stack.append(i+1)
    for _ in range(closes):
        if stack:
            open_line = stack.pop()
            if 'id="panelBCS"' in lines[open_line-1] or 'id="panelStudent"' in lines[open_line-1] or 'id="panelAdvisor"' in lines[open_line-1] or 'id="panelHistory"' in lines[open_line-1]:
                print(f"Panel at line {open_line} closed at line {i+1}")

print(f"Remaining open divs at 5472: {len(stack)}")

