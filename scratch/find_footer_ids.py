import re

with open("web/index.html", "r", encoding="utf-8") as f:
    text = f.read()

footer_match = re.search(r"<footer.*?</footer>", text, re.DOTALL)
if footer_match:
    footer_text = footer_match.group(0)
    ids = re.findall(r'id=["\'](.*?)["\']', footer_text)
    print("IDs in footer:", ids)
else:
    print("Footer not found")

