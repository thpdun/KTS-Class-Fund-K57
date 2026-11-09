from html.parser import HTMLParser

class BodyChildrenTracker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.in_body = False
        self.body_children = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        pos = self.getpos()
        if tag == 'body':
            self.in_body = True
        elif self.in_body and len(self.stack) == 1 and self.stack[0][0] == 'body':
            # Direct child of body
            self.body_children.append((tag, attrs_dict, pos))
        self.stack.append((tag, attrs_dict, pos))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                self.stack = self.stack[:i]
                break
        if tag == 'body':
            self.in_body = False

with open('web/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

parser = BodyChildrenTracker()
parser.feed(content)

print("Direct children of body:")
for tag, attrs, pos in parser.body_children:
    id_str = f" id='{attrs.get('id')}'" if 'id' in attrs else ""
    class_str = f" class='{attrs.get('class')}'" if 'class' in attrs else ""
    print(f"  <{tag}{id_str}{class_str}> at line {pos[0]}")

