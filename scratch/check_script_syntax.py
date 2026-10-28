import subprocess
import re

with open("web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

m = re.findall(r'<script(?:\s+type="[^"]*")?>([\s\S]*?)</script>', html)
for idx, s in enumerate(m):
    if len(s.strip()) > 100:
        filename = f"scratch/extracted_script_{idx}.js"
        with open(filename, "w", encoding="utf-8") as out:
            out.write(s)
        res = subprocess.run(["node", "-c", filename], capture_output=True, text=True)
        print(f"Script {idx}: returncode = {res.returncode}")
        if res.returncode != 0:
            print("ERROR STDOUT:\n", res.stdout)
            print("ERROR STDERR:\n", res.stderr)
        else:
            print("Syntax OK!")
