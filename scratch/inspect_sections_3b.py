import sys
import re

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

with open('web/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find section tags
sections = re.findall(r'<section[^>]*id="([^"]+)"[^>]*>', content)
print(f"Total sections with ID: {len(sections)}")
for s in sections:
    print(f"  - #{s}")

# Find content panels
panels = re.findall(r'<div[^>]*class="[^"]*content-panel[^"]*"[^>]*id="([^"]+)"', content)
print(f"\nContent panels with ID: {len(panels)}")
for p in panels:
    print(f"  - #{p}")

# Look at inline style margins in main container
matches = re.finditer(r'<(?:section|div)[^>]*style="[^"]*margin[^"]*"[^>]*>', content)
print(f"\nElements with inline margin styles:")
count = 0
for m in matches:
    tag = m.group(0)[:120]
    # Filter only relevant ones
    if any(k in tag for k in ['section', 'panel', 'banner', 'group', 'card', 'box', 'control']):
        print(f"  {tag}")
        count += 1
        if count > 25:
            print("  ... and more")
            break
