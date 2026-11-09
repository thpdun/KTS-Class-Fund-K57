import subprocess

out = subprocess.check_output(['git', 'diff', '2facdcc', '03c512b', 'web/index.html'], text=True)
print(out[:3000])

