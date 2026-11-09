import re

patterns = [
    r'rút phí',
    r'Rút phí',
    r'withdrawAdminFee',
    r'AdminFeeWithdrawn',
    r'Bù đắp gas cho Cố vấn',
    r'100% tiền gốc',
    r'tổng số Ban cán sự',
    r'đang hoạt động',
    r'Không tự động chuyển tiền',
    r'đạt ngưỡng có tự động',
    r'Cố vấn \(Duyệt'
]

with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines, 1):
    for pat in patterns:
        if re.search(pat, line, re.IGNORECASE):
            print(f"L{idx} [{pat}]: {line.strip()[:110]}")
            break

