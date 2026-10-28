# -*- coding: utf-8 -*-
"""
Inspect CSS rules for app-topbar, app-sidebar, app-main, buttons, modals, and flex wraps
"""
import re

with open("web/index.html", "r", encoding="utf-8") as f:
    content = f.read()

css_blocks = re.findall(r"<style>(.*?)</style>", content, re.DOTALL)
css = "\n".join(css_blocks)

def print_rules(pattern):
    print(f"\n=== MATCHES FOR: {pattern} ===")
    matches = re.findall(r"([^{}]+)\{([^}]+)\}", css)
    for sel, body in matches:
        if re.search(pattern, sel, re.I):
            clean_sel = " ".join(sel.split())
            clean_body = "; ".join([line.strip() for line in body.split(";") if line.strip()])
            print(f"{clean_sel} {{\n  {clean_body}\n}}")

print_rules(r"app-topbar|app-main|app-sidebar|app-shell")
print_rules(r"\.ann-|announcement|history")
print_rules(r"\.modal-")
print_rules(r"table-responsive|\.table")
