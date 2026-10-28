import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

idx = html.find('id="panelHistory"')
print(html[idx+2000:idx+4500])
