// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../contracts/project/ProjectCore.sol";

/// @title StudentActor - Hợp đồng đại diện cho sinh viên tham gia nạp và tạo yêu cầu hoàn tiền
contract StudentActor {
    receive() external payable {}

    function deposit(ProjectCore core, uint256 amount) external payable {
        core.deposit{value: amount}();
    }

    function depositDirect(ProjectCore core, uint256 amount) external payable {
        (bool ok, ) = address(core).call{value: amount}("");
        require(ok, "Deposit direct failed");
    }

    function createRefund(ProjectCore core, uint256 amount, string memory reason) external returns (uint256) {
        return core.createRefundRequest(amount, reason);
    }

    function executeRefund(ProjectCore core, uint256 refundId) external {
        core.executeRefundRequest(refundId);
    }
}

/// @title BCSActor - Hợp đồng đại diện cho thành viên Ban cán sự (BCS)
contract BCSActor {
    receive() external payable {}

    function createSpendRequest(
        ProjectCore core,
        address payable recipient,
        uint256 amount,
        string memory description
    ) external returns (uint256) {
        return core.createSpendRequest(recipient, amount, description);
    }

    function voteSpend(ProjectCore core, uint256 requestId, bool support) external {
        core.voteSpendRequest(requestId, support);
    }

    function executeSpend(ProjectCore core, uint256 requestId) external {
        core.executeSpendRequest(requestId);
    }

    function voteRefund(ProjectCore core, uint256 refundId, bool support) external {
        core.voteRefundRequest(refundId, support);
    }

    function executeRefund(ProjectCore core, uint256 refundId) external {
        core.executeRefundRequest(refundId);
    }
}

/// @title RecipientActor - Hợp đồng đại diện cho người thụ hưởng nhận tiền giải ngân
contract RecipientActor {
    uint256 public totalReceived;

    receive() external payable {
        totalReceived += msg.value;
    }
}

/// @title RejectingStudent - Sinh viên từ chối nhận ETH để kiểm tra cơ chế rollback khi execute refund
contract RejectingStudent {
    ProjectCore public target;
    uint256 public pendingRefundId;

    constructor(address payable _target) {
        target = ProjectCore(_target);
    }

    function deposit(uint256 amount) external payable {
        target.deposit{value: amount}();
    }

    function requestRefund(uint256 amount, string memory reason) external returns (uint256) {
        pendingRefundId = target.createRefundRequest(amount, reason);
        return pendingRefundId;
    }

    function executeRefund(uint256 refundId) external {
        target.executeRefundRequest(refundId);
    }

    receive() external payable {
        revert("REJECT_REFUND_ETH");
    }
}

/// @title MaliciousRefundAttacker - Hợp đồng độc hại cố tái nhập (re-enter) vào hàm executeRefundRequest()
contract MaliciousRefundAttacker {
    ProjectCore public target;
    uint256 public attackAttempts;
    bool public reentrancyBlocked;
    bytes4 public reentrancyRevertSelector;
    uint256 public myRefundId;

    constructor(address payable _target) {
        target = ProjectCore(_target);
    }

    function deposit(uint256 amount) external payable {
        target.deposit{value: amount}();
    }

    function applyRefund(uint256 amount) external returns (uint256) {
        myRefundId = target.createRefundRequest(amount, "Attack");
        return myRefundId;
    }

    function executeRefund() external {
        target.executeRefundRequest(myRefundId);
    }

    receive() external payable {
        if (attackAttempts == 0) {
            attackAttempts++;
            // Cố tình gọi lại executeRefundRequest() trước khi cập nhật (nếu hợp đồng dính lỗi reentrancy)
            (bool success, bytes memory returnData) = address(target).call(
                abi.encodeWithSignature("executeRefundRequest(uint256)", myRefundId)
            );
            if (!success) {
                reentrancyBlocked = true;
                if (returnData.length >= 4) {
                    bytes4 sel;
                    assembly {
                        sel := mload(add(returnData, 0x20))
                    }
                    reentrancyRevertSelector = sel;
                }
            }
        }
    }
}

/// @title ProjectCoreIntegrationTest - Bộ kiểm thử tích hợp chu trình dòng tiền có biểu quyết BCS & đo Gas (Lab 14)
/// @notice Kiểm tra toàn bộ chu trình 5 bước: Nạp -> Biểu quyết chi -> Chi -> Yêu cầu hoàn tiền -> BCS biểu quyết -> Thực thi hoàn tiền -> Rút phí
contract ProjectCoreIntegrationTest {
    uint256 public initialBalance = 100 ether;

    ProjectCore public core;
    StudentActor public student1;
    StudentActor public student2;
    BCSActor public bcs1;
    BCSActor public bcs2;
    BCSActor public bcs3;
    RecipientActor public recipient1;

    // Biến lưu trữ số đo Gas
    uint256 public gasDeposit;
    uint256 public gasSetBCS;
    uint256 public gasCreateSpendRequest;
    uint256 public gasVoteSpendRequest;
    uint256 public gasExecuteSpendRequest;
    uint256 public gasCreateRefundRequest;
    uint256 public gasVoteRefundRequest;
    uint256 public gasExecuteRefundRequest;
    uint256 public gasWithdrawAdminFee;

    receive() external payable {}

    function beforeEach() public {
        core = new ProjectCore();

        student1 = new StudentActor();
        student2 = new StudentActor();
        bcs1 = new BCSActor();
        bcs2 = new BCSActor();
        bcs3 = new BCSActor();
        recipient1 = new RecipientActor();

        (bool s1, ) = address(student1).call{value: 20 ether}("");
        (bool s2, ) = address(student2).call{value: 20 ether}("");
        require(s1 && s2, "Funding student actors failed");
    }

    // =========================================================================
    // PHẦN 1: CHU TRÌNH DÒNG TIỀN KHÉP KÍN 5 BƯỚC
    // =========================================================================

    /// @notice Kiểm tra liên hoàn 5 bước dòng tiền có kiểm soát biểu quyết BCS
    function testIntegration_FullFiveStepLifecycle() public payable {
        // Cài đặt 3 thành viên Ban cán sự
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);
        require(core.activeBCSCount() == 3, "Setup: Active BCS count must be 3");

        // -------------------------------------------------------------
        // BƯỚC 1: NẠP TIỀN (DEPOSIT)
        // Student1 nộp 10 ETH, Student2 nộp 5 ETH -> Tổng nộp: 15 ETH
        // -------------------------------------------------------------
        student1.deposit(core, 10 ether);
        student2.deposit(core, 5 ether);

        require(core.classFundBalance() == 14.85 ether, "Step 1: Class fund balance must be 14.85 ETH (99%)");
        require(core.adminFeePool() == 0.15 ether, "Step 1: Admin fee pool must be 0.15 ETH (1%)");
        require(core.studentContributions(address(student1)) == 10 ether, "Step 1: Student1 contribution must be 10 ETH");
        require(core.studentContributions(address(student2)) == 5 ether, "Step 1: Student2 contribution must be 5 ETH");
        require(address(core).balance == 15 ether, "Step 1: Total contract balance must be 15 ETH");
        require(core.getTotalContractBalance() == core.classFundBalance() + core.adminFeePool(), "Step 1: Invariant holds");

        // -------------------------------------------------------------
        // BƯỚC 2: BIỂU QUYẾT CHI TIÊU (VOTE SPEND)
        // BCS1 tạo đề xuất chi 4 ETH cho Recipient1
        // -------------------------------------------------------------
        uint256 reqId = bcs1.createSpendRequest(core, payable(address(recipient1)), 4 ether, "Chi hoat dong ngoai khoa");
        require(reqId == 1, "Step 2: Request ID must be 1");
        require(core.reservedSpendAmount() == 4 ether, "Step 2: Reserved spend amount must be 4 ETH");
        require(core.getAvailableClassFund() == 10.85 ether, "Step 2: Available fund must be 10.85 ETH");

        // BCS1 bỏ phiếu thuận (1/3 = 33.3% < 51% -> Pending)
        bcs1.voteSpend(core, reqId, true);
        (, , , , , , , , ProjectCore.RequestStatus sPending) = core.getSpendRequest(reqId);
        require(sPending == ProjectCore.RequestStatus.Pending, "Step 2: Status must still be Pending");

        // BCS2 bỏ phiếu thuận (2/3 = 66.6% >= 51% -> Ready)
        bcs2.voteSpend(core, reqId, true);
        (, , , , , , uint256 yes2, , ProjectCore.RequestStatus sReady) = core.getSpendRequest(reqId);
        require(yes2 == 2, "Step 2: Yes votes must be 2");
        require(sReady == ProjectCore.RequestStatus.Ready, "Step 2: Status must transition to Ready");

        // -------------------------------------------------------------
        // BƯỚC 3: CHI TIỀN (EXECUTE SPEND)
        // BCS1 gọi thực thi giải ngân 4 ETH
        // -------------------------------------------------------------
        uint256 recipientBalBefore = address(recipient1).balance;
        bcs1.executeSpend(core, reqId);
        uint256 recipientBalAfter = address(recipient1).balance;

        require(recipientBalAfter - recipientBalBefore == 4 ether, "Step 3: Recipient must receive exact 4 ETH");
        (, , , , , , , , ProjectCore.RequestStatus sExecuted) = core.getSpendRequest(reqId);
        require(sExecuted == ProjectCore.RequestStatus.Executed, "Step 3: Status must be Executed");
        require(core.reservedSpendAmount() == 0, "Step 3: Reserved spend amount must reset to 0");
        require(core.classFundBalance() == 10.85 ether, "Step 3: Class fund must decrease by 4 ETH to 10.85 ETH");
        require(address(core).balance == 11 ether, "Step 3: Contract balance must decrease to 11 ETH");
        require(core.getTotalContractBalance() == core.classFundBalance() + core.adminFeePool(), "Step 3: Invariant holds");

        // -------------------------------------------------------------
        // BƯỚC 4: HOÀN TIỀN CÓ BIỂU QUYẾT BCS (REFUND R7 NÂNG CẤP)
        // 4.1. Student2 tạo yêu cầu hoàn 3 ETH do nộp thừa
        // -------------------------------------------------------------
        uint256 refundId = student2.createRefund(core, 3 ether, "Nop nham quy lop");
        require(refundId == 1, "Step 4.1: Refund ID must be 1");
        require(core.reservedRefundAmount() == 3 ether, "Step 4.1: Reserved refund amount must be 3 ETH");
        require(core.pendingStudentRefundAmount(address(student2)) == 3 ether, "Step 4.1: Student2 pending refund must be 3 ETH");
        require(core.getAvailableClassFund() == 7.85 ether, "Step 4.1: Available fund must be 10.85 - 3 = 7.85 ETH");

        // 4.2. BCS1 và BCS2 biểu quyết thông qua yêu cầu hoàn tiền (2/3 >= 51%)
        bcs1.voteRefund(core, refundId, true);
        (, , , , , , , ProjectCore.RequestStatus refPending) = core.getRefundRequest(refundId);
        require(refPending == ProjectCore.RequestStatus.Pending, "Step 4.2: Refund request must still be Pending with 1 vote");

        bcs2.voteRefund(core, refundId, true);
        (, , , , , uint256 refYes, , ProjectCore.RequestStatus refReady) = core.getRefundRequest(refundId);
        require(refYes == 2, "Step 4.2: Refund yes votes must be 2");
        require(refReady == ProjectCore.RequestStatus.Ready, "Step 4.2: Refund request must transition to Ready");

        // 4.3. Thực thi hoàn tiền (Chuyển 3 ETH về ví Student2)
        uint256 student2BalBefore = address(student2).balance;
        student2.executeRefund(core, refundId);
        uint256 student2BalAfter = address(student2).balance;

        require(student2BalAfter - student2BalBefore == 3 ether, "Step 4.3: Student2 must receive exact 3 ETH refund");
        require(core.studentContributions(address(student2)) == 2 ether, "Step 4.3: Student2 contribution must decrease to 2 ETH");
        require(core.pendingStudentRefundAmount(address(student2)) == 0, "Step 4.3: Student2 pending refund must clear to 0");
        require(core.reservedRefundAmount() == 0, "Step 4.3: Reserved refund amount must clear to 0");
        require(core.classFundBalance() == 7.85 ether, "Step 4.3: Class fund must decrease to 7.85 ETH");
        require(address(core).balance == 8 ether, "Step 4.3: Contract balance must decrease to 8 ETH");
        require(core.adminFeePool() == 0.15 ether, "Step 4.3: Admin fee pool must remain untouched at 0.15 ETH");
        require(core.getTotalContractBalance() == core.classFundBalance() + core.adminFeePool(), "Step 4.3: Invariant holds");

        // -------------------------------------------------------------
        // BƯỚC 5: RÚT TIỀN (WITHDRAW ADMIN FEE)
        // CVHT rút 0.1 ETH từ Quỹ dịch vụ vận hành (adminFeePool)
        // -------------------------------------------------------------
        uint256 advisorBalBefore = address(this).balance;
        core.withdrawAdminFee(0.1 ether);
        uint256 advisorBalAfter = address(this).balance;

        require(advisorBalAfter > advisorBalBefore, "Step 5: Advisor must receive withdrawn fee");
        require(core.adminFeePool() == 0.05 ether, "Step 5: Admin fee pool must decrease to 0.05 ETH");
        require(core.classFundBalance() == 7.85 ether, "Step 5: Class fund must remain intact at 7.85 ETH");
        require(address(core).balance == 7.9 ether, "Step 5: Contract balance must be 7.9 ETH");
        require(core.getTotalContractBalance() == core.classFundBalance() + core.adminFeePool(), "Step 5: Final invariant holds 100%");
    }

    // =========================================================================
    // PHẦN 2: NHÓM A — KIỂM THỬ BIÊN VÀ GIAN LẬN KHI TẠO YÊU CẦU HOÀN TIỀN
    // =========================================================================

    /// @notice Ca A1: Tạo yêu cầu hoàn tiền bằng 0 -> Revert ZeroAmount()
    function testRefund_ZeroAmountReverts() public payable {
        core.deposit{value: 1 ether}();
        (bool success, bytes memory returnData) = address(core).call(
            abi.encodeWithSignature("createRefundRequest(uint256,string)", 0, "Zero refund")
        );
        require(!success, "Refund 0 must revert");
        bytes4 sel;
        assembly { sel := mload(add(returnData, 0x20)) }
        require(sel == bytes4(keccak256("ZeroAmount()")), "Must revert ZeroAmount()");
    }

    /// @notice Ca A2: Yêu cầu hoàn tiền vượt quá số tiền đã đóng góp -> Revert InsufficientContribution
    function testRefund_ExceedingContributionReverts() public payable {
        student1.deposit(core, 2 ether);
        // Student1 nộp 2 ETH, cố tình tạo yêu cầu hoàn 2.5 ETH
        (bool success, bytes memory returnData) = address(student1).call(
            abi.encodeWithSignature("createRefund(address,uint256,string)", address(core), 2.5 ether, "Too much")
        );
        require(!success, "Refund exceeding contribution must revert");
        bytes4 sel;
        assembly { sel := mload(add(returnData, 0x20)) }
        require(sel == bytes4(keccak256("InsufficientContribution(uint256,uint256)")), "Must revert InsufficientContribution");
    }

    /// @notice Ca A3: Người chưa từng đóng góp cố tạo yêu cầu hoàn tiền -> Revert InsufficientContribution
    function testRefund_NonContributorCannotRefund() public payable {
        (bool success, bytes memory returnData) = address(core).call(
            abi.encodeWithSignature("createRefundRequest(uint256,string)", 1 ether, "Outsider request")
        );
        require(!success, "Non contributor cannot request refund");
        bytes4 sel;
        assembly { sel := mload(add(returnData, 0x20)) }
        require(sel == bytes4(keccak256("InsufficientContribution(uint256,uint256)")), "Must revert InsufficientContribution");
    }

    /// @notice Ca A4: Yêu cầu và hoàn tiền đúng bằng hạn mức đóng góp tối đa
    function testRefund_ExactMaximumBoundary() public payable {
        student1.deposit(core, 5 ether);
        core.setBCSMember(address(bcs1), true);

        // Quỹ lớp có 4.95 ETH (sau 1% phí). Student1 xin hoàn 4.95 ETH
        uint256 refId = student1.createRefund(core, 4.95 ether, "Exact max");
        bcs1.voteRefund(core, refId, true);

        uint256 balBefore = address(student1).balance;
        student1.executeRefund(core, refId);
        uint256 balAfter = address(student1).balance;

        require(balAfter - balBefore == 4.95 ether, "Must receive exact 4.95 ETH");
        require(core.studentContributions(address(student1)) == 0.05 ether, "Remaining contribution must be 0.05 ETH");
        require(core.classFundBalance() == 0, "Class fund balance must be 0");
    }

    /// @notice Ca A5: Chặn tạo nhiều yêu cầu hoàn tiền đồng thời vượt tổng hạn mức đóng góp
    function testRefund_DoublePendingExceedingTotalReverts() public payable {
        student1.deposit(core, 4 ether);

        // Yêu cầu 1: 2.5 ETH -> Thành công (giữ chỗ 2.5 ETH, hạn mức khả dụng còn 1.5 ETH)
        uint256 refId1 = student1.createRefund(core, 2.5 ether, "Req 1");
        require(refId1 == 1, "First refund request created");
        require(core.getStudentAvailableContribution(address(student1)) == 1.5 ether, "Available contrib must be 1.5 ETH");

        // Yêu cầu 2: Cố tạo thêm yêu cầu 2 ETH (> 1.5 ETH còn lại) -> Bắt buộc phải Revert InsufficientContribution
        (bool success, bytes memory returnData) = address(student1).call(
            abi.encodeWithSignature("createRefund(address,uint256,string)", address(core), 2 ether, "Req 2 too large")
        );
        require(!success, "Second pending refund exceeding available contribution must revert");
        bytes4 sel;
        assembly { sel := mload(add(returnData, 0x20)) }
        require(sel == bytes4(keccak256("InsufficientContribution(uint256,uint256)")), "Must revert InsufficientContribution");
    }

    /// @notice Ca A6: Chặn tạo yêu cầu hoàn tiền xâm lấn vào hạn mức đã giữ chỗ cho đề xuất chi
    function testRefund_ExceedingAvailableFundDueToReservedSpendReverts() public payable {
        student1.deposit(core, 10 ether);
        core.setBCSMember(address(bcs1), true);

        // BCS1 tạo đề xuất chi giữ chỗ 7 ETH -> Quỹ khả dụng còn 2.9 ETH
        bcs1.createSpendRequest(core, payable(address(recipient1)), 7 ether, "Giu cho chi lon");
        require(core.getAvailableClassFund() == 2.9 ether, "Available fund must be 2.9 ETH");

        // Student1 xin hoàn 5 ETH (> 2.9 ETH quỹ khả dụng) -> Bắt buộc Revert InsufficientAvailableFund
        (bool success, bytes memory returnData) = address(student1).call(
            abi.encodeWithSignature("createRefund(address,uint256,string)", address(core), 5 ether, "Exceed available")
        );
        require(!success, "Refund exceeding available fund must revert");
        bytes4 sel;
        assembly { sel := mload(add(returnData, 0x20)) }
        require(sel == bytes4(keccak256("InsufficientAvailableFund(uint256,uint256)")), "Must revert InsufficientAvailableFund");
    }

    /// @notice Ca A7: Người nhận từ chối ETH thì revert ETHTransferFailed() và rollback toàn bộ kế toán
    function testRefund_RejectingRecipientRollsBack() public payable {
        RejectingStudent rejecter = new RejectingStudent(payable(address(core)));
        (bool fundOk, ) = address(rejecter).call{value: 5 ether}("");
        require(fundOk, "Funding rejecter failed");

        rejecter.deposit(3 ether);
        core.setBCSMember(address(bcs1), true);

        uint256 refId = rejecter.requestRefund(1 ether, "Rollback test");
        bcs1.voteRefund(core, refId, true);

        uint256 fundBefore = core.classFundBalance();
        uint256 contribBefore = core.studentContributions(address(rejecter));

        // Khi execute, RejectingStudent từ chối nhận ETH trong receive()
        (bool success, ) = address(rejecter).call(
            abi.encodeWithSignature("executeRefund(uint256)", refId)
        );
        require(!success, "Execution must fail when recipient refuses ETH");

        // Xác nhận trạng thái không bị thay đổi (Rollback)
        require(core.classFundBalance() == fundBefore, "Class fund must not change after failed transfer");
        require(core.studentContributions(address(rejecter)) == contribBefore, "Contribution must not change after rollback");
    }

    /// @notice Ca A8: Chống Reentrancy khi thực thi hoàn tiền nhờ CEI
    function testRefund_ReentrancyBlockedByCEI() public payable {
        MaliciousRefundAttacker attacker = new MaliciousRefundAttacker(payable(address(core)));
        (bool fundOk, ) = address(attacker).call{value: 10 ether}("");
        require(fundOk, "Funding attacker failed");

        attacker.deposit(4 ether);
        core.setBCSMember(address(bcs1), true);

        uint256 attackRefId = attacker.applyRefund(2 ether);
        bcs1.voteRefund(core, attackRefId, true);

        // Attacker gọi executeRefund, trong receive() sẽ cố re-enter executeRefundRequest()
        attacker.executeRefund();

        require(attacker.attackAttempts() == 1, "Attacker must have attempted reentrancy");
        require(attacker.reentrancyBlocked(), "Reentrant call must be blocked");
        require(
            attacker.reentrancyRevertSelector() == bytes4(keccak256("RefundAlreadyExecuted(uint256)")),
            "Reentrancy must revert RefundAlreadyExecuted"
        );
    }

    // =========================================================================
    // PHẦN 3: NHÓM B & C — KIỂM THỬ BIÊN VỀ BIỂU QUYẾT & THỰC THI HOÀN TIỀN
    // =========================================================================

    /// @notice Ca B1: Người không thuộc BCS không thể bỏ phiếu cho yêu cầu hoàn tiền
    function testRefundVoting_NonBCSCannotVote() public payable {
        student1.deposit(core, 5 ether);
        uint256 refId = student1.createRefund(core, 2 ether, "Reason");

        // Outsider cố tình bỏ phiếu
        (bool success, bytes memory returnData) = address(core).call(
            abi.encodeWithSignature("voteRefundRequest(uint256,bool)", refId, true)
        );
        require(!success, "Non BCS cannot vote on refund");
        bytes4 sel;
        assembly { sel := mload(add(returnData, 0x20)) }
        require(sel == bytes4(keccak256("NotActiveBCS()")), "Must revert NotActiveBCS()");
    }

    /// @notice Ca B2: Thành viên BCS không thể bỏ phiếu hai lần cho cùng một yêu cầu hoàn tiền
    function testRefundVoting_CannotVoteTwice() public payable {
        student1.deposit(core, 5 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);

        uint256 refId = student1.createRefund(core, 2 ether, "Reason");
        bcs1.voteRefund(core, refId, true);

        // BCS1 cố bỏ phiếu lần thứ 2
        (bool success, bytes memory returnData) = address(bcs1).call(
            abi.encodeWithSignature("voteRefund(address,uint256,bool)", address(core), refId, true)
        );
        require(!success, "BCS cannot vote twice on refund");
        bytes4 sel;
        assembly { sel := mload(add(returnData, 0x20)) }
        require(sel == bytes4(keccak256("AlreadyVotedRefund(uint256,address)")), "Must revert AlreadyVotedRefund");
    }

    /// @notice Ca C1: Yêu cầu hoàn tiền chưa đạt 51% không thể thực thi
    function testRefundExecution_CannotExecuteWithoutThreshold() public payable {
        student1.deposit(core, 5 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        uint256 refId = student1.createRefund(core, 2 ether, "Reason");
        // Mới có 1/3 phiếu (33% < 51%)
        bcs1.voteRefund(core, refId, true);

        (bool success, bytes memory returnData) = address(student1).call(
            abi.encodeWithSignature("executeRefund(address,uint256)", address(core), refId)
        );
        require(!success, "Cannot execute refund without 51% threshold");
        bytes4 sel;
        assembly { sel := mload(add(returnData, 0x20)) }
        require(sel == bytes4(keccak256("ThresholdNotMet(uint256,uint256)")), "Must revert ThresholdNotMet");
    }

    /// @notice Ca C2: Chặn thực thi hoàn tiền hai lần (Double Execution)
    function testRefundExecution_CannotExecuteTwice() public payable {
        student1.deposit(core, 5 ether);
        core.setBCSMember(address(bcs1), true);

        uint256 refId = student1.createRefund(core, 2 ether, "Reason");
        bcs1.voteRefund(core, refId, true);
        student1.executeRefund(core, refId);

        // Cố thực thi lần 2
        (bool success, bytes memory returnData) = address(student1).call(
            abi.encodeWithSignature("executeRefund(address,uint256)", address(core), refId)
        );
        require(!success, "Cannot execute refund twice");
        bytes4 sel;
        assembly { sel := mload(add(returnData, 0x20)) }
        require(sel == bytes4(keccak256("RefundAlreadyExecuted(uint256)")), "Must revert RefundAlreadyExecuted");
    }

    /// @notice Ca C3: Chặn chi tiêu khi chưa đạt ngưỡng 51%
    function testSpend_CannotExecuteWithoutThreshold() public payable {
        student1.deposit(core, 10 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);

        uint256 reqId = bcs1.createSpendRequest(core, payable(address(recipient1)), 3 ether, "Chua du phieu");
        // 0/2 phiếu
        (bool success, ) = address(bcs1).call(
            abi.encodeWithSignature("execute(address,uint256)", address(core), reqId)
        );
        require(!success, "Execute spend without threshold must revert");
    }

    /// @notice Ca C4: Chặn thực thi chi tiêu hai lần
    function testSpend_CannotExecuteTwice() public payable {
        student1.deposit(core, 10 ether);
        core.setBCSMember(address(bcs1), true);

        uint256 reqId = bcs1.createSpendRequest(core, payable(address(recipient1)), 2 ether, "Chi mot lan");
        bcs1.voteSpend(core, reqId, true);
        bcs1.executeSpend(core, reqId);

        // Thử thực thi lần 2
        (bool success, bytes memory returnData) = address(bcs1).call(
            abi.encodeWithSignature("execute(address,uint256)", address(core), reqId)
        );
        require(!success, "Spend cannot be executed twice");
        bytes4 sel;
        assembly { sel := mload(add(returnData, 0x20)) }
        require(sel == bytes4(keccak256("RequestAlreadyExecuted(uint256)")), "Must revert RequestAlreadyExecuted");
    }

    /// @notice Ca C5: Chặn bỏ phiếu kép cho đề xuất chi tiêu
    function testVoting_DoubleVotingReverts() public payable {
        student1.deposit(core, 10 ether);
        core.setBCSMember(address(bcs1), true);

        uint256 reqId = bcs1.createSpendRequest(core, payable(address(recipient1)), 1 ether, "Test double vote");
        bcs1.voteSpend(core, reqId, true);

        (bool success, bytes memory returnData) = address(bcs1).call(
            abi.encodeWithSignature("voteSpend(address,uint256,bool)", address(core), reqId, true)
        );
        require(!success, "Double voting on spend must revert");
        bytes4 sel;
        assembly { sel := mload(add(returnData, 0x20)) }
        require(sel == bytes4(keccak256("AlreadyVoted(uint256,address)")), "Must revert AlreadyVoted");
    }

    // =========================================================================
    // PHẦN 4: NHÓM D — NẠP TIỀN & BẢO TOÀN KẾ TOÁN
    // =========================================================================

    /// @notice Ca D1: Nạp nhiều lần từ cùng 1 tài khoản tích lũy chính xác
    function testDeposit_MultipleDepositsFromSameAccountAccumulate() public payable {
        student1.deposit(core, 2 ether);
        require(core.studentContributions(address(student1)) == 2 ether, "1st deposit: 2 ETH");

        student1.deposit(core, 3 ether);
        require(core.studentContributions(address(student1)) == 5 ether, "2nd deposit: 5 ETH");

        student1.deposit(core, 1.5 ether);
        require(core.studentContributions(address(student1)) == 6.5 ether, "3rd deposit: 6.5 ETH");
    }

    /// @notice Ca D2: Bất biến tổng tài sản không thất thoát wei sau chuỗi thao tác phức tạp
    function testAccounting_NoWeiLossAcrossAllOperations() public payable {
        student1.deposit(core, 10 ether);
        student2.deposit(core, 10 ether);
        core.setBCSMember(address(bcs1), true);

        // Tạo và chi 5 ETH
        uint256 reqId = bcs1.createSpendRequest(core, payable(address(recipient1)), 5 ether, "Chi tieu");
        bcs1.voteSpend(core, reqId, true);
        bcs1.executeSpend(core, reqId);

        // Tạo và hoàn tiền 3 ETH
        uint256 refId = student1.createRefund(core, 3 ether, "Hoan tien");
        bcs1.voteRefund(core, refId, true);
        student1.executeRefund(core, refId);

        // Rút 0.1 ETH phí
        core.withdrawAdminFee(0.1 ether);

        // Kiểm tra bất biến số dư
        uint256 expectedContract = address(core).balance;
        uint256 actualSum = core.classFundBalance() + core.adminFeePool();
        require(expectedContract == actualSum, "Balance invariant must hold with zero wei lost");
    }

    // =========================================================================
    // PHẦN 5: ĐO LƯỜNG GAS TIÊU THỤ THỰC TẾ
    // =========================================================================

    /// @notice Đo lường Gas tiêu thụ thực tế qua opcode GAS (gasleft)
    function testGas_MeasureAllFunctions() public payable {
        // 1. Đo Gas hàm setBCSMember()
        uint256 g0 = gasleft();
        core.setBCSMember(address(bcs1), true);
        gasSetBCS = g0 - gasleft();

        // 2. Đo Gas hàm deposit()
        uint256 g1 = gasleft();
        core.deposit{value: 5 ether}();
        gasDeposit = g1 - gasleft();

        // 3. Đo Gas hàm createSpendRequest()
        uint256 g2 = gasleft();
        uint256 reqId = bcs1.createSpendRequest(core, payable(address(recipient1)), 1 ether, "Do Gas de xuat");
        gasCreateSpendRequest = g2 - gasleft();

        // 4. Đo Gas hàm voteSpendRequest()
        uint256 g3 = gasleft();
        bcs1.voteSpend(core, reqId, true);
        gasVoteSpendRequest = g3 - gasleft();

        // 5. Đo Gas hàm executeSpendRequest()
        uint256 g4 = gasleft();
        bcs1.executeSpend(core, reqId);
        gasExecuteSpendRequest = g4 - gasleft();

        // 6. Đo Gas hàm createRefundRequest()
        uint256 g5 = gasleft();
        uint256 refId = core.createRefundRequest(1 ether, "Do Gas tao refund");
        gasCreateRefundRequest = g5 - gasleft();

        // 7. Đo Gas hàm voteRefundRequest()
        uint256 g6 = gasleft();
        bcs1.voteRefund(core, refId, true);
        gasVoteRefundRequest = g6 - gasleft();

        // 8. Đo Gas hàm executeRefundRequest()
        uint256 g7 = gasleft();
        core.executeRefundRequest(refId);
        gasExecuteRefundRequest = g7 - gasleft();

        // 9. Đo Gas hàm withdrawAdminFee()
        uint256 g8 = gasleft();
        core.withdrawAdminFee(0.01 ether);
        gasWithdrawAdminFee = g8 - gasleft();

        require(gasDeposit > 0 && gasCreateRefundRequest > 0 && gasExecuteRefundRequest > 0, "Gas measurements must be valid");
    }
}
