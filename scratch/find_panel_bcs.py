with open('web/index.html', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'id="panelBCS"' in line:
            print(f"panelBCS: {i+1}")
        if 'id="panelAdvisor"' in line:
            print(f"panelAdvisor: {i+1}")
        if 'id="sectionBcsCreateSpend"' in line:
            print(f"sectionBcsCreateSpend: {i+1}")
        if 'id="bcsSpendTableBody"' in line:
            print(f"bcsSpendTableBody: {i+1}")
        if 'id="bcsRefundTableBody"' in line:
            print(f"bcsRefundTableBody: {i+1}")

