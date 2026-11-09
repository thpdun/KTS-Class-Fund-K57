import os

matches = []
for root, dirs, files in os.walk('.'):
    if '.git' in root:
        continue
    for f in files:
        if f.endswith(('.html', '.js', '.css')):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                for line_no, line in enumerate(fp):
                    if 'Mỗi luồng tiền' in line:
                        matches.append(f"{path}:{line_no+1}: {line.strip()[:100]}")

print('\n'.join(matches))

