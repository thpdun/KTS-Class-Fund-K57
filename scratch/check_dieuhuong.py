with open('web/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = re.findall(r'.*Điều Hướng.*', text)
print("Matches in web/index.html:")
for m in matches:
    print(m)

matches2 = re.findall(r'.*Mạng Thử Nghiệm.*', text)
print("\nMatches for Mạng Thử Nghiệm:")
for m in matches2:
    print(m)

