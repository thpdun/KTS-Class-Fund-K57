# -*- coding: utf-8 -*-
"""
Inspect toolbar, filter pills, role buttons, topbar, and AI FAB in CSS
"""
import sys
import re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open("web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

css_blocks = re.findall(r"<style>(.*?)</style>", html, re.DOTALL)
css = "\n".join(css_blocks)

keywords = [
    "roster-filter", "roster-toolbar", "role-buttons-group", "role-btn-",
    "flow-filter", "faq-category", "faq-cat-btn", "ann-header", "ann-footer",
    "ai-fab", "ai-chat", "app-topbar", "modal-box", "modal-overlay",
    "table-responsive", "roster-table"
]

for kw in keywords:
    print(f"\n=================== CSS FOR '{kw}' ===================")
    matches = re.findall(r"([^{}]+)\{([^}]+)\}", css)
    for sel, body in matches:
        if kw in sel.lower():
            sel_clean = " ".join(sel.split())
            body_clean = "; ".join([line.strip() for line in body.split(";") if line.strip()])
            print(f"{sel_clean} {{\n  {body_clean}\n}}")
