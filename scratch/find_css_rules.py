import re
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

m_style = re.search(r'<style>([\s\S]*?)</style>', html)
style = m_style.group(1)

selectors = [
    ".app-topbar",
    ".hero-section",
    ".class-announcement-card",
    ".metrics-grid",
    ".metric-card",
    ".quick-control-bar",
    ".badge-network"
]

for s in selectors:
    pos = style.find(s)
    print(f"Selector {s} found at position: {pos}")
    if pos != -1:
        print(style[pos:pos+250])
        print("="*40)
