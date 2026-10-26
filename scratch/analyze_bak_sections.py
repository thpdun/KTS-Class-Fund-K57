import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

with open('web/index.html.bak', 'r', encoding='utf-8') as f:
    text = f.read()

script_pos = text.find('<script>')
html_body = text[:script_pos]

sections = re.findall(r'<section[^>]*id=["\']([^"\']+)["\']', html_body)
print("Sections found:", sections)

# Search for the IDs that were reported missing
missing_ids = [
    'advisorFeePoolBalance', 'bcsRefundTableBody', 'bcsSpendTableBody',
    'btnCreateRefundAction', 'btnCreateSpendAction', 'btnDepositAction',
    'btnOpenAnnModal', 'btnOpenRosterModal', 'btnQuickDisconnect',
    'btnQuickSwitch', 'btnResetQuickContract', 'btnSetBcsAction',
    'btnWithdrawFeeAction', 'flowBalAdminFee', 'flowBalClassFund',
    'flowBalExecutedCount', 'flowBalExecutedSpend', 'flowBalReserved',
    'flowFilterGroup', 'flowLedgerTableBody', 'flowLinkEtherscan', 'hero',
    'inputBcsAddress', 'inputDepositAmount', 'inputRefundAmount',
    'inputRefundReason', 'inputSpendAmount', 'inputSpendDesc',
    'inputSpendRecipient', 'inputWithdrawFeeAmount', 'itemRosterModalBtn',
    'metricActiveBCS', 'metricActiveBCSNote', 'metricAdminFeeNote',
    'metricClassFundNote', 'metricDepositorsCount', 'metricDepositorsNote',
    'myAvailableRefund', 'myPendingRefund', 'myTotalContribution',
    'quickNetworkStatus', 'quickRoleBadge', 'quickStudentIdentity',
    'quickWalletAccount', 'roleDetailContainer', 'roleDetailHint',
    'rosterCountBadge', 'selectBcsStatus', 'studentRefundTableBody',
    'walletBtnText'
]

print("\nWhere are missing IDs located in index.html.bak?")
for mid in missing_ids[:15]:
    pos = text.find(mid)
    if pos != -1:
        line_num = text[:pos].count('\n') + 1
        print(f"  {mid}: line {line_num}")
    else:
        print(f"  {mid}: NOT FOUND AT ALL in index.html.bak")
