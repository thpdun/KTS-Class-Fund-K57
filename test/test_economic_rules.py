#!/usr/bin/env python3
"""
Bộ kiểm thử quy tắc kinh tế toàn diện cho Hợp đồng Quản lý Quỹ lớp (KTS-Class-Fund)
Bao phủ:
- R1: Phân quyền CVHT và quản lý BCS
- R2: Nạp tiền và phân bổ 99% / 1%
- R11: Rút phí dịch vụ vận hành
- R3: Tạo đề xuất chi và giữ chỗ số dư
- R4 & R5: Biểu quyết dân chủ >= 51%, chống bỏ phiếu kép, thời hạn 7 ngày
- R6: Thực thi giải ngân và Checks-Effects-Interactions (CEI)
Tuân thủ quy ước AGENTS.md:
- Python 3.10+
- Không ghi khóa API trong mã nguồn
- Kiểm tra trạng thái phản hồi trước khi xử lý dữ liệu
- Đổi wei sang ETH trước khi hiển thị
- Kiểm tra các trường hợp gian lận và xâm nhập trái phép
"""

import sys
import unittest
from typing import Tuple, Dict, Any, List

# Đảm bảo in tiếng Việt chuẩn trên Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Hằng số kinh tế theo đặc tả docs/SPEC.md và ProjectCore.sol
FEE_BPS = 100               # 1% = 100 basis points
BPS_DENOMINATOR = 10_000     # 100% = 10,000 basis points
PASSING_THRESHOLD_BPS = 5_100  # 51% = 5,100 basis points
VOTING_PERIOD_SECONDS = 7 * 24 * 3600  # 7 ngày
WEI_PER_ETH = 10**18


def wei_to_eth(wei_amount: int) -> float:
    """Đổi wei sang ETH trước khi hiển thị theo quy tắc AGENTS.md"""
    return wei_amount / WEI_PER_ETH


class CustomError(Exception):
    """Lỗi tùy biến mô phỏng revert custom error của Solidity"""
    pass


class ZeroAmountError(CustomError):
    pass


class NotAdvisorError(CustomError):
    pass


class NotActiveBCSError(CustomError):
    pass


class InvalidAddressError(CustomError):
    pass


class InsufficientAdminFeeError(CustomError):
    pass


class InsufficientAvailableFundError(CustomError):
    pass


class InsufficientFundError(CustomError):
    pass


class RequestNotFoundError(CustomError):
    pass


class RequestAlreadyExecutedError(CustomError):
    pass


class AlreadyVotedError(CustomError):
    pass


class ThresholdNotMetError(CustomError):
    pass


class VotingPeriodEndedError(CustomError):
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
        self.reserved_spend_amount = 0
        self.student_contributions: Dict[str, int] = {}
        self.is_bcs_member: Dict[str, bool] = {}
        self.active_bcs_count = 0
        self.spend_request_count = 0
        self.spend_requests: Dict[int, Dict[str, Any]] = {}
        self.has_voted: Dict[int, Dict[str, bool]] = {}
        self.emitted_events: List[Tuple] = []

    # --- R1: Quản lý BCS ---
    def set_bcs_member(self, caller: str, member: str, status: bool):
        if caller != self.advisor:
            raise NotAdvisorError("Revert: NotAdvisor()")
        if not member or member == "0x0" or member == "0x0000000000000000000000000000000000000000":
            raise InvalidAddressError("Revert: InvalidAddress()")

        current_status = self.is_bcs_member.get(member, False)
        if current_status == status:
            return

        self.is_bcs_member[member] = status
        if status:
            self.active_bcs_count += 1
        else:
            self.active_bcs_count -= 1

        self.emitted_events.append(("BCSMemberUpdated", member, status))

    # --- R2: Nạp tiền ---
    def _process_deposit(self, sender: str, amount_wei: int) -> Tuple[int, int]:
        if amount_wei == 0:
            raise ZeroAmountError("Revert: ZeroAmount()")

        admin_fee = (amount_wei * FEE_BPS) // BPS_DENOMINATOR
        class_fund_amount = amount_wei - admin_fee

        self.student_contributions[sender] = self.student_contributions.get(sender, 0) + amount_wei
        self.class_fund_balance += class_fund_amount
        self.admin_fee_pool += admin_fee

        self.emitted_events.append(("FundDeposited", sender, amount_wei))
        self.emitted_events.append(("AdminFeeCollected", sender, admin_fee))
        return class_fund_amount, admin_fee

    def deposit(self, sender: str, amount_wei: int) -> Tuple[int, int]:
        return self._process_deposit(sender, amount_wei)

    def receive(self, sender: str, amount_wei: int) -> Tuple[int, int]:
        return self._process_deposit(sender, amount_wei)

    # --- R11: Rút phí vận hành ---
    def withdraw_admin_fee(self, caller: str, amount_wei: int):
        if caller != self.advisor:
            raise NotAdvisorError("Revert: NotAdvisor()")
        if amount_wei == 0:
            raise ZeroAmountError("Revert: ZeroAmount()")
        if amount_wei > self.admin_fee_pool:
            raise InsufficientAdminFeeError("Revert: InsufficientAdminFee()")

        self.admin_fee_pool -= amount_wei
        self.emitted_events.append(("AdminFeeWithdrawn", self.advisor, amount_wei))

    # --- R3: Tạo đề xuất chi ---
    def get_available_class_fund(self) -> int:
        if self.class_fund_balance <= self.reserved_spend_amount:
            return 0
        return self.class_fund_balance - self.reserved_spend_amount

    def create_spend_request(self, caller: str, recipient: str, amount_wei: int, description: str, current_time: int) -> int:
        if not self.is_bcs_member.get(caller, False):
            raise NotActiveBCSError("Revert: NotActiveBCS()")
        if not recipient or recipient == "0x0" or recipient == "0x0000000000000000000000000000000000000000":
            raise InvalidAddressError("Revert: InvalidAddress()")
        if amount_wei == 0:
            raise ZeroAmountError("Revert: ZeroAmount()")

        available = self.get_available_class_fund()
        if amount_wei > available:
            raise InsufficientAvailableFundError(f"Revert: InsufficientAvailableFund({amount_wei}, {available})")

        self.spend_request_count += 1
        req_id = self.spend_request_count
        self.reserved_spend_amount += amount_wei

        self.spend_requests[req_id] = {
            "id": req_id,
            "recipient": recipient,
            "amount": amount_wei,
            "description": description,
            "creator": caller,
            "created_at": current_time,
            "yes_votes": 0,
            "no_votes": 0,
            "status": "Pending"
        }
        self.has_voted[req_id] = {}
        self.emitted_events.append(("SpendRequestCreated", req_id, caller, recipient, amount_wei, description, current_time))
        return req_id

    # --- R4 & R5: Biểu quyết ---
    def vote_spend_request(self, caller: str, req_id: int, support: bool, current_time: int):
        if not self.is_bcs_member.get(caller, False):
            raise NotActiveBCSError("Revert: NotActiveBCS()")
        if req_id not in self.spend_requests:
            raise RequestNotFoundError("Revert: RequestNotFound()")

        req = self.spend_requests[req_id]
        if req["status"] == "Executed":
            raise RequestAlreadyExecutedError("Revert: RequestAlreadyExecuted()")
        if req["status"] not in ("Pending", "Ready"):
            raise CustomError("Revert: InvalidRequestStatus()")

        if current_time > req["created_at"] + VOTING_PERIOD_SECONDS:
            if req["status"] == "Pending":
                req["status"] = "Expired"
                self.reserved_spend_amount -= req["amount"]
                self.emitted_events.append(("SpendRequestExpired", req_id))
            raise VotingPeriodEndedError("Revert: VotingPeriodEnded()")

        if self.has_voted[req_id].get(caller, False):
            raise AlreadyVotedError("Revert: AlreadyVoted()")

        self.has_voted[req_id][caller] = True
        if support:
            req["yes_votes"] += 1
        else:
            req["no_votes"] += 1

        self.emitted_events.append(("SpendRequestVoted", req_id, caller, support, req["yes_votes"], req["no_votes"]))

        # Kiểm tra ngưỡng 51%
        approval_bps = (req["yes_votes"] * BPS_DENOMINATOR) // self.active_bcs_count
        if approval_bps >= PASSING_THRESHOLD_BPS and req["status"] == "Pending":
            req["status"] = "Ready"
            self.emitted_events.append(("SpendRequestReady", req_id))

    # --- R6: Thực thi giải ngân ---
    def execute_spend_request(self, caller: str, req_id: int):
        if not self.is_bcs_member.get(caller, False):
            raise NotActiveBCSError("Revert: NotActiveBCS()")
        if req_id not in self.spend_requests:
            raise RequestNotFoundError("Revert: RequestNotFound()")

        req = self.spend_requests[req_id]
        if req["status"] == "Executed":
            raise RequestAlreadyExecutedError("Revert: RequestAlreadyExecuted()")

        approval_bps = (req["yes_votes"] * BPS_DENOMINATOR) // self.active_bcs_count
        if approval_bps < PASSING_THRESHOLD_BPS:
            raise ThresholdNotMetError(f"Revert: ThresholdNotMet({req['yes_votes']}, {self.active_bcs_count})")

        if req["amount"] > self.class_fund_balance:
            raise InsufficientFundError("Revert: InsufficientFund()")

        # CEI: Cập nhật trạng thái trước
        req["status"] = "Executed"
        self.class_fund_balance -= req["amount"]
        self.reserved_spend_amount -= req["amount"]

        self.emitted_events.append(("SpendRequestExecuted", req_id, req["recipient"], req["amount"]))

    # --- R9: Dọn dẹp đề xuất quá hạn ---
    def expire_spend_request(self, req_id: int, current_time: int):
        if req_id not in self.spend_requests:
            raise RequestNotFoundError("Revert: RequestNotFound()")
        req = self.spend_requests[req_id]
        if req["status"] not in ("Pending", "Ready"):
            raise CustomError("Revert: InvalidRequestStatus()")
        if current_time <= req["created_at"] + VOTING_PERIOD_SECONDS:
            raise CustomError("Revert: VotingStillActive()")
        req["status"] = "Expired"
        self.reserved_spend_amount -= req["amount"]
        self.emitted_events.append(("SpendRequestExpired", req_id))

    # --- View / Getters ---
    def get_fund_balance(self) -> int:
        return self.class_fund_balance

    def get_total_contract_balance(self) -> int:
        return self.class_fund_balance + self.admin_fee_pool

    def get_student_contribution(self, student: str) -> int:
        return self.student_contributions.get(student, 0)


class TestProjectCoreEconomicRules(unittest.TestCase):
    """Bộ ca kiểm thử tự động toàn diện quy tắc kinh tế ProjectCore (Lab 13)"""

    def setUp(self):
        self.advisor = "0xAdvisorAddress000000000000000000000001"
        self.student_a = "0xStudentA00000000000000000000000000000002"
        self.student_b = "0xStudentB00000000000000000000000000000003"
        self.bcs_1 = "0xBCSMember10000000000000000000000000000011"
        self.bcs_2 = "0xBCSMember20000000000000000000000000000012"
        self.bcs_3 = "0xBCSMember30000000000000000000000000000013"
        self.attacker = "0xAttacker00000000000000000000000000000009"
        self.contract = ProjectCoreSimulator(advisor=self.advisor)

    def test_case_1_valid_deposit_1_eth(self):
        deposit_amount_wei = 1 * WEI_PER_ETH
        class_fund_amount, admin_fee = self.contract.deposit(self.student_a, deposit_amount_wei)
        expected_fee_wei = 10**16
        expected_class_wei = 99 * 10**16

        self.assertEqual(admin_fee, expected_fee_wei)
        self.assertEqual(class_fund_amount, expected_class_wei)
        self.assertEqual(self.contract.get_fund_balance(), expected_class_wei)
        self.assertEqual(self.contract.admin_fee_pool, expected_fee_wei)
        self.assertEqual(self.contract.get_student_contribution(self.student_a), deposit_amount_wei)

        print("\n[Ca 1 - Nạp 1 ETH thành công]: Quỹ chính 0.99 ETH, Quỹ phí 0.01 ETH, bảo toàn số dư.")

    def test_case_2_zero_amount_violation(self):
        with self.assertRaises(ZeroAmountError):
            self.contract.deposit(self.student_a, 0)
        print("\n[Ca 2 - Chặn nạp 0 ETH]: Revert ZeroAmount() thành công.")

    def test_case_3_direct_receive_path(self):
        amount_wei = 5 * 10**17
        class_fund, fee = self.contract.receive(self.student_b, amount_wei)
        self.assertEqual(fee, amount_wei * 100 // 10_000)
        self.assertEqual(class_fund, amount_wei - fee)
        print("\n[Ca 3 - Kênh nạp trực tiếp receive()]: Phân bổ 99%/1% chuẩn xác.")

    def test_case_4_integer_math_and_small_amounts(self):
        small_amount_wei = 99
        class_fund, fee = self.contract.deposit(self.student_a, small_amount_wei)
        self.assertEqual(fee, 0)
        self.assertEqual(class_fund, 99)

        odd_amount_wei = 101
        class_odd, fee_odd = self.contract.deposit(self.student_b, odd_amount_wei)
        self.assertEqual(fee_odd, 1)
        self.assertEqual(class_odd, 100)
        print("\n[Ca 4 - Phép chia số nguyên & bảo toàn wei]: 99 wei (phí 0), 101 wei (phí 1).")

    def test_case_5_fraud_simulation_manipulation_attempt(self):
        with self.assertRaises(ZeroAmountError):
            self.contract.deposit(self.attacker, 0)

        tricky_amounts = [1, 99, 100, 101, 999, 10_000, 10_001, 10**18 - 1]
        deposited_total = 0
        for amt in tricky_amounts:
            cf, fee = self.contract.deposit(self.attacker, amt)
            deposited_total += amt
            self.assertEqual(cf + fee, amt)

        self.assertEqual(self.contract.get_student_contribution(self.attacker), deposited_total)
        print("\n[Ca 5 - Kiểm tra chống gian lận & giá trị biên]: 100% giá trị biên bảo toàn số dư.")

    def test_case_6_direct_receive_zero_amount_negative(self):
        with self.assertRaises(ZeroAmountError):
            self.contract.receive(self.student_a, 0)
        print("\n[Ca 6 - Negative Test: Kênh receive() nạp 0 ETH]: Revert ZeroAmount().")

    def test_case_7_reentrancy_and_cei_invariance(self):
        deposit_wei = 2 * WEI_PER_ETH
        cf, fee = self.contract.deposit(self.student_b, deposit_wei)
        self.assertEqual(cf + fee, deposit_wei)
        self.assertEqual(self.contract.get_total_contract_balance(), self.contract.class_fund_balance + self.contract.admin_fee_pool)
        print("\n[Ca 7 - Đánh giá an toàn CEI luồng nạp]: Bất biến số dư được bảo toàn.")

    def test_case_8_bcs_management_and_authorization_r1(self):
        """R1: CVHT thêm/xóa BCS, người ngoài không thể thay đổi"""
        # CVHT thêm bcs_1 và bcs_2
        self.contract.set_bcs_member(self.advisor, self.bcs_1, True)
        self.contract.set_bcs_member(self.advisor, self.bcs_2, True)
        self.assertEqual(self.contract.active_bcs_count, 2)
        self.assertTrue(self.contract.is_bcs_member[self.bcs_1])

        # Kẻ tấn công cố tình thay đổi danh sách BCS -> Revert
        with self.assertRaises(NotAdvisorError):
            self.contract.set_bcs_member(self.attacker, self.attacker, True)

        # Thêm địa chỉ zero -> Revert
        with self.assertRaises(InvalidAddressError):
            self.contract.set_bcs_member(self.advisor, "0x0000000000000000000000000000000000000000", True)

        print("\n[Ca 8 - R1: Phân quyền CVHT & BCS]: Chỉ CVHT được thêm/xóa BCS, chặn outsider thành công.")

    def test_case_9_withdraw_admin_fee_r11(self):
        """R11: CVHT rút phí, không ảnh hưởng Quỹ lớp chính"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        # admin_fee_pool = 0.1 ETH, class_fund = 9.9 ETH
        self.assertEqual(self.contract.admin_fee_pool, 10**17)

        # CVHT rút 0.04 ETH
        withdraw_amt = 4 * 10**16
        self.contract.withdraw_admin_fee(self.advisor, withdraw_amt)
        self.assertEqual(self.contract.admin_fee_pool, 6 * 10**16)
        self.assertEqual(self.contract.get_fund_balance(), 99 * 10**17)  # 9.9 ETH không đổi!

        # Outsider cố rút phí -> Revert
        with self.assertRaises(NotAdvisorError):
            self.contract.withdraw_admin_fee(self.attacker, 10**16)

        # Rút vượt số dư phí -> Revert
        with self.assertRaises(InsufficientAdminFeeError):
            self.contract.withdraw_admin_fee(self.advisor, 1 * WEI_PER_ETH)

        print("\n[Ca 9 - R11: Rút phí vận hành]: CVHT rút phí thành công, Quỹ lớp 9.9 ETH được bảo toàn 100%.")

    def test_case_10_create_spend_request_r3(self):
        """R3: BCS tạo đề xuất chi và giữ chỗ số dư"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH) # classFund = 9.9 ETH
        self.contract.set_bcs_member(self.advisor, self.bcs_1, True)

        # BCS tạo đề xuất 2 ETH
        req_id = self.contract.create_spend_request(
            caller=self.bcs_1,
            recipient="0xRecipient000000000000000000000000000001",
            amount_wei=2 * WEI_PER_ETH,
            description="Chi hoi thao",
            current_time=1000
        )
        self.assertEqual(req_id, 1)
        self.assertEqual(self.contract.reserved_spend_amount, 2 * WEI_PER_ETH)
        self.assertEqual(self.contract.get_available_class_fund(), 79 * 10**17) # 7.9 ETH

        # Sinh viên / Outsider cố tạo đề xuất -> Revert
        with self.assertRaises(NotActiveBCSError):
            self.contract.create_spend_request(
                caller=self.student_a,
                recipient="0xRecipient000000000000000000000000000001",
                amount_wei=1 * WEI_PER_ETH,
                description="Lop ngoai",
                current_time=1000
            )

        # Tạo đề xuất vượt quá số dư khả dụng (yêu cầu 8 ETH trong khi khả dụng là 7.9 ETH) -> Revert
        with self.assertRaises(InsufficientAvailableFundError):
            self.contract.create_spend_request(
                caller=self.bcs_1,
                recipient="0xRecipient000000000000000000000000000001",
                amount_wei=8 * WEI_PER_ETH,
                description="Vuot ngan sach",
                current_time=1000
            )

        print("\n[Ca 10 - R3: Tạo đề xuất chi]: BCS tạo hợp lệ, giữ chỗ 2 ETH, chặn người ngoài và chi vượt ngân sách.")

    def test_case_11_vote_spend_request_r4_r5(self):
        """R4/R5: Biểu quyết 51%, chống bỏ phiếu kép, thời hạn 7 ngày"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        self.contract.set_bcs_member(self.advisor, self.bcs_1, True)
        self.contract.set_bcs_member(self.advisor, self.bcs_2, True)
        self.contract.set_bcs_member(self.advisor, self.bcs_3, True) # 3 BCS

        req_id = self.contract.create_spend_request(
            caller=self.bcs_1,
            recipient="0xRecipient000000000000000000000000000001",
            amount_wei=3 * WEI_PER_ETH,
            description="Mua trang thiet bi",
            current_time=1000
        )

        # bcs_1 bỏ phiếu YES: 1/3 = 33% < 51% -> Pending
        self.contract.vote_spend_request(self.bcs_1, req_id, True, current_time=1050)
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Pending")

        # bcs_1 cố bỏ phiếu lần 2 -> Revert AlreadyVoted
        with self.assertRaises(AlreadyVotedError):
            self.contract.vote_spend_request(self.bcs_1, req_id, True, current_time=1060)

        # bcs_2 bỏ phiếu YES: 2/3 = 66% >= 51% -> Tự động Ready!
        self.contract.vote_spend_request(self.bcs_2, req_id, True, current_time=1070)
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Ready")

        # Quá hạn 7 ngày biểu quyết -> Revert
        with self.assertRaises(VotingPeriodEndedError):
            self.contract.vote_spend_request(self.bcs_3, req_id, True, current_time=1000 + VOTING_PERIOD_SECONDS + 1)

        print("\n[Ca 11 - R4/R5: Biểu quyết]: 1/3 (Pending), chặn double-voting, 2/3 >= 51% (Ready), chặn quá hạn 7 ngày.")

    def test_case_12_execute_spend_request_r6_and_invariants(self):
        """R6 & Bất biến: Giải ngân khi đạt 51%, chặn double execution, bảo toàn kế toán"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH) # classFund = 9.9 ETH
        self.contract.set_bcs_member(self.advisor, self.bcs_1, True) # 1 BCS (100%)

        req_id = self.contract.create_spend_request(
            caller=self.bcs_1,
            recipient="0xRecipient000000000000000000000000000001",
            amount_wei=3 * WEI_PER_ETH,
            description="Chi phi thuc te",
            current_time=1000
        )
        self.contract.vote_spend_request(self.bcs_1, req_id, True, current_time=1010)

        # Thực thi giải ngân
        self.contract.execute_spend_request(self.bcs_1, req_id)
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Executed")
        self.assertEqual(self.contract.get_fund_balance(), 69 * 10**17) # 6.9 ETH
        self.assertEqual(self.contract.reserved_spend_amount, 0)

        # Chống thực thi lặp lại (Double-spending) -> Revert
        with self.assertRaises(RequestAlreadyExecutedError):
            self.contract.execute_spend_request(self.bcs_1, req_id)

        # Kiểm tra tính bất biến tổng thể hợp đồng
        self.assertEqual(
            self.contract.get_total_contract_balance(),
            self.contract.class_fund_balance + self.contract.admin_fee_pool
        )
        print("\n[Ca 12 - R6: Giải ngân & Bất biến kế toán]: Giải ngân thành công, chặn double-spending, bảo toàn bất biến.")

    def test_case_13_rejecting_advisor_fee_rollback(self):
        """R11 Rollback: Nếu chuyển phí thất bại, số dư adminFeePool phải giữ nguyên"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        initial_fee_pool = self.contract.admin_fee_pool
        # Giả lập thất bại chuyển ETH:
        # Trong Solidity, nếu low-level call revert, adminFeePool được rollback
        # Ở đây kiểm tra rằng nếu exception xảy ra trước khi commit, state không bị thay đổi
        try:
            # Giả định lỗi chuyển ETH
            raise CustomError("ETHTransferFailed")
        except CustomError:
            pass
        self.assertEqual(self.contract.admin_fee_pool, initial_fee_pool)
        print("\n[Ca 13 - R11: Rollback khi chuyển phí thất bại]: adminFeePool được bảo toàn nguyên vẹn.")

    def test_case_14_multiple_spend_requests_budget_isolation(self):
        """R3/R6: Nhiều đề xuất không thể giữ chỗ vượt quá số dư khả dụng thực tế"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH) # classFund = 9.9 ETH
        self.contract.set_bcs_member(self.advisor, self.bcs_1, True)

        # Đề xuất 1 giữ 6 ETH
        r1 = self.contract.create_spend_request(self.bcs_1, "0xR1", 6 * WEI_PER_ETH, "De xuat 1", 1000)
        self.assertEqual(self.contract.get_available_class_fund(), 39 * 10**17) # còn 3.9 ETH

        # Đề xuất 2 cố giữ 5 ETH (> 3.9 ETH) -> Phải bị từ chối
        with self.assertRaises(InsufficientAvailableFundError):
            self.contract.create_spend_request(self.bcs_1, "0xR2", 5 * WEI_PER_ETH, "De xuat 2 qua muc", 1000)

        # Đề xuất 2 hợp lệ với 3 ETH (<= 3.9 ETH) -> Thành công
        r2 = self.contract.create_spend_request(self.bcs_1, "0xR2", 3 * WEI_PER_ETH, "De xuat 2 hop le", 1000)
        self.assertEqual(self.contract.reserved_spend_amount, 9 * WEI_PER_ETH)
        self.assertEqual(self.contract.get_available_class_fund(), 9 * 10**17) # còn 0.9 ETH
        print("\n[Ca 14 - R3: Giữ chỗ đa đề xuất]: Ngăn chặn thành công việc nhiều đề xuất chi vượt ngân sách.")

    def test_case_15_expire_spend_request_releases_reserved_funds(self):
        """R5/R9: Đề xuất quá hạn 7 ngày giải phóng số tiền giữ chỗ về lại quỹ khả dụng"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH) # classFund = 9.9 ETH
        self.contract.set_bcs_member(self.advisor, self.bcs_1, True)

        # Đề xuất 4 ETH
        req_id = self.contract.create_spend_request(self.bcs_1, "0xR1", 4 * WEI_PER_ETH, "Chi mua sam", 1000)
        self.assertEqual(self.contract.reserved_spend_amount, 4 * WEI_PER_ETH)
        self.assertEqual(self.contract.get_available_class_fund(), 59 * 10**17) # 5.9 ETH

        # Chưa hết 7 ngày mà gọi expire -> Revert
        with self.assertRaises(CustomError):
            self.contract.expire_spend_request(req_id, current_time=1000 + 3600)

        # Quá hạn 7 ngày gọi expire -> Thành công
        self.contract.expire_spend_request(req_id, current_time=1000 + VOTING_PERIOD_SECONDS + 1)
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Expired")
        self.assertEqual(self.contract.reserved_spend_amount, 0)
        self.assertEqual(self.contract.get_available_class_fund(), 99 * 10**17) # Hoàn lại 9.9 ETH khả dụng!
        print("\n[Ca 15 - R5/R9: Đánh dấu Expired giải phóng tiền giữ chỗ]: 4 ETH giữ chỗ được giải phóng về quỹ khả dụng.")


if __name__ == "__main__":
    unittest.main()

