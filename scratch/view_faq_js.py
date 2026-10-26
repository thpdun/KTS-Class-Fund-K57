import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("web/index.html", "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find('function renderFaq')
end_pos = text.find('// --- 11.', pos)
if end_pos == -1: end_pos = pos + 2500
print(text[pos:end_pos])
