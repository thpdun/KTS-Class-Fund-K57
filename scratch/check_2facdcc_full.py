import subprocess
res = subprocess.run(["git", "show", "2facdcc:web/index.html"], capture_output=True, text=True)
import re
m = re.search(r'function openActionModal\(action\).*?function closeActionModal', res.stdout, re.DOTALL)
if m:
    print(m.group(0))

