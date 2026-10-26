import sys
import re
sys.stdout.reconfigure(encoding='utf-8')

with open("web/index.html", "r", encoding="utf-8") as f:
    text = f.read()

# Look for workflow sections and governance steps
sec_workflow = text[text.find('id="workflow"'):text.find('</section>', text.find('id="workflow"'))]
print("Workflow classes:")
print(re.findall(r'class="([^"]+)"', sec_workflow))

sec_gov = text[text.find('id="governance"'):text.find('</section>', text.find('id="governance"'))]
print("Gov classes:")
print(re.findall(r'class="([^"]+)"', sec_gov))

sec_eco = text[text.find('id="economics"'):text.find('</section>', text.find('id="economics"'))]
print("Eco classes:")
print(re.findall(r'class="([^"]+)"', sec_eco))
