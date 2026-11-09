with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

def find_closing_div(start_line):
    depth = 0
    for i in range(start_line - 1, len(lines)):
        line = lines[i]
        opens = line.count('<div')
        closes = line.count('</div')
        depth += opens - closes
        if depth == 0:
            return i + 1
    return -1

for panel_id in ['panelStudent', 'panelBCS', 'panelAdvisor', 'panelHistory']:
    for i, line in enumerate(lines):
        if f'id="{panel_id}"' in line:
            start = i + 1
            end = find_closing_div(start)
            print(f"{panel_id}: lines {start} to {end}")
            break

