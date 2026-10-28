import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

m = re.search(r'(<table[^>]*>.*?flowLedgerTableBody.*?</table>)', html, re.DOTALL)
if m:
    print("Found flowLedgerTable:")
    print(m.group(1)[:2000])
else:
    # search where flowLedgerTableBody is
    idx = html.find("flowLedgerTableBody")
    print(html[idx-500:idx+500])
