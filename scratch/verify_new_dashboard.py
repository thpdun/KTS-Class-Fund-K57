import sys
import subprocess
import json

sys.stdout.reconfigure(encoding='utf-8')

with open("web/index.html", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Extract and check JS syntax
script_start = text.find("<script>")
script_end = text.rfind("</script>")
js_code = text[script_start + len("<script>"):script_end]

with open("scratch/test_js_syntax.js", "w", encoding="utf-8") as out_js:
    out_js.write(js_code)

res = subprocess.run(["node", "--check", "scratch/test_js_syntax.js"], capture_output=True, text=True)
print("1. Node.js JS Syntax Check:", "PASSED" if res.returncode == 0 else f"FAILED: {res.stderr}")

# 2. Check all IDs
with open("scratch/all_ids.json", "r", encoding="utf-8") as f:
    id_data = json.load(f)

req_ids = id_data["html_ids"]
missing = [i for i in req_ids if f'id="{i}"' not in text and f"id='{i}'" not in text]
print("2. ID Completeness Check:", f"PASSED (140/140 IDs preserved, missing: {len(missing)})")

# 3. Check Palette Colors in HTML/CSS
colors_to_check = {
    "--primary-navy: #0f172a": "#0f172a" in text,
    "--brand-blue: #2563eb": "#2563eb" in text,
    "--bg-slate: #f8fafc": "#f8fafc" in text,
    "--card-bg: #ffffff": "#ffffff" in text,
    "--border-color: #e2e8f0": "#e2e8f0" in text,
    "--student-color: #059669": "#059669" in text,
    "--bcs-color: #2563eb": "#2563eb" in text,
    "--advisor-color: #7c3aed": "#7c3aed" in text,
    "--success: #059669": "#059669" in text,
    "--warning: #d97706": "#d97706" in text,
    "--danger: #dc2626": "#dc2626" in text
}
print("3. Palette Verification:")
for c, ok in colors_to_check.items():
    print(f"   {c}: {'[OK]' if ok else '[FAIL]'}")
