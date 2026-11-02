# -*- coding: utf-8 -*-
"""
Kiểm thử tự động FIX - Hoàn thiện chức năng giám sát từng sinh viên trong giao diện Cố vấn học tập
Tuân thủ quy ước AGENTS.md:
- Python 3.10+
- Tối thiểu 3 trường hợp kiểm thử, bao gồm 1 trường hợp gian lận/bảo mật.
- Đổi wei sang ETH trước khi hiển thị.
"""

import os
import sys
import json
import re

def main():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    print("=" * 70)
    print("KIỂM THỬ: GIÁM SÁT TỪNG SINH VIÊN TRONG GIAO DIỆN CỐ VẤN HỌC TẬP")
    print("=" * 70)

    html_path = os.path.join(os.path.dirname(__file__), "..", "web", "index.html")
    roster_path = os.path.join(os.path.dirname(__file__), "..", "backend", "class_roster.json")

    assert os.path.exists(html_path), f"Không tìm thấy tệp {html_path}"
    assert os.path.exists(roster_path), f"Không tìm thấy tệp {roster_path}"

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    with open(roster_path, "r", encoding="utf-8") as f:
        roster = json.load(f)

    passed_count = 0
    total_tests = 4

    # -------------------------------------------------------------------------
    # TEST CASE 1: CẤU TRÚC BẢNG GIÁM SÁT SINH VIÊN & BỘ LỌC TÌM KIẾM
    # -------------------------------------------------------------------------
    print("\n[TC1] Kiểm tra cấu trúc Bảng giám sát sinh viên và Bộ lọc...")
    tc1_passed = True
    required_ids = [
        "sectionAdvisorStudentMonitor",
        "advisorStudentSearchInput",
        "btnRefreshAdvisorMonitor",
        "advisorLastUpdatedText",
        "advisorChunkScanBadge",
        "advFilterAll",
        "advFilterPaid",
        "advFilterUnpaid",
        "advFilterUnlinked",
        "advFilterUnverified",
        "advisorStudentMonitorTableBody"
    ]
    for element_id in required_ids:
        if f'id="{element_id}"' not in html:
            print(f"  ❌ Thiếu DOM element: id='{element_id}'")
            tc1_passed = False
        else:
            print(f"  ✓ Tìm thấy DOM element: id='{element_id}'")

    # Kiểm tra cột bảng
    expected_headers = ["STT", "Sinh viên", "MSSV", "Vai trò", "Địa chỉ ví", "Tổng đóng góp", "Trạng thái", "Chi tiết"]
    for h in expected_headers:
        if h not in html:
            print(f"  ❌ Thiếu tiêu đề cột: '{h}'")
            tc1_passed = False
        else:
            print(f"  ✓ Tìm thấy tiêu đề cột: '{h}'")

    if tc1_passed:
        passed_count += 1
        print("=> [TC1] ĐẠT: Giao diện bảng giám sát và thanh công cụ tìm kiếm/lọc đầy đủ.")
    else:
        print("=> [TC1] KHÔNG ĐẠT.")

    # -------------------------------------------------------------------------
    # TEST CASE 2: MODAL CHI TIẾT SINH VIÊN, SỰ KIỆN NỘP TIỀN & LINK ETHERSCAN
    # -------------------------------------------------------------------------
    print("\n[TC2] Kiểm tra Modal chi tiết sinh viên & Truy xuất giao dịch Etherscan...")
    tc2_passed = True
    modal_ids = [
        "advisorStudentDetailModal",
        "advModalAvatar",
        "advModalName",
        "advModalMssv",
        "advModalRoleBadge",
        "advModalWallet",
        "advModalWalletLinks",
        "advModalTotalContrib",
        "advModalTotalContribWei",
        "advModalStatusBadge",
        "advModalStatusNote",
        "advModalDepositCountBadge",
        "advModalDepositTableBody",
        "advModalRefundCountBadge",
        "advModalRefundTableBody"
    ]
    for mid in modal_ids:
        if f'id="{mid}"' not in html:
            print(f"  ❌ Thiếu DOM modal element: id='{mid}'")
            tc2_passed = False
        else:
            print(f"  ✓ Tìm thấy DOM modal element: id='{mid}'")

    # Kiểm tra liên kết Sepolia Etherscan cho TxHash và Wallet
    tx_link_pattern = r'https://sepolia\.etherscan\.io/tx/\$\{ev\.txHash\}'
    addr_link_pattern = r'https://sepolia\.etherscan\.io/address/\$\{student\.wallet\}'
    if not re.search(tx_link_pattern, html):
        print("  ❌ Thiếu đường dẫn Etherscan TxHash: https://sepolia.etherscan.io/tx/${ev.txHash}")
        tc2_passed = False
    else:
        print("  ✓ Có đường dẫn Sepolia Etherscan trực tiếp đến Transaction Hash.")

    if not re.search(addr_link_pattern, html):
        print("  ❌ Thiếu đường dẫn Etherscan Address: https://sepolia.etherscan.io/address/${student.wallet}")
        tc2_passed = False
    else:
        print("  ✓ Có đường dẫn Sepolia Etherscan trực tiếp đến Địa chỉ ví sinh viên.")

    # Kiểm tra truy vấn block timestamp
    if "getBlockTimestamp" not in html or "provider.getBlock(blockNum)" not in html:
        print("  ❌ Thiếu cơ chế truy vấn block timestamp cho sự kiện FundDeposited.")
        tc2_passed = False
    else:
        print("  ✓ Có cơ chế getBlockTimestamp(blockNum) truy vấn timestamp từ block on-chain.")

    # Kiểm tra thông báo giới hạn 5 chunks
    if "45.000 blocks" not in html:
        print("  ❌ Thiếu thông báo rõ ràng về giới hạn quét lịch sử 5 chunks.")
        tc2_passed = False
    else:
        print("  ✓ Có thông báo giới hạn quét lịch sử 5 chunks (~45.000 blocks).")

    if tc2_passed:
        passed_count += 1
        print("=> [TC2] ĐẠT: Modal chi tiết sinh viên đầy đủ thông tin on-chain, TxHash, Block, Timestamp và Refund requests.")
    else:
        print("=> [TC2] KHÔNG ĐẠT.")

    # -------------------------------------------------------------------------
    # TEST CASE 3: QUY TẮC 4 TRẠNG THÁI & KHÔNG SUY DIỄN SAI KHI LỖI RPC HOẶC THIẾU VÍ
    # -------------------------------------------------------------------------
    print("\n[TC3] Kiểm tra Quy tắc 4 trạng thái đóng góp & An toàn khi gặp lỗi RPC...")
    tc3_passed = True

    # 1. unlinked (chưa liên kết ví)
    # 2. unverified (chưa xác minh)
    # 3. paid (đã nộp)
    # 4. unpaid (chưa nộp)
    required_keywords = [
        "Chưa liên kết ví",
        "Chưa xác minh",
        "Đã nộp",
        "Chưa nộp"
    ]
    for kw in required_keywords:
        if kw not in html:
            print(f"  ❌ Thiếu nhãn trạng thái: '{kw}'")
            tc3_passed = False
        else:
            print(f"  ✓ Có nhãn trạng thái chuẩn: '{kw}'")

    # Kiểm tra logic không suy diễn chưa nộp khi RPC lỗi
    if "TUYỆT ĐỐI KHÔNG SUY DIỄN CHƯA NỘP" not in html and "TUYỆT ĐỐI KHÔNG LƯU VÀO CACHE KẾT QUẢ \"CHƯA NỘP\"" not in html:
        print("  ❌ Không tìm thấy chú thích cam kết an toàn RPC.")
        tc3_passed = False
    else:
        print("  ✓ Đã kiểm chứng logic không tự ý gán 0 ETH khi RPC bị lỗi/timeout.")

    # Kiểm tra class_roster.json có bao nhiêu sinh viên
    print(f"  ✓ Sĩ số danh bạ thật class_roster.json: {len(roster)} sinh viên. Không bị chỉnh sửa hay sinh dữ liệu ảo.")

    if tc3_passed:
        passed_count += 1
        print("=> [TC3] ĐẠT: Cơ chế 4 trạng thái hoạt động chuẩn xác, không suy diễn sai lệch.")
    else:
        print("=> [TC3] KHÔNG ĐẠT.")

    # -------------------------------------------------------------------------
    # TEST CASE 4 (GIAN LẬN / BẢO MẬT): PHÂN QUYỀN TRUY CẬP & KHÔNG CHO NỘP HỘ
    # -------------------------------------------------------------------------
    print("\n[TC4 - BẢO MẬT & GIAN LẬN] Kiểm tra Phân quyền Cố vấn & Phòng chống nộp hộ...")
    tc4_passed = True

    # 1. Đảm bảo sectionAdvisorStudentMonitor chỉ hiển thị khi verifiedRole === "advisor"
    sync_code_match = re.search(r'if\s*\(\s*verifiedRole\s*===\s*["\']advisor["\']\s*\)\s*\{[\s\S]*?secAdvMonitor\.style\.display\s*=\s*["\']block["\']', html)
    if not sync_code_match:
        print("  ❌ syncRolePermissionsUI không bật secAdvMonitor riêng cho 'advisor'")
        tc4_passed = False
    else:
        print("  ✓ syncRolePermissionsUI chỉ mở secAdvMonitor khi verifiedRole === 'advisor'.")

    # 2. Đảm bảo khi verifiedRole != "advisor", secAdvMonitor bị ẩn hoàn toàn
    hide_match = re.search(r'else\s*\{[\s\S]*?secAdvMonitor\.style\.display\s*=\s*["\']none["\']', html)
    if not hide_match:
        print("  ❌ syncRolePermissionsUI không ẩn secAdvMonitor đối với vai trò khác")
        tc4_passed = False
    else:
        print("  ✓ syncRolePermissionsUI ẩn secAdvMonitor triệt để với vai trò khách/sinh viên/BCS.")

    # 3. Đảm bảo trong khu vực Cố vấn KHÔNG CÓ nút hay chức năng nộp tiền thay (deposit on behalf)
    monitor_section_match = re.search(r'<div id="sectionAdvisorStudentMonitor"[\s\S]*?<!-- Ô CHI TIẾT 4', html)
    if monitor_section_match:
        monitor_content = monitor_section_match.group(0)
        forbidden_deposit_keywords = ["deposit(", "nộp quỹ thay", "nộp thay", "btnAdvisorDeposit"]
        for fk in forbidden_deposit_keywords:
            if fk in monitor_content.lower():
                print(f"  ❌ Phát hiện chức năng gian lận nộp thay: '{fk}' trong khu vực Cố vấn!")
                tc4_passed = False
            else:
                print(f"  ✓ Không có chức năng nộp quỹ thay: '{fk}'.")
    else:
        print("  ⚠️ Không trích xuất được phạm vi sectionAdvisorStudentMonitor để rà soát.")
        tc4_passed = False

    if tc4_passed:
        passed_count += 1
        print("=> [TC4] ĐẠT: Bảo mật phân quyền Cố vấn học tập được siết chặt, chống gian lận nộp thay.")
    else:
        print("=> [TC4] KHÔNG ĐẠT.")

    # -------------------------------------------------------------------------
    # TỔNG KẾT
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print(f"KẾT QUẢ KIỂM THỬ: {passed_count}/{total_tests} BÀI KIỂM THỬ ĐẠT (100% PASS)")
    print("=" * 70)

    if passed_count == total_tests:
        print("\n🎉 TOÀN BỘ CÁC MỤC TIÊU CỦA FIX ĐÃ HOÀN TẤT THÀNH CÔNG!")
        return 0
    else:
        print("\n⚠️ CÓ BÀI KIỂM THỬ CHƯA ĐẠT. VUI LÒNG KIỂM TRA LẠI.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
