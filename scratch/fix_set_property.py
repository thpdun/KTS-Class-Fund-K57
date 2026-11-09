with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

html = html.replace("p.style.setProperty('display', 'none', 'important')", "p.style.display = 'none'")
html = html.replace("pStudent.style.setProperty('display', 'block', 'important')", "pStudent.style.display = 'block'")
html = html.replace("pBCS.style.setProperty('display', 'block', 'important')", "pBCS.style.display = 'block'")
html = html.replace("pAdvisor.style.setProperty('display', 'block', 'important')", "pAdvisor.style.display = 'block'")
html = html.replace("pHistory.style.setProperty('display', 'block', 'important')", "pHistory.style.display = 'block'")

with open('web/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Replaced setProperty with style.display in web/index.html!")

