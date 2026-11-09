import subprocess
res = subprocess.run(["git", "log", "-S", "FLOW 1: THU NẠP QUỸ", "--oneline"], capture_output=True, text=True)
print(res.stdout)

