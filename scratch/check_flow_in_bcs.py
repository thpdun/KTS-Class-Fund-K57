with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

in_bcs = False
for i, line in enumerate(lines):
    if 'id="panelBCS"' in line:
        in_bcs = True
    if 'id="panelAdvisor"' in line:
        in_bcs = False
    if in_bcs and 'FLOW 1' in line:
        print(f"FLOW 1 found inside panelBCS at line {i+1}!")
        break
else:
    print("FLOW 1 is NOT inside panelBCS.")

