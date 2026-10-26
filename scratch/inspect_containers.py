import re

with open('web/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

body_start = text.find('<body>')
main_script_start = text.rfind('<script>')
if main_script_start == -1:
    main_script_start = text.rfind('<script')

body_content = text[body_start:main_script_start]

pattern = re.compile(r'<(div|aside|main|header|nav|section|article)[^>]*id=\"([^\"]+)\"')
matches = pattern.findall(body_content)
print(f"Total matching containers with id: {len(matches)}")
for tag, id_val in matches:
    print(f"<{tag} id=\"{id_val}\">")
