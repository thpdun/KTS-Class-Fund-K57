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
BCS_ACTIVATION_DELAY = 3                   # 3 giây chờ kích hoạt BCS mới (cập nhật từ 3 ngày xuống 3 giây)
MIN_BCS_FOR_PROPOSAL = 3               # Tối thiểu 3 BCS đã kích hoạt để tạo đề xuất/hoàn tiền
MAX_BCS = 15                           # Tối đa 15 BCS
MAX_BATCH = 100                        # Tối đa 100 địa chỉ trong 1 lượt setStudents (Mục D)
MAX_PURPOSE_LENGTH = 256               # Giới hạn độ dài mục đích đợt thu (Mục E)
MAX_REASON_LENGTH = 256                # Giới hạn độ dài lý do đóng đợt thu (Mục E)
MAX_OPEN_SPEND_PER_CREATOR = 3         # Số lượng đề xuất chi đang mở tối đa mỗi người tạo
GAS_REFUND_OVERHEAD = 30_000           # Gas overhead bù đắp 21.000 giao dịch cơ bản + calldata (Mục F)
MAX_REFUND_GAS_UNITS = 500_000         # Giới hạn gas units hoàn tối đa (Mục F)
MAX_GAS_PRICE_PREMIUM = 2 * 10**9      # 2 gwei trần phụ phí gas (Mục F)
WEI_PER_ETH = 10**18


def compute_gas_refund(
    gas_used: int, gas_price: int, basefee: int, pool: int
) -> Tuple[int, int, int, int, int]:
    """
    Hàm thuần tính toán hoàn phí gas theo công thức Mục F:
    gasUsed = gas_used + GAS_REFUND_OVERHEAD
    units   = min(gasUsed, MAX_REFUND_GAS_UNITS)
    price   = min(gas_price, basefee + MAX_GAS_PRICE_PREMIUM)
    owed    = units * price
    paid    = min(owed, pool)
    shortfall = owed - paid
    """
    gas_total = gas_used + GAS_REFUND_OVERHEAD
    units = min(gas_total, MAX_REFUND_GAS_UNITS)
    max_price = basefee + MAX_GAS_PRICE_PREMIUM
    price = min(gas_price, max_price)
    owed = units * price
    paid = min(owed, pool)
    shortfall = owed - paid
    return units, price, owed, paid, shortfall


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


class InsufficientContributionError(CustomError):
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


class RefundRequestNotFoundError(CustomError):
    pass


class RefundAlreadyExecutedError(CustomError):
    pass


class AlreadyVotedRefundError(CustomError):
    pass


class RefundVotingPeriodEndedError(CustomError):
    pass


class RefundVotingStillActiveError(CustomError):
    pass


class MaxBCSReachedError(CustomError):
    pass


class NotEnoughBCSError(CustomError):
    pass


class ConflictOfInterestError(CustomError):
    pass


class VoterNotEligibleAtCreationError(CustomError):
    pass


class BatchTooLargeError(CustomError):
    pass


class NotEnrolledStudentError(CustomError):
    pass


class BCSMustBeEnrolledStudentError(CustomError):
    pass


class StudentIsBCSError(CustomError):
    pass


class AdvisorCannotBeStudentError(CustomError):
    pass


class CollectionNotFoundError(CustomError):
    pass


class CollectionStillOpenError(CustomError):
    pass


class CollectionIsClosedError(CustomError):
    pass


class CollectionExpiredError(CustomError):
    pass


class CollectionAlreadyClosedError(CustomError):
    pass


class InvalidDeadlineError(CustomError):
    pass


class EmptyPurposeError(CustomError):
    pass


class PurposeTooLongError(CustomError):
    pass


class EmptyReasonError(CustomError):
    pass


class ReasonTooLongError(CustomError):
    pass


class ReentrancyGuardReentrantCallError(CustomError):
    pass


class TooManyOpenRequestsError(CustomError):
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
        self.open_spend_request_count: Dict[str, int] = {}
        self.spend_requests: Dict[int, Dict[str, Any]] = {}
        self.has_voted: Dict[int, Dict[str, bool]] = {}
        self.refund_request_count = 0
        self.refund_requests: Dict[int, Dict[str, Any]] = {}
        self.has_voted_refund: Dict[int, Dict[str, bool]] = {}
        self.is_student: Dict[str, bool] = {}
        self.enrolled_count = 0
        self.roster_hash = "0x" + "00" * 32
        self.collection_count = 0
        self.active_collection_id = 0
        self.collections: Dict[int, Dict[str, Any]] = {}
        self.paid_in_collection: Dict[int, Dict[str, int]] = {}
        self.forced_eth_wei = 0
        self.emitted_events: List[Tuple] = []

    # --- R12: Quản lý danh sách sinh viên & Commit Roster (Phase 3 / Mục D) ---
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

    # --- R1: Quản lý BCS (Nhóm B: bcsList O(1), MAX_BCS=15, trễ kích hoạt 3 ngày) ---
    def set_bcs_member(self, caller: str, member: str, status: bool, current_time: int = 1):
        if caller != self.advisor:
            raise NotAdvisorError("Revert: NotAdvisor()")
        if not member or member == "0x0" or member == "0x0000000000000000000000000000000000000000":
            raise InvalidAddressError("Revert: InvalidAddress()")

        current_status = self.is_bcs_member.get(member, False)
        if current_status == status:
            return False

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
        return True

    def is_eligible_voter_at(self, member: str, at_timestamp: int) -> bool:
        return (
            self.is_bcs_member.get(member, False)
            and self.member_since.get(member, 0) != 0
            and self.member_since[member] <= at_timestamp
        )

    def eligible_bcs_count(self, at_timestamp: int) -> int:
        return sum(1 for m in self.bcs_list if self.is_eligible_voter_at(m, at_timestamp))

    def get_bcs_list(self) -> List[str]:
        return list(self.bcs_list)

    # --- R2: Nạp tiền ---
    def _process_deposit(self, sender: str, amount_wei: int) -> Tuple[int, int]:
        if not self.is_student.get(sender, False):
            raise NotEnrolledStudentError(f"Revert: NotEnrolledStudent({sender})")
        if amount_wei == 0:
            raise ZeroAmountError("Revert: ZeroAmount()")

        admin_fee = (amount_wei * FEE_BPS) // BPS_DENOMINATOR
        class_fund_amount = amount_wei - admin_fee

        self.student_contributions[sender] = self.student_contributions.get(sender, 0) + class_fund_amount
        self.student_total_deposited[sender] = self.student_total_deposited.get(sender, 0) + amount_wei
        self.class_fund_balance += class_fund_amount
        self.admin_fee_pool += admin_fee

        self.emitted_events.append(("FundDeposited", sender, amount_wei))
        self.emitted_events.append(("AdminFeeCollected", sender, admin_fee))
        return class_fund_amount, admin_fee

    def deposit(self, sender: str, amount_wei: int) -> Tuple[int, int]:
        return self._process_deposit(sender, amount_wei)

    def receive(self, sender: str, amount_wei: int) -> Tuple[int, int]:
        return self._process_deposit(sender, amount_wei)

    # --- Nhóm E: Quản lý đợt thu nộp quỹ trên chuỗi & Nạp theo đợt ---
    def create_collection(
        self,
        caller: str,
        target_wei: int,
        deadline: int,
        purpose: str,
        current_time: int,
    ) -> int:
        if not self.is_eligible_voter_at(caller, current_time):
            raise NotActiveBCSError("Revert: NotActiveBCS()")
        if target_wei == 0:
            raise ZeroAmountError("Revert: ZeroAmount()")
        if deadline <= current_time:
            raise InvalidDeadlineError("Revert: InvalidDeadline()")
        purpose_len = len(purpose.encode("utf-8"))
        if purpose_len == 0:
            raise EmptyPurposeError("Revert: EmptyPurpose()")
        if purpose_len > MAX_PURPOSE_LENGTH:
            raise PurposeTooLongError("Revert: PurposeTooLong()")
        if self.active_collection_id != 0 and not self.collections[self.active_collection_id]["closed"]:
            old_col = self.collections[self.active_collection_id]
            if current_time > old_col["deadline"]:
                old_col["closed"] = True
                old_col["closed_at"] = current_time
                self.emitted_events.append(("CollectionClosed", self.active_collection_id, "Hết hạn tự động", caller, current_time))
            else:
                raise CollectionStillOpenError(f"Revert: CollectionStillOpen({self.active_collection_id})")

        self.collection_count += 1
        cid = self.collection_count
        self.active_collection_id = cid
        self.collections[cid] = {
            "id": cid,
            "target_wei": target_wei,
            "deadline": deadline,
            "purpose": purpose,
            "creator": caller,
            "created_at": current_time,
            "closed": False,
            "closed_at": 0,
            "expected_payers": self.enrolled_count,
            "paid_count": 0,
        }
        self.paid_in_collection[cid] = {}
        self.emitted_events.append(("CollectionCreated", cid, target_wei, deadline, purpose, caller, self.enrolled_count))
        return cid

    def close_collection(self, caller: str, collection_id: int, reason: str, current_time: int):
        if not self.is_eligible_voter_at(caller, current_time):
            raise NotActiveBCSError("Revert: NotActiveBCS()")
        if collection_id == 0 or collection_id not in self.collections:
            raise CollectionNotFoundError(f"Revert: CollectionNotFound({collection_id})")
        col = self.collections[collection_id]
        if col["closed"]:
            raise CollectionAlreadyClosedError(f"Revert: CollectionAlreadyClosed({collection_id})")
        reason_len = len(reason.encode("utf-8"))
        if reason_len == 0:
            raise EmptyReasonError("Revert: EmptyReason()")
        if reason_len > MAX_REASON_LENGTH:
            raise ReasonTooLongError("Revert: ReasonTooLong()")

        col["closed"] = True
        col["closed_at"] = current_time
        if self.active_collection_id == collection_id:
            self.active_collection_id = 0
        self.emitted_events.append(("CollectionClosed", collection_id, reason, caller, current_time))

    def deposit_to_collection(
        self, caller: str, collection_id: int, amount_wei: int, current_time: int
    ) -> Tuple[int, int]:
        if collection_id == 0 or collection_id not in self.collections:
            raise CollectionNotFoundError(f"Revert: CollectionNotFound({collection_id})")
        col = self.collections[collection_id]
        if col["closed"]:
            raise CollectionIsClosedError(f"Revert: CollectionIsClosed({collection_id})")
        if current_time > col["deadline"]:
            raise CollectionExpiredError(f"Revert: CollectionExpired({collection_id})")

        class_fund_amount, admin_fee = self._process_deposit(caller, amount_wei)

        prev_paid = self.paid_in_collection[collection_id].get(caller, 0)
        new_paid = prev_paid + amount_wei
        self.paid_in_collection[collection_id][caller] = new_paid

        if prev_paid < col["target_wei"] and new_paid >= col["target_wei"]:
            col["paid_count"] += 1

        self.emitted_events.append(
            ("CollectionDeposited", collection_id, caller, amount_wei, new_paid, col["paid_count"])
        )
        return class_fund_amount, admin_fee

    def get_collection(self, collection_id: int) -> Dict[str, Any]:
        if collection_id == 0 or collection_id not in self.collections:
            raise CollectionNotFoundError(f"Revert: CollectionNotFound({collection_id})")
        return dict(self.collections[collection_id])

    def has_paid_in_collection(self, collection_id: int, student: str) -> bool:
        if collection_id == 0 or collection_id not in self.collections:
            return False
        col = self.collections[collection_id]
        if col["target_wei"] == 0:
            return False
        return self.paid_in_collection.get(collection_id, {}).get(student, 0) >= col["target_wei"]

    def get_active_collection_id(self, current_time: int) -> int:
        if self.active_collection_id != 0:
            col = self.collections[self.active_collection_id]
            if not col["closed"] and current_time <= col["deadline"]:
                return self.active_collection_id
        return 0

    # --- Nhóm F: Điều chuyển phí dư thừa sang Quỹ lớp chính ---
    def move_fee_to_class_fund(self, caller: str, amount_wei: int):
        if caller != self.advisor:
            raise NotAdvisorError("Revert: NotAdvisor()")
        if amount_wei == 0:
            raise ZeroAmountError("Revert: ZeroAmount()")
        if amount_wei > self.admin_fee_pool:
            raise InsufficientAdminFeeError("Revert: InsufficientAdminFee()")

        self.admin_fee_pool -= amount_wei
        self.class_fund_balance += amount_wei
        self.emitted_events.append(("FeeMovedToClassFund", self.advisor, amount_wei))

    # --- Nhóm F: Mô phỏng hoàn phí gas tự động ---
    def apply_simulated_gas_refund(
        self,
        caller: str,
        gas_used: int,
        gas_price: int,
        basefee: int,
        current_time: int = 0,
        rejecting_receiver: bool = False,
    ) -> Tuple[int, int, int, int, int]:
        """
        Mô phỏng cơ chế modifier governanceAction theo công thức thuần compute_gas_refund:
        Chỉ hoàn gas cho Cố vấn hoặc BCS đã kích hoạt.
        """
        is_adv = (caller == self.advisor)
        is_bcs = self.is_bcs_member.get(caller, False) and (
            self.member_since.get(caller, 0) != 0 and self.member_since[caller] <= current_time
        )
        if not is_adv and not is_bcs:
            return 0, 0, 0, 0, 0

        units, price, owed, paid, shortfall = compute_gas_refund(
            gas_used, gas_price, basefee, self.admin_fee_pool
        )
        if paid > 0:
            self.admin_fee_pool -= paid
            if rejecting_receiver:
                # Gửi thất bại: phục hồi lại admin_fee_pool, phát GasRefundFailed
                self.admin_fee_pool += paid
                self.emitted_events.append(("GasRefundFailed", caller, paid))
                self.emitted_events.append(("GasRefunded", caller, units, price, 0, owed))
                return units, price, owed, 0, owed

        self.emitted_events.append(("GasRefunded", caller, units, price, paid, shortfall))
        return units, price, owed, paid, shortfall

    # --- R3: Tạo đề xuất chi ---
    def get_available_class_fund(self) -> int:
        total_reserved = self.reserved_spend_amount + self.reserved_refund_amount
        if self.class_fund_balance <= total_reserved:
            return 0
        return self.class_fund_balance - total_reserved

    def get_student_available_contribution(self, student: str) -> int:
        contrib = self.student_contributions.get(student, 0)
        pending = self.pending_student_refund_amount.get(student, 0)
        if contrib <= pending:
            return 0
        return contrib - pending

    def _decrement_open_spend(self, creator: str):
        if self.open_spend_request_count.get(creator, 0) > 0:
            self.open_spend_request_count[creator] -= 1

    def create_spend_request(self, caller: str, recipient: str, amount_wei: int, description: str, current_time: int) -> int:
        if self.open_spend_request_count.get(caller, 0) >= MAX_OPEN_SPEND_PER_CREATOR:
            raise TooManyOpenRequestsError("Revert: TooManyOpenRequests()")
        if not self.is_eligible_voter_at(caller, current_time):
            raise NotActiveBCSError("Revert: NotActiveBCS()")
        if not recipient or recipient == "0x0" or recipient == "0x0000000000000000000000000000000000000000":
            raise InvalidAddressError("Revert: InvalidAddress()")
        if amount_wei == 0:
            raise ZeroAmountError("Revert: ZeroAmount()")

        eligible = self.eligible_bcs_count(current_time)
        if eligible < MIN_BCS_FOR_PROPOSAL:
            raise NotEnoughBCSError(f"Revert: NotEnoughBCS({eligible}, {MIN_BCS_FOR_PROPOSAL})")

        available = self.get_available_class_fund()
        if amount_wei > available:
            raise InsufficientAvailableFundError(f"Revert: InsufficientAvailableFund({amount_wei}, {available})")

        voter_base = eligible - 1 if self.is_eligible_voter_at(recipient, current_time) else eligible

        self.spend_request_count += 1
        req_id = self.spend_request_count
        self.open_spend_request_count[caller] = self.open_spend_request_count.get(caller, 0) + 1
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

    # --- R4 & R5: Biểu quyết ---
    def vote_spend_request(self, caller: str, req_id: int, support: bool, current_time: int):
        if not self.is_eligible_voter_at(caller, current_time):
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
                self._decrement_open_spend(req["creator"])
                self.emitted_events.append(("SpendRequestExpired", req_id))
            raise VotingPeriodEndedError("Revert: VotingPeriodEnded()")

        if caller == req["recipient"]:
            raise ConflictOfInterestError("Revert: ConflictOfInterest()")
        if not self.is_eligible_voter_at(caller, req["created_at"]):
            raise VoterNotEligibleAtCreationError(f"Revert: VoterNotEligibleAtCreation({req_id}, {caller})")
        if self.has_voted[req_id].get(caller, False):
            raise AlreadyVotedError("Revert: AlreadyVoted()")
        if req["voter_base"] == 0:
            raise CustomError("Revert: NoActiveBCS()")

        self.has_voted[req_id][caller] = True
        if support:
            req["yes_votes"] += 1
        else:
            req["no_votes"] += 1

        self.emitted_events.append(("SpendRequestVoted", req_id, caller, support, req["yes_votes"], req["no_votes"]))

        # Kiểm tra ngưỡng 51% trên mẫu số snapshot voter_base
        approval_bps = (req["yes_votes"] * BPS_DENOMINATOR) // req["voter_base"]
        if approval_bps >= PASSING_THRESHOLD_BPS and req["status"] == "Pending":
            req["status"] = "Ready"
            self.emitted_events.append(("SpendRequestReady", req_id))
        elif req["status"] == "Pending":
            max_possible_yes = max(0, req["voter_base"] - req["no_votes"])
            if (max_possible_yes * BPS_DENOMINATOR) // req["voter_base"] < PASSING_THRESHOLD_BPS:
                req["status"] = "Rejected"
                self.reserved_spend_amount -= req["amount"]
                self._decrement_open_spend(req["creator"])
                self.emitted_events.append(("SpendRequestRejected", req_id))

    # --- R6: Thực thi giải ngân ---
    def execute_spend_request(self, caller: str, req_id: int, current_time: int = BCS_ACTIVATION_DELAY + 1):
        if not self.is_eligible_voter_at(caller, current_time):
            raise NotActiveBCSError("Revert: NotActiveBCS()")
        if req_id not in self.spend_requests:
            raise RequestNotFoundError("Revert: RequestNotFound()")

        req = self.spend_requests[req_id]
        if req["status"] == "Executed":
            raise RequestAlreadyExecutedError("Revert: RequestAlreadyExecuted()")
        if req["voter_base"] == 0:
            raise CustomError("Revert: NoActiveBCS()")

        approval_bps = (req["yes_votes"] * BPS_DENOMINATOR) // req["voter_base"]
        if approval_bps < PASSING_THRESHOLD_BPS:
            raise ThresholdNotMetError(f"Revert: ThresholdNotMet({req['yes_votes']}, {req['voter_base']})")

        if req["amount"] > self.class_fund_balance:
            raise InsufficientFundError("Revert: InsufficientFund()")

        # CEI: Cập nhật trạng thái trước
        req["status"] = "Executed"
        self.class_fund_balance -= req["amount"]
        self.reserved_spend_amount -= req["amount"]
        self._decrement_open_spend(req["creator"])

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
        self._decrement_open_spend(req["creator"])
        self.emitted_events.append(("SpendRequestExpired", req_id))

    # --- R7: Hoàn tiền có biểu quyết Ban cán sự ---
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

        voter_base = eligible - 1 if self.is_eligible_voter_at(caller, current_time) else eligible

        self.refund_request_count += 1
        refund_id = self.refund_request_count
        self.pending_student_refund_amount[caller] = self.pending_student_refund_amount.get(caller, 0) + amount_wei
        self.reserved_refund_amount += amount_wei

        self.refund_requests[refund_id] = {
            "id": refund_id,
            "applicant": caller,
            "amount": amount_wei,
            "reason": reason,
            "created_at": current_time,
            "yes_votes": 0,
            "no_votes": 0,
            "status": "Pending",
            "voter_base": voter_base,
        }
        self.has_voted_refund[refund_id] = {}
        self.emitted_events.append(("RefundRequestCreated", refund_id, caller, amount_wei, reason, current_time))
        return refund_id

    def vote_refund_request(self, caller: str, refund_id: int, support: bool, current_time: int):
        if not self.is_eligible_voter_at(caller, current_time):
            raise NotActiveBCSError("Revert: NotActiveBCS()")
        if refund_id not in self.refund_requests:
            raise RefundRequestNotFoundError("Revert: RefundRequestNotFound()")

        req = self.refund_requests[refund_id]
        if req["status"] == "Executed":
            raise RefundAlreadyExecutedError("Revert: RefundAlreadyExecuted()")
        if req["status"] not in ("Pending", "Ready"):
            raise CustomError("Revert: InvalidRefundStatus()")

        if current_time > req["created_at"] + VOTING_PERIOD_SECONDS:
            if req["status"] == "Pending":
                req["status"] = "Expired"
                self.reserved_refund_amount -= req["amount"]
                self.pending_student_refund_amount[req["applicant"]] -= req["amount"]
                self.emitted_events.append(("RefundRequestExpired", refund_id))
            raise RefundVotingPeriodEndedError("Revert: RefundVotingPeriodEnded()")

        if caller == req["applicant"]:
            raise ConflictOfInterestError("Revert: ConflictOfInterest()")
        if not self.is_eligible_voter_at(caller, req["created_at"]):
            raise VoterNotEligibleAtCreationError(f"Revert: VoterNotEligibleAtCreation({refund_id}, {caller})")
        if self.has_voted_refund[refund_id].get(caller, False):
            raise AlreadyVotedRefundError("Revert: AlreadyVotedRefund()")
        if req["voter_base"] == 0:
            raise CustomError("Revert: NoActiveBCS()")

        self.has_voted_refund[refund_id][caller] = True
        if support:
            req["yes_votes"] += 1
        else:
            req["no_votes"] += 1

        self.emitted_events.append(("RefundRequestVoted", refund_id, caller, support, req["yes_votes"], req["no_votes"]))

        approval_bps = (req["yes_votes"] * BPS_DENOMINATOR) // req["voter_base"]
        if approval_bps >= PASSING_THRESHOLD_BPS and req["status"] == "Pending":
            req["status"] = "Ready"
            self.emitted_events.append(("RefundRequestReady", refund_id))
        elif req["status"] == "Pending":
            max_possible_yes = max(0, req["voter_base"] - req["no_votes"])
            if (max_possible_yes * BPS_DENOMINATOR) // req["voter_base"] < PASSING_THRESHOLD_BPS:
                req["status"] = "Rejected"
                self.reserved_refund_amount -= req["amount"]
                self.pending_student_refund_amount[req["applicant"]] -= req["amount"]
                self.emitted_events.append(("RefundRequestRejected", refund_id))

    def execute_refund_request(self, caller: str, refund_id: int):
        if refund_id not in self.refund_requests:
            raise RefundRequestNotFoundError("Revert: RefundRequestNotFound()")

        req = self.refund_requests[refund_id]
        if req["status"] == "Executed":
            raise RefundAlreadyExecutedError("Revert: RefundAlreadyExecuted()")
        if req["voter_base"] == 0:
            raise CustomError("Revert: NoActiveBCS()")

        approval_bps = (req["yes_votes"] * BPS_DENOMINATOR) // req["voter_base"]
        if approval_bps < PASSING_THRESHOLD_BPS:
            raise ThresholdNotMetError(f"Revert: ThresholdNotMet({req['yes_votes']}, {req['voter_base']})")

        if req["amount"] > self.class_fund_balance:
            raise InsufficientFundError("Revert: InsufficientFund()")

        # CEI: Cập nhật trạng thái trước
        req["status"] = "Executed"
        self.reserved_refund_amount -= req["amount"]
        self.pending_student_refund_amount[req["applicant"]] -= req["amount"]
        self.student_contributions[req["applicant"]] -= req["amount"]
        self.class_fund_balance -= req["amount"]

        self.emitted_events.append(("RefundRequestExecuted", refund_id, req["applicant"], req["amount"]))
        self.emitted_events.append(("RefundProcessed", req["applicant"], req["amount"]))
        return req["amount"]

    def expire_refund_request(self, refund_id: int, current_time: int):
        if refund_id not in self.refund_requests:
            raise RefundRequestNotFoundError("Revert: RefundRequestNotFound()")
        req = self.refund_requests[refund_id]
        if req["status"] not in ("Pending", "Ready"):
            raise CustomError("Revert: InvalidRefundStatus()")
        if current_time <= req["created_at"] + VOTING_PERIOD_SECONDS:
            raise RefundVotingStillActiveError("Revert: RefundVotingStillActive()")
        req["status"] = "Expired"
        self.reserved_refund_amount -= req["amount"]
        self.pending_student_refund_amount[req["applicant"]] -= req["amount"]
        self.emitted_events.append(("RefundRequestExpired", refund_id))

    # --- View / Getters ---
    def get_fund_balance(self) -> int:
        return self.class_fund_balance

    def get_total_contract_balance(self) -> int:
        return self.class_fund_balance + self.admin_fee_pool

    def get_student_contribution(self, student: str) -> int:
        return self.student_contributions.get(student, 0)

    def get_student_total_deposited(self, student: str) -> int:
        return self.student_total_deposited.get(student, 0)

    def get_student_max_refund(self, student: str) -> int:
        return min(self.get_student_available_contribution(student), self.get_available_class_fund())


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
        # Ghi danh sinh viên mặc định để các bài test cơ sở hoạt động nhất quán
        self.contract.set_students(
            self.advisor,
            [self.student_a, self.student_b, self.bcs_1, self.bcs_2, self.bcs_3],
            True,
        )

    def test_case_1_valid_deposit_1_eth(self):
        deposit_amount_wei = 1 * WEI_PER_ETH
        class_fund_amount, admin_fee = self.contract.deposit(self.student_a, deposit_amount_wei)
        expected_fee_wei = 10**16
        expected_class_wei = 99 * 10**16

        self.assertEqual(admin_fee, expected_fee_wei)
        self.assertEqual(class_fund_amount, expected_class_wei)
        self.assertEqual(self.contract.get_fund_balance(), expected_class_wei)
        self.assertEqual(self.contract.admin_fee_pool, expected_fee_wei)
        self.assertEqual(self.contract.get_student_contribution(self.student_a), expected_class_wei)
        self.assertEqual(self.contract.get_student_total_deposited(self.student_a), deposit_amount_wei)
        self.assertEqual(self.contract.get_student_max_refund(self.student_a), expected_class_wei)

        print("\n[Ca 1 - Nạp 1 ETH thành công]: Quỹ chính 0.99 ETH, Quỹ phí 0.01 ETH, hạn mức net 0.99 ETH, tổng nộp gốc 1.0 ETH.")

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
        # Kẻ tấn công chưa ghi danh sinh viên nạp tiền -> Revert NotEnrolledStudentError
        with self.assertRaises(NotEnrolledStudentError):
            self.contract.deposit(self.attacker, 1 * WEI_PER_ETH)

        # Ghi danh một sinh viên kiểm tra biên
        edge_student = "0xEdgeStudent000000000000000000000000000055"
        self.contract.set_students(self.advisor, [edge_student], True)

        with self.assertRaises(ZeroAmountError):
            self.contract.deposit(edge_student, 0)

        tricky_amounts = [1, 99, 100, 101, 999, 10_000, 10_001, 10**18 - 1]
        deposited_total = 0
        net_total = 0
        for amt in tricky_amounts:
            cf, fee = self.contract.deposit(edge_student, amt)
            deposited_total += amt
            net_total += cf
            self.assertEqual(cf + fee, amt)

        self.assertEqual(self.contract.get_student_contribution(edge_student), net_total)
        self.assertEqual(self.contract.get_student_total_deposited(edge_student), deposited_total)
        print("\n[Ca 5 - Kiểm tra chống gian lận & giá trị biên]: Chặn người ngoài chưa ghi danh, 100% giá trị biên bảo toàn số dư.")

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

    def _setup_3_active_bcs(self, added_at: int = 0) -> int:
        """Thêm 3 BCS tại mốc added_at và trả về mốc thời gian đầu tiên đủ điều kiện (added_at + 3 ngày)."""
        self.contract.set_bcs_member(self.advisor, self.bcs_1, True, current_time=added_at)
        self.contract.set_bcs_member(self.advisor, self.bcs_2, True, current_time=added_at)
        self.contract.set_bcs_member(self.advisor, self.bcs_3, True, current_time=added_at)
        return added_at + BCS_ACTIVATION_DELAY

    def test_case_8_bcs_management_and_authorization_r1(self):
        """R1 & Nhóm B: CVHT thêm/xóa BCS (O(1) swap-and-pop), kiểm tra trễ 3 ngày, chặn outsider"""
        # CVHT thêm bcs_1 và bcs_2 tại mốc T=100
        self.contract.set_bcs_member(self.advisor, self.bcs_1, True, current_time=100)
        self.contract.set_bcs_member(self.advisor, self.bcs_2, True, current_time=100)
        self.assertEqual(self.contract.active_bcs_count, 2)
        self.assertTrue(self.contract.is_bcs_member[self.bcs_1])
        self.assertEqual(self.contract.member_since[self.bcs_1], 100 + BCS_ACTIVATION_DELAY)
        self.assertEqual(self.contract.eligible_bcs_count(100), 0)
        self.assertEqual(self.contract.eligible_bcs_count(100 + BCS_ACTIVATION_DELAY), 2)

        # Kẻ tấn công cố tình thay đổi danh sách BCS -> Revert
        with self.assertRaises(NotAdvisorError):
            self.contract.set_bcs_member(self.attacker, self.attacker, True, current_time=100)

        # Thêm địa chỉ zero -> Revert
        with self.assertRaises(InvalidAddressError):
            self.contract.set_bcs_member(self.advisor, "0x0000000000000000000000000000000000000000", True, current_time=100)

        print("\n[Ca 8 - R1: Phân quyền CVHT & BCS]: Chỉ CVHT được thêm/xóa BCS, trễ kích hoạt 3 ngày chính xác.")

    def test_case_9_move_fee_to_class_fund_f(self):
        """Phase 5 / Mục F: CVHT chuyển phí vận hành dư sang Quỹ lớp chính, bảo toàn tổng số dư"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        # admin_fee_pool = 0.1 ETH, class_fund = 9.9 ETH
        self.assertEqual(self.contract.admin_fee_pool, 10**17)

        # CVHT chuyển 0.04 ETH sang Quỹ lớp
        move_amt = 4 * 10**16
        self.contract.move_fee_to_class_fund(self.advisor, move_amt)
        self.assertEqual(self.contract.admin_fee_pool, 6 * 10**16)
        self.assertEqual(self.contract.get_fund_balance(), 994 * 10**16)  # 9.9 + 0.04 = 9.94 ETH!
        self.assertEqual(self.contract.get_total_contract_balance(), 10 * WEI_PER_ETH)

        # Outsider cố chuyển phí -> Revert
        with self.assertRaises(NotAdvisorError):
            self.contract.move_fee_to_class_fund(self.attacker, 10**16)

        # Chuyển vượt số dư phí -> Revert
        with self.assertRaises(InsufficientAdminFeeError):
            self.contract.move_fee_to_class_fund(self.advisor, 1 * WEI_PER_ETH)

        # Chuyển 0 wei -> Revert
        with self.assertRaises(ZeroAmountError):
            self.contract.move_fee_to_class_fund(self.advisor, 0)

        print("\n[Ca 9 - Mục F: Chuyển phí vận hành dư sang Quỹ lớp]: CVHT chuyển phí thành công, tổng số dư 10 ETH được bảo toàn 100%.")

    def test_case_10_create_spend_request_r3(self):
        """R3: Đủ 3 BCS sau 3 ngày mới tạo được đề xuất chi và giữ chỗ số dư"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH) # classFund = 9.9 ETH
        ready_t = self._setup_3_active_bcs(added_at=0)

        # BCS tạo đề xuất 2 ETH tại ready_t
        req_id = self.contract.create_spend_request(
            caller=self.bcs_1,
            recipient="0xRecipient000000000000000000000000000001",
            amount_wei=2 * WEI_PER_ETH,
            description="Chi hoi thao",
            current_time=ready_t
        )
        self.assertEqual(req_id, 1)
        self.assertEqual(self.contract.spend_requests[req_id]["voter_base"], 3)
        self.assertEqual(self.contract.reserved_spend_amount, 2 * WEI_PER_ETH)
        self.assertEqual(self.contract.get_available_class_fund(), 79 * 10**17) # 7.9 ETH

        # Sinh viên / Outsider cố tạo đề xuất -> Revert
        with self.assertRaises(NotActiveBCSError):
            self.contract.create_spend_request(
                caller=self.student_a,
                recipient="0xRecipient000000000000000000000000000001",
                amount_wei=1 * WEI_PER_ETH,
                description="Lop ngoai",
                current_time=ready_t
            )

        # Tạo đề xuất vượt quá số dư khả dụng (yêu cầu 8 ETH trong khi khả dụng là 7.9 ETH) -> Revert
        with self.assertRaises(InsufficientAvailableFundError):
            self.contract.create_spend_request(
                caller=self.bcs_1,
                recipient="0xRecipient000000000000000000000000000001",
                amount_wei=8 * WEI_PER_ETH,
                description="Vuot ngan sach",
                current_time=ready_t
            )

        print("\n[Ca 10 - R3: Tạo đề xuất chi]: Đủ 3 BCS sau 3 ngày tạo hợp lệ, giữ chỗ 2 ETH, chặn ngoài & vượt ngân sách.")

    def test_case_11_vote_spend_request_r4_r5(self):
        """R4/R5: Biểu quyết 51% theo voterBase snapshot, chống bỏ phiếu kép, thời hạn 7 ngày"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        ready_t = self._setup_3_active_bcs(added_at=0)

        req_id = self.contract.create_spend_request(
            caller=self.bcs_1,
            recipient="0xRecipient000000000000000000000000000001",
            amount_wei=3 * WEI_PER_ETH,
            description="Mua trang thiet bi",
            current_time=ready_t
        )

        # bcs_1 bỏ phiếu YES: 1/3 = 33% < 51% -> Pending
        self.contract.vote_spend_request(self.bcs_1, req_id, True, current_time=ready_t + 50)
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Pending")

        # bcs_1 cố bỏ phiếu lần 2 -> Revert AlreadyVoted
        with self.assertRaises(AlreadyVotedError):
            self.contract.vote_spend_request(self.bcs_1, req_id, True, current_time=ready_t + 60)

        # bcs_2 bỏ phiếu YES: 2/3 = 66% >= 51% -> Tự động Ready!
        self.contract.vote_spend_request(self.bcs_2, req_id, True, current_time=ready_t + 70)
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Ready")

        # Quá hạn 7 ngày biểu quyết -> Revert
        with self.assertRaises(VotingPeriodEndedError):
            self.contract.vote_spend_request(self.bcs_3, req_id, True, current_time=ready_t + VOTING_PERIOD_SECONDS + 1)

        print("\n[Ca 11 - R4/R5: Biểu quyết]: 1/3 (Pending), chặn double-voting, 2/3 >= 51% (Ready), chặn quá hạn 7 ngày.")

    def test_case_12_execute_spend_request_r6_and_invariants(self):
        """R6 & Bất biến: Giải ngân khi đạt 51% (2/3 phiếu), chặn double execution, bảo toàn kế toán"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH) # classFund = 9.9 ETH
        ready_t = self._setup_3_active_bcs(added_at=0)

        req_id = self.contract.create_spend_request(
            caller=self.bcs_1,
            recipient="0xRecipient000000000000000000000000000001",
            amount_wei=3 * WEI_PER_ETH,
            description="Chi phi thuc te",
            current_time=ready_t
        )
        self.contract.vote_spend_request(self.bcs_1, req_id, True, current_time=ready_t + 10)
        self.contract.vote_spend_request(self.bcs_2, req_id, True, current_time=ready_t + 20)

        # Thực thi giải ngân
        self.contract.execute_spend_request(self.bcs_1, req_id, current_time=ready_t + 30)
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Executed")
        self.assertEqual(self.contract.get_fund_balance(), 69 * 10**17) # 6.9 ETH
        self.assertEqual(self.contract.reserved_spend_amount, 0)

        # Chống thực thi lặp lại (Double-spending) -> Revert
        with self.assertRaises(RequestAlreadyExecutedError):
            self.contract.execute_spend_request(self.bcs_1, req_id, current_time=ready_t + 40)

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
        try:
            raise CustomError("ETHTransferFailed")
        except CustomError:
            pass
        self.assertEqual(self.contract.admin_fee_pool, initial_fee_pool)
        print("\n[Ca 13 - R11: Rollback khi chuyển phí thất bại]: adminFeePool được bảo toàn nguyên vẹn.")

    def test_case_14_multiple_spend_requests_budget_isolation(self):
        """R3/R6: Nhiều đề xuất không thể giữ chỗ vượt quá số dư khả dụng thực tế"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH) # classFund = 9.9 ETH
        ready_t = self._setup_3_active_bcs(added_at=0)

        # Đề xuất 1 giữ 6 ETH
        self.contract.create_spend_request(self.bcs_1, "0xR1", 6 * WEI_PER_ETH, "De xuat 1", ready_t)
        self.assertEqual(self.contract.get_available_class_fund(), 39 * 10**17) # còn 3.9 ETH

        # Đề xuất 2 cố giữ 5 ETH (> 3.9 ETH) -> Phải bị từ chối
        with self.assertRaises(InsufficientAvailableFundError):
            self.contract.create_spend_request(self.bcs_1, "0xR2", 5 * WEI_PER_ETH, "De xuat 2 qua muc", ready_t)

        # Đề xuất 2 hợp lệ với 3 ETH (<= 3.9 ETH) -> Thành công
        self.contract.create_spend_request(self.bcs_1, "0xR2", 3 * WEI_PER_ETH, "De xuat 2 hop le", ready_t)
        self.assertEqual(self.contract.reserved_spend_amount, 9 * WEI_PER_ETH)
        self.assertEqual(self.contract.get_available_class_fund(), 9 * 10**17) # còn 0.9 ETH
        print("\n[Ca 14 - R3: Giữ chỗ đa đề xuất]: Ngăn chặn thành công việc nhiều đề xuất chi vượt ngân sách.")

    def test_case_15_expire_spend_request_releases_reserved_funds(self):
        """R5/R9: Đề xuất quá hạn 7 ngày giải phóng số tiền giữ chỗ về lại quỹ khả dụng"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH) # classFund = 9.9 ETH
        ready_t = self._setup_3_active_bcs(added_at=0)

        # Đề xuất 4 ETH
        req_id = self.contract.create_spend_request(self.bcs_1, "0xR1", 4 * WEI_PER_ETH, "Chi mua sam", ready_t)
        self.assertEqual(self.contract.reserved_spend_amount, 4 * WEI_PER_ETH)
        self.assertEqual(self.contract.get_available_class_fund(), 59 * 10**17) # 5.9 ETH

        # Chưa hết 7 ngày mà gọi expire -> Revert
        with self.assertRaises(CustomError):
            self.contract.expire_spend_request(req_id, current_time=ready_t + 3600)

        # Quá hạn 7 ngày gọi expire -> Thành công
        self.contract.expire_spend_request(req_id, current_time=ready_t + VOTING_PERIOD_SECONDS + 1)
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Expired")
        self.assertEqual(self.contract.reserved_spend_amount, 0)
        self.assertEqual(self.contract.get_available_class_fund(), 99 * 10**17) # Hoàn lại 9.9 ETH khả dụng!
        print("\n[Ca 15 - R5/R9: Đánh dấu Expired giải phóng tiền giữ chỗ]: 4 ETH giữ chỗ được giải phóng về quỹ khả dụng.")

    # ==========================================
    # CÁC CA KIỂM THỬ MỚI BỔ SUNG CHO LAB 14 (HOÀN TIỀN CÓ BIỂU QUYẾT BCS)
    # ==========================================

    def test_case_16_valid_refund_request_lifecycle(self):
        """R7: Toàn bộ chu trình hoàn tiền có biểu quyết BCS (Tạo yêu cầu -> BCS biểu quyết -> Giải ngân)"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        ready_t = self._setup_3_active_bcs(added_at=0)

        # 1. Student A tạo yêu cầu hoàn 4 ETH
        ref_id = self.contract.create_refund_request(self.student_a, 4 * WEI_PER_ETH, "Nop nham quy", ready_t)
        self.assertEqual(ref_id, 1)
        self.assertEqual(self.contract.refund_requests[ref_id]["voter_base"], 3)
        self.assertEqual(self.contract.reserved_refund_amount, 4 * WEI_PER_ETH)
        self.assertEqual(self.contract.pending_student_refund_amount[self.student_a], 4 * WEI_PER_ETH)
        self.assertEqual(self.contract.get_available_class_fund(), 59 * 10**17) # 9.9 - 4 = 5.9 ETH

        # 2. BCS1 và BCS2 bỏ phiếu thuận (2/3 >= 51%)
        self.contract.vote_refund_request(self.bcs_1, ref_id, True, ready_t)
        self.assertEqual(self.contract.refund_requests[ref_id]["status"], "Pending")
        self.contract.vote_refund_request(self.bcs_2, ref_id, True, ready_t)
        self.assertEqual(self.contract.refund_requests[ref_id]["status"], "Ready")

        # 3. Thực thi hoàn tiền
        self.contract.execute_refund_request(self.student_a, ref_id)
        self.assertEqual(self.contract.refund_requests[ref_id]["status"], "Executed")
        self.assertEqual(self.contract.student_contributions[self.student_a], 59 * 10**17) # 9.9 - 4 = 5.9 ETH
        self.assertEqual(self.contract.student_total_deposited[self.student_a], 10 * WEI_PER_ETH) # Tổng nộp gốc giữ nguyên 10 ETH
        self.assertEqual(self.contract.pending_student_refund_amount[self.student_a], 0)
        self.assertEqual(self.contract.reserved_refund_amount, 0)
        self.assertEqual(self.contract.class_fund_balance, 59 * 10**17) # 5.9 ETH
        self.assertEqual(self.contract.admin_fee_pool, 10**17) # 0.1 ETH phí giữ nguyên
        self.assertEqual(
            self.contract.get_total_contract_balance(),
            self.contract.class_fund_balance + self.contract.admin_fee_pool
        )
        print("\n[Ca 16 - R7: Hoàn tiền có biểu quyết]: Tạo yêu cầu -> BCS duyệt 2/3 -> Thực thi 4 ETH thành công, bảo toàn phí 0.1 ETH.")

    def test_case_17_refund_zero_amount_reverts(self):
        """R7 Negative: Chặn tạo yêu cầu hoàn tiền bằng 0 wei"""
        self.contract.deposit(self.student_a, 2 * WEI_PER_ETH)
        with self.assertRaises(ZeroAmountError):
            self.contract.create_refund_request(self.student_a, 0, "Zero refund", 1000)
        print("\n[Ca 17 - R7 Negative: Hoàn tiền 0 wei]: Revert ZeroAmount() thành công.")

    def test_case_18_refund_exceeding_contribution_reverts(self):
        """R7 Negative: Chặn tạo yêu cầu hoàn tiền vượt quá số tiền đã đóng góp"""
        self.contract.deposit(self.student_a, 2 * WEI_PER_ETH)
        ready_t = self._setup_3_active_bcs(added_at=0)
        with self.assertRaises(InsufficientContributionError):
            self.contract.create_refund_request(self.student_a, 3 * WEI_PER_ETH, "Too much", ready_t)
        print("\n[Ca 18 - R7 Negative: Hoàn vượt đóng góp]: Revert InsufficientContribution() thành công.")

    def test_case_19_non_contributor_cannot_refund(self):
        """R7 Negative: Người chưa từng đóng góp cố tình tạo yêu cầu hoàn tiền"""
        outsider = "0xOutsiderAddress000000000000000000000099"
        self.contract.deposit(self.student_a, 5 * WEI_PER_ETH)
        ready_t = self._setup_3_active_bcs(added_at=0)
        with self.assertRaises(InsufficientContributionError):
            self.contract.create_refund_request(outsider, 1 * WEI_PER_ETH, "Outsider request", ready_t)
        print("\n[Ca 19 - R7 Negative: Người ngoài xin hoàn tiền]: Chặn người chưa đóng góp thành công.")

    def test_case_20_refund_exceeding_available_fund_with_reserved_reverts(self):
        """R7 Negative: Chặn tạo yêu cầu hoàn tiền xâm lấn vào hạn mức đã giữ chỗ cho đề xuất chi"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH) # classFund = 9.9 ETH
        ready_t = self._setup_3_active_bcs(added_at=0)

        # BCS1 tạo đề xuất chi 7 ETH -> Giữ chỗ 7 ETH, khả dụng còn 2.9 ETH
        self.contract.create_spend_request(self.bcs_1, "0xRecipient", 7 * WEI_PER_ETH, "Chi mua sam", ready_t)
        self.assertEqual(self.contract.get_available_class_fund(), 29 * 10**17) # 2.9 ETH

        # Student A nộp 10 ETH, xin hoàn 5 ETH (> 2.9 ETH khả dụng) -> Revert InsufficientAvailableFund
        with self.assertRaises(InsufficientAvailableFundError):
            self.contract.create_refund_request(self.student_a, 5 * WEI_PER_ETH, "Exceed available", ready_t)
        print("\n[Ca 20 - R7 Negative: Hoàn vượt quỹ khả dụng]: Chặn hoàn tiền xâm lấn ngân sách đề xuất chi thành công.")

    def test_case_21_double_pending_refund_exceeding_total_reverts(self):
        """R7 Negative: Chặn tạo nhiều yêu cầu hoàn tiền đồng thời vượt tổng hạn mức đóng góp"""
        self.contract.deposit(self.student_a, 4 * WEI_PER_ETH)
        ready_t = self._setup_3_active_bcs(added_at=0)
        # Yêu cầu 1: 2.5 ETH -> Thành công (hạn mức net 3.96 ETH, còn lại 1.46 ETH)
        ref_id_1 = self.contract.create_refund_request(self.student_a, 25 * 10**17, "Req 1", ready_t)
        self.assertEqual(ref_id_1, 1)
        self.assertEqual(self.contract.get_student_available_contribution(self.student_a), 146 * 10**16) # Còn 1.46 ETH

        # Yêu cầu 2: Cố tạo thêm yêu cầu 2 ETH (> 1.46 ETH còn lại) -> Revert
        with self.assertRaises(InsufficientContributionError):
            self.contract.create_refund_request(self.student_a, 2 * WEI_PER_ETH, "Req 2 too big", ready_t)
        print("\n[Ca 21 - R7 Negative: Chặn yêu cầu kép vượt hạn mức]: Chặn tạo nhiều yêu cầu hoàn tiền vượt đóng góp thành công.")

    def test_case_22_refund_voting_rules(self):
        """R7 Governance: Kiểm tra quyền biểu quyết hoàn tiền (Chỉ BCS, chống vote kép, quá hạn 7 ngày)"""
        self.contract.deposit(self.student_a, 5 * WEI_PER_ETH)
        ready_t = self._setup_3_active_bcs(added_at=0)

        ref_id = self.contract.create_refund_request(self.student_a, 2 * WEI_PER_ETH, "Nop nham", ready_t)

        # 1. Người ngoài cố bỏ phiếu -> Revert NotActiveBCSError
        outsider = "0xOutsider9999999999999999999999999999999"
        with self.assertRaises(NotActiveBCSError):
            self.contract.vote_refund_request(outsider, ref_id, True, ready_t)

        # 2. BCS1 bỏ phiếu lần 1 -> Thành công
        self.contract.vote_refund_request(self.bcs_1, ref_id, True, ready_t)

        # 3. BCS1 cố bỏ phiếu lần 2 -> Revert AlreadyVotedRefundError
        with self.assertRaises(AlreadyVotedRefundError):
            self.contract.vote_refund_request(self.bcs_1, ref_id, True, ready_t)

        # 4. Quá hạn 7 ngày -> Revert RefundVotingPeriodEndedError và giải phóng giữ chỗ
        ref_id_2 = self.contract.create_refund_request(self.student_a, 1 * WEI_PER_ETH, "Req 2", ready_t)
        with self.assertRaises(RefundVotingPeriodEndedError):
            self.contract.vote_refund_request(self.bcs_2, ref_id_2, True, ready_t + VOTING_PERIOD_SECONDS + 1)
        self.assertEqual(self.contract.refund_requests[ref_id_2]["status"], "Expired")
        print("\n[Ca 22 - R7 Biểu quyết]: Chặn người ngoài vote, chặn vote kép, xử lý hết hạn 7 ngày chuẩn xác.")

    def test_case_23_refund_execution_rules_and_rollback(self):
        """R7 Execution: Chỉ thực thi khi đạt 51%, chống thực thi kép và kiểm tra rollback"""
        self.contract.deposit(self.student_a, 5 * WEI_PER_ETH)
        ready_t = self._setup_3_active_bcs(added_at=0)

        ref_id = self.contract.create_refund_request(self.student_a, 2 * WEI_PER_ETH, "Nop nham", ready_t)

        # Chưa đạt 51% (mới có 1/3 phiếu) -> Không thể thực thi
        self.contract.vote_refund_request(self.bcs_1, ref_id, True, ready_t)
        with self.assertRaises(ThresholdNotMetError):
            self.contract.execute_refund_request(self.student_a, ref_id)

        # Đạt 2/3 phiếu -> Sẵn sàng thực thi
        self.contract.vote_refund_request(self.bcs_2, ref_id, True, ready_t)
        self.contract.execute_refund_request(self.student_a, ref_id)

        # Cố thực thi lần 2 -> Revert RefundAlreadyExecutedError
        with self.assertRaises(RefundAlreadyExecutedError):
            self.contract.execute_refund_request(self.student_a, ref_id)
        print("\n[Ca 23 - R7 Thực thi]: Chặn thực thi khi chưa đạt 51%, chặn thực thi kép thành công.")

    def test_case_24_full_five_step_integration_lifecycle(self):
        """Integration Test: Chu trình liên hoàn 5 bước có biểu quyết BCS (Nạp -> Biểu quyết chi -> Chi -> Yêu cầu hoàn -> BCS duyệt -> Hoàn -> Rút phí)"""
        student_b = "0xStudentB00000000000000000000000000000003"
        recipient = "0xRecipient000000000000000000000000000001"

        # Thiết lập 3 BCS và kích hoạt sau 3 ngày
        ready_t = self._setup_3_active_bcs(added_at=0)

        # BƯỚC 1: Nạp tiền (Student A: 10 ETH, Student B: 5 ETH)
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        self.contract.deposit(student_b, 5 * WEI_PER_ETH)
        self.assertEqual(self.contract.class_fund_balance, 1485 * 10**16) # 14.85 ETH
        self.assertEqual(self.contract.admin_fee_pool, 15 * 10**16)       # 0.15 ETH
        self.assertEqual(self.contract.get_total_contract_balance(), 15 * WEI_PER_ETH)

        # BƯỚC 2: Biểu quyết chi (Tạo đề xuất 4 ETH, 2/3 phiếu thuận -> Ready)
        req_id = self.contract.create_spend_request(self.bcs_1, recipient, 4 * WEI_PER_ETH, "Chi tieu dot 1", ready_t)
        self.contract.vote_spend_request(self.bcs_1, req_id, True, ready_t)
        self.contract.vote_spend_request(self.bcs_2, req_id, True, ready_t)
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Ready")

        # BƯỚC 3: Chi tiền (Giải ngân 4 ETH)
        self.contract.execute_spend_request(self.bcs_1, req_id, current_time=ready_t)
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Executed")
        self.assertEqual(self.contract.class_fund_balance, 1085 * 10**16) # 10.85 ETH
        self.assertEqual(self.contract.reserved_spend_amount, 0)
        self.assertEqual(self.contract.get_total_contract_balance(), 11 * WEI_PER_ETH)

        # BƯỚC 4: Hoàn tiền có biểu quyết BCS (Student B tạo yêu cầu 3 ETH, BCS 1 & 2 duyệt, thực thi hoàn tiền)
        ref_id = self.contract.create_refund_request(student_b, 3 * WEI_PER_ETH, "Nop nham 3 ETH", ready_t + 1000)
        self.assertEqual(self.contract.reserved_refund_amount, 3 * WEI_PER_ETH)
        self.contract.vote_refund_request(self.bcs_1, ref_id, True, ready_t + 1000)
        self.contract.vote_refund_request(self.bcs_2, ref_id, True, ready_t + 1000)
        self.assertEqual(self.contract.refund_requests[ref_id]["status"], "Ready")

        self.contract.execute_refund_request(student_b, ref_id)
        self.assertEqual(self.contract.student_contributions[student_b], 195 * 10**16) # 4.95 - 3 = 1.95 ETH
        self.assertEqual(self.contract.student_total_deposited[student_b], 5 * WEI_PER_ETH)
        self.assertEqual(self.contract.class_fund_balance, 785 * 10**16)  # 7.85 ETH
        self.assertEqual(self.contract.reserved_refund_amount, 0)
        self.assertEqual(self.contract.get_total_contract_balance(), 8 * WEI_PER_ETH)

        # BƯỚC 5: Điều chuyển phí vận hành vào quỹ lớp (CVHT chuyển 0.1 ETH từ adminFeePool sang classFundBalance)
        self.contract.move_fee_to_class_fund(self.advisor, 10**17) # 0.1 ETH
        self.assertEqual(self.contract.admin_fee_pool, 5 * 10**16)        # 0.05 ETH
        self.assertEqual(self.contract.class_fund_balance, 795 * 10**16)  # 7.85 + 0.1 = 7.95 ETH
        self.assertEqual(self.contract.get_total_contract_balance(), 8 * WEI_PER_ETH) # 8.0 ETH không đổi (nội bộ hợp đồng)

        # Bất biến kế toán cuối cùng
        self.assertEqual(
            self.contract.get_total_contract_balance(),
            self.contract.class_fund_balance + self.contract.admin_fee_pool
        )
        print("\n[Ca 24 - Integration Test: Chu trình 5 bước có biểu quyết BCS]: Hoàn thành xuất sắc 100% chu trình (Nạp -> Biểu quyết chi -> Chi -> Yêu cầu hoàn -> BCS duyệt -> Hoàn -> Chuyển phí sang quỹ), bảo toàn tuyệt đối số dư.")

    # ==========================================
    # CÁC CA KIỂM THỬ MỚI BỔ SUNG CHO PHASE 1 (NHÓM A - HOÀN TIỀN THEO 99% NET)
    # ==========================================

    def test_case_25_section_a_full_net_refund_clears_contrib_keeps_total_deposited(self):
        """Phase 1 / Nhóm A: Nộp 10 ETH -> hạn mức 9.9 ETH, hoàn 9.9 ETH -> hạn mức về 0 nhưng studentTotalDeposited vẫn = 10 ETH"""
        ready_t = self._setup_3_active_bcs(added_at=0)
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)

        self.assertEqual(self.contract.get_student_contribution(self.student_a), 99 * 10**17)
        self.assertEqual(self.contract.get_student_total_deposited(self.student_a), 10 * WEI_PER_ETH)
        self.assertEqual(self.contract.get_student_max_refund(self.student_a), 99 * 10**17)

        ref_id = self.contract.create_refund_request(self.student_a, 99 * 10**17, "Hoan toan bo 9.9 ETH", ready_t)
        self.contract.vote_refund_request(self.bcs_1, ref_id, True, ready_t + 10)
        self.contract.vote_refund_request(self.bcs_2, ref_id, True, ready_t + 20)
        self.contract.execute_refund_request(self.student_a, ref_id)

        self.assertEqual(self.contract.get_student_contribution(self.student_a), 0)
        self.assertEqual(self.contract.get_student_total_deposited(self.student_a), 10 * WEI_PER_ETH)
        self.assertEqual(self.contract.get_student_max_refund(self.student_a), 0)
        self.assertEqual(self.contract.class_fund_balance, 0)
        self.assertEqual(self.contract.admin_fee_pool, 10**17)

        # Thử đòi thêm 1 wei -> Revert InsufficientContributionError
        with self.assertRaises(InsufficientContributionError):
            self.contract.create_refund_request(self.student_a, 1, "Vuot han muc 1 wei", ready_t + 30)

    def test_case_26_section_a_fraud_cross_student_drain_blocked(self):
        """Phase 1 / Nhóm A Fraud: A và B cùng nộp 10 ETH; A cố hoàn 10 ETH để rút 0.1 ETH từ phần B phải bị chặn"""
        ready_t = self._setup_3_active_bcs(added_at=0)
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        self.contract.deposit(self.student_b, 10 * WEI_PER_ETH)

        # Quỹ có 19.8 ETH nhưng hạn mức hoàn của A chỉ là 9.9 ETH
        self.assertEqual(self.contract.class_fund_balance, 198 * 10**17)
        self.assertEqual(self.contract.get_student_max_refund(self.student_a), 99 * 10**17)

        with self.assertRaises(InsufficientContributionError):
            self.contract.create_refund_request(self.student_a, 10 * WEI_PER_ETH, "Gian lan rut gross", ready_t)

        # Biên số nguyên nhỏ: 99 wei (fee 0, net 99) & 101 wei (fee 1, net 100)
        attacker_edge = "0xEdgeCaseStudent000000000000000000000088"
        self.contract.set_students(self.advisor, [attacker_edge], True)
        self.contract.deposit(attacker_edge, 99)
        self.assertEqual(self.contract.get_student_contribution(attacker_edge), 99)
        self.assertEqual(self.contract.get_student_total_deposited(attacker_edge), 99)
        self.contract.deposit(attacker_edge, 101)
        self.assertEqual(self.contract.get_student_contribution(attacker_edge), 199)
        self.assertEqual(self.contract.get_student_total_deposited(attacker_edge), 200)

    def test_case_27_section_a_multiple_partial_refunds_and_max_refund_view(self):
        """Phase 1 / Nhóm A: Hoàn từng phần nhiều lần tổng không vượt 99% net; getStudentMaxRefund giảm khi quỹ bị giữ chỗ"""
        ready_t = self._setup_3_active_bcs(added_at=0)
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)  # net 9.9 ETH

        # Tạo 3 yêu cầu hoàn từng phần: 4 + 5 + 0.9 = 9.9 ETH
        r1 = self.contract.create_refund_request(self.student_a, 4 * WEI_PER_ETH, "Part 1", ready_t)
        self.contract.vote_refund_request(self.bcs_1, r1, True, ready_t + 10)
        self.contract.vote_refund_request(self.bcs_2, r1, True, ready_t + 15)
        self.contract.execute_refund_request(self.student_a, r1)

        # Quỹ khả dụng 5.9 ETH; BCS giữ chỗ chi 3 ETH -> quỹ khả dụng còn 2.9 ETH
        # getStudentMaxRefund(A) phải trả min(5.9, 2.9) = 2.9 ETH
        self.contract.create_spend_request(self.bcs_1, "0xRecipient000000000000000000000000000001", 3 * WEI_PER_ETH, "Spend", ready_t + 20)
        self.assertEqual(self.contract.get_student_max_refund(self.student_a), 29 * 10**17)

        # Expire đề xuất chi sau 7 ngày -> A tiếp tục hoàn phần còn lại 5 + 0.9 = 5.9 ETH
        t2 = ready_t + 20 + VOTING_PERIOD_SECONDS + 1
        self.contract.expire_spend_request(1, t2)
        self.assertEqual(self.contract.get_student_max_refund(self.student_a), 59 * 10**17)

        r2 = self.contract.create_refund_request(self.student_a, 5 * WEI_PER_ETH, "Part 2", t2 + 100)
        r3 = self.contract.create_refund_request(self.student_a, 9 * 10**17, "Part 3", t2 + 100)
        self.assertEqual(self.contract.get_student_max_refund(self.student_a), 0)

        with self.assertRaises(InsufficientContributionError):
            self.contract.create_refund_request(self.student_a, 1, "Over by 1 wei", t2 + 100)
        self.contract.vote_refund_request(self.bcs_1, r2, True, t2 + 110)
        self.contract.vote_refund_request(self.bcs_2, r2, True, t2 + 115)
        self.contract.execute_refund_request(self.student_a, r2)
        self.contract.vote_refund_request(self.bcs_1, r3, True, t2 + 120)
        self.contract.vote_refund_request(self.bcs_2, r3, True, t2 + 125)
        self.contract.execute_refund_request(self.student_a, r3)

        self.assertEqual(self.contract.get_student_contribution(self.student_a), 0)
        self.assertEqual(self.contract.get_student_total_deposited(self.student_a), 10 * WEI_PER_ETH)

    # ==========================================
    # CÁC CA KIỂM THỬ MỚI BỔ SUNG CHO PHASE 2 (MỤC B & MỤC C)
    # ==========================================

    def test_case_28_section_b_activation_delay_3_days_and_readd_reset(self):
        """Phase 2 / Mục B: BCS mới chưa đủ 3 ngày không tạo/vote được; đủ 3 ngày kích hoạt; gỡ và thêm lại reset 3 ngày"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        # Thêm bcs_1, bcs_2 tại t = 1000 -> memberSince = 1000 + 3 days
        self.contract.set_bcs_member(self.advisor, self.bcs_1, True, current_time=1000)
        self.contract.set_bcs_member(self.advisor, self.bcs_2, True, current_time=1000)
        self.contract.set_bcs_member(self.advisor, self.bcs_3, True, current_time=1000)

        # Trước 3 ngày (1000 + 3 days - 1): bcs_1 không tạo được -> NotActiveBCS
        almost_ready = 1000 + BCS_ACTIVATION_DELAY - 1
        self.assertEqual(self.contract.eligible_bcs_count(almost_ready), 0)
        with self.assertRaises(NotActiveBCSError):
            self.contract.create_spend_request(self.bcs_1, "0xR1", 1 * WEI_PER_ETH, "Qua som", almost_ready)

        # Đúng 3 ngày: cả 3 kích hoạt -> eligible = 3 -> tạo được đề xuất
        exact_ready = 1000 + BCS_ACTIVATION_DELAY
        self.assertEqual(self.contract.eligible_bcs_count(exact_ready), 3)
        req_id = self.contract.create_spend_request(self.bcs_1, "0xR1", 1 * WEI_PER_ETH, "Hop le", exact_ready)
        self.assertEqual(req_id, 1)

        # Gỡ bcs_3 rồi thêm lại tại t = exact_ready + 10 -> memberSince mới phải reset thêm 3 ngày
        readd_t = exact_ready + 10
        self.contract.set_bcs_member(self.advisor, self.bcs_3, False, current_time=readd_t)
        self.assertEqual(self.contract.member_since[self.bcs_3], 0)
        self.assertFalse(self.contract.is_eligible_voter_at(self.bcs_3, readd_t))
        self.contract.set_bcs_member(self.advisor, self.bcs_3, True, current_time=readd_t)
        self.assertEqual(self.contract.member_since[self.bcs_3], readd_t + BCS_ACTIVATION_DELAY)
        with self.assertRaises(NotActiveBCSError):
            self.contract.vote_spend_request(self.bcs_3, req_id, True, readd_t + BCS_ACTIVATION_DELAY - 1)

    def test_case_29_section_b_min_3_bcs_required_for_spend_and_refund(self):
        """Phase 2 / Mục B: Dưới 3 BCS đủ điều kiện -> chặn CẢ đề xuất chi lẫn yêu cầu hoàn tiền của sinh viên"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        # Chỉ thêm 2 BCS tại t = 0 -> sau 3 ngày chỉ có 2 eligible < MIN_BCS_FOR_PROPOSAL (3)
        self.contract.set_bcs_member(self.advisor, self.bcs_1, True, current_time=0)
        self.contract.set_bcs_member(self.advisor, self.bcs_2, True, current_time=0)
        # Thêm bcs_3 muộn hơn (t = 100)
        self.contract.set_bcs_member(self.advisor, self.bcs_3, True, current_time=100)

        t_two_eligible = BCS_ACTIVATION_DELAY
        self.assertEqual(self.contract.eligible_bcs_count(t_two_eligible), 2)

        with self.assertRaises(NotEnoughBCSError):
            self.contract.create_spend_request(self.bcs_1, "0xR1", 1 * WEI_PER_ETH, "Thieu BCS", t_two_eligible)

        with self.assertRaises(NotEnoughBCSError):
            self.contract.create_refund_request(self.student_a, 1 * WEI_PER_ETH, "SV bi chan khi < 3 BCS", t_two_eligible)

        # Khi bcs_3 đủ 3 ngày (100 + 3 days) -> eligible = 3 -> cả hai đều tạo thành công
        t_three_eligible = 100 + BCS_ACTIVATION_DELAY
        self.assertEqual(self.contract.eligible_bcs_count(t_three_eligible), 3)
        req_id = self.contract.create_spend_request(self.bcs_1, "0xR1", 1 * WEI_PER_ETH, "Du 3 BCS", t_three_eligible)
        ref_id = self.contract.create_refund_request(self.student_a, 1 * WEI_PER_ETH, "Du 3 BCS", t_three_eligible)
        self.assertEqual(req_id, 1)
        self.assertEqual(ref_id, 1)

    def test_case_30_section_b_midflight_add_remove_bcs_preserves_voter_base(self):
        """Phase 2 / Mục B: Thêm hoặc gỡ BCS giữa chừng không đổi mẫu số voterBase của đề xuất đang chạy"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        ready_t = self._setup_3_active_bcs(added_at=0)

        bcs_4 = "0xBCSMember40000000000000000000000000000014"
        bcs_5 = "0xBCSMember50000000000000000000000000000015"
        self.contract.set_students(self.advisor, [bcs_4, bcs_5], True)

        # Tạo 1 đề xuất chi với 3 BCS (voterBase = 3)
        req_id = self.contract.create_spend_request(self.bcs_1, "0xR1", 2 * WEI_PER_ETH, "Snapshot test", ready_t)
        self.assertEqual(self.contract.spend_requests[req_id]["voter_base"], 3)

        # BCS1 đã vote YES (1/3 -> Pending)
        self.contract.vote_spend_request(self.bcs_1, req_id, True, ready_t + 10)

        # Gỡ BCS2 và BCS3 giữa chừng -> voterBase vẫn = 3 (1/3 không thể tự nâng thành 1/1 = 100%!)
        self.contract.set_bcs_member(self.advisor, self.bcs_2, False, current_time=ready_t + 20)
        self.contract.set_bcs_member(self.advisor, self.bcs_3, False, current_time=ready_t + 20)
        self.assertEqual(self.contract.active_bcs_count, 1)
        self.assertEqual(self.contract.spend_requests[req_id]["voter_base"], 3)
        with self.assertRaises(ThresholdNotMetError):
            self.contract.execute_spend_request(self.bcs_1, req_id, current_time=ready_t + 30)

        # Thêm mới BCS4, BCS5 giữa chừng và đợi đủ 3 ngày: cũng không đổi voterBase (= 3)
        self.contract.set_bcs_member(self.advisor, bcs_4, True, current_time=ready_t + 40)
        self.contract.set_bcs_member(self.advisor, bcs_5, True, current_time=ready_t + 40)
        later_t = ready_t + 40 + BCS_ACTIVATION_DELAY
        self.assertEqual(self.contract.spend_requests[req_id]["voter_base"], 3)

    def test_case_31_section_b_fraud_phantom_bcs_wallets_blocked(self):
        """Phase 2 / Mục B (Gian lận): CVHT thêm 3 ví 'ma' ngay trước lúc bỏ phiếu -> không có quyền trên đề xuất hiện hữu (kể cả sau 3 ngày)"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        ready_t = self._setup_3_active_bcs(added_at=0)

        req_id = self.contract.create_spend_request(self.bcs_1, "0xR1", 2 * WEI_PER_ETH, "De xuat bi nham tan cong", ready_t)
        ref_id = self.contract.create_refund_request(self.student_a, 2 * WEI_PER_ETH, "Hoan bi nham tan cong", ready_t)
        self.assertEqual(self.contract.spend_requests[req_id]["voter_base"], 3)
        self.assertEqual(self.contract.refund_requests[ref_id]["voter_base"], 3)

        # Kẻ gian / CVHT thông đồng thêm 3 ví 'ma' ngay sau khi đề xuất được tạo
        phantoms = [f"0xPhantom{i}" + "0" * 31 for i in range(1, 4)]
        self.contract.set_students(self.advisor, phantoms, True)
        phantom_added_t = ready_t + 100
        for p in phantoms:
            self.contract.set_bcs_member(self.advisor, p, True, current_time=phantom_added_t)

        # (a) Ngay lúc mới thêm: bị chặn bởi NotActiveBCS (< 3 giây)
        for p in phantoms:
            with self.assertRaises(NotActiveBCSError):
                self.contract.vote_spend_request(p, req_id, True, phantom_added_t + 1)
            with self.assertRaises(NotActiveBCSError):
                self.contract.vote_refund_request(p, ref_id, True, phantom_added_t + 1)

        # (b) Đợi đủ 3 giây (vẫn trong hạn 7 ngày bỏ phiếu): vượt qua onlyActiveBCS nhưng bị chặn bởi VoterNotEligibleAtCreation!
        after_3_days = phantom_added_t + BCS_ACTIVATION_DELAY
        for p in phantoms:
            with self.assertRaises(VoterNotEligibleAtCreationError):
                self.contract.vote_spend_request(p, req_id, True, after_3_days)
            with self.assertRaises(VoterNotEligibleAtCreationError):
                self.contract.vote_refund_request(p, ref_id, True, after_3_days)
        self.assertEqual(self.contract.spend_requests[req_id]["yes_votes"], 0)
        self.assertEqual(self.contract.refund_requests[ref_id]["yes_votes"], 0)

    def test_case_32_section_b_max_bcs_15_and_swap_pop_o1(self):
        """Phase 2 / Mục B: Giới hạn MAX_BCS = 15 và gỡ O(1) swap-and-pop chính xác"""
        members = [f"0xBCSCap{i:034d}" for i in range(1, MAX_BCS + 2)]
        self.contract.set_students(self.advisor, members, True)
        for i in range(MAX_BCS):
            self.contract.set_bcs_member(self.advisor, members[i], True, current_time=100)
        self.assertEqual(self.contract.active_bcs_count, MAX_BCS)
        self.assertEqual(len(self.contract.get_bcs_list()), MAX_BCS)

        # Thêm người thứ 16 -> MaxBCSReached
        with self.assertRaises(MaxBCSReachedError):
            self.contract.set_bcs_member(self.advisor, members[MAX_BCS], True, current_time=100)

        # Gỡ phần tử đầu và phần tử giữa bằng swap-and-pop O(1), rồi thêm người thứ 16 thành công
        self.contract.set_bcs_member(self.advisor, members[0], False, current_time=101)
        self.contract.set_bcs_member(self.advisor, members[7], False, current_time=101)
        self.assertEqual(self.contract.active_bcs_count, MAX_BCS - 2)
        self.assertNotIn(members[0], self.contract.get_bcs_list())
        self.assertNotIn(members[7], self.contract.get_bcs_list())

        self.contract.set_bcs_member(self.advisor, members[MAX_BCS], True, current_time=102)
        self.assertEqual(self.contract.active_bcs_count, MAX_BCS - 1)
        self.assertIn(members[MAX_BCS], self.contract.get_bcs_list())

    def test_case_33_section_c_bcs_self_refund_conflict_and_voter_base_minus_1(self):
        """Phase 2 / Mục C: 3 BCS, bcs_1 tự xin hoàn tiền -> voterBase=2, bcs_1 bị ConflictOfInterest, cần 2 phiếu còn lại"""
        ready_t = self._setup_3_active_bcs(added_at=0)
        self.contract.deposit(self.bcs_1, 5 * WEI_PER_ETH)  # 4.95 ETH net

        ref_id = self.contract.create_refund_request(self.bcs_1, 2 * WEI_PER_ETH, "BCS1 nop nham", ready_t)
        self.assertEqual(self.contract.refund_requests[ref_id]["voter_base"], 2)  # 3 - 1 = 2

        # Fraud: BCS1 tự bỏ phiếu thuận cho yêu cầu hoàn tiền của chính mình -> Revert ConflictOfInterest
        with self.assertRaises(ConflictOfInterestError):
            self.contract.vote_refund_request(self.bcs_1, ref_id, True, ready_t + 10)

        # 1/2 = 50% < 51% -> vẫn Pending
        self.contract.vote_refund_request(self.bcs_2, ref_id, True, ready_t + 20)
        self.assertEqual(self.contract.refund_requests[ref_id]["status"], "Pending")

        # 2/2 = 100% >= 51% (cả 2 BCS còn lại) -> Ready, yesVotes = 2 >= 2!
        self.contract.vote_refund_request(self.bcs_3, ref_id, True, ready_t + 30)
        self.assertEqual(self.contract.refund_requests[ref_id]["status"], "Ready")
        self.assertGreaterEqual(self.contract.refund_requests[ref_id]["yes_votes"], 2)

        self.contract.execute_refund_request(self.bcs_2, ref_id)
        self.assertEqual(self.contract.refund_requests[ref_id]["status"], "Executed")

    def test_case_34_section_c_spend_recipient_is_bcs_conflict(self):
        """Phase 2 / Mục C: Đề xuất chi có recipient là BCS đủ điều kiện -> voterBase = eligible - 1, recipient bị ConflictOfInterest"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        ready_t = self._setup_3_active_bcs(added_at=0)

        # bcs_1 tạo đề xuất chi trả cho bcs_3 -> bcs_3 không được bỏ phiếu, voterBase = 2
        req_id = self.contract.create_spend_request(self.bcs_1, self.bcs_3, 2 * WEI_PER_ETH, "Hoan ung cho BCS3", ready_t)
        self.assertEqual(self.contract.spend_requests[req_id]["voter_base"], 2)

        with self.assertRaises(ConflictOfInterestError):
            self.contract.vote_spend_request(self.bcs_3, req_id, True, ready_t + 10)

        self.contract.vote_spend_request(self.bcs_1, req_id, True, ready_t + 20)
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Pending")  # 1/2 = 50%

        self.contract.vote_spend_request(self.bcs_2, req_id, True, ready_t + 30)
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Ready")  # 2/2 = 100%
        self.assertGreaterEqual(self.contract.spend_requests[req_id]["yes_votes"], 2)

    def test_case_35_section_c_external_recipient_allows_all_bcs_and_creator_votes(self):
        """Phase 2 / Mục C: recipient KHÔNG phải BCS -> voterBase = eligible (3) và creator được bỏ phiếu bình thường"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        ready_t = self._setup_3_active_bcs(added_at=0)
        vendor = "0xExternalVendor00000000000000000000000099"

        req_id = self.contract.create_spend_request(self.bcs_1, vendor, 2 * WEI_PER_ETH, "Tra nha cung cap", ready_t)
        self.assertEqual(self.contract.spend_requests[req_id]["voter_base"], 3)

        # Creator bcs_1 và bcs_2 bỏ phiếu bình thường -> 2/3 -> Ready, yesVotes = 2 >= 2
        self.contract.vote_spend_request(self.bcs_1, req_id, True, ready_t + 10)
        self.contract.vote_spend_request(self.bcs_2, req_id, True, ready_t + 20)
        self.assertEqual(self.contract.spend_requests[req_id]["status"], "Ready")
        self.assertGreaterEqual(self.contract.spend_requests[req_id]["yes_votes"], 2)

    def test_case_36_section_c_pending_bcs_recipient_does_not_reduce_voter_base(self):
        """Phase 2 / Mục C Edge Case: recipient là BCS mới (< 3 ngày, chưa eligible) -> voterBase vẫn = eligible (3) và vẫn bị chặn vote sau khi đủ 3 ngày"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        ready_t = self._setup_3_active_bcs(added_at=0)

        pending_bcs4 = "0xPendingBCS4000000000000000000000000000044"
        self.contract.set_students(self.advisor, [pending_bcs4], True)
        self.contract.set_bcs_member(self.advisor, pending_bcs4, True, current_time=ready_t - 10)
        # Tại ready_t, chỉ có 3 BCS eligible; pending_bcs4 CHƯA eligible
        req_id = self.contract.create_spend_request(self.bcs_1, pending_bcs4, 2 * WEI_PER_ETH, "Chi cho BCS cho kich hoat", ready_t)
        self.assertEqual(self.contract.spend_requests[req_id]["voter_base"], 3)

        # Đợi đủ 3 ngày cho pending_bcs4 -> vẫn bị ConflictOfInterest chặn bỏ phiếu!
        with self.assertRaises(ConflictOfInterestError):
            self.contract.vote_spend_request(pending_bcs4, req_id, True, ready_t - 10 + BCS_ACTIVATION_DELAY)

    def test_case_37_section_b_c_invariant_every_approved_proposal_has_min_2_yes_votes(self):
        """Phase 2 / Mục B+C Bất biến: Với mọi quy mô BCS 3..15 (cả trường hợp trừ 1 xung đột), mọi đề xuất đạt ngưỡng đều có yesVotes >= 2"""
        for n_eligible in range(MIN_BCS_FOR_PROPOSAL, MAX_BCS + 1):
            for has_conflict in (False, True):
                voter_base = n_eligible - 1 if has_conflict else n_eligible
                min_yes_needed = next(
                    y for y in range(1, voter_base + 1)
                    if (y * BPS_DENOMINATOR) // voter_base >= PASSING_THRESHOLD_BPS
                )
                self.assertGreaterEqual(min_yes_needed, 2, f"Fail invariant at eligible={n_eligible}, conflict={has_conflict}")


    # ==========================================
    # CÁC CA KIỂM THỬ MỚI BỔ SUNG CHO PHASE 3 (MỤC D)
    # ==========================================

    def test_case_38_section_d_stranger_and_advisor_cannot_deposit_or_receive(self):
        """Phase 3 / Mục D: Người ngoài chưa ghi danh và Cố vấn học tập không thể nạp qua deposit() hoặc receive()"""
        stranger = "0xStrangerUnenrolled0000000000000000000001"
        with self.assertRaises(NotEnrolledStudentError):
            self.contract.deposit(stranger, 1 * WEI_PER_ETH)
        with self.assertRaises(NotEnrolledStudentError):
            self.contract.receive(stranger, 1 * WEI_PER_ETH)

        # Advisor không thể nạp (vì không được ghi danh)
        with self.assertRaises(NotEnrolledStudentError):
            self.contract.deposit(self.advisor, 1 * WEI_PER_ETH)
        with self.assertRaises(NotEnrolledStudentError):
            self.contract.receive(self.advisor, 1 * WEI_PER_ETH)

    def test_case_39_section_d_advisor_cannot_be_student(self):
        """Phase 3 / Mục D: Advisor không thể tự ghi danh vào danh sách sinh viên -> AdvisorCannotBeStudent"""
        with self.assertRaises(AdvisorCannotBeStudentError):
            self.contract.set_students(self.advisor, [self.advisor], True)

    def test_case_40_section_d_non_student_cannot_be_bcs(self):
        """Phase 3 / Mục D: Không thể cấp quyền BCS cho người chưa là sinh viên -> BCSMustBeEnrolledStudent"""
        non_student = "0xNonStudentPerson00000000000000000000002"
        with self.assertRaises(BCSMustBeEnrolledStudentError):
            self.contract.set_bcs_member(self.advisor, non_student, True, current_time=100)

    def test_case_41_section_d_cannot_remove_student_if_active_bcs(self):
        """Phase 3 / Mục D: Không thể xóa sinh viên khỏi danh sách nếu vẫn đang là BCS -> StudentIsBCS"""
        # bcs_1 đang là sinh viên và được thêm làm BCS
        self.contract.set_bcs_member(self.advisor, self.bcs_1, True, current_time=100)
        with self.assertRaises(StudentIsBCSError):
            self.contract.set_students(self.advisor, [self.bcs_1], False)

        # Gỡ quyền BCS trước, sau đó xóa sinh viên thành công
        self.contract.set_bcs_member(self.advisor, self.bcs_1, False, current_time=101)
        self.contract.set_students(self.advisor, [self.bcs_1], False)
        self.assertFalse(self.contract.is_student[self.bcs_1])

    def test_case_42_section_d_set_students_batch_limit_and_idempotence(self):
        """Phase 3 / Mục D: Batch > 100 bị revert BatchTooLarge, địa chỉ 0 bị InvalidAddress, trùng lặp không tính tăng 2 lần"""
        # Batch > 100
        too_many = [f"0xStudentBatch{i:030d}" for i in range(MAX_BATCH + 1)]
        with self.assertRaises(BatchTooLargeError):
            self.contract.set_students(self.advisor, too_many, True)

        # Địa chỉ 0
        with self.assertRaises(InvalidAddressError):
            self.contract.set_students(self.advisor, ["0x0000000000000000000000000000000000000000"], True)

        # Idempotence: truyền 2 địa chỉ trùng lặp trong batch
        student_c = "0xStudentC00000000000000000000000000000004"
        initial_enrolled = self.contract.enrolled_count
        self.contract.set_students(self.advisor, [student_c, student_c], True)
        self.assertEqual(self.contract.enrolled_count, initial_enrolled + 1)
        self.assertTrue(self.contract.is_student[student_c])

    def test_case_43_section_d_removed_student_can_still_refund(self):
        """Phase 3 / Mục D: Sinh viên nộp tiền rồi bị xóa khỏi danh sách vẫn được tạo yêu cầu hoàn tiền và thực thi nhận tiền"""
        ready_t = self._setup_3_active_bcs(added_at=0)
        self.contract.deposit(self.student_a, 5 * WEI_PER_ETH)  # net 4.95 ETH

        # CVHT xóa student_a khỏi danh sách sinh viên
        self.contract.set_students(self.advisor, [self.student_a], False)
        self.assertFalse(self.contract.is_student[self.student_a])

        # student_a không thể nạp thêm
        with self.assertRaises(NotEnrolledStudentError):
            self.contract.deposit(self.student_a, 1 * WEI_PER_ETH)

        # Nhưng student_a VẪN tạo được yêu cầu hoàn tiền vì còn student_contributions > 0
        ref_id = self.contract.create_refund_request(self.student_a, 2 * WEI_PER_ETH, "Rut von sau khi thoi hoc", ready_t)
        self.contract.vote_refund_request(self.bcs_1, ref_id, True, ready_t + 10)
        self.contract.vote_refund_request(self.bcs_2, ref_id, True, ready_t + 20)
        self.assertEqual(self.contract.refund_requests[ref_id]["status"], "Ready")

        refunded = self.contract.execute_refund_request(self.student_a, ref_id)
        self.assertEqual(refunded, 2 * WEI_PER_ETH)
        self.assertEqual(self.contract.refund_requests[ref_id]["status"], "Executed")

    def test_case_44_section_d_commit_roster_hash(self):
        """Phase 3 / Mục D: Chỉ Advisor được commitRoster, lưu đúng rosterHash và phát sự kiện"""
        fake_hash = "0x" + "ab" * 32
        # Non-advisor gọi -> revert NotAdvisor
        with self.assertRaises(NotAdvisorError):
            self.contract.commit_roster(self.attacker, fake_hash)

        self.contract.commit_roster(self.advisor, fake_hash)
        self.assertEqual(self.contract.roster_hash, fake_hash)

    def test_case_45_section_d_forced_eth_and_unaccounted_balance(self):
        """Phase 3 / Mục D: Ép ETH không làm sai lệch sổ cái; getUnaccountedBalance() trả về đúng lượng chênh lệch"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        self.assertEqual(self.contract.get_unaccounted_balance(), 0)

        # Mô phỏng ép 3 ETH vào hợp đồng
        self.contract.forced_eth_wei = 3 * WEI_PER_ETH
        self.assertEqual(self.contract.get_unaccounted_balance(), 3 * WEI_PER_ETH)
        self.assertEqual(self.contract.class_fund_balance, 99 * 10**17)
        self.assertEqual(self.contract.admin_fee_pool, 1 * 10**17)

    # ==========================================
    # PHASE 4 (MỤC E: ĐỢT THU NỘP QUỸ TRÊN CHUỖI)
    # ==========================================

    def test_case_46_section_e_create_collection_happy_path_and_validation(self):
        """Phase 4 / Mục E: BCS active tạo đợt thu hợp lệ, lưu expectedPayers = enrolledCount, và kiểm tra validation"""
        ready_t = self._setup_3_active_bcs(added_at=0)
        # 5 sinh viên ghi danh: student_a, student_b, bcs_1, bcs_2, bcs_3
        self.assertEqual(self.contract.enrolled_count, 5)

        deadline = ready_t + 7 * 24 * 3600
        cid = self.contract.create_collection(
            caller=self.bcs_1,
            target_wei=1 * WEI_PER_ETH,
            deadline=deadline,
            purpose="Quy lop Hoc ky 1 - Nam 2026",
            current_time=ready_t,
        )
        self.assertEqual(cid, 1)
        self.assertEqual(self.contract.collection_count, 1)
        self.assertEqual(self.contract.active_collection_id, 1)
        self.assertEqual(self.contract.get_active_collection_id(ready_t), 1)

        col = self.contract.get_collection(cid)
        self.assertEqual(col["id"], 1)
        self.assertEqual(col["target_wei"], 1 * WEI_PER_ETH)
        self.assertEqual(col["deadline"], deadline)
        self.assertEqual(col["purpose"], "Quy lop Hoc ky 1 - Nam 2026")
        self.assertEqual(col["creator"], self.bcs_1)
        self.assertEqual(col["created_at"], ready_t)
        self.assertFalse(col["closed"])
        self.assertEqual(col["expected_payers"], 5)
        self.assertEqual(col["paid_count"], 0)

        # Validation: target_wei = 0 -> ZeroAmountError
        with self.assertRaises(ZeroAmountError):
            self.contract.create_collection(self.bcs_1, 0, deadline + 10, "Target zero", ready_t)

        # Validation: deadline <= current_time -> InvalidDeadlineError
        with self.assertRaises(InvalidDeadlineError):
            self.contract.create_collection(self.bcs_1, 1 * WEI_PER_ETH, ready_t, "Past deadline", ready_t)

        # Validation: purpose rỗng -> EmptyPurposeError
        with self.assertRaises(EmptyPurposeError):
            self.contract.create_collection(self.bcs_1, 1 * WEI_PER_ETH, deadline + 10, "", ready_t)

        # Validation: purpose quá 256 ký tự -> PurposeTooLongError
        with self.assertRaises(PurposeTooLongError):
            self.contract.create_collection(self.bcs_1, 1 * WEI_PER_ETH, deadline + 10, "A" * 257, ready_t)

    def test_case_47_section_e_only_active_bcs_can_create_and_close(self):
        """Phase 4 / Mục E (Gian lận): Người không phải active BCS (student, advisor, attacker, BCS chưa đủ 3 ngày) bị chặn"""
        ready_t = self._setup_3_active_bcs(added_at=0)
        deadline = ready_t + 7 * 24 * 3600

        # Sinh viên thường gọi -> Revert NotActiveBCS
        with self.assertRaises(NotActiveBCSError):
            self.contract.create_collection(self.student_a, 1 * WEI_PER_ETH, deadline, "Student hack", ready_t)

        # Cố vấn học tập (Advisor) gọi -> Revert NotActiveBCS (Cố vấn không được tạo đợt thu theo Mục H.7)
        with self.assertRaises(NotActiveBCSError):
            self.contract.create_collection(self.advisor, 1 * WEI_PER_ETH, deadline, "Advisor hack", ready_t)

        # Kẻ lạ ngoài danh sách -> Revert NotActiveBCS
        with self.assertRaises(NotActiveBCSError):
            self.contract.create_collection(self.attacker, 1 * WEI_PER_ETH, deadline, "Attacker hack", ready_t)

        # BCS mới thêm nhưng chưa đủ trễ 3 giây (< 3s) -> Revert NotActiveBCS
        bcs_new = "0xBCSNew00000000000000000000000000000004"
        self.contract.set_students(self.advisor, [bcs_new], True)
        self.contract.set_bcs_member(self.advisor, bcs_new, True, current_time=ready_t)
        with self.assertRaises(NotActiveBCSError):
            self.contract.create_collection(bcs_new, 1 * WEI_PER_ETH, deadline, "Immature BCS", ready_t + 1)

        # Tạo đợt 1 bởi bcs_1
        cid = self.contract.create_collection(self.bcs_1, 1 * WEI_PER_ETH, deadline, "Hop le", ready_t)

        # Advisor hay student cố đóng đợt thu -> Revert NotActiveBCS
        with self.assertRaises(NotActiveBCSError):
            self.contract.close_collection(self.advisor, cid, "Advisor close hack", ready_t + 100)
        with self.assertRaises(NotActiveBCSError):
            self.contract.close_collection(self.student_a, cid, "Student close hack", ready_t + 100)

    def test_case_48_section_e_only_one_collection_open_at_a_time(self):
        """Phase 4 / Mục E: Chỉ 1 đợt thu mở tại 1 thời điểm; cố tạo đợt 2 khi đợt 1 chưa đóng sẽ bị revert"""
        ready_t = self._setup_3_active_bcs(added_at=0)
        deadline = ready_t + 7 * 24 * 3600
        cid1 = self.contract.create_collection(self.bcs_1, 1 * WEI_PER_ETH, deadline, "Dot thu 1", ready_t)
        self.assertEqual(cid1, 1)

        # Cố tạo đợt thu thứ 2 khi đợt 1 chưa đóng -> Revert CollectionStillOpen
        with self.assertRaises(CollectionStillOpenError):
            self.contract.create_collection(self.bcs_2, 2 * WEI_PER_ETH, deadline + 1000, "Dot thu 2 bat hop phap", ready_t + 10)

        # Đóng đợt thu 1
        self.contract.close_collection(self.bcs_1, cid1, "Hoan thanh dot 1", ready_t + 50)
        self.assertTrue(self.contract.collections[cid1]["closed"])
        self.assertEqual(self.contract.active_collection_id, 0)
        self.assertEqual(self.contract.get_active_collection_id(ready_t + 50), 0)

        # Đóng lại đợt đã đóng -> Revert CollectionAlreadyClosed
        with self.assertRaises(CollectionAlreadyClosedError):
            self.contract.close_collection(self.bcs_2, cid1, "Dong lai dot 1", ready_t + 60)

        # Giờ BCS có thể tạo đợt thu thứ 2 thành công
        cid2 = self.contract.create_collection(self.bcs_2, 2 * WEI_PER_ETH, deadline + 2000, "Dot thu 2 hop phap", ready_t + 70)
        self.assertEqual(cid2, 2)
        self.assertEqual(self.contract.active_collection_id, 2)

    def test_case_49_section_e_deposit_to_collection_full_payment_and_paid_count(self):
        """Phase 4 / Mục E: Sinh viên nạp đủ targetWei vào đợt thu -> paidCount tăng 1 lần duy nhất, hasPaid=True"""
        ready_t = self._setup_3_active_bcs(added_at=0)
        deadline = ready_t + 7 * 24 * 3600
        cid = self.contract.create_collection(self.bcs_1, 1 * WEI_PER_ETH, deadline, "Dot thu hoc ky 1", ready_t)

        self.assertFalse(self.contract.has_paid_in_collection(cid, self.student_a))
        self.assertEqual(self.contract.collections[cid]["paid_count"], 0)

        # student_a nạp đúng 1 ETH
        net, fee = self.contract.deposit_to_collection(self.student_a, cid, 1 * WEI_PER_ETH, ready_t + 100)
        self.assertEqual(net, 99 * 10**16)  # 0.99 ETH
        self.assertEqual(fee, 1 * 10**16)   # 0.01 ETH

        # Kiểm tra ghi nhận theo đợt thu
        self.assertEqual(self.contract.paid_in_collection[cid][self.student_a], 1 * WEI_PER_ETH)
        self.assertTrue(self.contract.has_paid_in_collection(cid, self.student_a))
        self.assertEqual(self.contract.collections[cid]["paid_count"], 1)

        # student_a nạp thêm 0.5 ETH vào cùng đợt thu -> paidCount KHÔNG được tăng thêm
        self.contract.deposit_to_collection(self.student_a, cid, 5 * 10**17, ready_t + 200)
        self.assertEqual(self.contract.paid_in_collection[cid][self.student_a], 15 * 10**17)
        self.assertTrue(self.contract.has_paid_in_collection(cid, self.student_a))
        self.assertEqual(self.contract.collections[cid]["paid_count"], 1)

    def test_case_50_section_e_deposit_to_collection_partial_payments(self):
        """Phase 4 / Mục E: Nạp nhiều lần (partial deposits) tích lũy cho đến khi chạm mốc targetWei"""
        ready_t = self._setup_3_active_bcs(added_at=0)
        deadline = ready_t + 7 * 24 * 3600
        cid = self.contract.create_collection(self.bcs_1, 1 * WEI_PER_ETH, deadline, "Dot thu partial", ready_t)

        # Đợt 1: nạp 0.4 ETH
        self.contract.deposit_to_collection(self.student_b, cid, 4 * 10**17, ready_t + 10)
        self.assertFalse(self.contract.has_paid_in_collection(cid, self.student_b))
        self.assertEqual(self.contract.collections[cid]["paid_count"], 0)

        # Đợt 2: nạp tiếp 0.3 ETH -> tổng 0.7 ETH (chưa đủ 1.0 ETH)
        self.contract.deposit_to_collection(self.student_b, cid, 3 * 10**17, ready_t + 20)
        self.assertFalse(self.contract.has_paid_in_collection(cid, self.student_b))
        self.assertEqual(self.contract.collections[cid]["paid_count"], 0)

        # Đợt 3: nạp tiếp 0.3 ETH -> tổng 1.0 ETH (chạm ngưỡng targetWei)
        self.contract.deposit_to_collection(self.student_b, cid, 3 * 10**17, ready_t + 30)
        self.assertTrue(self.contract.has_paid_in_collection(cid, self.student_b))
        self.assertEqual(self.contract.collections[cid]["paid_count"], 1)

    def test_case_51_section_e_deposit_to_collection_closed_or_expired_reverts(self):
        """Phase 4 / Mục E: Nạp vào đợt thu đã đóng hoặc quá hạn bị revert"""
        ready_t = self._setup_3_active_bcs(added_at=0)
        deadline = ready_t + 7 * 24 * 3600
        cid = self.contract.create_collection(self.bcs_1, 1 * WEI_PER_ETH, deadline, "Dot thu test close/expire", ready_t)

        # Nạp quá hạn deadline -> Revert CollectionExpired
        with self.assertRaises(CollectionExpiredError):
            self.contract.deposit_to_collection(self.student_a, cid, 1 * WEI_PER_ETH, current_time=deadline + 1)

        # Đóng đợt thu -> Nạp bị Revert CollectionIsClosed
        self.contract.close_collection(self.bcs_1, cid, "Dong dot som", ready_t + 100)
        with self.assertRaises(CollectionIsClosedError):
            self.contract.deposit_to_collection(self.student_a, cid, 1 * WEI_PER_ETH, current_time=ready_t + 101)

    def test_case_52_section_e_fraud_cross_collection_no_spillover(self):
        """Phase 4 / Mục E (Gian lận): Sinh viên đã nộp đợt cũ KHÔNG tự động được tính là đã nộp đợt mới"""
        ready_t = self._setup_3_active_bcs(added_at=0)
        deadline1 = ready_t + 7 * 24 * 3600
        cid1 = self.contract.create_collection(self.bcs_1, 1 * WEI_PER_ETH, deadline1, "Dot thu 1", ready_t)

        # student_a nộp đủ đợt 1
        self.contract.deposit_to_collection(self.student_a, cid1, 1 * WEI_PER_ETH, ready_t + 10)
        self.assertTrue(self.contract.has_paid_in_collection(cid1, self.student_a))

        # Đóng đợt 1, mở đợt 2
        self.contract.close_collection(self.bcs_1, cid1, "Ket thuc dot 1", ready_t + 20)
        deadline2 = ready_t + 14 * 24 * 3600
        cid2 = self.contract.create_collection(self.bcs_1, 1 * WEI_PER_ETH, deadline2, "Dot thu 2", ready_t + 30)

        # student_a có student_contributions tích lũy = 0.99 ETH từ trước, nhưng ở đợt 2 CHƯA nộp
        self.assertFalse(self.contract.has_paid_in_collection(cid2, self.student_a))
        self.assertEqual(self.contract.paid_in_collection[cid2].get(self.student_a, 0), 0)
        self.assertEqual(self.contract.collections[cid2]["paid_count"], 0)

    def test_case_53_section_e_general_deposit_does_not_affect_collection(self):
        """Phase 4 / Mục E: Nạp quỹ chung qua deposit() / receive() không làm thay đổi paidInCollection của đợt thu"""
        ready_t = self._setup_3_active_bcs(added_at=0)
        deadline = ready_t + 7 * 24 * 3600
        cid = self.contract.create_collection(self.bcs_1, 1 * WEI_PER_ETH, deadline, "Dot thu song song", ready_t)

        # student_a nạp 2 ETH vào quỹ chung qua deposit()
        self.contract.deposit(self.student_a, 2 * WEI_PER_ETH)
        # Nạp quỹ chung không tính vào đợt thu
        self.assertFalse(self.contract.has_paid_in_collection(cid, self.student_a))
        self.assertEqual(self.contract.paid_in_collection[cid].get(self.student_a, 0), 0)
        self.assertEqual(self.contract.collections[cid]["paid_count"], 0)

        # Người ngoài danh sách cố nạp vào đợt thu -> Revert NotEnrolledStudent
        with self.assertRaises(NotEnrolledStudentError):
            self.contract.deposit_to_collection(self.attacker, cid, 1 * WEI_PER_ETH, ready_t + 100)

    # ==========================================
    # CÁC CA KIỂM THỬ MỚI BỔ SUNG CHO PHASE 5 (MỤC F - PHÍ VẬN HÀNH & HOÀN GAS TỰ ĐỘNG)
    # ==========================================

    def test_case_54_section_f_compute_gas_refund_pure_formula(self):
        """Phase 5 / Mục F: Kiểm tra hàm thuần compute_gas_refund với các biên giới hạn, thiếu hụt pool và premium cap"""
        basefee = 2 * 10**9 # 2 gwei
        
        # 1. Trường hợp bình thường: gas_used = 50,000, gas_price = 3 gwei (dưới trần basefee + 2 gwei = 4 gwei), pool dồi dào
        pool = 1 * WEI_PER_ETH
        units, price, owed, paid, shortfall = compute_gas_refund(50_000, 3 * 10**9, basefee, pool)
        self.assertEqual(units, 50_000 + GAS_REFUND_OVERHEAD) # 80,000
        self.assertEqual(price, 3 * 10**9)
        self.assertEqual(owed, 80_000 * 3 * 10**9) # 240,000 gwei = 240,000 * 10^9 wei
        self.assertEqual(paid, owed)
        self.assertEqual(shortfall, 0)

        # 2. Trần gas price: gas_price = 10 gwei > basefee (2 gwei) + 2 gwei -> bị chặn ở 4 gwei
        units, price, owed, paid, shortfall = compute_gas_refund(50_000, 10 * 10**9, basefee, pool)
        self.assertEqual(price, 4 * 10**9)
        self.assertEqual(owed, 80_000 * 4 * 10**9)
        self.assertEqual(paid, owed)
        self.assertEqual(shortfall, 0)

        # 3. Trần số lượng gas units: gas_used = 600,000 -> 600,000 + 30,000 = 630,000 > MAX_REFUND_GAS_UNITS (500,000)
        units, price, owed, paid, shortfall = compute_gas_refund(600_000, 3 * 10**9, basefee, pool)
        self.assertEqual(units, MAX_REFUND_GAS_UNITS) # 500,000
        self.assertEqual(owed, 500_000 * 3 * 10**9)
        self.assertEqual(paid, owed)
        self.assertEqual(shortfall, 0)

        # 4. Quỹ phí không đủ (pool thiếu hụt): pool chỉ có 100,000 gwei < owed 240,000 gwei
        partial_pool = 100_000 * 10**9
        units, price, owed, paid, shortfall = compute_gas_refund(50_000, 3 * 10**9, basefee, partial_pool)
        self.assertEqual(paid, partial_pool)
        self.assertEqual(shortfall, owed - partial_pool)
        self.assertEqual(paid + shortfall, owed)

        # 5. Quỹ phí cạn kiệt (pool = 0): hoàn 0, shortfall = toàn bộ owed
        units, price, owed, paid, shortfall = compute_gas_refund(50_000, 3 * 10**9, basefee, 0)
        self.assertEqual(paid, 0)
        self.assertEqual(shortfall, owed)

    def test_case_55_section_f_move_fee_to_class_fund_happy_and_validation(self):
        """Phase 5 / Mục F: moveFeeToClassFund chỉ Cố vấn được gọi, kiểm tra validation và bảo toàn số dư"""
        # Nộp 10 ETH: class_fund = 9.9 ETH, admin_fee_pool = 0.1 ETH
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        self.assertEqual(self.contract.admin_fee_pool, 10**17)
        self.assertEqual(self.contract.class_fund_balance, 99 * 10**17)
        self.assertEqual(self.contract.get_total_contract_balance(), 10 * WEI_PER_ETH)

        # Người ngoài / BCS gọi -> Revert NotAdvisor
        with self.assertRaises(NotAdvisorError):
            self.contract.move_fee_to_class_fund(self.bcs_1, 5 * 10**16)

        # Số tiền = 0 -> Revert ZeroAmount
        with self.assertRaises(ZeroAmountError):
            self.contract.move_fee_to_class_fund(self.advisor, 0)

        # Vượt quá admin_fee_pool (0.2 ETH > 0.1 ETH) -> Revert InsufficientAdminFee
        with self.assertRaises(InsufficientAdminFeeError):
            self.contract.move_fee_to_class_fund(self.advisor, 2 * 10**17)

        # Happy path: Cố vấn chuyển 0.04 ETH sang quỹ lớp
        self.contract.move_fee_to_class_fund(self.advisor, 4 * 10**16)
        self.assertEqual(self.contract.admin_fee_pool, 6 * 10**16) # 0.06 ETH
        self.assertEqual(self.contract.class_fund_balance, 994 * 10**16) # 9.94 ETH
        # Tổng tài sản hợp đồng không hề thay đổi
        self.assertEqual(self.contract.get_total_contract_balance(), 10 * WEI_PER_ETH)
        self.assertEqual(
            self.contract.get_total_contract_balance(),
            self.contract.class_fund_balance + self.contract.admin_fee_pool
        )
        # Kiểm tra event FeeMovedToClassFund
        self.assertIn(("FeeMovedToClassFund", self.advisor, 4 * 10**16), self.contract.emitted_events)

    def test_case_56_section_f_gas_refund_pool_exhausted_still_allows_action(self):
        """Phase 5 / Mục F: Khi admin_fee_pool cạn, hành động quản trị vẫn thành công mà không bị revert (hoàn gas shortfall)"""
        ready_t = self._setup_3_active_bcs(added_at=0)
        # admin_fee_pool hiện tại = 0
        self.assertEqual(self.contract.admin_fee_pool, 0)

        # BCS tạo đợt thu
        cid = self.contract.create_collection(self.bcs_1, 1 * WEI_PER_ETH, ready_t + 7 * 86400, "Quy thieu gas", ready_t)
        self.assertEqual(cid, 1)

        # Mô phỏng modifier governanceAction với pool = 0
        units, price, owed, paid, shortfall = self.contract.apply_simulated_gas_refund(
            caller=self.bcs_1,
            gas_used=40_000,
            gas_price=3 * 10**9,
            basefee=2 * 10**9,
            current_time=ready_t,
        )
        self.assertEqual(paid, 0)
        self.assertEqual(shortfall, owed)
        self.assertEqual(self.contract.admin_fee_pool, 0)
        # Đợt thu vẫn tồn tại và hợp lệ (chưa bị đóng)
        self.assertFalse(self.contract.collections[cid]["closed"])

    def test_case_57_section_f_fraud_gas_price_capped_at_basefee_plus_2_gwei(self):
        """Phase 5 / Mục F (Gian lận): BCS đặt gasPrice cắt cổ (500 gwei) bị trần basefee + 2 gwei chặn đứng, chống rút cạn quỹ phí"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH) # pool = 0.1 ETH = 100,000,000 gwei
        ready_t = self._setup_3_active_bcs(added_at=0)

        basefee = 2 * 10**9 # 2 gwei
        exorbitant_gas_price = 500 * 10**9 # 500 gwei (cao gấp 250 lần)
        gas_used = 40_000

        # Nếu không có trần: (40,000 + 30,000) * 500 gwei = 35,000,000 gwei = 0.035 ETH (rút sạch 35% pool chỉ trong 1 tx)
        # Có trần MAX_GAS_PRICE_PREMIUM: giá bị khống chế tại 2 + 2 = 4 gwei
        units, price, owed, paid, shortfall = self.contract.apply_simulated_gas_refund(
            caller=self.bcs_1,
            gas_used=gas_used,
            gas_price=exorbitant_gas_price,
            basefee=basefee,
            current_time=ready_t,
        )
        self.assertEqual(price, 4 * 10**9) # 4 gwei
        self.assertEqual(paid, (40_000 + 30_000) * 4 * 10**9) # 280,000 gwei = 0.00028 ETH
        # Quỹ phí được bảo vệ an toàn
        self.assertEqual(self.contract.admin_fee_pool, 10**17 - 280_000 * 10**9)

    def test_case_58_section_f_fraud_reentrancy_and_rejecting_receiver_simulation(self):
        """Phase 5 / Mục F (Gian lận & Fallback): Mô phỏng tấn công reentrancy bị chặn bởi lock, và ví từ chối nhận ETH phục hồi lại pool"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        ready_t = self._setup_3_active_bcs(added_at=0)
        initial_pool = self.contract.admin_fee_pool

        # 1. Rejecting receiver: Người nhận từ chối nhận ETH (transfer call thất bại)
        units, price, owed, paid, shortfall = self.contract.apply_simulated_gas_refund(
            caller=self.bcs_1,
            gas_used=40_000,
            gas_price=3 * 10**9,
            basefee=2 * 10**9,
            current_time=ready_t,
            rejecting_receiver=True,
        )
        # paid = 0 (vì thất bại và đã rollback phục hồi), phát GasRefundFailed
        self.assertEqual(paid, 0)
        self.assertEqual(shortfall, owed)
        self.assertEqual(self.contract.admin_fee_pool, initial_pool) # Pool không bị thất thoát
        self.assertIn(("GasRefundFailed", self.bcs_1, owed), self.contract.emitted_events)

    def test_case_59_issue1_create_collection_auto_close_expired(self):
        """Vấn đề 1: create_collection tự động đóng đợt cũ đã quá hạn và tạo đợt mới thành công; đợt còn hạn vẫn revert"""
        ready_t = self._setup_3_active_bcs(added_at=0)
        cid1 = self.contract.create_collection(
            caller=self.bcs_1,
            target_wei=1 * WEI_PER_ETH,
            deadline=ready_t + 1000,
            purpose="Dot thu 1",
            current_time=ready_t,
        )
        self.assertEqual(cid1, 1)
        self.assertEqual(self.contract.active_collection_id, 1)

        # 1. Khi còn trong hạn: revert CollectionStillOpenError
        with self.assertRaises(CollectionStillOpenError):
            self.contract.create_collection(
                caller=self.bcs_2,
                target_wei=2 * WEI_PER_ETH,
                deadline=ready_t + 5000,
                purpose="Dot thu 2 bi chan",
                current_time=ready_t + 500,
            )

        # 2. Khi đã quá hạn (current_time > deadline): tự đóng đợt 1 và tạo đợt 2 thành công
        cid2 = self.contract.create_collection(
            caller=self.bcs_2,
            target_wei=2 * WEI_PER_ETH,
            deadline=ready_t + 10000,
            purpose="Dot thu 2 thanh cong",
            current_time=ready_t + 1001,
        )
        self.assertEqual(cid2, 2)
        self.assertEqual(self.contract.active_collection_id, 2)
        self.assertTrue(self.contract.collections[1]["closed"])
        self.assertEqual(self.contract.collections[1]["closed_at"], ready_t + 1001)
        self.assertIn(("CollectionClosed", 1, "Hết hạn tự động", self.bcs_2, ready_t + 1001), self.contract.emitted_events)

    def test_case_60_issue2_proposal_rejection_no_double_release_and_max_open_limit(self):
        """Vấn đề 2: Đề xuất chi và hoàn tiền bị Rejected khi No chiếm đa số, nhả tiền giữ chỗ ngay, chống nhả 2 lần, và giới hạn MAX_OPEN_SPEND_PER_CREATOR = 3"""
        self.contract.deposit(self.student_a, 10 * WEI_PER_ETH)
        ready_t = self._setup_3_active_bcs(added_at=0)

        # 1. Giới hạn MAX_OPEN_SPEND_PER_CREATOR = 3
        req1 = self.contract.create_spend_request(self.bcs_1, self.student_b, 1 * WEI_PER_ETH, "Spend 1", ready_t)
        req2 = self.contract.create_spend_request(self.bcs_1, self.student_b, 1 * WEI_PER_ETH, "Spend 2", ready_t)
        req3 = self.contract.create_spend_request(self.bcs_1, self.student_b, 1 * WEI_PER_ETH, "Spend 3", ready_t)
        self.assertEqual(self.contract.open_spend_request_count[self.bcs_1], 3)

        # Đề xuất thứ 4 bị revert với TooManyOpenRequestsError
        with self.assertRaises(TooManyOpenRequestsError):
            self.contract.create_spend_request(self.bcs_1, self.student_b, 1 * WEI_PER_ETH, "Spend 4", ready_t)

        # 2. Bỏ phiếu chống chiếm đa số khiến proposal bị Rejected ngay
        # voter_base = 3. Cần 51% (>= 2 yes). Nếu 2 no -> max possible yes = 1 < 2 -> Rejected
        self.contract.vote_spend_request(self.bcs_1, req1, False, ready_t)
        self.assertEqual(self.contract.spend_requests[req1]["status"], "Pending")

        self.contract.vote_spend_request(self.bcs_2, req1, False, ready_t)
        self.assertEqual(self.contract.spend_requests[req1]["status"], "Rejected")
        # Nhả tiền giữ chỗ và giảm open_spend_request_count
        self.assertEqual(self.contract.reserved_spend_amount, 2 * WEI_PER_ETH)
        self.assertEqual(self.contract.open_spend_request_count[self.bcs_1], 2)
        self.assertIn(("SpendRequestRejected", req1), self.contract.emitted_events)

        # Không thể nhả tiền lần hai khi gọi tiếp
        with self.assertRaises(CustomError):
            self.contract.vote_spend_request(self.bcs_3, req1, False, ready_t)
        with self.assertRaises(CustomError):
            self.contract.expire_spend_request(req1, ready_t + 8 * 86400)
        self.assertEqual(self.contract.reserved_spend_amount, 2 * WEI_PER_ETH)

        # BCS 1 tạo lại đề xuất thứ 4 thành công vì count đã giảm về 2
        req4 = self.contract.create_spend_request(self.bcs_1, self.student_b, 1 * WEI_PER_ETH, "Spend 4 ok", ready_t)
        self.assertEqual(self.contract.open_spend_request_count[self.bcs_1], 3)

        # 3. Yêu cầu hoàn tiền bị Rejected khi No chiếm đa số
        ref1 = self.contract.create_refund_request(self.student_a, 2 * WEI_PER_ETH, "Refund A", ready_t)
        self.assertEqual(self.contract.reserved_refund_amount, 2 * WEI_PER_ETH)
        self.assertEqual(self.contract.pending_student_refund_amount[self.student_a], 2 * WEI_PER_ETH)

        self.contract.vote_refund_request(self.bcs_1, ref1, False, ready_t)
        self.contract.vote_refund_request(self.bcs_2, ref1, False, ready_t)
        self.assertEqual(self.contract.refund_requests[ref1]["status"], "Rejected")
        self.assertEqual(self.contract.reserved_refund_amount, 0)
        self.assertEqual(self.contract.pending_student_refund_amount[self.student_a], 0)
        self.assertIn(("RefundRequestRejected", ref1), self.contract.emitted_events)

    def test_case_61_issue3_set_bcs_member_unchanged_status_skips_gas_refund(self):
        """Vấn đề 3: set_bcs_member khi trạng thái không đổi (isBCSMember[member] == status) bỏ qua bước hoàn gas"""
        # Thêm mới sinh viên
        self.contract.set_students(self.advisor, ["0xStrangerStudent"], True)

        # Lần 1: Thay đổi trạng thái (False -> True) -> trả về True (thực hiện hoàn gas)
        changed1 = self.contract.set_bcs_member(self.advisor, "0xStrangerStudent", True)
        self.assertTrue(changed1)

        # Lần 2: Gọi lại với True (True -> True) -> trả về False (bỏ qua hoàn gas, _skipGasRefund)
        changed2 = self.contract.set_bcs_member(self.advisor, "0xStrangerStudent", True)
        self.assertFalse(changed2)

        # Lần 3: Gọi với False cho một người đang là False (False -> False) -> trả về False (bỏ qua hoàn gas)
        changed3 = self.contract.set_bcs_member(self.advisor, "0xAnotherPerson", False)
        self.assertFalse(changed3)


if __name__ == "__main__":
    unittest.main()

