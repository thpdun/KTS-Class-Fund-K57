import sys
import re

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open("web/index.html.bak", "r", encoding="utf-8") as f:
    bak = f.read()

with open("web/index.html", "r", encoding="utf-8") as f:
    cur = f.read()

print("--- 1. Compare updateRoleDisplay / updateAuthUI ---")
def extract_fn(src, fn_name):
    pattern = rf'function\s+{fn_name}\s*\([^{{]*\{{'
    m = re.search(pattern, src)
    if not m:
        return f"Function {fn_name} not found"
    start = m.start()
    # brace matching
    brace_count = 0
    in_fn = False
    for i in range(start, len(src)):
        if src[i] == '{':
            brace_count += 1
            in_fn = True
        elif src[i] == '}':
            brace_count -= 1
            if in_fn and brace_count == 0:
                return src[start:i+1]
    return src[start:start+2000]

print("BAK updateRoleDisplay:\n", extract_fn(bak, "updateRoleDisplay")[:1000])
print("\nCUR updateRoleDisplay:\n", extract_fn(cur, "updateRoleDisplay")[:1000])

print("\n--- 2. Compare handleAccountChanged ---")
print("BAK handleAccountChanged:\n", extract_fn(bak, "handleAccountChanged")[:1000])
print("\nCUR handleAccountChanged:\n", extract_fn(cur, "handleAccountChanged")[:1000])

print("\n--- 3. Compare initDapp / loadContractData ---")
print("BAK loadContractData:\n", extract_fn(bak, "loadContractData")[:1000])
print("\nCUR loadContractData:\n", extract_fn(cur, "loadContractData")[:1000])
