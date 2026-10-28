import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open("web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

idx = html.find('id="walletBtnText"')
print("=== walletBtnText in HTML ===")
print(html[idx-100:idx+200])

idx_btn = html.find('id="btnConnectWallet"')
print("=== btnConnectWallet in HTML ===")
print(html[idx_btn-50:idx_btn+250])
