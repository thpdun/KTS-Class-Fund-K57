import subprocess
res = subprocess.run(["git", "diff", "03c512b~1..03c512b", "--", "web/index.html"], capture_output=True, text=True)
lines = [l for l in res.stdout.splitlines() if 'openActionModal' in l or 'flow-steps' in l or 'spend' in l][:40]
print('\n'.join(lines))

