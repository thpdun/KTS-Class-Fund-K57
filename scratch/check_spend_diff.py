import subprocess
res = subprocess.run(["git", "diff", "03c512b~1..03c512b", "--", "web/index.html"], capture_output=True, text=True)
import re
m = re.search(r'action === "spend".*', res.stdout)
if m:
    print(res.stdout[m.start()-100:m.start()+800])

