with open('web/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

print('panelStudent in html:', 'id="panelStudent"' in text)
print('roleViewStudent in html:', 'id="roleViewStudent"' in text)
