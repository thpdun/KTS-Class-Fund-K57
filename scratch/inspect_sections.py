import re
import sys
import json

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

m_script = re.search(r'<script(?![^>]*src=)[^>]*>', html)
idx_script = m_script.start()
markup = html[:idx_script]
script = html[idx_script:]

# Check FAQ_DATA
idx_faq = script.find('const FAQ_DATA')
if idx_faq != -1:
    end_faq = script.find('];', idx_faq)
    faq_block = script[idx_faq:end_faq+2]
    # find question objects
    q_matches = re.findall(r'question:\s*["\']([^"\']+)["\']', faq_block)
    cat_matches = re.findall(r'cat:\s*["\']([^"\']+)["\']', faq_block)
    print(f"Total FAQs found in FAQ_DATA: {len(q_matches)}")
    print(f"Categories found: {set(cat_matches)}")
    for i, q in enumerate(q_matches):
        print(f"  {i+1}. [{cat_matches[i] if i < len(cat_matches) else '?'}] {q}")

print("\n--- CHECKING CSS VARIABLES & CLASSES ---")
css_vars = re.findall(r'--[a-zA-Z0-9_-]+', html)
print(f"Total CSS variable usages/declarations: {len(css_vars)} (Unique: {len(set(css_vars))})")

# Check specifically --purple-role, --purple-bg, .btn-warning
print("Has --purple-role:", "--purple-role" in html)
print("Has --purple-bg:", "--purple-bg" in html)
print("Has .btn-warning:", ".btn-warning" in html)

# Check all sections in markup
print("\n--- ALL SECTIONS IN MARKUP ---")
sections = re.findall(r'<(section|aside|footer|header|nav)[^>]*id="([^"]+)"[^>]*>', markup)
for tag, sid in sections:
    print(f"<{tag} id=\"{sid}\">")
