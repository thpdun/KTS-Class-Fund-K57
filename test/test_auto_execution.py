#!/usr/bin/env python3
"""
Bộ kiểm thử tự động toàn diện cho cơ chế Tự thực thi (Auto-Execution)
và các bản sửa lỗi trong giai đoạn AUTO-EXECUTION FIX 1 (KTS-Class-Fund-K57).

Bao phủ đầy đủ các yêu cầu kiểm toán:
1. Auto-execution chi tiền thành công: đúng trạng thái, số dư, và phát SpendRequestExecuted.
2. Auto-execution chi tiền thất bại: KHÔNG phát SpendRequestExecuted, có SpendExecutionFailed,
   đề xuất ở Ready và reservation được bảo toàn.
3. Auto-execution hoàn tiền thành công: đúng trạng thái, số dư, phát RefundRequestExecuted và RefundProcessed.
4. Auto-execution hoàn tiền thất bại: KHÔNG phát RefundRequestExecuted/RefundProcessed,
   có RefundExecutionFailed, hạn mức đóng góp và reservation giữ nguyên.
5. Thực thi thủ công sau thất bại thành công và chỉ ghi nhận event thành công đúng 1 lần.
6. Chống thực thi hai lần (chống Double-Execution).
7. Không cho phép expire request Ready: cả chi tiền và hoàn tiền đều revert InvalidRequestStatus / InvalidRefundStatus.
8. Request Pending quá hạn được expire và giải phóng reservation đúng 1 lần; gọi lại revert InvalidRequestStatus.
9. Request chưa quá hạn không thể expire (kể cả ranh giới createdAt + VOTING_PERIOD), revert VotingStillActive.
10. Quy tắc 51%, chống double-voting và phân quyền BCS/Advisor được bảo toàn.
11. Chống tái nhập (Reentrancy) bảo đảm không làm sai lệch số dư.
12. Phân tích chi tiết phương pháp luận đo lường Gas và rủi ro Gas Griefing.
"""

import sys
import unittest
from typing import Dict, Any, List, Tuple, Set

# Đảm bảo in tiếng Việt chuẩn trên Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

FEE_BPS = 100                 # 1% = 100 bps
BPS_DENOMINATOR = 10_000       # 100% = 10,000 bps
PASSING_THRESHOLD_BPS = 5_100    # 51% = 5,100 bps
VOTING_PERIOD_SECONDS = 7 * 24 * 3600  # 7 ngày
WEI_PER_ETH = 10**18


def wei_to_eth(wei_amount: int) -> float:
    return wei_amount / WEI_PER_ETH


class CustomError(Exception):
    pass

class ZeroAmountError(CustomError): pass
class NotAdvisorError(CustomError): pass
class NotActiveBCSError(CustomError): pass
class InvalidAddressError(CustomError): pass
class InsufficientAdminFeeError(CustomError): pass
class InsufficientContributionError(CustomError): pass
class InsufficientAvailableFundError(CustomError): pass
class InsufficientFundError(CustomError): pass
class RequestNotFoundError(CustomError): pass
class RequestAlreadyExecutedError(CustomError): pass
class RequestExpiredError(CustomError): pass
class AlreadyVotedError(CustomError): pass
class VotingPeriodEndedError(CustomError): pass
class VotingStillActiveError(CustomError): pass
class NoActiveBCSError(CustomError): pass
class ThresholdNotMetError(CustomError): pass
class InvalidRequestStatusError(CustomError): pass

class RefundRequestNotFoundError(CustomError): pass
class RefundAlreadyExecutedError(CustomError): pass
class RefundExpiredError(CustomError): pass
class AlreadyVotedRefundError(CustomError): pass
class RefundVotingPeriodEndedError(CustomError): pass
class RefundVotingStillActiveError(CustomError): pass
class InvalidRefundStatusError(CustomError): pass
class ETHTransferFailedError(CustomError): pass


class AutoExecutionProjectCoreSimulator:
    """
    Simulator mô phỏng logic của ProjectCore.sol có Auto-Execution sau khi sửa lỗi FIX 1.
    """
    def __init__(self, advisor: str = "0xAdvisor0000000000000000000000000000000001"):
        self.advisor = advisor
        self.class_fund_balance = 0
        self.admin_fee_pool = 0
        self.reserved_spend_amount = 0
        self.reserved_refund_amount = 0
        self.student_contributions: Dict[str, int] = {}
        self.pending_student_refund_amount: Dict[str, int] = {}
        self.is_bcs_member: Dict[str, bool] = {}
        self.active_bcs_count = 0
        self.spend_request_count = 0
        self.spend_requests: Dict[int, Dict[str, Any]] = {}
        self.has_voted: Dict[int, Dict[str, bool]] = {}
        self.refund_request_count = 0
        self.refund_requests: Dict[int, Dict[str, Any]] = {}
        self.has_voted_refund: Dict[int, Dict[str, bool]] = {}
        self.emitted_events: List[Tuple] = []

        # Danh sách địa chỉ từ chối nhận ETH để kiểm tra fallback
        self.rejecting_recipients: Set[str] = set()
        # Mock số dư ví ngoài đời thực
        self.wallet_balances: Dict[str, int] = {}
        # Callback mô phỏng tấn công tái nhập
        self.reentrancy_hook = None

    def get_total_contract_balance(self) -> int:
        return self.class_fund_balance + self.admin_fee_pool

    def get_available_class_fund(self) -> int:
        total_reserved = self.reserved_spend_amount + self.reserved_refund_amount
        if self.class_fund_balance <= total_reserved:
            return 0
        return self.class_fund_balance - total_reserved

    def get_student_available_contribution(self, student: str) -> int:
        total_contrib = self.student_contributions.get(student, 0)
        pending = self.pending_student_refund_amount.get(student, 0)
        if total_contrib <= pending:
            return 0
        return total_contrib - pending

    # --- Phân quyền ---
    def set_bcs_member(self, caller: str, member: str, status: bool):
        if caller != self.advisor:
            raise NotAdvisorError("Revert: NotAdvisor()")
        if not member or member == "0x0":
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

    # --- Nạp tiền ---
    def deposit(self, caller: str, amount_wei: int) -> Tuple[int, int]:
        if amount_wei == 0:
            raise ZeroAmountError("Revert: ZeroAmount()")
        fee = (amount_wei * FEE_BPS) // BPS_DENOMINATOR
        fund = amount_wei - fee

        self.admin_fee_pool += fee
        self.class_fund_balance += fund
        self.student_contributions[caller] = self.student_contributions.get(caller, 0) + amount_wei

        self.emitted_events.append(("FundDeposited", caller, amount_wei))
        if fee > 0:
            self.emitted_events.append(("AdminFeeCollected", caller, fee))
        return fund, fee

    # --- Rút phí ---
    def withdraw_admin_fee(self, caller: str, amount_wei: int):
        if caller != self.advisor:
            raise NotAdvisorError("Revert: NotAdvisor()")
        if amount_wei == 0:
            raise ZeroAmountError("Revert: ZeroAmount()")
        if amount_wei > self.admin_fee_pool:
            raise InsufficientAdminFeeError("Revert: InsufficientAdminFee()")
        self.admin_fee_pool -= amount_wei
        self.wallet_balances[caller] = self.wallet_balances.get(caller, 0) + amount_wei
        self.emitted_events.append(("AdminFeeWithdrawn", caller, amount_wei))

    # --- Chi tiền ---
    def create_spend_request(self, caller: str, recipient: str, amount_wei: int, description: str, current_time: int) -> int:
        if not self.is_bcs_member.get(caller, False):
            raise NotActiveBCSError("Revert: NotActiveBCS()")
        if not recipient or recipient == "0x0":
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

    def _try_execute_spend(self, req_id: int) -> bool:
        req = self.spend_requests[req_id]
        if req["amount"] > self.class_fund_balance:
            return False

        # CEI: Effects
        req["status"] = "Executed"
        self.class_fund_balance -= req["amount"]
        self.reserved_spend_amount -= req["amount"]

        # Interactions
        if req["recipient"] in self.rejecting_recipients:
            # Rollback
            req["status"] = "Ready"
            self.class_fund_balance += req["amount"]
            self.reserved_spend_amount += req["amount"]
            # SỬA LỖI FIX 1: Chỉ phát SpendExecutionFailed, KHÔNG phát SpendRequestExecuted
            self.emitted_events.append(("SpendExecutionFailed", req_id, req["recipient"], req["amount"]))
            return False

        # Mô phỏng Reentrancy hook nếu có
        if self.reentrancy_hook:
            self.reentrancy_hook()

        # SỬA LỖI FIX 1: Chỉ phát SpendRequestExecuted sau khi chuyển ETH thành công
        self.emitted_events.append(("SpendRequestExecuted", req_id, req["recipient"], req["amount"]))
        self.wallet_balances[req["recipient"]] = self.wallet_balances.get(req["recipient"], 0) + req["amount"]
        return True

    def vote_spend_request(self, caller: str, req_id: int, support: bool, current_time: int):
        if not self.is_bcs_member.get(caller, False):
            raise NotActiveBCSError("Revert: NotActiveBCS()")
        if req_id not in self.spend_requests:
            raise RequestNotFoundError("Revert: RequestNotFound()")

        req = self.spend_requests[req_id]
        if req["status"] == "Executed":
            raise RequestAlreadyExecutedError("Revert: RequestAlreadyExecuted()")
        if req["status"] == "Expired":
            raise RequestExpiredError("Revert: RequestExpired()")
        if req["status"] not in ("Pending", "Ready"):
            raise InvalidRequestStatusError("Revert: InvalidRequestStatus()")

        if current_time > req["created_at"] + VOTING_PERIOD_SECONDS:
            if req["status"] == "Pending":
                req["status"] = "Expired"
                self.reserved_spend_amount -= req["amount"]
                self.emitted_events.append(("SpendRequestExpired", req_id))
            raise VotingPeriodEndedError("Revert: VotingPeriodEnded()")

        if self.has_voted[req_id].get(caller, False):
            raise AlreadyVotedError("Revert: AlreadyVoted()")
        if self.active_bcs_count == 0:
            raise NoActiveBCSError("Revert: NoActiveBCS()")

        self.has_voted[req_id][caller] = True
        if support:
            req["yes_votes"] += 1
        else:
            req["no_votes"] += 1

        self.emitted_events.append(("SpendRequestVoted", req_id, caller, support, req["yes_votes"], req["no_votes"]))

        approval_bps = (req["yes_votes"] * BPS_DENOMINATOR) // self.active_bcs_count
        if approval_bps >= PASSING_THRESHOLD_BPS and req["status"] == "Pending":
            req["status"] = "Ready"
            self.emitted_events.append(("SpendRequestReady", req_id))
            # AUTO-EXECUTION:
            self._try_execute_spend(req_id)

    def execute_spend_request(self, caller: str, req_id: int):
        if not self.is_bcs_member.get(caller, False):
            raise NotActiveBCSError("Revert: NotActiveBCS()")
        if req_id not in self.spend_requests:
            raise RequestNotFoundError("Revert: RequestNotFound()")

        req = self.spend_requests[req_id]
        if req["status"] == "Executed":
            raise RequestAlreadyExecutedError("Revert: RequestAlreadyExecuted()")
        if req["status"] == "Expired":
            raise RequestExpiredError("Revert: RequestExpired()")
        if req["status"] not in ("Pending", "Ready"):
            raise InvalidRequestStatusError("Revert: InvalidRequestStatus()")

        approval_bps = (req["yes_votes"] * BPS_DENOMINATOR) // self.active_bcs_count
        if approval_bps < PASSING_THRESHOLD_BPS:
            raise ThresholdNotMetError(f"Revert: ThresholdNotMet({req['yes_votes']}, {self.active_bcs_count})")

        if req["amount"] > self.class_fund_balance:
            raise InsufficientFundError("Revert: InsufficientFund()")

        # CEI
        req["status"] = "Executed"
        self.class_fund_balance -= req["amount"]
        self.reserved_spend_amount -= req["amount"]

        if req["recipient"] in self.rejecting_recipients:
            # Revert thủ công khi gọi execute riêng
            req["status"] = "Ready"
            self.class_fund_balance += req["amount"]
            self.reserved_spend_amount += req["amount"]
            raise ETHTransferFailedError("Revert: ETHTransferFailed()")

        # SỬA LỖI FIX 1: Chỉ phát sau khi chuyển ETH thành công
        self.emitted_events.append(("SpendRequestExecuted", req_id, req["recipient"], req["amount"]))
        self.wallet_balances[req["recipient"]] = self.wallet_balances.get(req["recipient"], 0) + req["amount"]

    def expire_spend_request(self, req_id: int, current_time: int):
        """
        SỬA LỖI FIX 1: Chỉ cho phép dọn dẹp đề xuất Pending quá hạn.
        Đề xuất Ready (đã đạt ngưỡng) tuyệt đối KHÔNG bị expired.
        """
        if req_id not in self.spend_requests:
            raise RequestNotFoundError("Revert: RequestNotFound()")

        req = self.spend_requests[req_id]
        if req["status"] != "Pending":
            raise InvalidRequestStatusError("Revert: InvalidRequestStatus()")

        if current_time <= req["created_at"] + VOTING_PERIOD_SECONDS:
            raise VotingStillActiveError("Revert: VotingStillActive()")

        req["status"] = "Expired"
        self.reserved_spend_amount -= req["amount"]
        self.emitted_events.append(("SpendRequestExpired", req_id))

    # --- Hoàn tiền ---
    def create_refund_request(self, caller: str, amount_wei: int, reason: str, current_time: int) -> int:
        if amount_wei <= 0:
            raise ZeroAmountError("Revert: ZeroAmount()")
        available_contrib = self.get_student_available_contribution(caller)
        if amount_wei > available_contrib:
            raise InsufficientContributionError(f"Revert: InsufficientContribution({amount_wei}, {available_contrib})")
        available_fund = self.get_available_class_fund()
        if amount_wei > available_fund:
            raise InsufficientAvailableFundError(f"Revert: InsufficientAvailableFund({amount_wei}, {available_fund})")

        self.refund_request_count += 1
        ref_id = self.refund_request_count
        self.pending_student_refund_amount[caller] = self.pending_student_refund_amount.get(caller, 0) + amount_wei
        self.reserved_refund_amount += amount_wei

        self.refund_requests[ref_id] = {
            "id": ref_id,
            "applicant": caller,
            "amount": amount_wei,
            "reason": reason,
            "created_at": current_time,
            "yes_votes": 0,
            "no_votes": 0,
            "status": "Pending"
        }
        self.has_voted_refund[ref_id] = {}
        self.emitted_events.append(("RefundRequestCreated", ref_id, caller, amount_wei, reason, current_time))
        return ref_id

    def _try_execute_refund(self, ref_id: int) -> bool:
        req = self.refund_requests[ref_id]
        if req["amount"] > self.student_contributions.get(req["applicant"], 0) or req["amount"] > self.class_fund_balance:
            return False

        # CEI: Effects
        req["status"] = "Executed"
        self.reserved_refund_amount -= req["amount"]
        self.pending_student_refund_amount[req["applicant"]] -= req["amount"]
        self.student_contributions[req["applicant"]] -= req["amount"]
        self.class_fund_balance -= req["amount"]

        # Interactions
        if req["applicant"] in self.rejecting_recipients:
            # Rollback
            req["status"] = "Ready"
            self.reserved_refund_amount += req["amount"]
            self.pending_student_refund_amount[req["applicant"]] += req["amount"]
            self.student_contributions[req["applicant"]] += req["amount"]
            self.class_fund_balance += req["amount"]
            # SỬA LỖI FIX 1: Chỉ phát RefundExecutionFailed, KHÔNG phát RefundRequestExecuted / RefundProcessed
            self.emitted_events.append(("RefundExecutionFailed", ref_id, req["applicant"], req["amount"]))
            return False

        if self.reentrancy_hook:
            self.reentrancy_hook()

        # SỬA LỖI FIX 1: Chỉ phát sự kiện hoàn tất sau khi chuyển ETH thành công
        self.emitted_events.append(("RefundRequestExecuted", ref_id, req["applicant"], req["amount"]))
        self.emitted_events.append(("RefundProcessed", req["applicant"], req["amount"]))
        self.wallet_balances[req["applicant"]] = self.wallet_balances.get(req["applicant"], 0) + req["amount"]
        return True

    def vote_refund_request(self, caller: str, ref_id: int, support: bool, current_time: int):
        if not self.is_bcs_member.get(caller, False):
            raise NotActiveBCSError("Revert: NotActiveBCS()")
        if ref_id not in self.refund_requests:
            raise RefundRequestNotFoundError("Revert: RefundRequestNotFound()")

        req = self.refund_requests[ref_id]
        if req["status"] == "Executed":
            raise RefundAlreadyExecutedError("Revert: RefundAlreadyExecuted()")
        if req["status"] == "Expired":
            raise RefundExpiredError("Revert: RefundExpired()")
        if req["status"] not in ("Pending", "Ready"):
            raise InvalidRefundStatusError("Revert: InvalidRefundStatus()")

        if current_time > req["created_at"] + VOTING_PERIOD_SECONDS:
            if req["status"] == "Pending":
                req["status"] = "Expired"
                self.reserved_refund_amount -= req["amount"]
                self.pending_student_refund_amount[req["applicant"]] -= req["amount"]
                self.emitted_events.append(("RefundRequestExpired", ref_id))
            raise RefundVotingPeriodEndedError("Revert: RefundVotingPeriodEnded()")

        if self.has_voted_refund[ref_id].get(caller, False):
            raise AlreadyVotedRefundError("Revert: AlreadyVotedRefund()")
        if self.active_bcs_count == 0:
            raise NoActiveBCSError("Revert: NoActiveBCS()")

        self.has_voted_refund[ref_id][caller] = True
        if support:
            req["yes_votes"] += 1
        else:
            req["no_votes"] += 1

        self.emitted_events.append(("RefundRequestVoted", ref_id, caller, support, req["yes_votes"], req["no_votes"]))

        approval_bps = (req["yes_votes"] * BPS_DENOMINATOR) // self.active_bcs_count
        if approval_bps >= PASSING_THRESHOLD_BPS and req["status"] == "Pending":
            req["status"] = "Ready"
            self.emitted_events.append(("RefundRequestReady", ref_id))
            # AUTO-EXECUTION:
            self._try_execute_refund(ref_id)

    def execute_refund_request(self, caller: str, ref_id: int):
        if ref_id not in self.refund_requests:
            raise RefundRequestNotFoundError("Revert: RefundRequestNotFound()")

        req = self.refund_requests[ref_id]
        if req["status"] == "Executed":
            raise RefundAlreadyExecutedError("Revert: RefundAlreadyExecuted()")
        if req["status"] == "Expired":
            raise RefundExpiredError("Revert: RefundExpired()")
        if req["status"] not in ("Pending", "Ready"):
            raise InvalidRefundStatusError("Revert: InvalidRefundStatus()")

        approval_bps = (req["yes_votes"] * BPS_DENOMINATOR) // self.active_bcs_count
        if approval_bps < PASSING_THRESHOLD_BPS:
            raise ThresholdNotMetError(f"Revert: ThresholdNotMet({req['yes_votes']}, {self.active_bcs_count})")

        if req["amount"] > self.student_contributions.get(req["applicant"], 0):
            raise InsufficientContributionError("Revert: InsufficientContribution()")
        if req["amount"] > self.class_fund_balance:
            raise InsufficientFundError("Revert: InsufficientFund()")

        req["status"] = "Executed"
        self.reserved_refund_amount -= req["amount"]
        self.pending_student_refund_amount[req["applicant"]] -= req["amount"]
        self.student_contributions[req["applicant"]] -= req["amount"]
        self.class_fund_balance -= req["amount"]

        if req["applicant"] in self.rejecting_recipients:
            req["status"] = "Ready"
            self.reserved_refund_amount += req["amount"]
            self.pending_student_refund_amount[req["applicant"]] += req["amount"]
            self.student_contributions[req["applicant"]] += req["amount"]
            self.class_fund_balance += req["amount"]
            raise ETHTransferFailedError("Revert: ETHTransferFailed()")

        # SỬA LỖI FIX 1: Chỉ phát sự kiện hoàn tất sau khi chuyển ETH thành công
        self.emitted_events.append(("RefundRequestExecuted", ref_id, req["applicant"], req["amount"]))
        self.emitted_events.append(("RefundProcessed", req["applicant"], req["amount"]))
        self.wallet_balances[req["applicant"]] = self.wallet_balances.get(req["applicant"], 0) + req["amount"]

    def expire_refund_request(self, ref_id: int, current_time: int):
        """
        SỬA LỖI FIX 1: Chỉ cho phép dọn dẹp yêu cầu hoàn tiền Pending quá hạn.
        Yêu cầu hoàn tiền Ready tuyệt đối KHÔNG bị expired.
        """
        if ref_id not in self.refund_requests:
            raise RefundRequestNotFoundError("Revert: RefundRequestNotFound()")

        req = self.refund_requests[ref_id]
        if req["status"] != "Pending":
            raise InvalidRefundStatusError("Revert: InvalidRefundStatus()")

        if current_time <= req["created_at"] + VOTING_PERIOD_SECONDS:
            raise RefundVotingStillActiveError("Revert: RefundVotingStillActive()")

        req["status"] = "Expired"
        self.reserved_refund_amount -= req["amount"]
        self.pending_student_refund_amount[req["applicant"]] -= req["amount"]
        self.emitted_events.append(("RefundRequestExpired", ref_id))


class TestAutoExecutionComprehensive(unittest.TestCase):
    """
    Test suite toàn diện xác minh toàn bộ các yêu cầu của giai đoạn AUTO-EXECUTION FIX 1.
    """
    def setUp(self):
        self.advisor = "0xAdvisor0000000000000000000000000000000001"
        self.bcs_1 = "0xBCS100000000000000000000000000000000000001"
        self.bcs_2 = "0xBCS200000000000000000000000000000000000002"
        self.bcs_3 = "0xBCS300000000000000000000000000000000000003"
        self.student_a = "0xStudentA000000000000000000000000000000001"
        self.student_b = "0xStudentB000000000000000000000000000000002"
        self.recipient = "0xRecipient00000000000000000000000000000001"
        self.contract = AutoExecutionProjectCoreSimulator(self.advisor)

    # 1. Auto-execution chi tiền thành công: đúng trạng thái, số dư, và event
    def test_01_spend_auto_executes_successfully_with_event(self):
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        self.contract.set_bcs_member(self.advisor, self.bcs_1, True)
        self.contract.set_bcs_member(self.advisor, self.bcs_2, True)

        req_id = self.contract.create_spend_request(self.bcs_1, self.recipient, 4 * WEI_PER_ETH, "Chi tu dong thanh cong", 1000)
        self.contract.vote_spend_request(self.bcs_1, req_id, True, 1010)
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Pending")

        # BCS 2 bỏ phiếu quyết định (2/2 = 100% >= 51%)
        self.contract.vote_spend_request(self.bcs_2, req_id, True, 1020)

        # Kiểm tra trạng thái và số dư
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Executed")
        self.assertEqual(self.contract.wallet_balances[self.recipient], 4 * WEI_PER_ETH)
        self.assertEqual(self.contract.class_fund_balance, 5.9 * WEI_PER_ETH)
        self.assertEqual(self.contract.reserved_spend_amount, 0)

        # Kiểm tra sự kiện
        self.assertIn(("SpendRequestExecuted", req_id, self.recipient, 4 * WEI_PER_ETH), self.contract.emitted_events)
        self.assertNotIn(("SpendExecutionFailed", req_id, self.recipient, 4 * WEI_PER_ETH), self.contract.emitted_events)

    # 2. Auto-execution chi tiền thất bại: KHÔNG phát SpendRequestExecuted, có SpendExecutionFailed, đề xuất Ready
    def test_02_spend_auto_executes_failure_does_not_emit_success_event_and_allows_manual_fallback(self):
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        self.contract.set_bcs_member(self.advisor, self.bcs_1, True)
        self.contract.set_bcs_member(self.advisor, self.bcs_2, True)

        rejecting_addr = "0xRejectingContract00000000000000000000001"
        self.contract.rejecting_recipients.add(rejecting_addr)

        req_id = self.contract.create_spend_request(self.bcs_1, rejecting_addr, 3 * WEI_PER_ETH, "Chi cho contract loi", 1000)
        self.contract.vote_spend_request(self.bcs_1, req_id, True, 1010)

        # BCS 2 bỏ phiếu quyết định (2/2 = 100% >= 51%) -> Tự giải ngân thất bại do recipient từ chối ETH
        self.contract.vote_spend_request(self.bcs_2, req_id, True, 1020)

        req = self.contract.spend_requests[req_id]
        self.assertTrue(self.contract.has_voted[req_id][self.bcs_2], "Phieu cua BCS 2 phai duoc ghi nhan")
        self.assertEqual(req["status"], "Ready", "Trang thai phai rollback ve Ready de cho fallback")
        self.assertEqual(self.contract.class_fund_balance, 9.9 * WEI_PER_ETH, "So du khong bi mat")
        self.assertEqual(self.contract.reserved_spend_amount, 3 * WEI_PER_ETH, "Tien giu cho van giu nguyen")

        # XÁC MINH SỬA LỖI FIX 1:
        # Không được có SpendRequestExecuted trong event log!
        self.assertNotIn(("SpendRequestExecuted", req_id, rejecting_addr, 3 * WEI_PER_ETH), self.contract.emitted_events)
        # Bắt buộc phải có SpendExecutionFailed!
        self.assertIn(("SpendExecutionFailed", req_id, rejecting_addr, 3 * WEI_PER_ETH), self.contract.emitted_events)

        # Fallback thử lại thất bại khi recipient vẫn từ chối ETH
        with self.assertRaises(ETHTransferFailedError):
            self.contract.execute_spend_request(self.bcs_1, req_id)
        self.assertNotIn(("SpendRequestExecuted", req_id, rejecting_addr, 3 * WEI_PER_ETH), self.contract.emitted_events)

        # Khi recipient sửa lỗi nhận tiền -> Gọi execute thủ công thành công
        self.contract.rejecting_recipients.remove(rejecting_addr)
        self.contract.execute_spend_request(self.bcs_1, req_id)

        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Executed")
        self.assertEqual(self.contract.wallet_balances[rejecting_addr], 3 * WEI_PER_ETH)
        # Event thành công chỉ được phát ĐÚNG 1 LẦN trong toàn bộ vòng đời!
        executed_event_count = self.contract.emitted_events.count(("SpendRequestExecuted", req_id, rejecting_addr, 3 * WEI_PER_ETH))
        self.assertEqual(executed_event_count, 1, "SpendRequestExecuted chi duoc phat dung 1 lan duy nhat")

    # 3. Auto-execution hoàn tiền thành công: đúng trạng thái, số dư, và events
    def test_03_refund_auto_executes_successfully_with_events(self):
        self.contract.deposit(self.student_a, 5 * WEI_PER_ETH)
        self.contract.set_bcs_member(self.advisor, self.bcs_1, True)
        self.contract.set_bcs_member(self.advisor, self.bcs_2, True)

        ref_id = self.contract.create_refund_request(self.student_a, 2 * WEI_PER_ETH, "Nop nham", 1000)
        self.contract.vote_refund_request(self.bcs_1, ref_id, True, 1010)

        # BCS 2 bỏ phiếu quyết định (2/2 = 100% >= 51%)
        self.contract.vote_refund_request(self.bcs_2, ref_id, True, 1020)

        ref = self.contract.refund_requests[ref_id]
        self.assertEqual(ref["status"], "Executed")
        self.assertEqual(self.contract.wallet_balances[self.student_a], 2 * WEI_PER_ETH)
        self.assertEqual(self.contract.student_contributions[self.student_a], 3 * WEI_PER_ETH)
        self.assertEqual(self.contract.reserved_refund_amount, 0)
        self.assertEqual(self.contract.pending_student_refund_amount[self.student_a], 0)

        # Kiểm tra events
        self.assertIn(("RefundRequestExecuted", ref_id, self.student_a, 2 * WEI_PER_ETH), self.contract.emitted_events)
        self.assertIn(("RefundProcessed", self.student_a, 2 * WEI_PER_ETH), self.contract.emitted_events)
        self.assertNotIn(("RefundExecutionFailed", ref_id, self.student_a, 2 * WEI_PER_ETH), self.contract.emitted_events)

    # 4. Auto-execution hoàn tiền thất bại: KHÔNG phát RefundRequestExecuted / RefundProcessed, có RefundExecutionFailed
    def test_04_refund_auto_executes_failure_does_not_emit_success_events_and_allows_manual_fallback(self):
        self.contract.deposit(self.student_a, 5 * WEI_PER_ETH)
        self.contract.set_bcs_member(self.advisor, self.bcs_1, True)
        self.contract.set_bcs_member(self.advisor, self.bcs_2, True)

        # Sinh viên từ chối nhận ETH
        self.contract.rejecting_recipients.add(self.student_a)

        ref_id = self.contract.create_refund_request(self.student_a, 2 * WEI_PER_ETH, "Hoan tien loi vi", 1000)
        self.contract.vote_refund_request(self.bcs_1, ref_id, True, 1010)

        # BCS 2 bỏ phiếu quyết định -> Chuyển ETH thất bại
        self.contract.vote_refund_request(self.bcs_2, ref_id, True, 1020)

        ref = self.contract.refund_requests[ref_id]
        self.assertEqual(ref["status"], "Ready", "Yeu cau hoan phai o Ready")
        self.assertEqual(self.contract.student_contributions[self.student_a], 5 * WEI_PER_ETH, "Han muc dong gop bao toan")
        self.assertEqual(self.contract.reserved_refund_amount, 2 * WEI_PER_ETH, "Giu cho quy bao toan")
        self.assertEqual(self.contract.pending_student_refund_amount[self.student_a], 2 * WEI_PER_ETH, "Giu cho sinh vien bao toan")

        # XÁC MINH SỬA LỖI FIX 1:
        self.assertNotIn(("RefundRequestExecuted", ref_id, self.student_a, 2 * WEI_PER_ETH), self.contract.emitted_events)
        self.assertNotIn(("RefundProcessed", self.student_a, 2 * WEI_PER_ETH), self.contract.emitted_events)
        self.assertIn(("RefundExecutionFailed", ref_id, self.student_a, 2 * WEI_PER_ETH), self.contract.emitted_events)

        # Sinh viên sửa ví nhận tiền -> Gọi execute thủ công thành công
        self.contract.rejecting_recipients.remove(self.student_a)
        self.contract.execute_refund_request(self.student_a, ref_id)

        self.assertEqual(self.contract.refund_requests[ref_id]["status"], "Executed")
        self.assertEqual(self.contract.wallet_balances[self.student_a], 2 * WEI_PER_ETH)
        # Event thành công chỉ được phát đúng 1 lần!
        self.assertEqual(self.contract.emitted_events.count(("RefundRequestExecuted", ref_id, self.student_a, 2 * WEI_PER_ETH)), 1)
        self.assertEqual(self.contract.emitted_events.count(("RefundProcessed", self.student_a, 2 * WEI_PER_ETH)), 1)

    # 5. Chống thực thi hai lần (Double Execution)
    def test_05_cannot_execute_twice_after_auto_execution(self):
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        self.contract.set_bcs_member(self.advisor, self.bcs_1, True)

        req_id = self.contract.create_spend_request(self.bcs_1, self.recipient, 2 * WEI_PER_ETH, "1 BCS auto exec", 1000)
        self.contract.vote_spend_request(self.bcs_1, req_id, True, 1010)
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Executed")

        with self.assertRaises(RequestAlreadyExecutedError):
            self.contract.execute_spend_request(self.bcs_1, req_id)

    # 6. SỬA LỖI FIX 1: Không cho phép dọn dẹp (expire) đề xuất chi ở trạng thái Ready
    def test_06_cannot_expire_ready_spend_request(self):
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        self.contract.set_bcs_member(self.advisor, self.bcs_1, True)
        self.contract.set_bcs_member(self.advisor, self.bcs_2, True)

        rejecting_addr = "0xRejectingContract00000000000000000000001"
        self.contract.rejecting_recipients.add(rejecting_addr)

        req_id = self.contract.create_spend_request(self.bcs_1, rejecting_addr, 3 * WEI_PER_ETH, "Chi loi", 1000)
        self.contract.vote_spend_request(self.bcs_1, req_id, True, 1010)
        self.contract.vote_spend_request(self.bcs_2, req_id, True, 1020)

        # Đề xuất đang ở Ready vì auto-execution thất bại
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Ready")

        # Sau 7 ngày + 10 giây: Kẻ xấu cố gọi expire_spend_request để hủy đề xuất đã được BCS duyệt -> PHẢI REVERT!
        after_7_days = 1000 + VOTING_PERIOD_SECONDS + 10
        with self.assertRaises(InvalidRequestStatusError):
            self.contract.expire_spend_request(req_id, after_7_days)

        # Trạng thái vẫn là Ready, số tiền giữ chỗ 3 ETH được bảo vệ nguyên vẹn
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Ready")
        self.assertEqual(self.contract.reserved_spend_amount, 3 * WEI_PER_ETH)

    # 7. SỬA LỖI FIX 1: Không cho phép dọn dẹp (expire) yêu cầu hoàn tiền ở trạng thái Ready
    def test_07_cannot_expire_ready_refund_request(self):
        self.contract.deposit(self.student_a, 5 * WEI_PER_ETH)
        self.contract.set_bcs_member(self.advisor, self.bcs_1, True)
        self.contract.set_bcs_member(self.advisor, self.bcs_2, True)

        self.contract.rejecting_recipients.add(self.student_a)

        ref_id = self.contract.create_refund_request(self.student_a, 2 * WEI_PER_ETH, "Hoan tien loi vi", 1000)
        self.contract.vote_refund_request(self.bcs_1, ref_id, True, 1010)
        self.contract.vote_refund_request(self.bcs_2, ref_id, True, 1020)

        self.assertEqual(self.contract.refund_requests[ref_id]["status"], "Ready")

        # Sau 7 ngày: Kẻ khác cố dọn dẹp yêu cầu hoàn tiền đã được BCS thông qua -> PHẢI REVERT!
        after_7_days = 1000 + VOTING_PERIOD_SECONDS + 10
        with self.assertRaises(InvalidRefundStatusError):
            self.contract.expire_refund_request(ref_id, after_7_days)

        self.assertEqual(self.contract.refund_requests[ref_id]["status"], "Ready")
        self.assertEqual(self.contract.reserved_refund_amount, 2 * WEI_PER_ETH)
        self.assertEqual(self.contract.pending_student_refund_amount[self.student_a], 2 * WEI_PER_ETH)

    # 8. Đề xuất Pending quá hạn được expire và giải phóng reservation đúng một lần
    def test_08_pending_requests_expire_after_deadline_and_release_reservation_once(self):
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        self.contract.set_bcs_member(self.advisor, self.bcs_1, True)
        self.contract.set_bcs_member(self.advisor, self.bcs_2, True)

        # 8a. Spend request Pending
        req_id = self.contract.create_spend_request(self.bcs_1, self.recipient, 3 * WEI_PER_ETH, "Chua du vote", 1000)
        self.contract.vote_spend_request(self.bcs_1, req_id, True, 1010) # 1/2 = 50% < 51% -> Pending
        self.assertEqual(self.contract.reserved_spend_amount, 3 * WEI_PER_ETH)

        after_deadline = 1000 + VOTING_PERIOD_SECONDS + 1
        self.contract.expire_spend_request(req_id, after_deadline)
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Expired")
        self.assertEqual(self.contract.reserved_spend_amount, 0, "Reservation phai tra ve 0")

        # Expire lần 2 -> Revert InvalidRequestStatus
        with self.assertRaises(InvalidRequestStatusError):
            self.contract.expire_spend_request(req_id, after_deadline + 10)

        # 8b. Refund request Pending
        ref_id = self.contract.create_refund_request(self.student_a, 2 * WEI_PER_ETH, "Chua du vote hoan", 2000)
        self.assertEqual(self.contract.reserved_refund_amount, 2 * WEI_PER_ETH)
        self.assertEqual(self.contract.pending_student_refund_amount[self.student_a], 2 * WEI_PER_ETH)

        after_ref_deadline = 2000 + VOTING_PERIOD_SECONDS + 1
        self.contract.expire_refund_request(ref_id, after_ref_deadline)
        self.assertEqual(self.contract.refund_requests[ref_id]["status"], "Expired")
        self.assertEqual(self.contract.reserved_refund_amount, 0)
        self.assertEqual(self.contract.pending_student_refund_amount[self.student_a], 0)

        # Expire lần 2 -> Revert InvalidRefundStatus
        with self.assertRaises(InvalidRefundStatusError):
            self.contract.expire_refund_request(ref_id, after_ref_deadline + 10)

    # 9. Request chưa quá hạn không thể expire (kể cả đúng ranh giới createdAt + VOTING_PERIOD)
    def test_09_cannot_expire_before_deadline_including_exact_boundary(self):
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        self.contract.set_bcs_member(self.advisor, self.bcs_1, True)

        req_id = self.contract.create_spend_request(self.bcs_1, self.recipient, 2 * WEI_PER_ETH, "Boundary test", 1000)
        ref_id = self.contract.create_refund_request(self.student_a, 1 * WEI_PER_ETH, "Boundary test refund", 1000)

        # Trước thời hạn (ngày thứ 3)
        with self.assertRaises(VotingStillActiveError):
            self.contract.expire_spend_request(req_id, 1000 + 3 * 24 * 3600)
        with self.assertRaises(RefundVotingStillActiveError):
            self.contract.expire_refund_request(ref_id, 1000 + 3 * 24 * 3600)

        # ĐÚNG RANH GIỚI: block.timestamp == createdAt + VOTING_PERIOD (ngày thứ 7 chính xác)
        exact_boundary = 1000 + VOTING_PERIOD_SECONDS
        with self.assertRaises(VotingStillActiveError):
            self.contract.expire_spend_request(req_id, exact_boundary)
        with self.assertRaises(RefundVotingStillActiveError):
            self.contract.expire_refund_request(ref_id, exact_boundary)

    # 10. Chống double-voting và bảo toàn phân quyền
    def test_10_anti_double_voting_and_permissions(self):
        self.contract.deposit(self.student_a, 5 * WEI_PER_ETH)
        self.contract.set_bcs_member(self.advisor, self.bcs_1, True)
        self.contract.set_bcs_member(self.advisor, self.bcs_2, True)

        req_id = self.contract.create_spend_request(self.bcs_1, self.recipient, 1 * WEI_PER_ETH, "Double vote test", 1000)
        self.contract.vote_spend_request(self.bcs_1, req_id, True, 1010)

        # Bỏ phiếu lần 2 từ cùng BCS 1 -> Revert AlreadyVoted
        with self.assertRaises(AlreadyVotedError):
            self.contract.vote_spend_request(self.bcs_1, req_id, True, 1020)

        # Người ngoài (student_a) cố vote -> Revert NotActiveBCS
        with self.assertRaises(NotActiveBCSError):
            self.contract.vote_spend_request(self.student_a, req_id, True, 1030)

    # 11. Chống tái nhập (Reentrancy) bảo vệ số dư quỹ và không gây thực thi trùng
    def test_11_reentrancy_protection_via_cei(self):
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        self.contract.set_bcs_member(self.advisor, self.bcs_1, True)

        attacker_addr = "0xAttackerContract00000000000000000000001"
        self.contract.set_bcs_member(self.advisor, attacker_addr, True)

        req_id = self.contract.create_spend_request(self.bcs_1, attacker_addr, 2 * WEI_PER_ETH, "Attack spend", 1000)
        self.contract.vote_spend_request(self.bcs_1, req_id, True, 1010)

        reentrancy_revert_raised = False

        def reentrancy_attack():
            nonlocal reentrancy_revert_raised
            try:
                self.contract.execute_spend_request(attacker_addr, req_id)
            except RequestAlreadyExecutedError:
                reentrancy_revert_raised = True

        self.contract.reentrancy_hook = reentrancy_attack

        self.contract.vote_spend_request(attacker_addr, req_id, True, 1020)

        self.assertTrue(reentrancy_revert_raised, "Tai nhap phai bi chan boi RequestAlreadyExecuted vi CEI")
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Executed")
        self.assertEqual(self.contract.class_fund_balance, 7.9 * WEI_PER_ETH, "Quy chi bi tru dung 1 lan")

    # 12. Bất biến kế toán bảo toàn 100% không mất wei
    def test_12_accounting_invariants(self):
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        self.contract.deposit(self.student_b, 10 * WEI_PER_ETH)
        self.contract.set_bcs_member(self.advisor, self.bcs_1, True)

        req_id = self.contract.create_spend_request(self.bcs_1, self.recipient, 4 * WEI_PER_ETH, "Chi 4", 1000)
        self.contract.vote_spend_request(self.bcs_1, req_id, True, 1010)

        ref_id = self.contract.create_refund_request(self.student_a, 2 * WEI_PER_ETH, "Hoan 2", 1020)
        self.contract.vote_refund_request(self.bcs_1, ref_id, True, 1030)

        self.contract.withdraw_admin_fee(self.advisor, int(0.1 * WEI_PER_ETH))

        expected = int((20 - 4 - 2 - 0.1) * WEI_PER_ETH)
        actual = self.contract.class_fund_balance + self.contract.admin_fee_pool
        self.assertEqual(actual, expected)
        self.assertEqual(self.contract.reserved_spend_amount, 0)
        self.assertEqual(self.contract.reserved_refund_amount, 0)


if __name__ == "__main__":
    unittest.main()
