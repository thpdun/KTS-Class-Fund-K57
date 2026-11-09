from html.parser import HTMLParser

class BalanceChecker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.void_tags = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
    
    def handle_starttag(self, tag, attrs):
        if tag.lower() not in self.void_tags:
            self.stack.append((tag.lower(), self.getpos()))
            
    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.void_tags:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                self.stack = self.stack[:i]
                return

parser = BalanceChecker()
with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

parser.feed(html)
print(f"Unclosed tags count: {len(parser.stack)}")
for item in parser.stack:
    print(f"<{item[0]}> opened at line {item[1][0]}")

