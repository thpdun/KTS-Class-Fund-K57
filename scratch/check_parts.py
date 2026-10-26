import os
import re
import json

def generate_redesign():
    with open("web/index.html.bak", "r", encoding="utf-8") as f:
        original = f.read()

    # Locate the <script> block and extract everything from <script> to </script>
    script_start = original.find("<script>")
    script_end = original.rfind("</script>") + len("</script>")
    js_code = original[script_start:script_end]

    # Check for AI Chat widget markup which was after </script>
    ai_widget_start = original.find('<div class="ai-fab-container"', script_end)
    ai_widget_end = original.find('</body>', ai_widget_start)
    ai_widget_html = original[ai_widget_start:ai_widget_end].strip()

    print(f"Original JS length: {len(js_code)} chars")
    print(f"AI Widget HTML length: {len(ai_widget_html)} chars")

if __name__ == "__main__":
    generate_redesign()
