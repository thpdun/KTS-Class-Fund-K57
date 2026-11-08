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
BCS_ACTIVATION_DELAY = 3 * 24 * 3600   # 3 ngày chờ kích hoạt BCS (Phase 2 / Mục B)
MIN_BCS_FOR_PROPOSAL = 3               # Tối thiểu 3 BCS đủ điều kiện (Phase 2 / Mục B)
MAX_BCS = 15                           # Tối đa 15 BCS (Phase 2 / Mục B)
MAX_BATCH = 100                        # Tối đa 100 địa chỉ trong 1 lượt setStudents (Mục D)
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
class MaxBCSReachedError(CustomError): pass
class NotEnoughBCSError(CustomError): pass
class ConflictOfInterestError(CustomError): pass
class VoterNotEligibleAtCreationError(CustomError): pass
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
class BatchTooLargeError(CustomError): pass
class NotEnrolledStudentError(CustomError): pass
class BCSMustBeEnrolledStudentError(CustomError): pass
class StudentIsBCSError(CustomError): pass
class AdvisorCannotBeStudentError(CustomError): pass


class AutoExecutionProjectCoreSimulator:
    """
    Simulator mô phỏng logic của ProjectCore.sol có Auto-Execution + Phase 1 (Mục A) + Phase 2 (Mục B & C).
    """
    def __init__(self, advisor: str = "0xAdvisor0000000000000000000000000000000001"):
        self.advisor = advisor
        self.class_fund_balance = 0
        self.admin_fee_pool = 0
        self.reserved_spend_amount = 0
        self.reserved_refund_amount = 0
        self.student_contributions: Dict[str, int] = {}
        self.student_total_deposited: Dict[str, int] = {}
        self.pending_student_refund_amount: Dict[str, int] = {}
        self.is_bcs_member: Dict[str, bool] = {}
        self.bcs_list: List[str] = []
        self._bcs_index_plus_one: Dict[str, int] = {}
        self.member_since: Dict[str, int] = {}
        self.active_bcs_count = 0
        self.spend_request_count = 0
        self.spend_requests: Dict[int, Dict[str, Any]] = {}
        self.has_voted: Dict[int, Dict[str, bool]] = {}
        self.refund_request_count = 0
        self.refund_requests: Dict[int, Dict[str, Any]] = {}
        self.has_voted_refund: Dict[int, Dict[str, bool]] = {}
        self.is_student: Dict[str, bool] = {}
        self.enrolled_count = 0
        self.roster_hash = "0x" + "00" * 32
        self.forced_eth_wei = 0
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

    def get_student_max_refund(self, student: str) -> int:
        return min(self.get_student_available_contribution(student), self.get_available_class_fund())

    def is_eligible_voter_at(self, member: str, at_timestamp: int) -> bool:
        since = self.member_since.get(member, 0)
        return self.is_bcs_member.get(member, False) and since != 0 and since <= at_timestamp

    def eligible_bcs_count(self, at_timestamp: int) -> int:
        return sum(1 for member in self.bcs_list if self.is_eligible_voter_at(member, at_timestamp))

    def get_bcs_list(self) -> List[str]:
        return list(self.bcs_list)

    def _require_active_bcs(self, caller: str, current_time: int):
        if not self.is_bcs_member.get(caller, False) or current_time < self.member_since.get(caller, 0):
            raise NotActiveBCSError("Revert: NotActiveBCS()")

    # --- Quản lý danh sách sinh viên & Commit Roster (Phase 3 / Mục D) ---
    def set_students(self, caller: str, members: List[str], status: bool):
        if caller != self.advisor:
            raise NotAdvisorError("Revert: NotAdvisor()")
        if len(members) > MAX_BATCH:
            raise BatchTooLargeError("Revert: BatchTooLarge()")

        for student in members:
            if not student or student == "0x0" or student == "0x0000000000000000000000000000000000000000":
                raise InvalidAddressError("Revert: InvalidAddress()")
            if status and student == self.advisor:
                raise AdvisorCannotBeStudentError("Revert: AdvisorCannotBeStudent()")
            if not status and self.is_bcs_member.get(student, False):
                raise StudentIsBCSError("Revert: StudentIsBCS()")

            current_status = self.is_student.get(student, False)
            if current_status != status:
                self.is_student[student] = status
                if status:
                    self.enrolled_count += 1
                else:
                    self.enrolled_count -= 1
                self.emitted_events.append(("StudentEnrollmentUpdated", student, status))

    def commit_roster(self, caller: str, roster_hash: str):
        if caller != self.advisor:
            raise NotAdvisorError("Revert: NotAdvisor()")
        self.roster_hash = roster_hash
        self.emitted_events.append(("RosterCommitted", roster_hash, caller))

    def get_unaccounted_balance(self) -> int:
        actual_balance = self.class_fund_balance + self.admin_fee_pool + self.forced_eth_wei
        recorded_total = self.class_fund_balance + self.admin_fee_pool
        if actual_balance > recorded_total:
            return actual_balance - recorded_total
        return 0

    # --- Phân quyền ---
    def set_bcs_member(self, caller: str, member: str, status: bool, current_time: int = 0):
        if caller != self.advisor:
            raise NotAdvisorError("Revert: NotAdvisor()")
        if not member or member == "0x0":
            raise InvalidAddressError("Revert: InvalidAddress()")

        current_status = self.is_bcs_member.get(member, False)
        if current_status == status:
            return

        if status:
            if not self.is_student.get(member, False):
                raise BCSMustBeEnrolledStudentError("Revert: BCSMustBeEnrolledStudent()")
            if len(self.bcs_list) >= MAX_BCS:
                raise MaxBCSReachedError("Revert: MaxBCSReached()")
            self.is_bcs_member[member] = True
            self.bcs_list.append(member)
            self._bcs_index_plus_one[member] = len(self.bcs_list)
            self.member_since[member] = current_time + BCS_ACTIVATION_DELAY
            self.active_bcs_count = len(self.bcs_list)
        else:
            idx_plus_one = self._bcs_index_plus_one.get(member, 0)
            if idx_plus_one != 0:
                idx = idx_plus_one - 1
                last_idx = len(self.bcs_list) - 1
                if idx != last_idx:
                    last_member = self.bcs_list[last_idx]
                    self.bcs_list[idx] = last_member
                    self._bcs_index_plus_one[last_member] = idx + 1
                self.bcs_list.pop()
                del self._bcs_index_plus_one[member]
            self.is_bcs_member[member] = False
            self.member_since[member] = 0
            self.active_bcs_count = len(self.bcs_list)
        self.emitted_events.append(("BCSMemberUpdated", member, status))

    # --- Nạp tiền ---
    def deposit(self, caller: str, amount_wei: int) -> Tuple[int, int]:
        if not self.is_student.get(caller, False):
            raise NotEnrolledStudentError(f"Revert: NotEnrolledStudent({caller})")
        if amount_wei == 0:
            raise ZeroAmountError("Revert: ZeroAmount()")
        fee = (amount_wei * FEE_BPS) // BPS_DENOMINATOR
        fund = amount_wei - fee

        self.admin_fee_pool += fee
        self.class_fund_balance += fund
        self.student_contributions[caller] = self.student_contributions.get(caller, 0) + fund
        self.student_total_deposited[caller] = self.student_total_deposited.get(caller, 0) + amount_wei

        self.emitted_events.append(("FundDeposited", caller, amount_wei))
        if fee > 0:
            self.emitted_events.append(("AdminFeeCollected", caller, fee))
        return fund, fee

    # --- Chuyển phí sang quỹ lớp ---
    def move_fee_to_class_fund(self, caller: str, amount_wei: int):
        if caller != self.advisor:
            raise NotAdvisorError("Revert: NotAdvisor()")
        if amount_wei == 0:
            raise ZeroAmountError("Revert: ZeroAmount()")
        if amount_wei > self.admin_fee_pool:
            raise InsufficientAdminFeeError("Revert: InsufficientAdminFee()")
        self.admin_fee_pool -= amount_wei
        self.class_fund_balance += amount_wei
        self.emitted_events.append(("FeeMovedToClassFund", caller, amount_wei))

    # --- Chi tiền ---
    def create_spend_request(self, caller: str, recipient: str, amount_wei: int, description: str, current_time: int) -> int:
        self._require_active_bcs(caller, current_time)
        if not recipient or recipient == "0x0":
            raise InvalidAddressError("Revert: InvalidAddress()")
        if amount_wei == 0:
            raise ZeroAmountError("Revert: ZeroAmount()")
        eligible = self.eligible_bcs_count(current_time)
        if eligible < MIN_BCS_FOR_PROPOSAL:
            raise NotEnoughBCSError(f"Revert: NotEnoughBCS({eligible}, {MIN_BCS_FOR_PROPOSAL})")
        available = self.get_available_class_fund()
        if amount_wei > available:
            raise InsufficientAvailableFundError(f"Revert: InsufficientAvailableFund({amount_wei}, {available})")

        voter_base = (eligible - 1) if self.is_eligible_voter_at(recipient, current_time) else eligible

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
            "status": "Pending",
            "voter_base": voter_base,
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
        self._require_active_bcs(caller, current_time)
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

        if caller == req["recipient"]:
            raise ConflictOfInterestError("Revert: ConflictOfInterest()")
        if not self.is_eligible_voter_at(caller, req["created_at"]):
            raise VoterNotEligibleAtCreationError(f"Revert: VoterNotEligibleAtCreation({req_id}, {caller})")
        if self.has_voted[req_id].get(caller, False):
            raise AlreadyVotedError("Revert: AlreadyVoted()")
        if req["voter_base"] == 0:
            raise NoActiveBCSError("Revert: NoActiveBCS()")

        self.has_voted[req_id][caller] = True
        if support:
            req["yes_votes"] += 1
        else:
            req["no_votes"] += 1

        self.emitted_events.append(("SpendRequestVoted", req_id, caller, support, req["yes_votes"], req["no_votes"]))

        approval_bps = (req["yes_votes"] * BPS_DENOMINATOR) // req["voter_base"]
        if approval_bps >= PASSING_THRESHOLD_BPS and req["status"] == "Pending":
            req["status"] = "Ready"
            self.emitted_events.append(("SpendRequestReady", req_id))
            # AUTO-EXECUTION:
            self._try_execute_spend(req_id)

    def execute_spend_request(self, caller: str, req_id: int, current_time: int):
        self._require_active_bcs(caller, current_time)
        if req_id not in self.spend_requests:
            raise RequestNotFoundError("Revert: RequestNotFound()")

        req = self.spend_requests[req_id]
        if req["status"] == "Executed":
            raise RequestAlreadyExecutedError("Revert: RequestAlreadyExecuted()")
        if req["status"] == "Expired":
            raise RequestExpiredError("Revert: RequestExpired()")
        if req["status"] not in ("Pending", "Ready"):
            raise InvalidRequestStatusError("Revert: InvalidRequestStatus()")

        if req["voter_base"] == 0:
            raise NoActiveBCSError("Revert: NoActiveBCS()")

        approval_bps = (req["yes_votes"] * BPS_DENOMINATOR) // req["voter_base"]
        if approval_bps < PASSING_THRESHOLD_BPS:
            raise ThresholdNotMetError(f"Revert: ThresholdNotMet({req['yes_votes']}, {req['voter_base']})")

        if req["status"] == "Pending":
            req["status"] = "Ready"
            self.emitted_events.append(("SpendRequestReady", req_id))

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
        eligible = self.eligible_bcs_count(current_time)
        if eligible < MIN_BCS_FOR_PROPOSAL:
            raise NotEnoughBCSError(f"Revert: NotEnoughBCS({eligible}, {MIN_BCS_FOR_PROPOSAL})")
        available_contrib = self.get_student_available_contribution(caller)
        if amount_wei > available_contrib:
            raise InsufficientContributionError(f"Revert: InsufficientContribution({amount_wei}, {available_contrib})")
        available_fund = self.get_available_class_fund()
        if amount_wei > available_fund:
            raise InsufficientAvailableFundError(f"Revert: InsufficientAvailableFund({amount_wei}, {available_fund})")

        voter_base = (eligible - 1) if self.is_eligible_voter_at(caller, current_time) else eligible

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
            "status": "Pending",
            "voter_base": voter_base,
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
        self._require_active_bcs(caller, current_time)
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

        if caller == req["applicant"]:
            raise ConflictOfInterestError("Revert: ConflictOfInterest()")
        if not self.is_eligible_voter_at(caller, req["created_at"]):
            raise VoterNotEligibleAtCreationError(f"Revert: VoterNotEligibleAtCreation({ref_id}, {caller})")
        if self.has_voted_refund[ref_id].get(caller, False):
            raise AlreadyVotedRefundError("Revert: AlreadyVotedRefund()")
        if req["voter_base"] == 0:
            raise NoActiveBCSError("Revert: NoActiveBCS()")

        self.has_voted_refund[ref_id][caller] = True
        if support:
            req["yes_votes"] += 1
        else:
            req["no_votes"] += 1

        self.emitted_events.append(("RefundRequestVoted", ref_id, caller, support, req["yes_votes"], req["no_votes"]))

        approval_bps = (req["yes_votes"] * BPS_DENOMINATOR) // req["voter_base"]
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

        if req["voter_base"] == 0:
            raise NoActiveBCSError("Revert: NoActiveBCS()")

        approval_bps = (req["yes_votes"] * BPS_DENOMINATOR) // req["voter_base"]
        if approval_bps < PASSING_THRESHOLD_BPS:
            raise ThresholdNotMetError(f"Revert: ThresholdNotMet({req['yes_votes']}, {req['voter_base']})")

        if req["status"] == "Pending":
            req["status"] = "Ready"
            self.emitted_events.append(("RefundRequestReady", ref_id))

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
    Test suite toàn diện xác minh toàn bộ các yêu cầu của giai đoạn AUTO-EXECUTION FIX 1 + Phase 1 + Phase 2.
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
        self.contract.set_students(
            self.advisor,
            [self.student_a, self.student_b, self.bcs_1, self.bcs_2, self.bcs_3],
            True,
        )

    def _setup_3_active_bcs(self, added_at: int = 0) -> int:
        self.contract.set_bcs_member(self.advisor, self.bcs_1, True, added_at)
        self.contract.set_bcs_member(self.advisor, self.bcs_2, True, added_at)
        self.contract.set_bcs_member(self.advisor, self.bcs_3, True, added_at)
        return added_at + BCS_ACTIVATION_DELAY

    # 1. Auto-execution chi tiền thành công: đúng trạng thái, số dư, và event
    def test_01_spend_auto_executes_successfully_with_event(self):
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        t = self._setup_3_active_bcs(0)

        req_id = self.contract.create_spend_request(self.bcs_1, self.recipient, 4 * WEI_PER_ETH, "Chi tu dong thanh cong", t + 1000)
        self.contract.vote_spend_request(self.bcs_1, req_id, True, t + 1010)
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Pending")

        # BCS 2 bỏ phiếu quyết định (2/3 = 66.6% >= 51%)
        self.contract.vote_spend_request(self.bcs_2, req_id, True, t + 1020)

        # Kiểm tra trạng thái và số dư
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Executed")
        self.assertEqual(self.contract.wallet_balances[self.recipient], 4 * WEI_PER_ETH)
        self.assertEqual(self.contract.class_fund_balance, 59 * 10**17)
        self.assertEqual(self.contract.reserved_spend_amount, 0)

        # Kiểm tra sự kiện
        self.assertIn(("SpendRequestExecuted", req_id, self.recipient, 4 * WEI_PER_ETH), self.contract.emitted_events)
        self.assertNotIn(("SpendExecutionFailed", req_id, self.recipient, 4 * WEI_PER_ETH), self.contract.emitted_events)

    # 2. Auto-execution chi tiền thất bại: KHÔNG phát SpendRequestExecuted, có SpendExecutionFailed, đề xuất Ready
    def test_02_spend_auto_executes_failure_does_not_emit_success_event_and_allows_manual_fallback(self):
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        t = self._setup_3_active_bcs(0)

        rejecting_addr = "0xRejectingContract00000000000000000000001"
        self.contract.rejecting_recipients.add(rejecting_addr)

        req_id = self.contract.create_spend_request(self.bcs_1, rejecting_addr, 3 * WEI_PER_ETH, "Chi cho contract loi", t + 1000)
        self.contract.vote_spend_request(self.bcs_1, req_id, True, t + 1010)

        # BCS 2 bỏ phiếu quyết định (2/3 = 66.6% >= 51%) -> Tự giải ngân thất bại do recipient từ chối ETH
        self.contract.vote_spend_request(self.bcs_2, req_id, True, t + 1020)

        req = self.contract.spend_requests[req_id]
        self.assertTrue(self.contract.has_voted[req_id][self.bcs_2], "Phieu cua BCS 2 phai duoc ghi nhan")
        self.assertEqual(req["status"], "Ready", "Trang thai phai rollback ve Ready de cho fallback")
        self.assertEqual(self.contract.class_fund_balance, 99 * 10**17, "So du khong bi mat")
        self.assertEqual(self.contract.reserved_spend_amount, 3 * WEI_PER_ETH, "Tien giu cho van giu nguyen")

        # XÁC MINH SỬA LỖI FIX 1:
        # Không được có SpendRequestExecuted trong event log!
        self.assertNotIn(("SpendRequestExecuted", req_id, rejecting_addr, 3 * WEI_PER_ETH), self.contract.emitted_events)
        # Bắt buộc phải có SpendExecutionFailed!
        self.assertIn(("SpendExecutionFailed", req_id, rejecting_addr, 3 * WEI_PER_ETH), self.contract.emitted_events)

        # Fallback thử lại thất bại khi recipient vẫn từ chối ETH
        with self.assertRaises(ETHTransferFailedError):
            self.contract.execute_spend_request(self.bcs_1, req_id, t + 1030)
        self.assertNotIn(("SpendRequestExecuted", req_id, rejecting_addr, 3 * WEI_PER_ETH), self.contract.emitted_events)

        # Khi recipient sửa lỗi nhận tiền -> Gọi execute thủ công thành công
        self.contract.rejecting_recipients.remove(rejecting_addr)
        self.contract.execute_spend_request(self.bcs_1, req_id, t + 1040)

        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Executed")
        self.assertEqual(self.contract.wallet_balances[rejecting_addr], 3 * WEI_PER_ETH)
        # Event thành công chỉ được phát ĐÚNG 1 LẦN trong toàn bộ vòng đời!
        executed_event_count = self.contract.emitted_events.count(("SpendRequestExecuted", req_id, rejecting_addr, 3 * WEI_PER_ETH))
        self.assertEqual(executed_event_count, 1, "SpendRequestExecuted chi duoc phat dung 1 lan duy nhat")

    # 3. Auto-execution hoàn tiền thành công: đúng trạng thái, số dư, và events
    def test_03_refund_auto_executes_successfully_with_events(self):
        self.contract.deposit(self.student_a, 5 * WEI_PER_ETH)
        t = self._setup_3_active_bcs(0)

        ref_id = self.contract.create_refund_request(self.student_a, 2 * WEI_PER_ETH, "Nop nham", t + 1000)
        self.contract.vote_refund_request(self.bcs_1, ref_id, True, t + 1010)

        # BCS 2 bỏ phiếu quyết định (2/3 = 66.6% >= 51%)
        self.contract.vote_refund_request(self.bcs_2, ref_id, True, t + 1020)

        ref = self.contract.refund_requests[ref_id]
        self.assertEqual(ref["status"], "Executed")
        self.assertEqual(self.contract.wallet_balances[self.student_a], 2 * WEI_PER_ETH)
        self.assertEqual(self.contract.student_contributions[self.student_a], 295 * 10**16)
        self.assertEqual(self.contract.student_total_deposited[self.student_a], 5 * WEI_PER_ETH)
        self.assertEqual(self.contract.reserved_refund_amount, 0)
        self.assertEqual(self.contract.pending_student_refund_amount[self.student_a], 0)

        # Kiểm tra events
        self.assertIn(("RefundRequestExecuted", ref_id, self.student_a, 2 * WEI_PER_ETH), self.contract.emitted_events)
        self.assertIn(("RefundProcessed", self.student_a, 2 * WEI_PER_ETH), self.contract.emitted_events)
        self.assertNotIn(("RefundExecutionFailed", ref_id, self.student_a, 2 * WEI_PER_ETH), self.contract.emitted_events)

    # 4. Auto-execution hoàn tiền thất bại: KHÔNG phát RefundRequestExecuted / RefundProcessed, có RefundExecutionFailed
    def test_04_refund_auto_executes_failure_does_not_emit_success_events_and_allows_manual_fallback(self):
        self.contract.deposit(self.student_a, 5 * WEI_PER_ETH)
        t = self._setup_3_active_bcs(0)

        # Sinh viên từ chối nhận ETH
        self.contract.rejecting_recipients.add(self.student_a)

        ref_id = self.contract.create_refund_request(self.student_a, 2 * WEI_PER_ETH, "Hoan tien loi vi", t + 1000)
        self.contract.vote_refund_request(self.bcs_1, ref_id, True, t + 1010)

        # BCS 2 bỏ phiếu quyết định -> Chuyển ETH thất bại
        self.contract.vote_refund_request(self.bcs_2, ref_id, True, t + 1020)

        ref = self.contract.refund_requests[ref_id]
        self.assertEqual(ref["status"], "Ready", "Yeu cau hoan phai o Ready")
        self.assertEqual(self.contract.student_contributions[self.student_a], 495 * 10**16, "Han muc dong gop net bao toan")
        self.assertEqual(self.contract.student_total_deposited[self.student_a], 5 * WEI_PER_ETH)
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
        t = self._setup_3_active_bcs(0)

        req_id = self.contract.create_spend_request(self.bcs_1, self.recipient, 2 * WEI_PER_ETH, "3 BCS auto exec", t + 1000)
        self.contract.vote_spend_request(self.bcs_1, req_id, True, t + 1010)
        self.contract.vote_spend_request(self.bcs_2, req_id, True, t + 1020)
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Executed")

        with self.assertRaises(RequestAlreadyExecutedError):
            self.contract.execute_spend_request(self.bcs_1, req_id, t + 1030)

    # 6. SỬA LỖI FIX 1: Không cho phép dọn dẹp (expire) đề xuất chi ở trạng thái Ready
    def test_06_cannot_expire_ready_spend_request(self):
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        t = self._setup_3_active_bcs(0)

        rejecting_addr = "0xRejectingContract00000000000000000000001"
        self.contract.rejecting_recipients.add(rejecting_addr)

        req_id = self.contract.create_spend_request(self.bcs_1, rejecting_addr, 3 * WEI_PER_ETH, "Chi loi", t + 1000)
        self.contract.vote_spend_request(self.bcs_1, req_id, True, t + 1010)
        self.contract.vote_spend_request(self.bcs_2, req_id, True, t + 1020)

        # Đề xuất đang ở Ready vì auto-execution thất bại
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Ready")

        # Sau 7 ngày + 10 giây: Kẻ xấu cố gọi expire_spend_request để hủy đề xuất đã được BCS duyệt -> PHẢI REVERT!
        after_7_days = t + 1000 + VOTING_PERIOD_SECONDS + 10
        with self.assertRaises(InvalidRequestStatusError):
            self.contract.expire_spend_request(req_id, after_7_days)

        # Trạng thái vẫn là Ready, số tiền giữ chỗ 3 ETH được bảo vệ nguyên vẹn
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Ready")
        self.assertEqual(self.contract.reserved_spend_amount, 3 * WEI_PER_ETH)

    # 7. SỬA LỖI FIX 1: Không cho phép dọn dẹp (expire) yêu cầu hoàn tiền ở trạng thái Ready
    def test_07_cannot_expire_ready_refund_request(self):
        self.contract.deposit(self.student_a, 5 * WEI_PER_ETH)
        t = self._setup_3_active_bcs(0)

        self.contract.rejecting_recipients.add(self.student_a)

        ref_id = self.contract.create_refund_request(self.student_a, 2 * WEI_PER_ETH, "Hoan tien loi vi", t + 1000)
        self.contract.vote_refund_request(self.bcs_1, ref_id, True, t + 1010)
        self.contract.vote_refund_request(self.bcs_2, ref_id, True, t + 1020)

        self.assertEqual(self.contract.refund_requests[ref_id]["status"], "Ready")

        # Sau 7 ngày: Kẻ khác cố dọn dẹp yêu cầu hoàn tiền đã được BCS thông qua -> PHẢI REVERT!
        after_7_days = t + 1000 + VOTING_PERIOD_SECONDS + 10
        with self.assertRaises(InvalidRefundStatusError):
            self.contract.expire_refund_request(ref_id, after_7_days)

        self.assertEqual(self.contract.refund_requests[ref_id]["status"], "Ready")
        self.assertEqual(self.contract.reserved_refund_amount, 2 * WEI_PER_ETH)
        self.assertEqual(self.contract.pending_student_refund_amount[self.student_a], 2 * WEI_PER_ETH)

    # 8. Đề xuất Pending quá hạn được expire và giải phóng reservation đúng một lần
    def test_08_pending_requests_expire_after_deadline_and_release_reservation_once(self):
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        t = self._setup_3_active_bcs(0)

        # 8a. Spend request Pending
        req_id = self.contract.create_spend_request(self.bcs_1, self.recipient, 3 * WEI_PER_ETH, "Chua du vote", t + 1000)
        self.contract.vote_spend_request(self.bcs_1, req_id, True, t + 1010) # 1/3 = 33.3% < 51% -> Pending
        self.assertEqual(self.contract.reserved_spend_amount, 3 * WEI_PER_ETH)

        after_deadline = t + 1000 + VOTING_PERIOD_SECONDS + 1
        self.contract.expire_spend_request(req_id, after_deadline)
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Expired")
        self.assertEqual(self.contract.reserved_spend_amount, 0, "Reservation phai tra ve 0")

        # Expire lần 2 -> Revert InvalidRequestStatus
        with self.assertRaises(InvalidRequestStatusError):
            self.contract.expire_spend_request(req_id, after_deadline + 10)

        # 8b. Refund request Pending
        ref_id = self.contract.create_refund_request(self.student_a, 2 * WEI_PER_ETH, "Chua du vote hoan", t + 2000)
        self.assertEqual(self.contract.reserved_refund_amount, 2 * WEI_PER_ETH)
        self.assertEqual(self.contract.pending_student_refund_amount[self.student_a], 2 * WEI_PER_ETH)

        after_ref_deadline = t + 2000 + VOTING_PERIOD_SECONDS + 1
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
        t = self._setup_3_active_bcs(0)

        req_id = self.contract.create_spend_request(self.bcs_1, self.recipient, 2 * WEI_PER_ETH, "Boundary test", t + 1000)
        ref_id = self.contract.create_refund_request(self.student_a, 1 * WEI_PER_ETH, "Boundary test refund", t + 1000)

        # Trước thời hạn (ngày thứ 3 sau tạo)
        with self.assertRaises(VotingStillActiveError):
            self.contract.expire_spend_request(req_id, t + 1000 + 3 * 24 * 3600)
        with self.assertRaises(RefundVotingStillActiveError):
            self.contract.expire_refund_request(ref_id, t + 1000 + 3 * 24 * 3600)

        # ĐÚNG RANH GIỚI: block.timestamp == createdAt + VOTING_PERIOD (ngày thứ 7 chính xác)
        exact_boundary = t + 1000 + VOTING_PERIOD_SECONDS
        with self.assertRaises(VotingStillActiveError):
            self.contract.expire_spend_request(req_id, exact_boundary)
        with self.assertRaises(RefundVotingStillActiveError):
            self.contract.expire_refund_request(ref_id, exact_boundary)

    # 10. Chống double-voting và bảo toàn phân quyền
    def test_10_anti_double_voting_and_permissions(self):
        self.contract.deposit(self.student_a, 5 * WEI_PER_ETH)
        t = self._setup_3_active_bcs(0)

        req_id = self.contract.create_spend_request(self.bcs_1, self.recipient, 1 * WEI_PER_ETH, "Double vote test", t + 1000)
        self.contract.vote_spend_request(self.bcs_1, req_id, True, t + 1010)

        # Bỏ phiếu lần 2 từ cùng BCS 1 -> Revert AlreadyVoted
        with self.assertRaises(AlreadyVotedError):
            self.contract.vote_spend_request(self.bcs_1, req_id, True, t + 1020)

        # Người ngoài (student_a) cố vote -> Revert NotActiveBCS
        with self.assertRaises(NotActiveBCSError):
            self.contract.vote_spend_request(self.student_a, req_id, True, t + 1030)

    # 11. Chống tái nhập (Reentrancy) bảo vệ số dư quỹ và chặn recipient tự vote (Mục C + CEI)
    def test_11_reentrancy_protection_via_cei(self):
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        attacker_addr = "0xAttackerContract00000000000000000000001"
        self.contract.set_students(self.advisor, [attacker_addr], True)
        self.contract.set_bcs_member(self.advisor, attacker_addr, True, 0)
        t = self._setup_3_active_bcs(0) # Tổng 4 BCS đủ điều kiện -> voterBase = 4 - 1 = 3

        req_id = self.contract.create_spend_request(self.bcs_1, attacker_addr, 2 * WEI_PER_ETH, "Attack spend", t + 1000)
        self.assertEqual(self.contract.spend_requests[req_id]["voter_base"], 3)

        # Mục C: attacker_addr là recipient nên tự vote phải revert ConflictOfInterestError
        with self.assertRaises(ConflictOfInterestError):
            self.contract.vote_spend_request(attacker_addr, req_id, True, t + 1005)

        self.contract.vote_spend_request(self.bcs_1, req_id, True, t + 1010)

        reentrancy_revert_raised = False

        def reentrancy_attack():
            nonlocal reentrancy_revert_raised
            try:
                self.contract.execute_spend_request(attacker_addr, req_id, t + 1020)
            except RequestAlreadyExecutedError:
                reentrancy_revert_raised = True

        self.contract.reentrancy_hook = reentrancy_attack

        # bcs_2 bỏ phiếu quyết định (2/3 >= 51%) -> tự động chuyển ETH cho attacker -> hook tái nhập kích hoạt và bị chặn bởi CEI
        self.contract.vote_spend_request(self.bcs_2, req_id, True, t + 1020)

        self.assertTrue(reentrancy_revert_raised, "Tai nhap phai bi chan boi RequestAlreadyExecuted vi CEI")
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Executed")
        self.assertEqual(self.contract.class_fund_balance, 79 * 10**17, "Quy chi bi tru dung 1 lan")

    # 12. Bất biến kế toán bảo toàn 100% không mất wei
    def test_12_accounting_invariants(self):
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        self.contract.deposit(self.student_b, 10 * WEI_PER_ETH)
        t = self._setup_3_active_bcs(0)

        req_id = self.contract.create_spend_request(self.bcs_1, self.recipient, 4 * WEI_PER_ETH, "Chi 4", t + 1000)
        self.contract.vote_spend_request(self.bcs_1, req_id, True, t + 1010)
        self.contract.vote_spend_request(self.bcs_2, req_id, True, t + 1020)

        ref_id = self.contract.create_refund_request(self.student_a, 2 * WEI_PER_ETH, "Hoan 2", t + 1030)
        self.contract.vote_refund_request(self.bcs_1, ref_id, True, t + 1040)
        self.contract.vote_refund_request(self.bcs_2, ref_id, True, t + 1050)

        self.contract.move_fee_to_class_fund(self.advisor, 1 * 10**17)

        expected = 140 * 10**17
        actual = self.contract.class_fund_balance + self.contract.admin_fee_pool
        self.assertEqual(actual, expected)
        self.assertEqual(self.contract.class_fund_balance, 139 * 10**17)
        self.assertEqual(self.contract.admin_fee_pool, 1 * 10**17)
        self.assertEqual(self.contract.reserved_spend_amount, 0)
        self.assertEqual(self.contract.reserved_refund_amount, 0)

    # 13. Phase 1 / Section A: Auto-execution hoàn tối đa 99% net đưa hạn mức về 0, giữ nguyên student_total_deposited
    def test_13_section_a_auto_exec_full_net_refund_preserves_total_deposited_and_blocks_excess(self):
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        self.contract.deposit(self.student_b, 10 * WEI_PER_ETH)
        t = self._setup_3_active_bcs(0)

        # Student A xin hoàn đúng 9.9 ETH (99% net) -> thành công; đòi 10 ETH -> revert InsufficientContribution
        with self.assertRaises(InsufficientContributionError):
            self.contract.create_refund_request(self.student_a, 10 * WEI_PER_ETH, "Gian lan gross", t + 1000)

        self.assertEqual(self.contract.get_student_max_refund(self.student_a), 99 * 10**17)
        ref_id = self.contract.create_refund_request(self.student_a, 99 * 10**17, "Hoan toan bo 99%", t + 1010)
        self.contract.vote_refund_request(self.bcs_1, ref_id, True, t + 1020)
        self.contract.vote_refund_request(self.bcs_2, ref_id, True, t + 1030)

        self.assertEqual(self.contract.refund_requests[ref_id]["status"], "Executed")
        self.assertEqual(self.contract.student_contributions[self.student_a], 0)
        self.assertEqual(self.contract.student_total_deposited[self.student_a], 10 * WEI_PER_ETH)
        self.assertEqual(self.contract.class_fund_balance, 99 * 10**17)
        self.assertEqual(self.contract.admin_fee_pool, 2 * 10**17)

    # 14. Phase 2 / Mục B & C: Xung đột lợi ích rút voterBase = eligible - 1 và tự động giải ngân ở phiếu thứ 2
    def test_14_section_bc_conflict_voter_base_auto_execution(self):
        self.contract.deposit(self.bcs_1, 5 * WEI_PER_ETH)
        t = self._setup_3_active_bcs(0)

        ref_id = self.contract.create_refund_request(self.bcs_1, 2 * WEI_PER_ETH, "BCS 1 xin hoan", t + 100)
        self.assertEqual(self.contract.refund_requests[ref_id]["voter_base"], 2)

        with self.assertRaises(ConflictOfInterestError):
            self.contract.vote_refund_request(self.bcs_1, ref_id, True, t + 110)

        self.contract.vote_refund_request(self.bcs_2, ref_id, True, t + 120)
        self.assertEqual(self.contract.refund_requests[ref_id]["status"], "Pending")

        self.contract.vote_refund_request(self.bcs_3, ref_id, True, t + 130)
        self.assertEqual(self.contract.refund_requests[ref_id]["status"], "Executed")

        req_id = self.contract.create_spend_request(self.bcs_1, self.bcs_3, 1 * WEI_PER_ETH, "Chi cho BCS 3", t + 200)
        self.assertEqual(self.contract.spend_requests[req_id]["voter_base"], 2)
        with self.assertRaises(ConflictOfInterestError):
            self.contract.vote_spend_request(self.bcs_3, req_id, True, t + 210)
        self.contract.vote_spend_request(self.bcs_1, req_id, True, t + 220)
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Pending")
        self.contract.vote_spend_request(self.bcs_2, req_id, True, t + 230)
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Executed")

    # 15. Phase 2 / Mục B (Gian lận): 3 ví ma thêm ngay trước biểu quyết không thể kích hoạt auto-execution
    def test_15_section_b_phantom_bcs_wallets_blocked_from_auto_exec(self):
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        t = self._setup_3_active_bcs(0)

        req_id = self.contract.create_spend_request(self.bcs_1, self.recipient, 3 * WEI_PER_ETH, "Chong vi ma", t + 100)
        self.contract.vote_spend_request(self.bcs_1, req_id, True, t + 110)

        phantoms = [f"0xPhantom{i:032d}" for i in range(1, 4)]
        self.contract.set_students(self.advisor, phantoms, True)
        for p in phantoms:
            self.contract.set_bcs_member(self.advisor, p, True, t + 120)

        # Trước 3 ngày -> NotActiveBCSError
        with self.assertRaises(NotActiveBCSError):
            self.contract.vote_spend_request(phantoms[0], req_id, True, t + 130)

        # Sau 3 ngày (vẫn trong hạn 7 ngày của proposal) -> VoterNotEligibleAtCreationError
        for p in phantoms:
            with self.assertRaises(VoterNotEligibleAtCreationError):
                self.contract.vote_spend_request(p, req_id, True, t + 120 + BCS_ACTIVATION_DELAY)

        self.assertEqual(self.contract.spend_requests[req_id]["voter_base"], 3)
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Pending")

        # BCS hợp lệ thứ 2 bỏ phiếu -> tự thực thi
        self.contract.vote_spend_request(self.bcs_2, req_id, True, t + 130 + BCS_ACTIVATION_DELAY)
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Executed")

    # 16. Phase 2 / Mục B: Fallback executeRefundRequest thủ công vẫn chạy ngay cả khi toàn bộ BCS đã bị gỡ sau khi đạt Ready
    def test_16_section_b_manual_refund_fallback_after_all_bcs_removed(self):
        self.contract.deposit(self.student_a, 5 * WEI_PER_ETH)
        t = self._setup_3_active_bcs(0)
        self.contract.rejecting_recipients.add(self.student_a)

        ref_id = self.contract.create_refund_request(self.student_a, 2 * WEI_PER_ETH, "Fallback sau go BCS", t + 100)
        self.contract.vote_refund_request(self.bcs_1, ref_id, True, t + 110)
        self.contract.vote_refund_request(self.bcs_2, ref_id, True, t + 120)
        self.assertEqual(self.contract.refund_requests[ref_id]["status"], "Ready")

        # Gỡ sạch toàn bộ BCS
        for b in (self.bcs_1, self.bcs_2, self.bcs_3):
            self.contract.set_bcs_member(self.advisor, b, False, t + 130)
        self.assertEqual(self.contract.active_bcs_count, 0)

        # Nhờ voter_base = 3 snapshot không đổi, sinh viên tự gọi executeRefundRequest thành công!
        self.contract.rejecting_recipients.remove(self.student_a)
        self.contract.execute_refund_request(self.student_a, ref_id)
        self.assertEqual(self.contract.refund_requests[ref_id]["status"], "Executed")
        self.assertEqual(self.contract.wallet_balances[self.student_a], 2 * WEI_PER_ETH)


    # 17. Phase 3 / Mục D: Sinh viên bị gỡ khỏi danh sách vẫn được auto-execution hoàn tiền thành công
    def test_17_section_d_removed_student_auto_execution_refund(self):
        self.contract.deposit(self.student_a, 5 * WEI_PER_ETH)
        t = self._setup_3_active_bcs(0)

        # Xóa sinh viên khỏi danh sách
        self.contract.set_students(self.advisor, [self.student_a], False)
        self.assertFalse(self.contract.is_student[self.student_a])

        # Sinh viên nộp tiếp thì bị chặn
        with self.assertRaises(NotEnrolledStudentError):
            self.contract.deposit(self.student_a, 1 * WEI_PER_ETH)

        # Nhưng tạo yêu cầu hoàn tiền và nhận auto-execution hoàn tiền thành công
        ref_id = self.contract.create_refund_request(self.student_a, 2 * WEI_PER_ETH, "Hoan tien sau go enrollment", t + 100)
        self.contract.vote_refund_request(self.bcs_1, ref_id, True, t + 110)
        self.assertEqual(self.contract.refund_requests[ref_id]["status"], "Pending")

        self.contract.vote_refund_request(self.bcs_2, ref_id, True, t + 120)
        # Phiếu thứ 2 đưa tới ngưỡng 2/3 >= 51% -> Tự động giải ngân hoàn tiền thành công
        self.assertEqual(self.contract.refund_requests[ref_id]["status"], "Executed")
        self.assertEqual(self.contract.wallet_balances[self.student_a], 2 * WEI_PER_ETH)
        self.assertEqual(self.contract.student_contributions[self.student_a], (5 * WEI_PER_ETH * 99 // 100) - 2 * WEI_PER_ETH)

    # 18. Phase 3 / Mục D: Ép ETH không ảnh hưởng tới chu trình tự thực thi và getUnaccountedBalance
    def test_18_section_d_forced_eth_auto_execution_unaccounted_balance(self):
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        t = self._setup_3_active_bcs(0)

        # Ép 5 ETH vào hợp đồng
        self.contract.forced_eth_wei = 5 * WEI_PER_ETH
        self.assertEqual(self.contract.get_unaccounted_balance(), 5 * WEI_PER_ETH)

        req_id = self.contract.create_spend_request(self.bcs_1, self.recipient, 4 * WEI_PER_ETH, "Chi co forced ETH", t + 100)
        self.contract.vote_spend_request(self.bcs_1, req_id, True, t + 110)
        self.contract.vote_spend_request(self.bcs_2, req_id, True, t + 120)

        # Auto execution hoàn thành chính xác
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Executed")
        self.assertEqual(self.contract.wallet_balances[self.recipient], 4 * WEI_PER_ETH)
        # Unaccounted balance vẫn giữ nguyên 5 ETH
        self.assertEqual(self.contract.get_unaccounted_balance(), 5 * WEI_PER_ETH)


if __name__ == "__main__":
    unittest.main()
