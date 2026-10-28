# -*- coding: utf-8 -*-
"""
Deep scan of buttons, containers, modals, and potential overlap areas using html.parser
"""
import re
from html.parser import HTMLParser
from pathlib import Path

content = Path("web/index.html").read_text(encoding="utf-8")

class ElementScanner(HTMLParser):
    def __init__(self):
        super().__init__()
        self.buttons = []
        self.modals = []
        self.tag_stack = []

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        self.tag_stack.append((tag, attr_dict))
        
        cid = attr_dict.get("id", "")
        cclass = attr_dict.get("class", "")
        
        if tag == "button" or "btn" in cclass or "onclick" in attr_dict:
            parent = self.tag_stack[-2] if len(self.tag_stack) >= 2 else ("root", {})
            self.buttons.append({
                "tag": tag,
                "id": cid,
                "class": cclass,
                "onclick": attr_dict.get("onclick", ""),
                "parent_tag": parent[0],
                "parent_id": parent[1].get("id", ""),
                "parent_class": parent[1].get("class", "")
            })
            
        if "modal" in cid.lower() or "modal" in cclass.lower() or "overlay" in cclass.lower():
            self.modals.append({
                "tag": tag,
                "id": cid,
                "class": cclass,
                "style": attr_dict.get("style", "")
            })

    def handle_endtag(self, tag):
        if self.tag_stack and self.tag_stack[-1][0] == tag:
            self.tag_stack.pop()

scanner = ElementScanner()
scanner.feed(content)

print(f"Total buttons/clickable elements: {len(scanner.buttons)}")
print("\n--- KEY ACTION BUTTONS ---")
for b in scanner.buttons:
    if b["id"] or "btn" in b["class"]:
        print(f"[{b['tag'].upper()}] id='{b['id']}' class='{b['class']}' parent=<{b['parent_tag']} id='{b['parent_id']}' class='{b['parent_class']}'>")

print(f"\nTotal modal-related elements: {len(scanner.modals)}")
for m in scanner.modals:
    print(f"<{m['tag']}> id='{m['id']}' class='{m['class']}' style='{m['style'][:60]}'")
