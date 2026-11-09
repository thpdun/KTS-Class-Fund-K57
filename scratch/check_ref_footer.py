import re

with open("web/design-reference/kts-home.html", "r", encoding="utf-8") as f:
    text = f.read()

footer_match = re.search(r"<footer.*?</footer>", text, re.DOTALL)
if footer_match:
    print(footer_match.group(0))
else:
    print("No footer tag found in kts-home.html")
    # let's search for footer class or id
    matches = re.findall(r".{0,50}footer.{0,50}", text, re.IGNORECASE)
    for m in matches[:5]:
        print("Match:", m)

