import re

with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Let's find start: <header class="app-topbar">
topbar_start = html.find('<header class="app-topbar">')
# Let's find end: <section class="dapp-hero-section" id="dapp-workspace">
workspace_start = html.find('<section class="dapp-hero-section" id="dapp-workspace">')

print(f"topbar_start: {topbar_start}, workspace_start: {workspace_start}")
assert topbar_start != -1 and workspace_start != -1

