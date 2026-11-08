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

    function depositToCollection(ProjectCore core, uint256 id, uint256 amount) external payable {
        core.depositToCollection{value: amount}(id);
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

    function createCollection(
        ProjectCore core,
        uint256 targetWei,
        uint64 deadline,
        string memory purpose
    ) external returns (uint256) {
        return core.createCollection(targetWei, deadline, purpose);
    }

    function closeCollection(
        ProjectCore core,
        uint256 id,
        string memory reason
    ) external {
        core.closeCollection(id, reason);
    }

    function depositToCore(ProjectCore core) external payable {
        core.deposit{value: msg.value}();
    }

    function createRefund(ProjectCore core, uint256 amount, string memory reason) external returns (uint256) {
        return core.createRefundRequest(amount, reason);
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

    function fund() external payable {}

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

    function fund() external payable {}

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
    uint256 public gasMoveFeeToClassFund;

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

        address[] memory studs = new address[](5);
        studs[0] = address(student1);
        studs[1] = address(student2);
        studs[2] = address(bcs1);
        studs[3] = address(bcs2);
        studs[4] = address(bcs3);
        core.setStudents(studs, true);
    }

    // =========================================================================
    // PHẦN 1: CHU TRÌNH DÒNG TIỀN KHÉP KÍN 5 BƯỚC
    // @dev Ghi chú EVM thời gian: Các ca yêu cầu tạo đề xuất/hoàn tiền dưới đây giả định
    //      block.timestamp đã tăng >= 3 ngày sau setBCSMember(..., true) (kiểm chứng tự động
    //      bằng time.increase trong test/hardhat/ProjectCore.baseline.test.js & phase1 & phase2).
    // =========================================================================

    /// @notice Kiểm tra liên hoàn 5 bước dòng tiền có kiểm soát biểu quyết BCS (voterBase = 3)
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
        require(core.studentContributions(address(student1)) == 9.9 ether, "Step 1: Student1 net contribution must be 9.9 ETH");
        require(core.studentContributions(address(student2)) == 4.95 ether, "Step 1: Student2 net contribution must be 4.95 ETH");
        require(core.studentTotalDeposited(address(student1)) == 10 ether, "Step 1: Student1 total deposited must be 10 ETH");
        require(core.studentTotalDeposited(address(student2)) == 5 ether, "Step 1: Student2 total deposited must be 5 ETH");
        require(address(core).balance == 15 ether, "Step 1: Total contract balance must be 15 ETH");
        require(core.getTotalContractBalance() == core.classFundBalance() + core.adminFeePool(), "Step 1: Invariant holds");

        // -------------------------------------------------------------
        // BƯỚC 2: BIỂU QUYẾT CHI TIÊU (VOTE SPEND)
        // BCS1 tạo đề xuất chi 4 ETH cho Recipient1
        // -------------------------------------------------------------
        uint256 reqId = bcs1.createSpendRequest(core, payable(address(recipient1)), 4 ether, "Chi hoat dong ngoai khoa");
        require(reqId == 1, "Step 2: Request ID must be 1");
        (, , , , , , , , , uint256 spendVb) = core.spendRequests(reqId);
        require(spendVb == 3, "Step 2: Spend voterBase snapshot must be 3");
        require(core.reservedSpendAmount() == 4 ether, "Step 2: Reserved spend amount must be 4 ETH");
        require(core.getAvailableClassFund() == 10.85 ether, "Step 2: Available fund must be 10.85 ETH");

        // BCS1 bỏ phiếu thuận (1/3 = 33.3% < 51% -> Pending)
        bcs1.voteSpend(core, reqId, true);
        (, , , , , , , , ProjectCore.RequestStatus sPending) = core.getSpendRequest(reqId);
        require(sPending == ProjectCore.RequestStatus.Pending, "Step 2: Status must still be Pending");

        // BCS2 bỏ phiếu thuận (2/3 = 66.6% >= 51% -> TỰ ĐỘNG THỰC THI CHI TIỀN NGAY TRONG GIAO DỊCH VOTE!)
        uint256 recipientBalBefore = address(recipient1).balance;
        bcs2.voteSpend(core, reqId, true);
        uint256 recipientBalAfter = address(recipient1).balance;

        (, , , , , , uint256 yes2, , ProjectCore.RequestStatus sExecuted) = core.getSpendRequest(reqId);
        require(yes2 == 2, "Step 2: Yes votes must be 2");
        require(sExecuted == ProjectCore.RequestStatus.Executed, "Step 2: Status must transition directly to Executed via auto-execution");
        require(recipientBalAfter - recipientBalBefore == 4 ether, "Step 2: Recipient must receive exact 4 ETH from decisive vote tx");
        require(core.reservedSpendAmount() == 0, "Step 2: Reserved spend amount must reset to 0 upon auto-execution");
        require(core.classFundBalance() == 10.85 ether, "Step 2: Class fund must decrease by 4 ETH to 10.85 ETH");
        require(address(core).balance == 11 ether, "Step 2: Contract balance must decrease to 11 ETH");
        require(core.getTotalContractBalance() == core.classFundBalance() + core.adminFeePool(), "Step 2: Invariant holds");

        // -------------------------------------------------------------
        // BƯỚC 3: XÁC MINH CHỐNG THỰC THI THỦ CÔNG LẶP LẠI (EXECUTE SPEND AFTER AUTO-EXEC)
        // BCS1 gọi executeSpend sau khi đã auto-execute -> Bắt buộc Revert RequestAlreadyExecuted
        // -------------------------------------------------------------
        (bool sExecAgain, bytes memory rExecAgain) = address(bcs1).call(
            abi.encodeWithSignature("executeSpend(address,uint256)", address(core), reqId)
        );
        require(!sExecAgain, "Step 3: Calling manual execute after auto-exec must revert");
        bytes4 aExecAgain;
        assembly { aExecAgain := mload(add(rExecAgain, 0x20)) }
        require(aExecAgain == bytes4(keccak256("RequestAlreadyExecuted(uint256)")), "Step 3: Must revert RequestAlreadyExecuted");

        // -------------------------------------------------------------
        // BƯỚC 4: HOÀN TIỀN CÓ BIỂU QUYẾT BCS VÀ TỰ ĐỘNG HOÀN TRẢ
        // 4.1. Student2 tạo yêu cầu hoàn 3 ETH do nộp thừa
        // -------------------------------------------------------------
        uint256 refundId = student2.createRefund(core, 3 ether, "Nop nham quy lop");
        require(refundId == 1, "Step 4.1: Refund ID must be 1");
        (, , , , , , , , uint256 refVb) = core.refundRequests(refundId);
        require(refVb == 3, "Step 4.1: Refund voterBase snapshot must be 3");
        require(core.reservedRefundAmount() == 3 ether, "Step 4.1: Reserved refund amount must be 3 ETH");
        require(core.pendingStudentRefundAmount(address(student2)) == 3 ether, "Step 4.1: Student2 pending refund must be 3 ETH");
        require(core.getAvailableClassFund() == 7.85 ether, "Step 4.1: Available fund must be 10.85 - 3 = 7.85 ETH");

        // 4.2. BCS1 bỏ phiếu thuận (1/3 = 33.3% < 51% -> Pending)
        bcs1.voteRefund(core, refundId, true);
        (, , , , , , , ProjectCore.RequestStatus refPending) = core.getRefundRequest(refundId);
        require(refPending == ProjectCore.RequestStatus.Pending, "Step 4.2: Refund request must still be Pending with 1 vote");

        // 4.3. BCS2 bỏ phiếu thuận (2/3 = 66.6% >= 51% -> TỰ ĐỘNG HOÀN TIỀN NGAY VỀ VÍ SINH VIÊN!)
        uint256 student2BalBefore = address(student2).balance;
        bcs2.voteRefund(core, refundId, true);
        uint256 student2BalAfter = address(student2).balance;

        (, , , , , uint256 refYes, , ProjectCore.RequestStatus refExecuted) = core.getRefundRequest(refundId);
        require(refYes == 2, "Step 4.3: Refund yes votes must be 2");
        require(refExecuted == ProjectCore.RequestStatus.Executed, "Step 4.3: Refund request must transition directly to Executed via auto-execution");
        require(student2BalAfter - student2BalBefore == 3 ether, "Step 4.3: Student2 must receive exact 3 ETH refund from decisive vote tx");
        require(core.studentContributions(address(student2)) == 1.95 ether, "Step 4.3: Student2 net contribution must decrease to 1.95 ETH");
        require(core.studentTotalDeposited(address(student2)) == 5 ether, "Step 4.3: Student2 total deposited must remain 5 ETH");
        require(core.pendingStudentRefundAmount(address(student2)) == 0, "Step 4.3: Student2 pending refund must clear to 0");
        require(core.reservedRefundAmount() == 0, "Step 4.3: Reserved refund amount must clear to 0");
        require(core.classFundBalance() == 7.85 ether, "Step 4.3: Class fund must decrease to 7.85 ETH");
        require(address(core).balance == 8 ether, "Step 4.3: Contract balance must decrease to 8 ETH");
        require(core.adminFeePool() == 0.15 ether, "Step 4.3: Admin fee pool must remain untouched at 0.15 ETH");
        require(core.getTotalContractBalance() == core.classFundBalance() + core.adminFeePool(), "Step 4.3: Invariant holds");

        // 4.4. Thử gọi executeRefund thủ công sau khi đã auto-execute -> Bắt buộc Revert RefundAlreadyExecuted
        (bool sRefAgain, bytes memory rRefAgain) = address(student2).call(
            abi.encodeWithSignature("executeRefund(address,uint256)", address(core), refundId)
        );
        require(!sRefAgain, "Step 4.4: Calling manual executeRefund after auto-exec must revert");
        bytes4 aRefAgain;
        assembly { aRefAgain := mload(add(rRefAgain, 0x20)) }
        require(aRefAgain == bytes4(keccak256("RefundAlreadyExecuted(uint256)")), "Step 4.4: Must revert RefundAlreadyExecuted");

        // -------------------------------------------------------------
        // BƯỚC 5: ĐIỀU CHUYỂN PHÍ VẬN HÀNH (MOVE ADMIN FEE TO CLASS FUND)
        // CVHT chuyển 0.1 ETH từ Quỹ dịch vụ vận hành (adminFeePool) sang Quỹ lớp
        // -------------------------------------------------------------
        core.moveFeeToClassFund(0.1 ether);

        require(core.adminFeePool() == 0.05 ether, "Step 5: Admin fee pool must decrease to 0.05 ETH");
        require(core.classFundBalance() == 7.95 ether, "Step 5: Class fund must increase to 7.95 ETH");
        require(address(core).balance == 8.0 ether, "Step 5: Contract balance must remain 8.0 ETH");
        require(core.getTotalContractBalance() == core.classFundBalance() + core.adminFeePool(), "Step 5: Final invariant holds 100%");
    }

    // =========================================================================
    // PHẦN 2: NHÓM A — KIỂM THỬ BIÊN VÀ GIAN LẬN KHI TẠO YÊU CẦU HOÀN TIỀN
    // =========================================================================

    /// @notice Ca A1: Tạo yêu cầu hoàn tiền bằng 0 -> Revert ZeroAmount()
    function testRefund_ZeroAmountReverts() public payable {
        student1.deposit(core, 1 ether);
        (bool success, bytes memory returnData) = address(student1).call(
            abi.encodeWithSignature("createRefund(address,uint256,string)", address(core), 0, "Zero refund")
        );
        require(!success, "Refund 0 must revert");
        bytes4 sel;
        assembly { sel := mload(add(returnData, 0x20)) }
        require(sel == bytes4(keccak256("ZeroAmount()")), "Must revert ZeroAmount()");
    }

    /// @notice Ca A2: Yêu cầu hoàn tiền vượt quá số tiền đã đóng góp -> Revert InsufficientContribution
    function testRefund_ExceedingContributionReverts() public payable {
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);
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
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);
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
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        // Quỹ lớp có 4.95 ETH (sau 1% phí). Student1 xin hoàn 4.95 ETH
        uint256 refId = student1.createRefund(core, 4.95 ether, "Exact max");

        uint256 balBefore = address(student1).balance;
        bcs1.voteRefund(core, refId, true);
        bcs2.voteRefund(core, refId, true);
        uint256 balAfter = address(student1).balance;

        require(balAfter - balBefore == 4.95 ether, "Must receive exact 4.95 ETH directly from auto-exec vote");
        require(core.studentContributions(address(student1)) == 0, "Remaining net contribution must be 0");
        require(core.studentTotalDeposited(address(student1)) == 5 ether, "Total deposited must remain 5 ETH");
        require(core.getStudentMaxRefund(address(student1)) == 0, "Max refund must be 0");
        require(core.classFundBalance() == 0, "Class fund balance must be 0");
    }

    /// @notice Ca A5: Chặn tạo nhiều yêu cầu hoàn tiền đồng thời vượt tổng hạn mức đóng góp
    function testRefund_DoublePendingExceedingTotalReverts() public payable {
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);
        student1.deposit(core, 4 ether);

        // Yêu cầu 1: 2.5 ETH -> Thành công (hạn mức net 3.96 ETH, giữ chỗ 2.5 ETH, hạn mức khả dụng còn 1.46 ETH)
        uint256 refId1 = student1.createRefund(core, 2.5 ether, "Req 1");
        require(refId1 == 1, "First refund request created");
        require(core.getStudentAvailableContribution(address(student1)) == 1.46 ether, "Available contrib must be 1.46 ETH");

        // Yêu cầu 2: Cố tạo thêm yêu cầu 2 ETH (> 1.46 ETH còn lại) -> Bắt buộc phải Revert InsufficientContribution
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
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

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
        rejecter.fund{value: 5 ether}();

        address[] memory studs = new address[](1);
        studs[0] = address(rejecter);
        core.setStudents(studs, true);

        rejecter.deposit(3 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        uint256 refId = rejecter.requestRefund(1 ether, "Rollback test");
        bcs1.voteRefund(core, refId, true);
        bcs2.voteRefund(core, refId, true);

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
        attacker.fund{value: 10 ether}();

        address[] memory studs = new address[](1);
        studs[0] = address(attacker);
        core.setStudents(studs, true);

        attacker.deposit(4 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        uint256 attackRefId = attacker.applyRefund(2 ether);
        // 2/3 phiếu thuận -> auto-execute chuyển ETH tới attacker,
        // kích hoạt receive() cố re-enter executeRefundRequest() và bị chặn ngay lập tức bởi CEI
        bcs1.voteRefund(core, attackRefId, true);
        bcs2.voteRefund(core, attackRefId, true);

        require(attacker.attackAttempts() == 1, "Attacker must have attempted reentrancy");
        require(attacker.reentrancyBlocked(), "Reentrant call must be blocked");
        require(
            attacker.reentrancyRevertSelector() == bytes4(keccak256("RefundAlreadyExecuted(uint256)")),
            "Reentrancy must revert RefundAlreadyExecuted"
        );
        require(core.classFundBalance() == 1.96 ether, "Class fund must decrease exactly once to 1.96 ETH");
        require(core.studentContributions(address(attacker)) == 1.96 ether, "Student net contribution must decrease exactly once to 1.96 ETH");
        require(core.studentTotalDeposited(address(attacker)) == 4 ether, "Student total deposited must remain 4 ETH");
        require(address(attacker).balance == 8 ether, "Attacker balance must be exactly 10 - 4 + 2 = 8 ETH");
    }

    // =========================================================================
    // PHẦN 3: NHÓM B & C — KIỂM THỬ BIÊN VỀ BIỂU QUYẾT & THỰC THI HOÀN TIỀN
    // =========================================================================

    /// @notice Ca B1: Người không thuộc BCS không thể bỏ phiếu cho yêu cầu hoàn tiền
    function testRefundVoting_NonBCSCannotVote() public payable {
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);
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
        core.setBCSMember(address(bcs3), true);

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

    /// @notice Ca C2: Chặn thực thi hoàn tiền hai lần (Double Execution sau auto-exec)
    function testRefundExecution_CannotExecuteTwice() public payable {
        student1.deposit(core, 5 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        uint256 refId = student1.createRefund(core, 2 ether, "Reason");
        bcs1.voteRefund(core, refId, true);
        bcs2.voteRefund(core, refId, true); // 2/3 -> Đã auto-execute hoàn tiền thành công

        // Cố thực thi thủ công lần 1 (sau auto-exec) -> Revert RefundAlreadyExecuted
        (bool success, bytes memory returnData) = address(student1).call(
            abi.encodeWithSignature("executeRefund(address,uint256)", address(core), refId)
        );
        require(!success, "Cannot execute refund after auto-exec");
        bytes4 sel;
        assembly { sel := mload(add(returnData, 0x20)) }
        require(sel == bytes4(keccak256("RefundAlreadyExecuted(uint256)")), "Must revert RefundAlreadyExecuted");
    }

    /// @notice Ca C3: Chặn chi tiêu khi chưa đạt ngưỡng 51%
    function testSpend_CannotExecuteWithoutThreshold() public payable {
        student1.deposit(core, 10 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        uint256 reqId = bcs1.createSpendRequest(core, payable(address(recipient1)), 3 ether, "Chua du phieu");
        // 0/3 phiếu
        (bool success, ) = address(bcs1).call(
            abi.encodeWithSignature("execute(address,uint256)", address(core), reqId)
        );
        require(!success, "Execute spend without threshold must revert");
    }

    /// @notice Ca C4: Chặn thực thi chi tiêu hai lần (sau auto-exec)
    function testSpend_CannotExecuteTwice() public payable {
        student1.deposit(core, 10 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        uint256 reqId = bcs1.createSpendRequest(core, payable(address(recipient1)), 2 ether, "Chi mot lan");
        bcs1.voteSpend(core, reqId, true);
        bcs2.voteSpend(core, reqId, true); // 2/3 -> Đã auto-execute giải ngân thành công

        // Thử thực thi thủ công lần 1 (sau auto-exec) -> Revert RequestAlreadyExecuted
        (bool success, bytes memory returnData) = address(bcs1).call(
            abi.encodeWithSignature("executeSpend(address,uint256)", address(core), reqId)
        );
        require(!success, "Spend cannot be executed after auto-exec");
        bytes4 sel;
        assembly { sel := mload(add(returnData, 0x20)) }
        require(sel == bytes4(keccak256("RequestAlreadyExecuted(uint256)")), "Must revert RequestAlreadyExecuted");
    }

    /// @notice Ca C5: Chặn bỏ phiếu kép cho đề xuất chi tiêu
    function testVoting_DoubleVotingReverts() public payable {
        student1.deposit(core, 10 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        uint256 reqId = bcs1.createSpendRequest(core, payable(address(recipient1)), 1 ether, "Test double vote");
        bcs1.voteSpend(core, reqId, true); // 1/3 Pending

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

    /// @notice Ca D1: Nạp nhiều lần từ cùng 1 tài khoản tích lũy chính xác (net 99% và tổng nộp gốc 100%)
    function testDeposit_MultipleDepositsFromSameAccountAccumulate() public payable {
        student1.deposit(core, 2 ether);
        require(core.studentContributions(address(student1)) == 1.98 ether, "1st deposit net: 1.98 ETH");
        require(core.studentTotalDeposited(address(student1)) == 2 ether, "1st deposit gross: 2 ETH");

        student1.deposit(core, 3 ether);
        require(core.studentContributions(address(student1)) == 4.95 ether, "2nd deposit net: 4.95 ETH");
        require(core.studentTotalDeposited(address(student1)) == 5 ether, "2nd deposit gross: 5 ETH");

        student1.deposit(core, 1.5 ether);
        require(core.studentContributions(address(student1)) == 6.435 ether, "3rd deposit net: 6.435 ETH");
        require(core.studentTotalDeposited(address(student1)) == 6.5 ether, "3rd deposit gross: 6.5 ETH");
    }

    /// @notice Ca D1b (Phase 1 / Nhóm A Fraud): Hai sinh viên cùng nộp 10 ETH, Student1 cố hoàn 10 ETH để rút 0.1 ETH từ phần Student2 bị chặn
    function testRefund_SectionA_CrossStudentPoolDrainBlocked() public payable {
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);
        student1.deposit(core, 10 ether);
        student2.deposit(core, 10 ether);

        require(core.classFundBalance() == 19.8 ether, "Class fund holds 19.8 ETH net");
        require(core.getStudentMaxRefund(address(student1)) == 9.9 ether, "Student1 max refund is 9.9 ETH");

        (bool sFraud, bytes memory rFraud) = address(student1).call(
            abi.encodeWithSignature("createRefund(address,uint256,string)", address(core), 10 ether, "Drain 10 ETH gross")
        );
        require(!sFraud, "Student1 must not be allowed to request 10 ETH gross refund");
        bytes4 selFraud;
        assembly { selFraud := mload(add(rFraud, 0x20)) }
        require(selFraud == bytes4(keccak256("InsufficientContribution(uint256,uint256)")), "Must revert InsufficientContribution");
    }

    /// @notice Ca D2: Bất biến tổng tài sản không thất thoát wei sau chuỗi thao tác phức tạp
    function testAccounting_NoWeiLossAcrossAllOperations() public payable {
        student1.deposit(core, 10 ether);
        student2.deposit(core, 10 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        // Tạo và chi 5 ETH (2/3 auto-execution)
        uint256 reqId = bcs1.createSpendRequest(core, payable(address(recipient1)), 5 ether, "Chi tieu");
        bcs1.voteSpend(core, reqId, true);
        bcs2.voteSpend(core, reqId, true);

        // Tạo và hoàn tiền 3 ETH (2/3 auto-execution)
        uint256 refId = student1.createRefund(core, 3 ether, "Hoan tien");
        bcs1.voteRefund(core, refId, true);
        bcs2.voteRefund(core, refId, true);

        // Chuyển 0.1 ETH phí sang Quỹ lớp
        core.moveFeeToClassFund(0.1 ether);

        // Kiểm tra bất biến số dư
        uint256 expectedContract = address(core).balance;
        uint256 actualSum = core.classFundBalance() + core.adminFeePool();
        require(expectedContract == actualSum, "Balance invariant must hold with zero wei lost");
    }

    // =========================================================================
    // PHẦN 5: NHÓM B & C (PHASE 2) — ĐỘ TRỄ, SNAPSHOT VOTERBASE & XUNG ĐỘT LỢI ÍCH
    // =========================================================================

    /// @notice Ca P2-1 (chạy đơn TX trên Remix): Độ trễ 3 ngày & chặn hoàn tiền khi chưa đủ 3 BCS
    function testPhase2_ActivationDelayAndUnderMinBCSReverts() public payable {
        student1.deposit(core, 5 ether);
        uint256 tAdd = block.timestamp;
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        require(core.memberSince(address(bcs1)) == tAdd + 3 seconds, "memberSince set to +3 seconds");
        require(core.eligibleBCSCount(tAdd) == 0, "Eligible BCS at tAdd must be 0");
        require(core.eligibleBCSCount(tAdd + 3 seconds) == 2, "Eligible BCS at +3 seconds must be 2");

        // Chưa đủ 3 BCS -> student1 xin hoàn tiền bị chặn NotEnoughBCS(0, 3)
        (bool sRef, bytes memory rRef) = address(student1).call(
            abi.encodeWithSignature("createRefund(address,uint256,string)", address(core), 1 ether, "Thieu BCS")
        );
        require(!sRef, "createRefundRequest must revert under MIN_BCS_FOR_PROPOSAL");
        bytes4 aRef;
        assembly { aRef := mload(add(rRef, 0x20)) }
        require(aRef == bytes4(keccak256("NotEnoughBCS(uint256,uint256)")), "Must revert NotEnoughBCS");
    }

    /// @notice Ca P2-2: Snapshot voterBase cố định và chặn 3 ví ma thêm sau thời điểm tạo đề xuất
    function testPhase2_SnapshotVoterBaseAndPhantomBCSBlocked() public payable {
        student1.deposit(core, 10 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        uint256 reqId = bcs1.createSpendRequest(core, payable(address(recipient1)), 2 ether, "Snapshot integration");
        BCSActor phantom1 = new BCSActor();
        BCSActor phantom2 = new BCSActor();
        BCSActor phantom3 = new BCSActor();
        core.setBCSMember(address(phantom1), true);
        core.setBCSMember(address(phantom2), true);
        core.setBCSMember(address(phantom3), true);

        (, , , , , , , , , uint256 vb) = core.spendRequests(reqId);
        require(vb == 3, "voterBase must remain 3");

        (bool sPh, ) = address(phantom1).call(
            abi.encodeWithSignature("voteSpend(address,uint256,bool)", address(core), reqId, true)
        );
        require(!sPh, "Phantom BCS must be blocked");
    }

    /// @notice Ca P2-3: Xung đột lợi ích (BCS tự xin hoàn & recipient là BCS) với voterBase = eligible - 1 và yesVotes >= 2
    function testPhase2_ConflictOfInterestSpendAndRefundLifecycle() public payable {
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);
        (bool f1, ) = address(bcs1).call{value: 5 ether}("");
        require(f1, "Fund bcs1");

        bcs1.depositToCore{value: 5 ether}(core);
        uint256 refId = bcs1.createRefund(core, 2 ether, "BCS1 self refund");
        (, , , , , , , , uint256 refVb) = core.refundRequests(refId);
        require(refVb == 2, "Refund voterBase must be 2");

        (bool sSelfRef, bytes memory rSelfRef) = address(bcs1).call(
            abi.encodeWithSignature("voteRefund(address,uint256,bool)", address(core), refId, true)
        );
        require(!sSelfRef, "BCS1 self refund vote must revert ConflictOfInterest");
        bytes4 aSelfRef;
        assembly { aSelfRef := mload(add(rSelfRef, 0x20)) }
        require(aSelfRef == bytes4(keccak256("ConflictOfInterest()")), "Must revert ConflictOfInterest");

        bcs2.voteRefund(core, refId, true);
        bcs3.voteRefund(core, refId, true);
        (, , , , , uint256 refYes, , ProjectCore.RequestStatus refSt) = core.getRefundRequest(refId);
        require(refYes == 2 && refSt == ProjectCore.RequestStatus.Executed, "2/2 remaining votes execute refund");

        uint256 spendId = bcs1.createSpendRequest(core, payable(address(bcs3)), 1 ether, "Spend to bcs3");
        (, , , , , , , , , uint256 spendVb) = core.spendRequests(spendId);
        require(spendVb == 2, "Spend voterBase must be 2 for BCS recipient");

        (bool sSelfSpend, bytes memory rSelfSpend) = address(bcs3).call(
            abi.encodeWithSignature("voteSpend(address,uint256,bool)", address(core), spendId, true)
        );
        require(!sSelfSpend, "bcs3 recipient vote must revert ConflictOfInterest");
        bytes4 aSelfSpend;
        assembly { aSelfSpend := mload(add(rSelfSpend, 0x20)) }
        require(aSelfSpend == bytes4(keccak256("ConflictOfInterest()")), "Must revert ConflictOfInterest");

        bcs1.voteSpend(core, spendId, true);
        bcs2.voteSpend(core, spendId, true);
        (, , , , , , uint256 spendYes, , ProjectCore.RequestStatus spendSt) = core.getSpendRequest(spendId);
        require(spendYes == 2 && spendSt == ProjectCore.RequestStatus.Executed, "2/2 non-conflicted votes execute spend");
    }

    // =========================================================================
    // PHẦN 6: ĐO LƯỜNG GAS TIÊU THỤ THỰC TẾ
    // =========================================================================

    /// @notice Đo lường Gas tiêu thụ thực tế qua opcode GAS (gasleft)
    function testGas_MeasureAllFunctions() public payable {
        // 1. Đo Gas hàm setBCSMember()
        uint256 g0 = gasleft();
        core.setBCSMember(address(bcs1), true);
        gasSetBCS = g0 - gasleft();
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        // 2. Đo Gas hàm deposit()
        uint256 g1 = gasleft();
        student1.deposit(core, 5 ether);
        gasDeposit = g1 - gasleft();

        // 3. Đo Gas hàm createSpendRequest()
        uint256 g2 = gasleft();
        uint256 reqId = bcs1.createSpendRequest(core, payable(address(recipient1)), 1 ether, "Do Gas de xuat");
        gasCreateSpendRequest = g2 - gasleft();

        // 4. Đo Gas hàm voteSpendRequest() có Auto-Execution (2/3 phiếu thuận)
        bcs1.voteSpend(core, reqId, true);
        uint256 g3 = gasleft();
        bcs2.voteSpend(core, reqId, true);
        gasVoteSpendRequest = g3 - gasleft();

        // 5. Đo Gas hàm createRefundRequest()
        uint256 g5 = gasleft();
        uint256 refId = student1.createRefund(core, 1 ether, "Do Gas tao refund");
        gasCreateRefundRequest = g5 - gasleft();

        // 6. Đo Gas hàm voteRefundRequest() có Auto-Execution (2/3 phiếu thuận)
        bcs1.voteRefund(core, refId, true);
        uint256 g6 = gasleft();
        bcs2.voteRefund(core, refId, true);
        gasVoteRefundRequest = g6 - gasleft();

        // 7. Đo Gas hàm moveFeeToClassFund()
        uint256 g8 = gasleft();
        core.moveFeeToClassFund(0.01 ether);
        gasMoveFeeToClassFund = g8 - gasleft();

        require(gasDeposit > 0 && gasCreateRefundRequest > 0 && gasVoteSpendRequest > 0, "Gas measurements must be valid");
    }

    // =========================================================================
    // PHẦN 6: PHASE 3 (MỤC D) — ON-CHAIN STUDENT LIST & ROSTER HASH COMMITMENT
    // =========================================================================

    /// @notice Kiểm tra whitelist sinh viên, commit roster hash và chặn người ngoài
    function testPhase3_StudentEnrollmentAndCommitRoster() public payable {
        // Cố vấn học tập (address(this)) không thể tự nạp tiền
        (bool okDeposit, ) = address(core).call(abi.encodeWithSignature("deposit()"));
        require(!okDeposit, "Advisor cannot deposit");

        bytes32 sampleHash = keccak256("CANONICAL_ROSTER_V1");
        core.commitRoster(sampleHash);
        require(core.rosterHash() == sampleHash, "Roster hash must match committed hash");
    }

    /// @notice Sinh viên bị xóa khỏi danh sách vẫn hoàn tiền thành công
    function testPhase3_RemovedStudentCanRefund() public payable {
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        student1.deposit(core, 5 ether);
        require(core.studentContributions(address(student1)) == 4.95 ether, "Net contribution 4.95 ETH");

        // Xóa student1 khỏi danh sách
        address[] memory toRemove = new address[](1);
        toRemove[0] = address(student1);
        core.setStudents(toRemove, false);
        require(!core.isStudent(address(student1)), "Student1 must be unenrolled");

        // student1 vẫn xin hoàn tiền được
        uint256 refId = student1.createRefund(core, 2 ether, "Hoan tien sau khi thoi hoc");
        uint256 balBefore = address(student1).balance;
        bcs1.voteRefund(core, refId, true);
        bcs2.voteRefund(core, refId, true);
        uint256 balAfter = address(student1).balance;

        require(balAfter - balBefore == 2 ether, "Must receive 2 ETH via auto-execution");
        require(core.studentContributions(address(student1)) == 2.95 ether, "Remaining net 2.95 ETH");
    }

    /// @notice Bất biến kế toán khi ép ETH và getUnaccountedBalance
    function testPhase3_ForcedETHAndUnaccountedBalance() public payable {
        student1.deposit(core, 10 ether);
        require(core.getUnaccountedBalance() == 0, "Initial unaccounted balance must be 0");
        require(core.classFundBalance() == 9.9 ether, "Class fund 9.9 ETH");
        require(core.adminFeePool() == 0.1 ether, "Admin fee 0.1 ETH");
        require(core.getTotalContractBalance() == 10 ether, "Total 10 ETH");
    }

    // =========================================================================
    // PHẦN 7: PHASE 4 (MỤC E) — ĐỢT THU NỘP QUỸ TRÊN CHUỖI VÀ NẠP THEO ĐỢT
    // =========================================================================

    /// @notice Chu trình tạo đợt thu, nạp tiền từng phần và đạt ngưỡng 'Đã nộp'
    function testPhase4_CollectionLifecycleAndDeposit() public payable {
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        uint64 deadline = uint64(block.timestamp + 7 days);
        uint256 cid = bcs1.createCollection(core, 1 ether, deadline, "Dot thu hoc ky 1");
        require(cid == 1, "CID must be 1");
        require(core.activeCollectionId() == 1, "activeCollectionId must be 1");

        // Sinh viên 1 nạp từng phần: 0.4 ETH
        student1.depositToCollection{value: 0.4 ether}(core, cid, 0.4 ether);
        require(!core.hasPaidInCollection(cid, address(student1)), "Not paid yet");

        // Sinh viên 1 nạp tiếp 0.6 ETH -> Đạt 1.0 ETH
        student1.depositToCollection{value: 0.6 ether}(core, cid, 0.6 ether);
        require(core.hasPaidInCollection(cid, address(student1)), "Must be paid");
        (, , , , , , , , , uint256 paidCount) = core.collections(cid);
        require(paidCount == 1, "paidCount must be 1");

        // Đóng đợt thu
        bcs1.closeCollection(core, cid, "Dong dot thu 1");
        require(core.activeCollectionId() == 0, "activeCollectionId must be 0 after close");
    }

    /// @notice Chỉ 1 đợt thu mở tại 1 thời điểm; cố tạo đợt 2 khi đợt 1 chưa đóng sẽ bị revert
    function testPhase4_OnlyOneOpenCollection() public {
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        uint64 deadline = uint64(block.timestamp + 7 days);
        bcs1.createCollection(core, 1 ether, deadline, "Dot 1");

        // Cố tạo đợt 2
        (bool ok, ) = address(bcs2).call(
            abi.encodeWithSignature(
                "createCollection(address,uint256,uint64,string)",
                address(core),
                2 ether,
                deadline + 1000,
                "Dot 2"
            )
        );
        require(!ok, "Creating second collection while first open must fail");
    }

    /// @notice Gian lận: Sinh viên đã nộp đợt 1 không tự động được tính đã nộp đợt 2
    function testPhase4_FraudCrossCollectionIsolation() public payable {
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        uint64 deadline1 = uint64(block.timestamp + 7 days);
        uint256 cid1 = bcs1.createCollection(core, 1 ether, deadline1, "Dot 1");

        student1.depositToCollection{value: 1 ether}(core, cid1, 1 ether);
        require(core.hasPaidInCollection(cid1, address(student1)), "Paid in dot 1");

        bcs1.closeCollection(core, cid1, "Ket thuc dot 1");

        uint64 deadline2 = uint64(block.timestamp + 14 days);
        uint256 cid2 = bcs2.createCollection(core, 1 ether, deadline2, "Dot 2");

        require(!core.hasPaidInCollection(cid2, address(student1)), "Must NOT be paid in dot 2");
        require(core.paidInCollection(cid2, address(student1)) == 0, "Paid in dot 2 must be 0");
    }
}
