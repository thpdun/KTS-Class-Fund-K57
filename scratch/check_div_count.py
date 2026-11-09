with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'id="panelBCS"' in l:
        start_bcs = i
    if 'id="panelAdvisor"' in l:
        start_adv = i
    if 'id="panelHistory"' in l:
        start_hist = i

print(f"panelBCS: line {start_bcs+1}")
print(f"panelAdvisor: line {start_adv+1}")
print(f"panelHistory: line {start_hist+1}")

bcs_text = "".join(lines[start_bcs:start_adv])
print("panelBCS open divs:", bcs_text.count('<div'))
print("panelBCS close divs:", bcs_text.count('</div>'))

