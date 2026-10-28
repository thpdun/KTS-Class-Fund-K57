import re
import subprocess
import sys

with open("web/index.html", "r", encoding="utf-8") as f:
    content = f.read()

scripts = re.findall(r'<script(?![^>]*src=)[^>]*>(.*?)</script>', content, re.DOTALL)
print(f"Found {len(scripts)} inline script tags")

for idx, script in enumerate(scripts):
    filename = f"scratch/test_inline_script_{idx}.js"
    with open(filename, "w", encoding="utf-8") as out:
        out.write(script)
    print(f"Saved {filename} ({len(script)} chars)")
    res = subprocess.run(["node", "-c", filename], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"SYNTAX ERROR in script {idx}:")
        print(res.stderr)
        sys.exit(1)
    else:
        print(f"Script {idx}: SYNTAX OK!")

print("All scripts passed node syntax check!")
