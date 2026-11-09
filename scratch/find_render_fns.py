with open('web/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
fns = ['renderPendingActions', 'renderMultipleProgressCards', 'updateTopRoleBadge', 'updateUIOnDisconnect', 'renderFlowLedgerTable']
for fn in fns:
    m = re.search(r'function\s+' + fn + r'\s*\([^)]*\)\s*\{', text)
    if m:
        start = m.start()
        print(f"Found {fn} at index {start}")
    else:
        print(f"NOT found {fn}")

