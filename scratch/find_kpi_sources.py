import re
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

kpi_ids = [
    "metricClassFund",
    "metricAdminFee",
    "metricDepositorsCount",
    "metricSpendCount",
    "metricRefundCount",
    "metricActiveBCS"
]

for kid in kpi_ids:
    print(f"\n--- SEARCHING FOR {kid} ---")
    for m in re.finditer(rf'.{{0,100}}{kid}.{{0,100}}', html):
        # only lines in script
        print("  ...", m.group(0).strip().replace('\n', ' '))
