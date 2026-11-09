from html.parser import HTMLParser

VOID_ELEMENTS = {
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
    'link', 'meta', 'param', 'source', 'track', 'wbr'
}

class ProperHTMLTracker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.footer_parents = None
        self.footer_pos = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        pos = self.getpos()
        if tag == 'footer' or 'site-footer' in attrs_dict.get('class', ''):
            self.footer_parents = list(self.stack)
            self.footer_pos = pos
        if tag.lower() not in VOID_ELEMENTS:
            self.stack.append((tag, attrs_dict, pos))

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in VOID_ELEMENTS:
            return
        # Pop matching tag from stack
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0].lower() == tag_lower:
                self.stack = self.stack[:i]
                break

with open('web/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

parser = ProperHTMLTracker()
parser.feed(content)

print(f"Footer position: {parser.footer_pos}")
if parser.footer_parents:
    print(f"True parent hierarchy of <footer> (depth {len(parser.footer_parents)}):")
    for depth, (tag, attrs, pos) in enumerate(parser.footer_parents):
        id_str = f" id='{attrs.get('id')}'" if 'id' in attrs else ""
        class_str = f" class='{attrs.get('class')}'" if 'class' in attrs else ""
        print(f"  [{depth}] <{tag}{id_str}{class_str}> (opened at line {pos[0]}:{pos[1]})")
else:
    print("Footer NOT found!")

