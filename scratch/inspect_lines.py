import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('web/index.html.bak', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("Line 2000 to 2050:")
for i in range(1999, min(2050, len(lines))):
    if any(k in lines[i] for k in ['<section', 'id=', 'class=']):
        print(f"L{i+1}: {lines[i].strip()[:90]}")

print("\nLine 2150 to 2250:")
for i in range(2149, min(2250, len(lines))):
    if any(k in lines[i] for k in ['<section', 'id=', 'class=']):
        print(f"L{i+1}: {lines[i].strip()[:90]}")
