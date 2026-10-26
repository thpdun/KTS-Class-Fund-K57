import re
import json

def check_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # The main inline script is near the bottom
    script_pos = content.rfind("<script>")
    html_part = content[:script_pos]
    js_part = content[script_pos:]

    html_ids = set(re.findall(r'id=["\']([a-zA-Z0-9_\-]+)["\']', html_part))
    js_ids = set(re.findall(r'getElementById\(["\']([a-zA-Z0-9_\-]+)["\']\)', js_part))

    print(f"=== {filepath} ===")
    print(f"HTML IDs count: {len(html_ids)}")
    print(f"JS accessed IDs count: {len(js_ids)}")
    missing = js_ids - html_ids
    print(f"Missing in HTML: {missing}")
    return html_ids, js_ids

if __name__ == "__main__":
    check_file("web/index.html")
    check_file("web/index.html.bak")
