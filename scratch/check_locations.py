with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
for i, line in enumerate(lines):
    if 'id="panelHistory"' in line:
        print(f"panelHistory defined at line {i+1}")
    if 'function openActionModal' in line:
        print(f"openActionModal defined at line {i+1}")
    if 'function selectRoleView' in line:
        print(f"selectRoleView defined at line {i+1}")
    if 'id="dapp-workspace"' in line:
        print(f"dapp-workspace at line {i+1}")

