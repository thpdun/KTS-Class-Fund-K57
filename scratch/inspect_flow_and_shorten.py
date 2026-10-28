import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

def find_func_lines(name):
    start = -1
    for i, line in enumerate(lines):
        if re.search(rf'function\s+{name}\s*\(', line):
            start = i
            break
    if start == -1:
        return f"Function {name} not found"
    # return next 80 lines
    return "".join(lines[start:start+120])

print("=== shortenAddress ===")
print(find_func_lines("shortenAddress"))

print("\n=== renderFlowLedgerTable ===")
print(find_func_lines("renderFlowLedgerTable"))
