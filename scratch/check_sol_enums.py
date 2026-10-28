import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

with open('contracts/project/ProjectCore.sol', 'r', encoding='utf-8') as f:
    sol = f.read()

m = re.search(r'enum\s+(?:RequestStatus|SpendStatus|RefundStatus)[^{]*\{([^}]+)\}', sol)
if m:
    print("Found enum:", m.group(0))
else:
    enums = re.findall(r'enum\s+[A-Za-z0-9_]+\s*\{[^}]+\}', sol)
    print("All enums in sol:")
    for e in enums:
        print(" ", e)
