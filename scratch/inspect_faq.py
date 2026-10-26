import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("web/index.html", "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find('id="faq"')
print("FAQ section pos:", pos)
print(text[pos-100:pos+1500])

# Also check how faqAccordionContainer is populated in JS
js_pos = text.find('faqAccordionContainer')
while js_pos != -1:
    print(f"\n--- faqAccordionContainer at {js_pos} ---")
    print(text[js_pos-100:js_pos+500])
    js_pos = text.find('faqAccordionContainer', js_pos + 1)
