import re
import sys

with open("web/index.html", "r", encoding="utf-8") as f:
    content = f.read()

required_target_ids = [
    "panelStudent",
    "panelBCS",
    "panelAdvisor",
    "panelHistory",
    "aiChatDrawer",
    "aiFabToggle",
    "btnDepositAction",
    "btnCreateRefundAction",
    "btnCreateSpendAction",
    "btnWithdrawFeeAction",
    "btnSetBcsAction"
]

stage2_new_ids = [
    "sectionDepositForm",
    "sectionRefundForm",
    "noticeStudentNeedWallet",
    "noticeStudentGuest",
    "noticeStudentAdvisorView",
    "sectionBcsCreateSpend",
    "noticeBcsRestricted",
    "noticeBcsRestrictedContent",
    "sectionAdvisorManageBcs",
    "sectionAdvisorWithdrawFee",
    "noticeAdvisorRestricted",
    "noticeAdvisorRestrictedContent"
]

found_ids = set(re.findall(r'id=["\']([^"\']+)["\']', content))

all_ok = True
print("--- CHECKING 11 TARGET IDs ---")
for tid in required_target_ids:
    if tid in found_ids:
        print(f"[OK] Found target ID: #{tid}")
    else:
        print(f"[ERROR] Missing target ID: #{tid}")
        all_ok = False

print("\n--- CHECKING STAGE 2 WRAPPER & NOTICE IDs ---")
for nid in stage2_new_ids:
    if nid in found_ids:
        print(f"[OK] Found Stage 2 ID: #{nid}")
    else:
        print(f"[ERROR] Missing Stage 2 ID: #{nid}")
        all_ok = False

if not all_ok:
    sys.exit(1)
print(f"\nAll {len(required_target_ids)} target IDs and {len(stage2_new_ids)} Stage 2 IDs verified successfully!")
