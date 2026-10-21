// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../contracts/project/ProjectCore.sol";

/// @notice Hợp đồng đóng vai trò thành viên Ban cán sự (BCS) để kiểm thử phân quyền và biểu quyết
contract BCSActor {
    receive() external payable {}

    function createSpendRequest(
        ProjectCore target,
        address payable recipient,
        uint256 amount,
        string memory desc
    ) external returns (uint256) {
        return target.createSpendRequest(recipient, amount, desc);
    }

    function vote(ProjectCore target, uint256 requestId, bool support) external {
        target.voteSpendRequest(requestId, support);
    }

    function execute(ProjectCore target, uint256 requestId) external {
        target.executeSpendRequest(requestId);
    }
}

/// @notice Hợp đồng đóng vai trò người ngoài (Non-Advisor, Non-BCS) để kiểm thử xâm nhập trái phép
contract NonAdvisorActor {
    receive() external payable {}

    function trySetBCS(ProjectCore target, address member, bool status) external returns (bool success, bytes memory returnData) {
        (success, returnData) = address(target).call(
            abi.encodeWithSignature("setBCSMember(address,bool)", member, status)
        );
    }

    function tryWithdrawFee(ProjectCore target, uint256 amount) external returns (bool success, bytes memory returnData) {
        (success, returnData) = address(target).call(
            abi.encodeWithSignature("withdrawAdminFee(uint256)", amount)
        );
    }

    function tryCreateRequest(ProjectCore target, address payable recipient, uint256 amount, string memory desc) external returns (bool success, bytes memory returnData) {
        (success, returnData) = address(target).call(
            abi.encodeWithSignature("createSpendRequest(address,uint256,string)", recipient, amount, desc)
        );
    }

    function tryVote(ProjectCore target, uint256 requestId, bool support) external returns (bool success, bytes memory returnData) {
        (success, returnData) = address(target).call(
            abi.encodeWithSignature("voteSpendRequest(uint256,bool)", requestId, support)
        );
    }
}

/// @notice Hợp đồng thụ hưởng từ chối nhận ETH để kiểm tra khả năng xử lý rollback của low-level call
contract RejectingRecipient {
    // Không có receive() hay fallback(), mọi giao dịch chuyển ETH tới sẽ thất bại
}

/// @notice Hợp đồng Cố vấn học tập từ chối nhận ETH để kiểm tra rollback khi withdrawAdminFee thất bại
contract RejectingAdvisor {
    ProjectCore public target;

    constructor() {
        target = new ProjectCore();
    }

    function depositToCore() external payable {
        target.deposit{value: msg.value}();
    }

    function tryWithdrawFee(uint256 amount) external returns (bool success, bytes memory returnData) {
        (success, returnData) = address(target).call(
            abi.encodeWithSignature("withdrawAdminFee(uint256)", amount)
        );
    }

    // Từ chối nhận ETH (không có receive, hoặc revert trong receive)
    receive() external payable {
        revert("RejectingAdvisor: refused ETH");
    }
}

/// @notice Hợp đồng thụ hưởng độc hại ĐỒNG THỜI LÀ THÀNH VIÊN BAN CÁN SỰ
/// @dev Nhờ có quyền BCS, lần tái nhập vượt qua kiểm tra onlyActiveBCS và thực sự kiểm tra trạng thái Executed / CEI
contract MaliciousBCSRecipient {
    ProjectCore public target;
    uint256 public attackAttempts;
    bool public reentrancyBlocked;
    bytes4 public reentrancyRevertSelector;

    constructor(address payable _target) {
        target = ProjectCore(_target);
    }

    function vote(uint256 requestId, bool support) external {
        target.voteSpendRequest(requestId, support);
    }

    receive() external payable {
        if (attackAttempts == 0) {
            attackAttempts++;
            // Thử tái nhập (re-enter) gọi lại executeSpendRequest(1)
            // Vì contract này đã được CVHT cấp quyền BCS, lệnh gọi sẽ vượt qua onlyActiveBCS
            (bool success, bytes memory returnData) = address(target).call(
                abi.encodeWithSignature("executeSpendRequest(uint256)", 1)
            );
            // Đòn reentrancy phải thất bại VÌ TRẠNG THÁI ĐÃ LÀ EXECUTED (CEI)
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

/// @title ProjectCoreTest - Bộ kiểm thử tự động toàn diện cho ProjectCore (Lab 13)
/// @notice Kiểm tra đầy đủ 7 nhóm: R2 (Nạp), R1 (Quyền), R11 (Rút phí), R3 (Đề xuất), R4/R5 (Biểu quyết), R6 (Giải ngân & CEI), Nhóm G (Kế toán & Bất biến)
contract ProjectCoreTest {
    uint256 public initialBalance = 100 ether; // Cấp vốn cho test runner trên Remix VM
    ProjectCore core;
    BCSActor bcs1;
    BCSActor bcs2;
    BCSActor bcs3;
    NonAdvisorActor outsider;

    /// @notice Hỗ trợ nhận ETH cho test contract
    receive() external payable {}

    /// @notice Chuẩn bị môi trường độc lập trước mỗi ca kiểm thử
    function beforeEach() public {
        core = new ProjectCore();
        bcs1 = new BCSActor();
        bcs2 = new BCSActor();
        bcs3 = new BCSActor();
        outsider = new NonAdvisorActor();
    }

    // ==========================================
    // NHÓM A — R2: NẠP TIỀN & PHÂN BỔ 99% / 1%
    // ==========================================

    /// @notice Ca A1: Nạp 1 ETH -> 99% Quỹ lớp chính (0.99 ETH), 1% adminFeePool (0.01 ETH)
    function testGroupA1_Deposit1ETH_Split99_1() public payable {
        uint256 depositAmt = 1 ether;
        core.deposit{value: depositAmt}();

        require(core.classFundBalance() == 0.99 ether, "Class fund balance must be 0.99 ETH");
        require(core.adminFeePool() == 0.01 ether, "Admin fee pool must be 0.01 ETH");
        require(core.getFundBalance() == 0.99 ether, "getFundBalance() must match classFundBalance");
        require(core.studentContributions(address(this)) == depositAmt, "Student contributions must record full 1 ETH");
        require(core.getTotalContractBalance() == depositAmt, "Total contract balance must match 1 ETH");
    }

    /// @notice Ca A2: Nạp trực tiếp qua kênh receive() 0.5 ETH
    function testGroupA2_DirectReceive() public payable {
        uint256 depositAmt = 0.5 ether;
        (bool success, ) = address(core).call{value: depositAmt}("");
        require(success, "Direct transfer to receive() must succeed");

        require(core.classFundBalance() == 0.495 ether, "Class fund must receive 0.495 ETH");
        require(core.adminFeePool() == 0.005 ether, "Admin fee must receive 0.005 ETH");
    }

    /// @notice Ca A3: Nạp 0 ETH qua deposit() và receive() đều bị revert ZeroAmount()
    function testGroupA3_ZeroAmountReverts() public {
        bytes4 expectedSelector = bytes4(keccak256("ZeroAmount()"));

        (bool s1, bytes memory r1) = address(core).call{value: 0}(
            abi.encodeWithSignature("deposit()")
        );
        require(!s1, "deposit(0) must revert");
        require(r1.length >= 4, "Must return error data");
        bytes4 a1;
        assembly { a1 := mload(add(r1, 0x20)) }
        require(a1 == expectedSelector, "Revert reason must be ZeroAmount()");

        (bool s2, bytes memory r2) = address(core).call{value: 0}("");
        require(!s2, "receive(0) must revert");
        require(r2.length >= 4, "Must return error data");
        bytes4 a2;
        assembly { a2 := mload(add(r2, 0x20)) }
        require(a2 == expectedSelector, "Revert reason must be ZeroAmount()");
    }

    /// @notice Ca A4: Phép tính số nguyên và các giá trị biên (< 100 wei)
    function testGroupA4_IntegerMathEdgeCases() public payable {
        core.deposit{value: 99}();
        require(core.adminFeePool() == 0, "Fee for 99 wei must be 0");
        require(core.classFundBalance() == 99, "Fund must receive all 99 wei");

        core.deposit{value: 101}();
        require(core.adminFeePool() == 1, "Cumulative fee must be 1 wei");
        require(core.classFundBalance() == 99 + 100, "Cumulative fund must be 199 wei");
        require(core.classFundBalance() + core.adminFeePool() == 200, "Sum must equal 200 wei");
    }

    // ==========================================
    // NHÓM B — R1: PHÂN QUYỀN CVHT & QUẢN LÝ BCS
    // ==========================================

    /// @notice Ca B1: Cố vấn học tập thêm và xóa thành viên Ban cán sự thành công
    function testGroupB1_AdvisorAddAndRemoveBCS() public {
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        require(core.isBCSMember(address(bcs1)), "bcs1 must be active");
        require(core.isBCSMember(address(bcs2)), "bcs2 must be active");
        require(core.activeBCSCount() == 2, "activeBCSCount must be 2");

        // Vô hiệu hóa bcs1
        core.setBCSMember(address(bcs1), false);
        require(!core.isBCSMember(address(bcs1)), "bcs1 must be deactivated");
        require(core.activeBCSCount() == 1, "activeBCSCount must be 1");
    }

    /// @notice Ca B2: Người ngoài không thể thay đổi danh sách Ban cán sự
    function testGroupB2_NonAdvisorCannotSetBCS() public {
        (bool success, bytes memory returnData) = outsider.trySetBCS(core, address(bcs1), true);
        require(!success, "Outsider setBCSMember must revert");
        require(returnData.length >= 4, "Must return error data");
        bytes4 actual;
        assembly { actual := mload(add(returnData, 0x20)) }
        require(actual == bytes4(keccak256("NotAdvisor()")), "Must revert NotAdvisor()");
    }

    /// @notice Ca B3: Thêm địa chỉ zero bị từ chối
    function testGroupB3_ZeroAddressBCSReverts() public {
        (bool success, bytes memory returnData) = address(core).call(
            abi.encodeWithSignature("setBCSMember(address,bool)", address(0), true)
        );
        require(!success, "Adding address(0) must revert");
        require(returnData.length >= 4, "Must return error data");
        bytes4 actual;
        assembly { actual := mload(add(returnData, 0x20)) }
        require(actual == bytes4(keccak256("InvalidAddress()")), "Must revert InvalidAddress()");
    }

    /// @notice Ca B4: BCS đã bị vô hiệu hóa không thể tạo đề xuất chi
    function testGroupB4_DisabledBCSCannotAct() public payable {
        core.deposit{value: 2 ether}();
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs1), false); // Tạm khóa

        (bool success, bytes memory returnData) = address(bcs1).call(
            abi.encodeWithSignature(
                "createSpendRequest(address,address,uint256,string)",
                address(core),
                payable(address(this)),
                1 ether,
                "Mua tai lieu"
            )
        );
        require(!success, "Deactivated BCS cannot create spend request");
        require(returnData.length >= 4, "Must return error data");
        bytes4 actual;
        assembly { actual := mload(add(returnData, 0x20)) }
        require(actual == bytes4(keccak256("NotActiveBCS()")), "Must revert NotActiveBCS()");
    }

    // ==========================================
    // NHÓM C — R11: RÚT PHÍ VẬN HÀNH (CVHT)
    // ==========================================

    /// @notice Ca C1: CVHT rút phí vận hành hợp lệ, bảo toàn Quỹ lớp chính
    function testGroupC1_AdvisorWithdrawValidFee() public payable {
        core.deposit{value: 10 ether}();
        // adminFeePool = 0.1 ETH, classFundBalance = 9.9 ETH
        require(core.adminFeePool() == 0.1 ether, "Fee pool must be 0.1 ETH");

        uint256 withdrawAmt = 0.04 ether;
        core.withdrawAdminFee(withdrawAmt);

        require(core.adminFeePool() == 0.06 ether, "Fee pool must decrease to 0.06 ETH");
        require(core.classFundBalance() == 9.9 ether, "Class fund balance must remain strictly 9.9 ETH");
    }

    /// @notice Ca C2: Người ngoài không thể rút phí vận hành
    function testGroupC2_NonAdvisorCannotWithdrawFee() public payable {
        core.deposit{value: 5 ether}();
        (bool success, bytes memory returnData) = outsider.tryWithdrawFee(core, 0.01 ether);
        require(!success, "Non-advisor withdrawAdminFee must revert");
        require(returnData.length >= 4, "Must return error data");
        bytes4 actual;
        assembly { actual := mload(add(returnData, 0x20)) }
        require(actual == bytes4(keccak256("NotAdvisor()")), "Must revert NotAdvisor()");
    }

    /// @notice Ca C3: Không thể rút phí vượt quá số dư adminFeePool hiện có
    function testGroupC3_CannotWithdrawExceedingFeePool() public payable {
        core.deposit{value: 2 ether}(); // fee pool = 0.02 ETH
        (bool success, bytes memory returnData) = address(core).call(
            abi.encodeWithSignature("withdrawAdminFee(uint256)", 1 ether)
        );
        require(!success, "Withdrawing more than adminFeePool must revert");
        require(returnData.length >= 4, "Must return error data");
        bytes4 actual;
        assembly { actual := mload(add(returnData, 0x20)) }
        require(actual == bytes4(keccak256("InsufficientAdminFee(uint256,uint256)")), "Must revert InsufficientAdminFee");
    }

    /// @notice Ca C4: Không thể rút 0 ETH phí
    function testGroupC4_CannotWithdrawZeroFee() public payable {
        core.deposit{value: 2 ether}();
        (bool success, bytes memory returnData) = address(core).call(
            abi.encodeWithSignature("withdrawAdminFee(uint256)", 0)
        );
        require(!success, "Withdrawing 0 ETH must revert");
        require(returnData.length >= 4, "Must return error data");
        bytes4 actual;
        assembly { actual := mload(add(returnData, 0x20)) }
        require(actual == bytes4(keccak256("ZeroAmount()")), "Must revert ZeroAmount()");
    }

    /// @notice Ca C5: Ví nhận phí từ chối ETH thì giao dịch revert và số dư được rollback nguyên vẹn
    function testGroupC5_RejectingAdvisorWithdrawFeeRevertsAndRollsBack() public payable {
        RejectingAdvisor rejectingAdvisor = new RejectingAdvisor();
        // Nạp 10 ETH vào hợp đồng core của RejectingAdvisor -> fee pool = 0.1 ETH
        rejectingAdvisor.depositToCore{value: 10 ether}();
        ProjectCore targetCore = rejectingAdvisor.target();

        require(targetCore.adminFeePool() == 0.1 ether, "Initial fee pool must be 0.1 ETH");

        // Gọi rút phí: call tới RejectingAdvisor sẽ thất bại vì receive() revert
        (bool success, bytes memory returnData) = rejectingAdvisor.tryWithdrawFee(0.05 ether);
        require(!success, "Withdraw to rejecting advisor must revert");
        require(returnData.length >= 4, "Must return error data");
        bytes4 actual;
        assembly { actual := mload(add(returnData, 0x20)) }
        require(actual == bytes4(keccak256("ETHTransferFailed()")), "Must revert ETHTransferFailed()");

        // Số dư kế toán adminFeePool được rollback bảo toàn 100%
        require(targetCore.adminFeePool() == 0.1 ether, "adminFeePool must remain 0.1 ETH after revert");
    }

    // ==========================================
    // NHÓM D — R3: TẠO ĐỀ XUẤT CHI TIÊU (BCS)
    // ==========================================

    /// @notice Ca D1: BCS đang hoạt động tạo đề xuất chi thành công và giữ chỗ số dư
    function testGroupD1_ActiveBCSCreateSpendRequest() public payable {
        core.deposit{value: 10 ether}(); // classFund = 9.9 ETH
        core.setBCSMember(address(bcs1), true);

        uint256 reqId = bcs1.createSpendRequest(
            core,
            payable(address(this)),
            2 ether,
            "Chi phi to chuc hoi thao"
        );

        require(reqId == 1, "First requestId must be 1");
        require(core.spendRequestCount() == 1, "spendRequestCount must be 1");
        require(core.reservedSpendAmount() == 2 ether, "reservedSpendAmount must be 2 ETH");
        require(core.getAvailableClassFund() == 7.9 ether, "Available class fund must be 7.9 ETH");
    }

    /// @notice Ca D2: Người ngoài không phải BCS không thể tạo đề xuất chi
    function testGroupD2_NonBCSCannotCreateRequest() public payable {
        core.deposit{value: 5 ether}();
        (bool success, bytes memory returnData) = outsider.tryCreateRequest(
            core,
            payable(address(this)),
            1 ether,
            "Tieu xai ca nhan"
        );
        require(!success, "Outsider createSpendRequest must revert");
        require(returnData.length >= 4, "Must return error data");
        bytes4 actual;
        assembly { actual := mload(add(returnData, 0x20)) }
        require(actual == bytes4(keccak256("NotActiveBCS()")), "Must revert NotActiveBCS()");
    }

    /// @notice Ca D3: Người nhận zero, số tiền zero hoặc vượt quá quỹ khả dụng đều bị từ chối
    function testGroupD3_ZeroRecipientOrAmountOrExceedingFundReverts() public payable {
        core.deposit{value: 1 ether}(); // classFund = 0.99 ETH
        core.setBCSMember(address(bcs1), true);

        // Recipient zero
        (bool s1, bytes memory r1) = address(bcs1).call(
            abi.encodeWithSignature(
                "createSpendRequest(address,address,uint256,string)",
                address(core),
                payable(address(0)),
                0.1 ether,
                "Loi zero address"
            )
        );
        require(!s1, "Recipient address(0) must revert");
        bytes4 a1;
        assembly { a1 := mload(add(r1, 0x20)) }
        require(a1 == bytes4(keccak256("InvalidAddress()")), "Must revert InvalidAddress()");

        // Amount zero
        (bool s2, bytes memory r2) = address(bcs1).call(
            abi.encodeWithSignature(
                "createSpendRequest(address,address,uint256,string)",
                address(core),
                payable(address(this)),
                0,
                "Loi zero amount"
            )
        );
        require(!s2, "Amount 0 must revert");
        bytes4 a2;
        assembly { a2 := mload(add(r2, 0x20)) }
        require(a2 == bytes4(keccak256("ZeroAmount()")), "Must revert ZeroAmount()");

        // Amount > availableFund (yêu cầu 2 ETH trong khi chỉ có 0.99 ETH)
        (bool s3, bytes memory r3) = address(bcs1).call(
            abi.encodeWithSignature(
                "createSpendRequest(address,address,uint256,string)",
                address(core),
                payable(address(this)),
                2 ether,
                "Vuot ngan sach"
            )
        );
        require(!s3, "Exceeding available fund must revert");
        bytes4 a3;
        assembly { a3 := mload(add(r3, 0x20)) }
        require(a3 == bytes4(keccak256("InsufficientAvailableFund(uint256,uint256)")), "Must revert InsufficientAvailableFund");
    }

    /// @notice Ca D4: Nhiều đề xuất không thể giữ chỗ vượt quá số dư khả dụng
    function testGroupD4_MultipleRequestsCannotExceedAvailableFund() public payable {
        core.deposit{value: 10 ether}(); // classFund = 9.9 ETH
        core.setBCSMember(address(bcs1), true);

        // Đề xuất 1: Giữ chỗ 6 ETH -> còn khả dụng 3.9 ETH
        uint256 r1 = bcs1.createSpendRequest(core, payable(address(this)), 6 ether, "De xuat 1");
        require(r1 == 1, "Request 1 created");
        require(core.reservedSpendAmount() == 6 ether, "Reserved is 6 ETH");
        require(core.getAvailableClassFund() == 3.9 ether, "Available is 3.9 ETH");

        // Đề xuất 2: Cố giữ chỗ 5 ETH (> 3.9 ETH) -> Phải bị REVERT
        (bool s2, bytes memory ret2) = address(bcs1).call(
            abi.encodeWithSignature(
                "createSpendRequest(address,address,uint256,string)",
                address(core),
                payable(address(this)),
                5 ether,
                "De xuat 2 qua muc"
            )
        );
        require(!s2, "Request 2 exceeding available fund must revert");
        bytes4 a2;
        assembly { a2 := mload(add(ret2, 0x20)) }
        require(a2 == bytes4(keccak256("InsufficientAvailableFund(uint256,uint256)")), "Must revert InsufficientAvailableFund");

        // Đề xuất 2 hợp lệ: Giữ chỗ 3 ETH (<= 3.9 ETH) -> Thành công
        uint256 r2 = bcs1.createSpendRequest(core, payable(address(this)), 3 ether, "De xuat 2 hop le");
        require(r2 == 2, "Request 2 created");
        require(core.reservedSpendAmount() == 9 ether, "Total reserved is 9 ETH");
        require(core.getAvailableClassFund() == 0.9 ether, "Remaining available is 0.9 ETH");
    }

    // ==========================================
    // NHÓM E — R4 & R5: BIỂU QUYẾT & NGƯỠNG 51%
    // ==========================================

    /// @notice Ca E1: Bỏ phiếu thuận/chống, chống bỏ phiếu kép, đạt 51% chuyển sang Ready
    function testGroupE1_VoteYesAndNo_AndDoubleVotingReverts() public payable {
        core.deposit{value: 10 ether}();
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true); // activeBCSCount = 3

        uint256 reqId = bcs1.createSpendRequest(
            core,
            payable(address(this)),
            3 ether,
            "Mua ban ghe"
        );

        // bcs1 bỏ phiếu thuận (1/3 = 33% < 51% -> vẫn Pending)
        bcs1.vote(core, reqId, true);
        require(core.hasMemberVoted(reqId, address(bcs1)), "bcs1 has voted");
        (, , , , , , uint256 yes1, , ProjectCore.RequestStatus st1) = core.getSpendRequest(reqId);
        require(yes1 == 1, "yesVotes must be 1");
        require(st1 == ProjectCore.RequestStatus.Pending, "Status must still be Pending");

        // bcs1 cố bỏ phiếu lần 2 -> REVERT (Chống Double Voting)
        (bool sDouble, bytes memory rDouble) = address(bcs1).call(
            abi.encodeWithSignature("vote(address,uint256,bool)", address(core), reqId, true)
        );
        require(!sDouble, "Double voting from bcs1 must revert");
        bytes4 aDouble;
        assembly { aDouble := mload(add(rDouble, 0x20)) }
        require(aDouble == bytes4(keccak256("AlreadyVoted(uint256,address)")), "Must revert AlreadyVoted");

        // bcs2 bỏ phiếu thuận (2/3 = 66% >= 51% -> Tự động Ready)
        bcs2.vote(core, reqId, true);
        (, , , , , , uint256 yes2, , ProjectCore.RequestStatus st2) = core.getSpendRequest(reqId);
        require(yes2 == 2, "yesVotes must be 2");
        require(st2 == ProjectCore.RequestStatus.Ready, "Status must transition to Ready at 51%");
    }

    /// @notice Ca E2: Người ngoài cố tình bỏ phiếu bị từ chối
    function testGroupE2_NonBCSCannotVote() public payable {
        core.deposit{value: 5 ether}();
        core.setBCSMember(address(bcs1), true);
        uint256 reqId = bcs1.createSpendRequest(core, payable(address(this)), 1 ether, "Hoi khoa");

        (bool success, bytes memory returnData) = outsider.tryVote(core, reqId, true);
        require(!success, "Outsider vote must revert");
        bytes4 actual;
        assembly { actual := mload(add(returnData, 0x20)) }
        require(actual == bytes4(keccak256("NotActiveBCS()")), "Must revert NotActiveBCS()");
    }

    /// @notice Ca E3: Xác minh mẫu số động khi danh sách BCS thay đổi giữa quá trình biểu quyết
    function testGroupE3_DynamicBCSDenominator() public payable {
        core.deposit{value: 5 ether}();
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true); // 2 BCS hiện hành

        uint256 reqId = bcs1.createSpendRequest(core, payable(address(this)), 1 ether, "Lop");
        bcs1.vote(core, reqId, true); // 1/2 = 50% < 51% -> Pending

        (, , , , , , , , ProjectCore.RequestStatus st1) = core.getSpendRequest(reqId);
        require(st1 == ProjectCore.RequestStatus.Pending, "50% is not >= 51%");

        // CVHT xóa bcs2 do ngừng hoạt động -> activeBCSCount giảm còn 1
        core.setBCSMember(address(bcs2), false);
        require(core.activeBCSCount() == 1, "activeBCSCount is now 1");

        // Với 1 BCS hoạt động, 1 phiếu thuận đạt 1/1 = 100% >= 51%
        bcs1.execute(core, reqId);
        (, , , , , , , , ProjectCore.RequestStatus st2) = core.getSpendRequest(reqId);
        require(st2 == ProjectCore.RequestStatus.Executed, "Executed successfully after denominator adjustment");
    }

    /// @notice Ca E4: Gọi dọn dẹp hết hạn khi thời hạn 7 ngày vẫn còn hiệu lực thì bị từ chối
    function testGroupE4_ExpireBeforeVotingPeriodReverts() public payable {
        core.deposit{value: 5 ether}();
        core.setBCSMember(address(bcs1), true);
        uint256 reqId = bcs1.createSpendRequest(core, payable(address(this)), 1 ether, "Test Expire");

        // Gọi expire khi vừa tạo (block.timestamp <= createdAt + 7 days) -> REVERT
        (bool success, bytes memory returnData) = address(core).call(
            abi.encodeWithSignature("expireSpendRequest(uint256)", reqId)
        );
        require(!success, "expireSpendRequest must revert while voting is still active");
        bytes4 actual;
        assembly { actual := mload(add(returnData, 0x20)) }
        require(actual == bytes4(keccak256("VotingStillActive(uint256)")), "Must revert VotingStillActive");
    }

    // ==========================================
    // NHÓM F — R6: GIẢI NGÂN & AN NINH CHUYỂN TIỀN (CEI)
    // ==========================================

    /// @notice Ca F1: Giải ngân thành công khi đạt >= 51% phiếu, cập nhật chính xác số dư
    function testGroupF1_ExecuteSuccessfulWhenThresholdMet() public payable {
        core.deposit{value: 10 ether}(); // classFund = 9.9 ETH
        core.setBCSMember(address(bcs1), true);

        // 1 BCS duy nhất: 1 vote = 100% >= 51%
        uint256 reqId = bcs1.createSpendRequest(core, payable(address(this)), 3 ether, "Tham quan hoc tap");
        bcs1.vote(core, reqId, true);

        uint256 balBefore = address(this).balance;
        bcs1.execute(core, reqId);
        uint256 balAfter = address(this).balance;

        require(balAfter - balBefore == 3 ether, "Recipient must receive exactly 3 ETH");
        require(core.classFundBalance() == 6.9 ether, "Class fund must decrease to 6.9 ETH");
        require(core.reservedSpendAmount() == 0, "reservedSpendAmount must decrease back to 0");

        (, , , , , , , , ProjectCore.RequestStatus st) = core.getSpendRequest(reqId);
        require(st == ProjectCore.RequestStatus.Executed, "Status must be Executed");
    }

    /// @notice Ca F2: Chưa đủ ngưỡng 51% thì không được phép giải ngân
    function testGroupF2_CannotExecuteWithoutThreshold() public payable {
        core.deposit{value: 5 ether}();
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);

        uint256 reqId = bcs1.createSpendRequest(core, payable(address(this)), 1 ether, "Chua du phieu");
        // Chưa ai bỏ phiếu (0% < 51%)
        (bool success, bytes memory returnData) = address(bcs1).call(
            abi.encodeWithSignature("execute(address,uint256)", address(core), reqId)
        );
        require(!success, "Execution without 51% threshold must revert");
        bytes4 actual;
        assembly { actual := mload(add(returnData, 0x20)) }
        require(actual == bytes4(keccak256("ThresholdNotMet(uint256,uint256)")), "Must revert ThresholdNotMet");
    }

    /// @notice Ca F3: Chống thực thi lặp lại (Double execution / Double spending)
    function testGroupF3_DoubleExecutionReverts() public payable {
        core.deposit{value: 5 ether}();
        core.setBCSMember(address(bcs1), true);

        uint256 reqId = bcs1.createSpendRequest(core, payable(address(this)), 1 ether, "Chi 1 lan");
        bcs1.vote(core, reqId, true);
        bcs1.execute(core, reqId);

        // Cố thực thi lần 2
        (bool s2, bytes memory r2) = address(bcs1).call(
            abi.encodeWithSignature("execute(address,uint256)", address(core), reqId)
        );
        require(!s2, "Second execution must revert");
        bytes4 a2;
        assembly { a2 := mload(add(r2, 0x20)) }
        require(a2 == bytes4(keccak256("RequestAlreadyExecuted(uint256)")), "Must revert RequestAlreadyExecuted");
    }

    /// @notice Ca F4: Người nhận từ chối ETH thì toàn bộ giao dịch giải ngân revert và bảo toàn trạng thái (CEI)
    function testGroupF4_ExecuteRevertsIfRecipientRefusesETH() public payable {
        core.deposit{value: 5 ether}();
        core.setBCSMember(address(bcs1), true);

        RejectingRecipient rejector = new RejectingRecipient();
        uint256 reqId = bcs1.createSpendRequest(core, payable(address(rejector)), 1 ether, "Nguoi nhan tu choi");
        bcs1.vote(core, reqId, true);

        (bool success, bytes memory returnData) = address(bcs1).call(
            abi.encodeWithSignature("execute(address,uint256)", address(core), reqId)
        );
        require(!success, "Execution to rejecting recipient must revert");
        bytes4 actual;
        assembly { actual := mload(add(returnData, 0x20)) }
        require(actual == bytes4(keccak256("ETHTransferFailed()")), "Must revert ETHTransferFailed()");

        // Số dư và trạng thái được rollback hoàn toàn
        require(core.classFundBalance() == 4.95 ether, "Class fund must remain 4.95 ETH");
        require(core.reservedSpendAmount() == 1 ether, "Reserved spend amount must remain unchanged after revert");
    }

    /// @notice Ca F5: Chống Reentrancy khi giải ngân nhờ mô hình Checks-Effects-Interactions (CEI)
    /// @dev Kẻ tấn công đồng thời là thành viên BCS, đảm bảo cuộc gọi tái nhập vượt qua onlyActiveBCS và thực sự kiểm tra trạng thái Executed
    function testGroupF5_ReentrancyDuringExecuteIsBlockedByCEI() public payable {
        core.deposit{value: 5 ether}();
        core.setBCSMember(address(bcs1), true);

        // Tạo MaliciousBCSRecipient và cấp quyền BCS cho chính nó
        MaliciousBCSRecipient attackerRecipient = new MaliciousBCSRecipient(payable(address(core)));
        core.setBCSMember(address(attackerRecipient), true); // Cấp quyền BCS!

        uint256 reqId = bcs1.createSpendRequest(core, payable(address(attackerRecipient)), 1 ether, "Ke tan cong co quyen BCS");
        bcs1.vote(core, reqId, true);
        // Attacker bỏ phiếu thuận cho chính mình -> 2/2 = 100% >= 51%
        attackerRecipient.vote(reqId, true);
        bcs1.execute(core, reqId);

        // Xác nhận đòn tái nhập đã xảy ra
        require(attackerRecipient.attackAttempts() == 1, "Attacker must have attempted reentrancy");
        // Xác nhận đòn tái nhập bị chặn bởi CEI
        require(attackerRecipient.reentrancyBlocked(), "Reentrancy must be blocked by CEI");
        // Xác nhận lỗi revert từ đòn tái nhập chính là RequestAlreadyExecuted (không phải NotActiveBCS!)
        require(
            attackerRecipient.reentrancyRevertSelector() == bytes4(keccak256("RequestAlreadyExecuted(uint256)")),
            "Reentrancy must be blocked specifically by RequestAlreadyExecuted custom error"
        );
        // Số dư giảm chính xác 1 lần duy nhất từ 4.95 ETH xuống 3.95 ETH
        require(core.classFundBalance() == 3.95 ether, "Class fund must decrease only once to 3.95 ETH");
    }

    // ==========================================
    // NHÓM G — TÍNH BẤT BIẾN & KẾ TOÁN (INVARIANTS)
    // ==========================================

    /// @notice Ca G1: Tính bất biến kế toán bảo toàn tuyệt đối qua chuỗi thao tác liên hoàn
    function testGroupG1_AccountingConservationAndIsolation() public payable {
        // 1. Nạp 10 ETH
        core.deposit{value: 10 ether}();
        require(core.getTotalContractBalance() == core.classFundBalance() + core.adminFeePool(), "Invariant 1: Total balance matches sum of pools");

        // 2. CVHT rút 0.05 ETH phí
        core.withdrawAdminFee(0.05 ether);
        require(core.getTotalContractBalance() == core.classFundBalance() + core.adminFeePool(), "Invariant 2: Balance conserved after fee withdrawal");

        // 3. BCS tạo đề xuất 4 ETH
        core.setBCSMember(address(bcs1), true);
        uint256 reqId = bcs1.createSpendRequest(core, payable(address(this)), 4 ether, "Ke toan bat bien");
        require(core.classFundBalance() == core.getAvailableClassFund() + core.reservedSpendAmount(), "Invariant 3: Class fund = Available + Reserved");

        // 4. Giải ngân 4 ETH
        bcs1.vote(core, reqId, true);
        bcs1.execute(core, reqId);
        require(core.getTotalContractBalance() == core.classFundBalance() + core.adminFeePool(), "Invariant 4: Total balance conserved after spend execution");
        require(core.reservedSpendAmount() == 0, "Invariant 5: Reserved returns to 0 after execution");
    }
}
