import subprocess
res = subprocess.run(["git", "show", "03c512b~1:web/index.html"], capture_output=True, text=True)
import re
m = re.search(r'function openActionModal\(action\).*?function ', res.stdout, re.DOTALL)
if m:
    print(m.group(0)[:1500])

