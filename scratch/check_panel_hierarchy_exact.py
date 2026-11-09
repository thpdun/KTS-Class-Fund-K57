with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for panel_id in ['panelStudent', 'panelBCS', 'panelAdvisor', 'panelHistory']:
    found_start = -1
    for i, line in enumerate(lines):
        if f'id="{panel_id}"' in line:
            found_start = i
            break
    print(f"{panel_id} starts at line {found_start+1}")

# Check tag depth of panelHistory

