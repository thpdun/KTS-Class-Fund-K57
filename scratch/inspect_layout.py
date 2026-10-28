# -*- coding: utf-8 -*-
"""
Inspect layout, positioning, z-index, and responsive rules in web/index.html
"""
import re
from pathlib import Path

html_path = Path("web/index.html")
content = html_path.read_text(encoding="utf-8")

# Extract CSS content
css_matches = re.findall(r"<style>(.*?)</style>", content, re.DOTALL)
css = "\n".join(css_matches)

print(f"Total CSS length: {len(css)} chars")

# 1. Search for position: fixed and position: absolute
print("\n=== 1. FIXED & ABSOLUTE ELEMENTS IN CSS ===")
pos_rules = re.findall(r"([^{}]+)\{[^{}]*?position\s*:\s*(fixed|absolute)[^{}]*?\}", css, re.DOTALL)
for sel, pos in pos_rules:
    sel_clean = " ".join(sel.split())
    # find block content
    block_match = re.search(re.escape(sel) + r"\{([^}]+)\}", css)
    block_props = ""
    if block_match:
        props = [p.strip() for p in block_match.group(1).split(";") if p.strip()]
        relevant = [p for p in props if any(k in p for k in ["position", "top", "bottom", "left", "right", "z-index", "overflow", "width", "height"])]
        block_props = "; ".join(relevant)
    print(f"[{pos.upper()}] {sel_clean} -> {block_props}")

# 2. Search for z-index values
print("\n=== 2. Z-INDEX HIERARCHY ===")
z_rules = re.findall(r"([^{}]+)\{[^{}]*?z-index\s*:\s*([0-9]+)[^{}]*?\}", css, re.DOTALL)
z_dict = {}
for sel, z in z_rules:
    sel_clean = " ".join(sel.split())
    z_val = int(z)
    z_dict.setdefault(z_val, []).append(sel_clean)

for z in sorted(z_dict.keys(), reverse=True):
    print(f"z-index: {z} -> {', '.join(z_dict[z][:5])} {'...' if len(z_dict[z]) > 5 else ''}")

# 3. Check Modals
print("\n=== 3. MODAL RULES ===")
modal_matches = re.findall(r"([^{}]*modal[^{}]*)\{([^}]+)\}", css, re.DOTALL | re.IGNORECASE)
for sel, body in modal_matches:
    sel_clean = " ".join(sel.split())
    if any(k in sel_clean.lower() for k in [".modal", "#modal", "modal-box", "modal-overlay", "modal-content", "modal-footer"]):
        body_clean = "; ".join([p.strip() for p in body.split(";") if p.strip() and any(k in p for k in ["height", "overflow", "display", "flex", "position", "z-index", "max-", "padding"])])
        print(f"{sel_clean} -> {body_clean}")

# 4. Check media queries
print("\n=== 4. MEDIA QUERIES ===")
mqs = re.findall(r"@media[^{]+\{", css)
for mq in set(mqs):
    print(mq.strip())

# 5. Check all modals in HTML
print("\n=== 5. MODALS IN HTML ===")
html_modals = re.findall(r'(<div[^>]+id=["\']([^"\']*(?:modal|drawer|popup|overlay)[^"\']*)["\'][^>]*>)', content, re.IGNORECASE)
for tag, mid in html_modals:
    print(f"Modal ID: {mid} -> {tag[:100]}...")

# 6. Check floating buttons / drawers / widgets in HTML
print("\n=== 6. FLOATING / FIXED ELEMENTS IN HTML ===")
fixed_tags = re.findall(r'<[^>]+(?:class|id)=["\'][^"\']*(?:float|drawer|bubble|toast|fixed|dock|banner)[^"\']*["\'][^>]*>', content, re.IGNORECASE)
for t in set(fixed_tags[:15]):
    print(t[:120])
