import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for j in range(7400, 7540):
    print(f"{j+1}: {lines[j].rstrip()}")
