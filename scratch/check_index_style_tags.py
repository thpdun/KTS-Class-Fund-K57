with open('web/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
styles = re.findall(r'<style>(.*?)</style>', text, re.DOTALL)
for s in styles:
    for line in s.splitlines():
        if 'history' in line.lower() or 'panel' in line.lower():
            if 'display' in line or '{' in line or '}' in line:
                print(line)

