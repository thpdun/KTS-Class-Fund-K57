with open('scratch/apply_focused_action_modals.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(70, min(150, len(lines))):
    print(f'{i+1}: {lines[i]}', end='')

