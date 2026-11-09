import subprocess
res = subprocess.run(["git", "log", "-S", "Điều Hướng", "--oneline"], capture_output=True, text=True)
print(res.stdout)

