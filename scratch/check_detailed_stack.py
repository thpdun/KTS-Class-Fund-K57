from html.parser import HTMLParser

VOID_ELEMENTS = {
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
    'link', 'meta', 'param', 'source', 'track', 'wbr'
}

class DetailedTracker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.events = []

    def handle_starttag(self, tag, attrs):
        pos = self.getpos()
        attrs_dict = dict(attrs)
        if pos[0] >= 3905 and pos[0] <= 6220:
            id_str = f" id='{attrs_dict.get('id')}'" if 'id' in attrs_dict else ""
            class_str = f" class='{attrs_dict.get('class')}'" if 'class' in attrs_dict else ""
            self.events.append(('start', tag, id_str, class_str, pos, len(self.stack)))
        if tag.lower() not in VOID_ELEMENTS:
            self.stack.append((tag, attrs_dict, pos))

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in VOID_ELEMENTS:
            return
        pos = self.getpos()
        popped = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0].lower() == tag_lower:
                popped = self.stack[i]
                self.stack = self.stack[:i]
                break
        if pos[0] >= 3905 and pos[0] <= 6220:
            self.events.append(('end', tag, popped, pos, len(self.stack)))

with open('web/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

parser = DetailedTracker()
parser.feed(content)

print(f"Stack at line 6208 (right before footer):")
for depth, (t, a, p) in enumerate(parser.stack):
    id_s = f" id='{a.get('id')}'" if 'id' in a else ""
    class_s = f" class='{a.get('class')}'" if 'class' in a else ""
    print(f"  [{depth}] <{t}{id_s}{class_s}> (from line {p[0]}:{p[1]})")

