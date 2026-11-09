import subprocess
res = subprocess.run(["git", "show", "b04fb91:web/index.html"], capture_output=True, text=True)
lines = res.stdout.splitlines()
for i, l in enumerate(lines):
    if '<footer' in l:
        print('\n'.join(lines[max(0, i-20):min(len(lines), i+30)]))
        break

