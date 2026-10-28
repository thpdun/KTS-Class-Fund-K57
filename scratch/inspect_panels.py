import re
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

panels = ["panelStudent", "panelBCS", "panelAdvisor", "panelHistory"]

for p in panels:
    m = re.search(rf'<(?:div|section)[^>]*id=["\']{p}["\'][\s\S]*?</(?:div|section)>', html)
    # find all inputs and buttons inside panel
    idx = html.find(f'id="{p}"')
    if idx != -1:
        # find end of this panel
        # search next 4000 chars
        snippet = html[idx:idx+4000]
        inputs = re.findall(r'<input[^>]*id=["\']([^"\']+)["\']', snippet)
        buttons = re.findall(r'<button[^>]*id=["\']([^"\']+)["\']', snippet)
        print(f"=== {p} ===")
        print("  Inputs:", inputs)
        print("  Buttons with ID:", buttons)
        # find all headings or card titles
        titles = re.findall(r'<(?:h[1-6]|div class="[^"]*title[^"]*")[^>]*>([\s\S]*?)</(?:h[1-6]|div)>', snippet)
        print("  Titles:", [re.sub(r'<[^>]+>', '', t).strip() for t in titles[:5]])
