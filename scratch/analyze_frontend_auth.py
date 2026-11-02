import re

with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines in web/index.html: {len(lines)}")

# Find all fetch calls in web/index.html
fetch_calls = []
for i, line in enumerate(lines):
    if 'fetch(' in line:
        fetch_calls.append((i + 1, line.strip()))

print(f"\nTotal fetch() calls found: {len(fetch_calls)}")
for line_no, content in fetch_calls:
    print(f"  Line {line_no}: {content}")

# Inspect authenticateWalletSession
in_auth = False
auth_lines = []
for i, line in enumerate(lines):
    if 'async function authenticateWalletSession' in line:
        in_auth = True
    if in_auth:
        auth_lines.append((i + 1, line))
        if line.strip() == '}' and len(auth_lines) > 20 and 'catch' in "".join(l[1] for l in auth_lines[-15:]):
            in_auth = False

print("\n--- authenticateWalletSession snippet ---")
for line_no, content in auth_lines[:40]:
    print(f"{line_no}: {content}", end="")
