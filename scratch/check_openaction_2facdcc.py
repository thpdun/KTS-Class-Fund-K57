import subprocess
out = subprocess.check_output(['git', 'show', '2facdcc:web/index.html'], text=True)
import re
match = re.search(r'function openActionModal\(action\)\s*\{([\s\S]*?)\n    \}', out)
if match:
    print(match.group(0))

