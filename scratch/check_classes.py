import re

with open('web/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

script = re.search(r'<script>(.*)</script>', text, re.DOTALL).group(1)
classList = set(re.findall(r'classList\.(?:add|remove|toggle)\([\'"]([^\'"]+)[\'"]\)', script))
className = set(re.findall(r'className\s*=\s*[\'"]([^\'"]+)[\'"]', script))
print('classList items:', sorted(list(classList)))
print('className items count:', len(className))

