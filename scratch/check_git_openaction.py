import subprocess
res = subprocess.run(["git", "log", "-S", "openActionModal", "--oneline"], capture_output=True, text=True)
print(res.stdout)

