import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

print("=== TAB BUTTONS / NAV ===")
tabs = re.findall(r'<button[^>]*class="[^"]*nav-tab[^"]*"[^>]*data-tab="([^"]+)"', html)
print("Data tabs:", tabs)

print("\n=== PANELS / SECTIONS WITH IDS ===")
sections = re.findall(r'<(?:div|section)[^>]*id="([^"]+)"[^>]*class="[^"]*(?:panel|section|view)[^"]*"', html)
print("Sections/panels:", sections)

print("\n=== HISTORY / CASH FLOW TABLES / SECTIONS ===")
history_matches = re.findall(r'id="([^"]*(?:history|tx|transaction|cashflow)[^"]*)"', html, re.I)
print("History/tx elements:", set(history_matches))

print("\n=== ROSTER / ANNOUNCEMENT ELEMENTS ===")
other_matches = re.findall(r'id="([^"]*(?:roster|announcement|action|task)[^"]*)"', html, re.I)
print("Roster/announcement/action elements:", set(other_matches))

print("\n=== JS FUNCTIONS DEFINED ===")
functions = re.findall(r'function\s+([A-Za-z0-9_$]+)\s*\(', html)
print(f"Total functions: {len(functions)}")
for fn in sorted(set(functions)):
    if any(k in fn.lower() for k in ['tx', 'hist', 'roster', 'announc', 'action', 'wallet', 'short', 'role', 'render']):
        print(f"  - {fn}")
