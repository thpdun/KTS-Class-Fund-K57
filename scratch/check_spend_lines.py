import subprocess
res = subprocess.run(["git", "diff", "03c512b~1..03c512b", "--", "web/index.html"], capture_output=True, text=True)
lines = res.stdout.splitlines()
for i, l in enumerate(lines):
    if 'action === "spend"' in l:
        print('\n'.join(lines[i-5:i+35]))
        break

