with open('web/styles.css', 'r', encoding='utf-8') as f:
    css1 = f.read()
with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

import re
print("Styles.css role-panel / panel-:")
for line in css1.splitlines():
    if any(k in line for k in ['role-panel', 'panel-history', 'panel-bcs', 'panel-student', 'panel-advisor']):
        print(line)

print("\nInline styles in index.html <style>:")
style_blocks = re.findall(r'<style>(.*?)</style>', html, re.DOTALL)
for b in style_blocks:
    for line in b.splitlines():
        if any(k in line for k in ['panel-history', 'panelHistory']):
            print(line)

