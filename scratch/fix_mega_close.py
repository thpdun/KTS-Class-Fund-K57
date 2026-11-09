with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

target = """              </div>
            </div>

        <!-- 4. Sổ quỹ (link trực tiếp) -->"""

replacement = """              </div>
            </div>
          </div>
        </div>

        <!-- 4. Sổ quỹ (link trực tiếp) -->"""

if target in html:
    html = html.replace(target, replacement, 1)
    with open('web/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Fixed missing closing divs for mega menu!")
else:
    print("Target not found!")

