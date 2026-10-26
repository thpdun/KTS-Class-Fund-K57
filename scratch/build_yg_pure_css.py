import os
import re
import json
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("=== BUILDING YG EDITORIAL DASHBOARD VIA COMPLETE CSS UPGRADE ===")

    with open("web/index.html.bak", "r", encoding="utf-8") as f:
        orig = f.read()

    # Load required IDs
    with open("scratch/all_ids.json", "r", encoding="utf-8") as f:
        id_data = json.load(f)
    required_ids = id_data["html_ids"]

    # Locate parts of index.html.bak
    # 1. <head> up to <style>
    style_start = orig.find("<style>")
    head_prefix = orig[:style_start]

    # 2. </style> down to <body>
    style_end = orig.find("</style>") + len("</style>")
    
    # 3. Everything inside <body>
    body_content = orig[style_end:]

    # Import our YG Editorial CSS
    from yg_css_complete import get_yg_editorial_css
    yg_css = get_yg_editorial_css()

    # Build new index.html
    new_html = head_prefix + "<style>\n" + yg_css + "\n  </style>" + body_content

    with open("web/index.html", "w", encoding="utf-8") as f:
        f.write(new_html)

    print(f"Written web/index.html: {len(new_html)} bytes.")

    # Validate IDs
    new_html_ids = set(re.findall(r'id=["\']([a-zA-Z0-9_\-]+)["\']', new_html))
    missing = [rid for rid in required_ids if rid not in new_html_ids]
    print(f"Total HTML IDs in new file: {len(new_html_ids)}")
    print(f"Missing required IDs: {missing}")

    return len(missing) == 0

if __name__ == "__main__":
    main()
