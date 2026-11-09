from html.parser import HTMLParser

class FooterParentChecker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.void_tags = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
        self.footer_parents = None
    
    def handle_starttag(self, tag, attrs):
        if tag.lower() not in self.void_tags:
            self.stack.append((tag.lower(), attrs, self.getpos()))
            if tag.lower() == 'footer':
                self.footer_parents = [(t[0], dict(t[1]).get('class', ''), dict(t[1]).get('id', '')) for t in self.stack[:-1]]
            
    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.void_tags:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                self.stack = self.stack[:i]
                return

parser = FooterParentChecker()
with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

parser.feed(html)
print("Footer parents:")
for p in parser.footer_parents:
    print(f"<{p[0]} class='{p[1]}' id='{p[2]}'>")

