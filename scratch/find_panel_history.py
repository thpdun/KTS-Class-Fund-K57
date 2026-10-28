import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

idx = html.find('id="panelHistory"')
if idx != -1:
    print(html[idx-100:idx+2500])
else:
    print("panelHistory not found")
