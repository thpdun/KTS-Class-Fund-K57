import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for j in range(8445, 8680):
    print(f"{j+1}: {lines[j].rstrip()}")
