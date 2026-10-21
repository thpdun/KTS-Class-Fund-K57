#!/usr/bin/env python3
"""
Bộ kiểm thử quy tắc kinh tế R2 cho Hợp đồng Quản lý Quỹ lớp (KTS-Class-Fund)
Tuân thủ quy ước AGENTS.md:
- Python 3.10+
- Không ghi khóa API trong mã nguồn
- Kiểm tra trạng thái phản hồi trước khi xử lý dữ liệu
- Đổi wei sang ETH trước khi hiển thị
- Tối thiểu 3 trường hợp kiểm thử, gồm 1 trường hợp gian lận
"""

import sys
import unittest
from typing import Tuple

# Đảm bảo in tiếng Việt chuẩn trên Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Hằng số kinh tế theo đặc tả docs/SPEC.md và ProjectCore.sol
FEE_BPS = 100               # 1% = 100 basis points
BPS_DENOMINATOR = 10_000     # 100% = 10,000 basis points
WEI_PER_ETH = 10**18


def wei_to_eth(wei_amount: int) -> float:
    """Đổi wei sang ETH trước khi hiển thị theo quy tắc AGENTS.md"""
    return wei_amount / WEI_PER_ETH


class CustomError(Exception):
    """Lỗi tùy biến mô phỏng revert custom error của Solidity"""
    pass


class ZeroAmountError(CustomError):
    """Mô phỏng custom error ZeroAmount() trong ProjectCore.sol"""
    pass


class ProjectCoreSimulator:
    """
    Lớp mô phỏng chính xác logic nghiệp vụ của hợp đồng ProjectCore.sol
    Phục vụ kiểm thử tự động quy tắc kinh tế độc lập với môi trường node/chain
    """
    def __init__(self, advisor: str):
        self.advisor = advisor
        self.class_fund_balance = 0
        self.admin_fee_pool = 0
        self.student_contributions = {}
        self.emitted_events = []

    def _process_deposit(self, sender: str, amount_wei: int) -> Tuple[int, int]:
        # 1. Checks: Từ chối nếu amount == 0
        if amount_wei == 0:
            raise ZeroAmountError("Revert: ZeroAmount()")

        # 2. Phân bổ số nguyên theo basis points (R2)
        admin_fee = (amount_wei * FEE_BPS) // BPS_DENOMINATOR
        class_fund_amount = amount_wei - admin_fee

        # 3. Effects: Cập nhật trạng thái
        current_contrib = self.student_contributions.get(sender, 0)
        self.student_contributions[sender] = current_contrib + amount_wei
        self.class_fund_balance += class_fund_amount
        self.admin_fee_pool += admin_fee

        # 4. Phát sự kiện
        self.emitted_events.append(("FundDeposited", sender, amount_wei))
        self.emitted_events.append(("AdminFeeCollected", sender, admin_fee))

        return class_fund_amount, admin_fee

    def deposit(self, sender: str, amount_wei: int) -> Tuple[int, int]:
        """Mô phỏng hàm deposit() external payable"""
        return self._process_deposit(sender, amount_wei)

    def receive(self, sender: str, amount_wei: int) -> Tuple[int, int]:
        """Mô phỏng hàm receive() external payable"""
        return self._process_deposit(sender, amount_wei)

    def get_fund_balance(self) -> int:
        """Tra cứu số dư khả dụng Quỹ lớp chính"""
        return self.class_fund_balance

    def get_total_contract_balance(self) -> int:
        """Tra cứu tổng số dư hợp đồng (Quỹ chính + adminFeePool)"""
        return self.class_fund_balance + self.admin_fee_pool

    def get_student_contribution(self, student: str) -> int:
        """Tra cứu tổng số tiền đã đóng góp của sinh viên"""
        return self.student_contributions.get(student, 0)


class TestProjectCoreEconomicRules(unittest.TestCase):
    """Bộ ca kiểm thử tự động quy tắc kinh tế Lab 11"""

    def setUp(self):
        self.advisor = "0xAdvisorAddress000000000000000000000001"
        self.student_a = "0xStudentA00000000000000000000000000000002"
        self.student_b = "0xStudentB00000000000000000000000000000003"
        self.attacker = "0xAttacker00000000000000000000000000000009"
        self.contract = ProjectCoreSimulator(advisor=self.advisor)

    def test_case_1_valid_deposit_1_eth(self):
        """
        Ca 1 – Hợp lệ:
        Sinh viên nạp 1 ETH (10^18 wei):
        - Quỹ lớp chính tăng 0.99 ETH (99 * 10^16 wei)
        - adminFeePool tăng 0.01 ETH (10^16 wei)
        - studentContributions tăng 1.0 ETH
        - Sự kiện phát ra đúng
        - Tổng hai quỹ bảo toàn chính xác 1.0 ETH
        """
        deposit_amount_wei = 1 * WEI_PER_ETH
        initial_main = self.contract.get_fund_balance()
        initial_admin = self.contract.admin_fee_pool

        class_fund_amount, admin_fee = self.contract.deposit(self.student_a, deposit_amount_wei)

        # Kiểm tra tính toán phân bổ 99% / 1%
        expected_fee_wei = 10**16        # 0.01 ETH
        expected_class_wei = 99 * 10**16  # 0.99 ETH

        self.assertEqual(admin_fee, expected_fee_wei)
        self.assertEqual(class_fund_amount, expected_class_wei)

        # Kiểm tra trạng thái quỹ
        self.assertEqual(self.contract.get_fund_balance() - initial_main, expected_class_wei)
        self.assertEqual(self.contract.admin_fee_pool - initial_admin, expected_fee_wei)
        self.assertEqual(self.contract.get_student_contribution(self.student_a), deposit_amount_wei)

        # Kiểm tra bảo toàn tổng tiền
        total_contract = self.contract.get_total_contract_balance()
        self.assertEqual(total_contract, deposit_amount_wei)

        # Đổi wei sang ETH trước khi hiển thị (theo AGENTS.md)
        print("\n[Ca 1 - Thành công]")
        print(f"  + Nạp vào: {wei_to_eth(deposit_amount_wei):.4f} ETH")
        print(f"  + Quỹ lớp chính nhận (99%): {wei_to_eth(self.contract.get_fund_balance()):.4f} ETH")
        print(f"  + Quỹ adminFeePool nhận (1%): {wei_to_eth(self.contract.admin_fee_pool):.4f} ETH")
        print(f"  + Đóng góp ghi nhận: {wei_to_eth(self.contract.get_student_contribution(self.student_a)):.4f} ETH")
        print(f"  + Tổng số dư hợp đồng: {wei_to_eth(total_contract):.4f} ETH")

    def test_case_2_zero_amount_violation(self):
        """
        Ca 2 – Vi phạm:
        Tài khoản gọi deposit() với 0 ETH:
        - Giao dịch bị revert với ZeroAmountError
        - Không có bất kỳ thay đổi trạng thái nào được lưu
        """
        initial_main = self.contract.get_fund_balance()
        initial_admin = self.contract.admin_fee_pool
        initial_events_count = len(self.contract.emitted_events)

        with self.assertRaises(ZeroAmountError):
            self.contract.deposit(self.student_a, 0)

        # Xác nhận trạng thái được giữ nguyên sau khi revert
        self.assertEqual(self.contract.get_fund_balance(), initial_main)
        self.assertEqual(self.contract.admin_fee_pool, initial_admin)
        self.assertEqual(len(self.contract.emitted_events), initial_events_count)
        self.assertEqual(self.contract.get_student_contribution(self.student_a), 0)

        print("\n[Ca 2 - Chặn vi phạm]")
        print("  + Giao dịch gửi 0 ETH đã bị từ chối thành công bằng lỗi ZeroAmount")
        print("  + Trạng thái hợp đồng giữ nguyên hoàn toàn (Không lưu vết số dư rác)")

    def test_case_3_direct_receive_path(self):
        """
        Ca 3 – Kiểm tra đường nạp trực tiếp qua receive():
        Chuyển 0.5 ETH trực tiếp vào hợp đồng:
        - Tiền phân bổ đúng tỷ lệ 99% / 1% như deposit()
        - Số dư đóng góp và sự kiện được ghi nhận nhất quán
        """
        amount_wei = 5 * 10**17  # 0.5 ETH
        class_fund, fee = self.contract.receive(self.student_b, amount_wei)

        expected_fee = amount_wei * 100 // 10_000        # 0.005 ETH
        expected_class = amount_wei - expected_fee         # 0.495 ETH

        self.assertEqual(fee, expected_fee)
        self.assertEqual(class_fund, expected_class)
        self.assertEqual(self.contract.get_student_contribution(self.student_b), amount_wei)

        print("\n[Ca 3 - Kênh nạp trực tiếp receive()]")
        print(f"  + Nạp trực tiếp: {wei_to_eth(amount_wei):.4f} ETH")
        print(f"  + Phân bổ Quỹ lớp (99%): {wei_to_eth(class_fund):.4f} ETH")
        print(f"  + Phân bổ adminFeePool (1%): {wei_to_eth(fee):.4f} ETH")

    def test_case_4_integer_math_and_small_amounts(self):
        """
        Ca 4 – Phép tính số nguyên và khoản nạp nhỏ (< 100 wei):
        - Kiểm tra khoản nạp 99 wei:
          adminFee = 99 * 100 // 10000 = 0 wei
          classFundAmount = 99 - 0 = 99 wei
        - Phí không bị làm tròn lên, giao dịch không bị revert vô lý
        - Tổng tiền (0 + 99 = 99 wei) hoàn toàn chính xác, không thất thoát 1 wei nào
        """
        small_amount_wei = 99
        class_fund, fee = self.contract.deposit(self.student_a, small_amount_wei)

        self.assertEqual(fee, 0)
        self.assertEqual(class_fund, small_amount_wei)
        self.assertEqual(fee + class_fund, small_amount_wei)

        # Kiểm tra khoản nạp lẻ: 101 wei
        odd_amount_wei = 101
        class_odd, fee_odd = self.contract.deposit(self.student_b, odd_amount_wei)
        # 101 * 100 // 10000 = 1 wei fee
        # class = 101 - 1 = 100 wei
        self.assertEqual(fee_odd, 1)
        self.assertEqual(class_odd, 100)
        self.assertEqual(fee_odd + class_odd, odd_amount_wei)

        print("\n[Ca 4 - Phép chia số nguyên & bảo toàn số dư]")
        print(f"  + Nạp {small_amount_wei} wei: Phí = {fee} wei, Quỹ chính = {class_fund} wei (Tổng = {fee + class_fund} wei)")
        print(f"  + Nạp {odd_amount_wei} wei: Phí = {fee_odd} wei, Quỹ chính = {class_odd} wei (Tổng = {fee_odd + class_odd} wei)")

    def test_case_5_fraud_simulation_manipulation_attempt(self):
        """
        Ca 5 – Kiểm tra trường hợp gian lận (Fraud Simulation):
        Kẻ tấn công cố tình thực hiện nhiều vi phạm:
        1. Gửi 0 ETH để tạo lịch sử đóng góp ảo nhằm gian lận quyền hoàn tiền (R7/R10).
           -> Bị chặn ngay lập tức bởi ZeroAmount.
        2. Gửi hàng loạt giao dịch cực nhỏ để làm lệch số dư quỹ (Rounding exploit).
           -> Đảm bảo mọi giao dịch đều tuân thủ công thức: classFundAmount = msg.value - adminFee,
              tổng số dư hai quỹ luôn luôn khớp chính xác 100% với tổng ETH nạp vào.
        """
        # 1. Thử gửi 0 wei
        with self.assertRaises(ZeroAmountError):
            self.contract.deposit(self.attacker, 0)

        # 2. Thử tấn công tích lũy số dư làm tròn với các giá trị biên
        tricky_amounts = [1, 99, 100, 101, 999, 10_000, 10_001, 10**18 - 1]
        deposited_total = 0

        for amt in tricky_amounts:
            cf, fee = self.contract.deposit(self.attacker, amt)
            deposited_total += amt
            self.assertEqual(cf + fee, amt, f"Lệch số dư tại giá trị {amt} wei")

        # Xác minh tổng số dư ghi nhận của attacker bằng chính xác tổng nạp
        self.assertEqual(self.contract.get_student_contribution(self.attacker), deposited_total)
        print("\n[Ca 5 - Kiểm tra chống gian lận (Fraud/Exploit Defense)]")
        print("  + Kẻ tấn công cố gửi 0 ETH tạo lịch sử đóng góp: BỊ CHẶN (ZeroAmount)")
        print(f"  + Thử nghiệm làm tròn trên {len(tricky_amounts)} giá trị biên phức tạp:")
        print(f"    Tổng nạp: {deposited_total} wei ({wei_to_eth(deposited_total):.6f} ETH)")
        print("    Kết quả: 100% các giá trị đều bảo toàn số dư, không xảy ra thất thoát hay tràn số.")


if __name__ == "__main__":
    unittest.main()
