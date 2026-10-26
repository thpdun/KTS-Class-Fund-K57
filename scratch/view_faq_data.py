import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("web/index.html", "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find('const FAQ_DATA = [')
end_pos = text.find('];', pos)
print(text[pos:end_pos+2])
