import sys

with open('web/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

style_start = text.find('<style>')
style_end = text.find('</style>')
body_start = text.find('<body')
body_close = text.find('</body>')

# Find the main inline script in body
last_script_open = text.rfind('<script>')
if last_script_open == -1:
    last_script_open = text.rfind('<script')

print(f"Total length: {len(text)}")
print(f"Style start: {style_start}, end: {style_end} (length: {style_end - style_start})")
print(f"Body start: {body_start}, end: {body_close}")
print(f"Main script starts at: {last_script_open}")
