import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("web/index.html", "r", encoding="utf-8") as f:
    text = f.read()

def show_context(keyword, length=1200):
    pos = text.find(keyword)
    if pos != -1:
        print(f"\n==================== {keyword} ====================")
        print(text[pos:pos+length])

show_context('class="flow-balance-grid"')
show_context('class="flow-steps-grid"')
show_context('class="ann-meta-grid"')
show_context('class="roster-stats-grid"')
