import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

with open('contracts/project/ProjectCore.sol', 'r', encoding='utf-8') as f:
    sol = f.read()

events = re.findall(r'event\s+([A-Za-z0-9_]+)\s*\((.*?)\);', sol, re.DOTALL)
print("Events in ProjectCore.sol:")
for name, params in events:
    clean_params = re.sub(r'\s+', ' ', params).strip()
    print(f"  - {name}({clean_params})")
