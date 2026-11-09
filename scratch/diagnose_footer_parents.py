from html.parser import HTMLParser

class ParentTracker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.footer_parents = None
        self.footer_line = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self.stack.append((tag, attrs_dict, self.getpos()))
        if tag == 'footer' or 'site-footer' in attrs_dict.get('class', ''):
            if self.footer_parents is None:
                self.footer_parents = list(self.stack)
                self.footer_line = self.getpos()

    def handle_endtag(self, tag):
        # find matching starttag from top of stack
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                self.stack = self.stack[:i]
                break

with open('web/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

parser = ParentTracker()
parser.feed(content)

print(f"Footer found at line: {parser.footer_line}")
if parser.footer_parents:
    print(f"Parent hierarchy of footer (depth {len(parser.footer_parents)}):")
    for depth, (tag, attrs, pos) in enumerate(parser.footer_parents):
        id_str = f" id='{attrs.get('id')}'" if 'id' in attrs else ""
        class_str = f" class='{attrs.get('class')}'" if 'class' in attrs else ""
        print(f"  {'  '*depth}[{depth}] <{tag}{id_str}{class_str}> (line {pos[0]})")
else:
    print("Footer NOT found!")

