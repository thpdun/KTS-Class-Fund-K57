# -*- coding: utf-8 -*-
"""
Deep inspection of modals, forms, tables, and buttons
"""
import sys
import re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open("web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1. Inspect all modal markup
print("=== 1. MODAL STRUCTURES IN HTML ===")
modal_matches = re.findall(r'(<div[^>]*class=["\'][^"\']*modal-overlay[^"\']*["\'][^>]*>)(.*?)(<!--\s*/modal|\Z)', html, re.DOTALL | re.IGNORECASE)
for open_tag, modal_inner, _ in modal_matches:
    mid = re.search(r'id=["\']([^"\']+)["\']', open_tag)
    mid_str = mid.group(1) if mid else "unknown"
    print(f"\n--- MODAL: {mid_str} ---")
    print(f"Tag: {open_tag}")
    
    # Check if modal-box exists and its styles
    mbox = re.search(r'(<div[^>]*class=["\'][^"\']*modal-box[^"\']*["\'][^>]*>)', modal_inner)
    if mbox:
        print(f"Modal box tag: {mbox.group(1)}")
    
    # Check footer or action buttons inside this modal
    buttons = re.findall(r'(<button[^>]*>.*?</button>)', modal_inner, re.DOTALL)
    print(f"Buttons inside ({len(buttons)}):")
    for b in buttons:
        b_clean = " ".join(b.split())
        print(f"  {b_clean[:120]}")

# 2. Inspect Announcement Card markup
print("\n=== 2. ANNOUNCEMENT CARD & HISTORY CARD MARKUP ===")
ann_card = re.search(r'(<div[^>]*id=["\']classAnnouncementCard["\'][^>]*>.*?</div>\s*</div>\s*</div>)', html, re.DOTALL)
if ann_card:
    print("Found classAnnouncementCard:")
    ann_lines = [l.strip() for l in ann_card.group(1).split("\n") if "<button" in l or "class=" in l][:15]
    for l in ann_lines:
        print("  ", l[:120])

ann_hist = re.search(r'(<div[^>]*id=["\']announcementHistoryCard["\'][^>]*>.*?</div>\s*</div>)', html, re.DOTALL)
if ann_hist:
    print("\nFound announcementHistoryCard header/buttons:")
    hist_lines = [l.strip() for l in ann_hist.group(1).split("\n") if "<button" in l or "id=" in l][:10]
    for l in hist_lines:
        print("  ", l[:120])

# 3. Inspect Quick Status Bar
print("\n=== 3. QUICK STATUS BAR MARKUP ===")
quick_bar = re.search(r'(<div[^>]*class=["\'][^"\']*quick-status-bar[^"\']*["\'][^>]*>.*?</div>\s*</div>\s*</div>)', html, re.DOTALL)
if quick_bar:
    print("Quick status bar elements:")
    for l in quick_bar.group(1).split("\n")[:20]:
        if "id=" in l or "class=" in l:
            print("  ", l.strip()[:120])

# 4. Inspect Tables and action buttons inside tables
print("\n=== 4. TABLES IN HTML ===")
tables = re.findall(r'(<table[^>]*>.*?</table>)', html, re.DOTALL)
print(f"Total <table> elements in HTML: {len(tables)}")
for i, t in enumerate(tables):
    tid = re.search(r'id=["\']([^"\']+)["\']', t)
    tcls = re.search(r'class=["\']([^"\']+)["\']', t)
    print(f"Table {i+1}: id='{tid.group(1) if tid else ''}' class='{tcls.group(1) if tcls else ''}'")
