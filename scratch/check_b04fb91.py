import subprocess
res = subprocess.run(["git", "show", "b04fb91", "--stat"], capture_output=True, text=True)
print(res.stdout)
res2 = subprocess.run(["git", "diff", "b04fb91~1..b04fb91", "--", "web/index.html"], capture_output=True, text=True)
lines = [l for l in res2.stdout.splitlines() if 'openActionModal' in l or 'flow-steps' in l or 'spend' in l][:40]
print('\n'.join(lines))

