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

    function voteRefund(ProjectCore target, uint256 refundId, bool support) external {
        target.voteRefundRequest(refundId, support);
    }

    function execute(ProjectCore target, uint256 requestId) external {
        target.executeSpendRequest(requestId);
    }

    function depositToCore(ProjectCore target) external payable {
        target.deposit{value: msg.value}();
    }

    function createRefundRequest(
        ProjectCore target,
        uint256 amount,
        string memory reason
    ) external returns (uint256) {
        return target.createRefundRequest(amount, reason);
    }

    function createCollection(
        ProjectCore target,
        uint256 targetWei,
        uint64 deadline,
        string memory purpose
    ) external returns (uint256) {
        return target.createCollection(targetWei, deadline, purpose);
    }

    function closeCollection(
        ProjectCore target,
        uint256 id,
        string memory reason
    ) external {
        target.closeCollection(id, reason);
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

    function tryMoveFee(ProjectCore target, uint256 amount) external returns (bool success, bytes memory returnData) {
        (success, returnData) = address(target).call(
            abi.encodeWithSignature("moveFeeToClassFund(uint256)", amount)
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

/// @notice Hợp đồng sinh viên kiểm thử nạp và tạo hoàn tiền
contract StudentTestActor {
    receive() external payable {}

    function deposit(ProjectCore target) external payable {
        target.deposit{value: msg.value}();
    }

    function directSend(ProjectCore target) external payable {
        (bool ok, ) = address(target).call{value: msg.value}("");
        require(ok, "Direct send failed");
    }

    function createRefund(ProjectCore target, uint256 amount, string memory reason) external returns (uint256) {
        return target.createRefundRequest(amount, reason);
    }

    function executeRefund(ProjectCore target, uint256 refundId) external {
        target.executeRefundRequest(refundId);
    }

    function depositToCollection(ProjectCore target, uint256 id) external payable {
        target.depositToCollection{value: msg.value}(id);
    }
}

/// @notice Hợp đồng Cố vấn học tập từ chối nhận ETH để kiểm tra cơ chế GasRefundFailed khi hoàn gas thất bại
contract RejectingAdvisor {
    ProjectCore public target;
    StudentTestActor public studentHelper;

    constructor() {
        target = new ProjectCore();
        studentHelper = new StudentTestActor();
        address[] memory studs = new address[](1);
        studs[0] = address(studentHelper);
        target.setStudents(studs, true);
    }

    function depositToCore() external payable {
        studentHelper.deposit{value: msg.value}(target);
    }

    function tryCommitRoster(bytes32 rHash) external returns (bool success, bytes memory returnData) {
        (success, returnData) = address(target).call(
            abi.encodeWithSignature("commitRoster(bytes32)", rHash)
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

/// @notice Hợp đồng sinh viên từ chối nhận ETH để kiểm tra fallback khi hoàn tiền
contract RejectingStudentTestActor {
    ProjectCore public target;

    constructor(address payable _target) {
        target = ProjectCore(_target);
    }

    function fund() external payable {}

    function deposit(uint256 amount) external payable {
        target.deposit{value: amount}();
    }

    function createRefund(uint256 amount, string memory reason) external returns (uint256) {
        return target.createRefundRequest(amount, reason);
    }

    receive() external payable {
        revert("RejectingStudentTestActor: refuse ETH");
    }
}

/// @title ProjectCoreTest - Bộ kiểm thử tự động toàn diện cho ProjectCore (Lab 13)
/// @notice Kiểm tra đầy đủ 7 nhóm: R2 (Nạp), R1 (Quyền), R11 (Rút phí), R3 (Đề xuất), R4/R5 (Biểu quyết), R6 (Giải ngân & CEI), Nhóm G (Kế toán & Bất biến)
contract ProjectCoreTest {
    uint256 public initialBalance = 100 ether; // Cấp vốn cho test runner trên Remix VM
    ProjectCore core;
    StudentTestActor student1;
    BCSActor bcs1;
    BCSActor bcs2;
    BCSActor bcs3;
    NonAdvisorActor outsider;

    /// @notice Hỗ trợ nhận ETH cho test contract
    receive() external payable {}

    /// @notice Nạp tiền đại diện sinh viên đã ghi danh
    function depositAsStudent(uint256 amount) internal {
        student1.deposit{value: amount}(core);
    }

    /// @notice Chuẩn bị môi trường độc lập trước mỗi ca kiểm thử
    function beforeEach() public {
        core = new ProjectCore();
        student1 = new StudentTestActor();
        bcs1 = new BCSActor();
        bcs2 = new BCSActor();
        bcs3 = new BCSActor();
        outsider = new NonAdvisorActor();

        (bool s1, ) = address(student1).call{value: 50 ether}("");
        require(s1, "Funding student1 failed");

        address[] memory studs = new address[](4);
        studs[0] = address(student1);
        studs[1] = address(bcs1);
        studs[2] = address(bcs2);
        studs[3] = address(bcs3);
        core.setStudents(studs, true);
    }

    // ==========================================
    // NHÓM A — R2: NẠP TIỀN & PHÂN BỔ 99% / 1%
    // ==========================================

    /// @notice Ca A1: Nạp 1 ETH -> 99% Quỹ lớp chính (0.99 ETH), 1% adminFeePool (0.01 ETH)
    function testGroupA1_Deposit1ETH_Split99_1() public payable {
        uint256 depositAmt = 1 ether;
        student1.deposit{value: depositAmt}(core);

        require(core.classFundBalance() == 0.99 ether, "Class fund balance must be 0.99 ETH");
        require(core.adminFeePool() == 0.01 ether, "Admin fee pool must be 0.01 ETH");
        require(core.getFundBalance() == 0.99 ether, "getFundBalance() must match classFundBalance");
        require(core.studentContributions(address(student1)) == 0.99 ether, "Student net contribution limit must be 0.99 ETH");
        require(core.studentTotalDeposited(address(student1)) == depositAmt, "Student total deposited must record full 1 ETH");
        require(core.getStudentMaxRefund(address(student1)) == 0.99 ether, "Max refund must be 0.99 ETH");
        require(core.getTotalContractBalance() == depositAmt, "Total contract balance must match 1 ETH");
    }

    /// @notice Ca A2: Nạp trực tiếp qua kênh receive() 0.5 ETH
    function testGroupA2_DirectReceive() public payable {
        uint256 depositAmt = 0.5 ether;
        student1.directSend{value: depositAmt}(core);

        require(core.classFundBalance() == 0.495 ether, "Class fund must receive 0.495 ETH");
        require(core.adminFeePool() == 0.005 ether, "Admin fee must receive 0.005 ETH");
    }

    /// @notice Ca A3: Nạp 0 ETH qua deposit() và receive() đều bị revert ZeroAmount()
    function testGroupA3_ZeroAmountReverts() public {
        bytes4 expectedSelector = bytes4(keccak256("ZeroAmount()"));

        (bool s1, bytes memory r1) = address(student1).call(
            abi.encodeWithSignature("deposit(address)", address(core))
        );
        require(!s1, "deposit(0) must revert");
        require(r1.length >= 4, "Must return error data");
        bytes4 a1;
        assembly { a1 := mload(add(r1, 0x20)) }
        require(a1 == expectedSelector, "Revert reason must be ZeroAmount()");

        (bool s2, bytes memory r2) = address(student1).call(
            abi.encodeWithSignature("directSend(address)", address(core))
        );
        require(!s2, "receive(0) must revert");
        require(r2.length >= 4, "Must return error data");
        bytes4 a2;
        assembly { a2 := mload(add(r2, 0x20)) }
        require(a2 == expectedSelector, "Revert reason must be ZeroAmount()");
    }

    /// @notice Ca A4: Phép tính số nguyên và các giá trị biên (< 100 wei)
    function testGroupA4_IntegerMathEdgeCases() public payable {
        depositAsStudent(99);
        require(core.adminFeePool() == 0, "Fee for 99 wei must be 0");
        require(core.classFundBalance() == 99, "Fund must receive all 99 wei");

        depositAsStudent(101);
        require(core.adminFeePool() == 1, "Cumulative fee must be 1 wei");
        require(core.classFundBalance() == 99 + 100, "Cumulative fund must be 199 wei");
        require(core.classFundBalance() + core.adminFeePool() == 200, "Sum must equal 200 wei");
    }

    // ==========================================
    // NHÓM B — R1: PHÂN QUYỀN CVHT & QUẢN LÝ BCS (PHASE 2: DELAY 3 NGÀY, MAX_BCS, O(1) SWAP-AND-POP)
    // ==========================================

    /// @notice Ca B1: Cố vấn học tập thêm và xóa thành viên Ban cán sự thành công (cập nhật memberSince & bcsList O(1))
    function testGroupB1_AdvisorAddAndRemoveBCS() public {
        uint256 tNow = block.timestamp;
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        require(core.isBCSMember(address(bcs1)), "bcs1 must be listed as BCS");
        require(core.isBCSMember(address(bcs2)), "bcs2 must be listed as BCS");
        require(core.memberSince(address(bcs1)) == tNow + core.BCS_ACTIVATION_DELAY(), "bcs1 memberSince must equal now + 3 days");
        require(core.activeBCSCount() == 2, "activeBCSCount must be 2");
        require(core.getBCSList().length == 2, "bcsList length must be 2");

        // Vô hiệu hóa bcs1 (O(1) swap-and-pop và xóa memberSince)
        core.setBCSMember(address(bcs1), false);
        require(!core.isBCSMember(address(bcs1)), "bcs1 must be deactivated");
        require(core.memberSince(address(bcs1)) == 0, "bcs1 memberSince must reset to 0");
        require(core.activeBCSCount() == 1, "activeBCSCount must be 1");
        address[] memory listAfter = core.getBCSList();
        require(listAfter.length == 1 && listAfter[0] == address(bcs2), "O(1) swap-and-pop must leave bcs2");
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
        depositAsStudent(2 ether);
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

    /// @notice Ca B5 (Phase 2 / Mục B - chạy đơn TX trên Remix): Độ trễ kích hoạt 3 ngày, truy vấn view và chặn BCS mới
    function testGroupB5_SectionB_ActivationDelayAndViewQueries() public {
        require(core.BCS_ACTIVATION_DELAY() == 3 days, "Activation delay must be 3 days");
        require(core.MIN_BCS_FOR_PROPOSAL() == 3, "Min BCS for proposal must be 3");
        require(core.MAX_BCS() == 15, "Max BCS must be 15");

        uint256 tAdd = block.timestamp;
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        // Chưa đủ 3 ngày: eligibleBCSCount(tAdd) == 0, eligibleBCSCount(tAdd + 3 days) == 3
        require(core.eligibleBCSCount(tAdd) == 0, "Eligible count at tAdd must be 0");
        require(core.eligibleBCSCount(tAdd + 3 days) == 3, "Eligible count at tAdd + 3 days must be 3");
        require(!core.isEligibleVoterAt(address(bcs1), tAdd + 3 days - 1), "Before 3 days must be false");
        require(core.isEligibleVoterAt(address(bcs1), tAdd + 3 days), "Exact 3 days must be true");

        // BCS mới thêm (< 3 ngày) gọi createSpendRequest bị chặn NotActiveBCS()
        (bool sEarly, bytes memory rEarly) = address(bcs1).call(
            abi.encodeWithSignature(
                "createSpendRequest(address,address,uint256,string)",
                address(core),
                payable(address(this)),
                0.5 ether,
                "Tao som"
            )
        );
        require(!sEarly, "Immature BCS < 3 days cannot create spend request");
        bytes4 aEarly;
        assembly { aEarly := mload(add(rEarly, 0x20)) }
        require(aEarly == bytes4(keccak256("NotActiveBCS()")), "Must revert NotActiveBCS()");
    }

    /// @notice Ca B6 (Phase 2 / Mục B - chạy đơn TX trên Remix): Giới hạn MAX_BCS = 15 và gỡ O(1) swap-and-pop đầu/giữa/cuối
    function testGroupB6_SectionB_MaxBCSAndSwapAndPop() public {
        address[] memory studs = new address[](16);
        for (uint160 i = 1; i <= 16; i++) {
            studs[i - 1] = address(0x1000 + i);
        }
        core.setStudents(studs, true);

        for (uint160 i = 1; i <= 15; i++) {
            core.setBCSMember(address(0x1000 + i), true);
        }
        require(core.activeBCSCount() == 15, "activeBCSCount must reach MAX_BCS 15");

        // Thêm người thứ 16 -> Revert MaxBCSReached()
        (bool sOver, bytes memory rOver) = address(core).call(
            abi.encodeWithSignature("setBCSMember(address,bool)", address(0x1010), true)
        );
        require(!sOver, "16th BCS must revert MaxBCSReached");
        bytes4 aOver;
        assembly { aOver := mload(add(rOver, 0x20)) }
        require(aOver == bytes4(keccak256("MaxBCSReached()")), "Must revert MaxBCSReached()");

        // Gỡ phần tử đầu (0x1001), giữa (0x1008) và cuối danh sách hiện tại
        core.setBCSMember(address(0x1001), false);
        core.setBCSMember(address(0x1008), false);
        address[] memory list = core.getBCSList();
        require(list.length == 13, "List length must decrease to 13");
        core.setBCSMember(list[list.length - 1], false);
        require(core.getBCSList().length == 12, "List length must decrease to 12");
    }

    /// @notice Ca B7 (Phase 2 / Mục B - chạy đơn TX trên Remix): Sinh viên xin hoàn tiền bị chặn NotEnoughBCS(0, 3) khi chưa đủ 3 BCS đủ điều kiện
    function testGroupB7_SectionB_StudentRefundBlockedUnderMinBCS() public payable {
        depositAsStudent(5 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true); // mới 2 BCS và chưa qua 3 ngày -> eligible = 0

        (bool success, bytes memory returnData) = address(student1).call(
            abi.encodeWithSignature("createRefund(address,uint256,string)", address(core), 1 ether, "Xin hoan khi thieu BCS")
        );
        require(!success, "Student createRefundRequest must revert when eligible < 3");
        bytes4 actual;
        assembly { actual := mload(add(returnData, 0x20)) }
        require(actual == bytes4(keccak256("NotEnoughBCS(uint256,uint256)")), "Must revert NotEnoughBCS");
    }

    // ==========================================
    // NHÓM C — R11: RÚT PHÍ VẬN HÀNH (CVHT)
    // ==========================================

    /// @notice Ca C1: CVHT rút phí vận hành hợp lệ, bảo toàn Quỹ lớp chính
    function testGroupC1_AdvisorMoveValidFee() public payable {
        depositAsStudent(10 ether);
        // adminFeePool = 0.1 ETH, classFundBalance = 9.9 ETH
        require(core.adminFeePool() == 0.1 ether, "Fee pool must be 0.1 ETH");

        uint256 moveAmt = 0.04 ether;
        core.moveFeeToClassFund(moveAmt);

        require(core.adminFeePool() == 0.06 ether, "Fee pool must decrease to 0.06 ETH");
        require(core.classFundBalance() == 9.94 ether, "Class fund balance must increase to 9.94 ETH");
        require(core.getTotalContractBalance() == 10 ether, "Total balance must remain 10 ETH");
    }

    /// @notice Ca C2: Người ngoài không thể điều chuyển phí vận hành
    function testGroupC2_NonAdvisorCannotMoveFee() public payable {
        depositAsStudent(5 ether);
        (bool success, bytes memory returnData) = outsider.tryMoveFee(core, 0.01 ether);
        require(!success, "Non-advisor moveFeeToClassFund must revert");
        require(returnData.length >= 4, "Must return error data");
        bytes4 actual;
        assembly { actual := mload(add(returnData, 0x20)) }
        require(actual == bytes4(keccak256("NotAdvisor()")), "Must revert NotAdvisor()");
    }

    /// @notice Ca C3: Không thể chuyển phí vượt quá số dư adminFeePool hiện có
    function testGroupC3_CannotMoveExceedingFeePool() public payable {
        depositAsStudent(2 ether); // fee pool = 0.02 ETH
        (bool success, bytes memory returnData) = address(core).call(
            abi.encodeWithSignature("moveFeeToClassFund(uint256)", 1 ether)
        );
        require(!success, "Moving more than adminFeePool must revert");
        require(returnData.length >= 4, "Must return error data");
        bytes4 actual;
        assembly { actual := mload(add(returnData, 0x20)) }
        require(actual == bytes4(keccak256("InsufficientAdminFee(uint256,uint256)")), "Must revert InsufficientAdminFee");
    }

    /// @notice Ca C4: Không thể chuyển 0 ETH phí
    function testGroupC4_CannotMoveZeroFee() public payable {
        depositAsStudent(2 ether);
        (bool success, bytes memory returnData) = address(core).call(
            abi.encodeWithSignature("moveFeeToClassFund(uint256)", 0)
        );
        require(!success, "Moving 0 ETH must revert");
        require(returnData.length >= 4, "Must return error data");
        bytes4 actual;
        assembly { actual := mload(add(returnData, 0x20)) }
        require(actual == bytes4(keccak256("ZeroAmount()")), "Must revert ZeroAmount()");
    }

    /// @notice Ca C5: Ví nhận hoàn gas từ chối nhận ETH thì giao dịch quản trị chính không bị revert và pool được bảo toàn
    function testGroupC5_GasRefundOnRejectingActorRecoversPool() public payable {
        RejectingAdvisor rejectingAdvisor = new RejectingAdvisor();
        // Nạp 10 ETH vào hợp đồng core của RejectingAdvisor -> fee pool = 0.1 ETH
        rejectingAdvisor.depositToCore{value: 10 ether}();
        ProjectCore targetCore = rejectingAdvisor.target();

        require(targetCore.adminFeePool() == 0.1 ether, "Initial fee pool must be 0.1 ETH");

        // Gọi commitRoster (governanceAction): Cố vấn từ chối ETH nên gas refund thất bại nhưng commitRoster vẫn thành công
        bytes32 sampleHash = keccak256("test_roster_hash");
        (bool success, ) = rejectingAdvisor.tryCommitRoster(sampleHash);
        require(success, "commitRoster must succeed even if gas refund to caller fails");
        require(targetCore.rosterHash() == sampleHash, "Roster hash committed successfully");

        // Số dư kế toán adminFeePool được phục hồi nguyên vẹn 100%
        require(targetCore.adminFeePool() == 0.1 ether, "adminFeePool must remain 0.1 ETH after refund failure");
    }

    // ==========================================
    // NHÓM D — R3: TẠO ĐỀ XUẤT CHI TIÊU (BCS)
    // @dev Ghi chú EVM thời gian: Các ca D1, D3, D4, E*, F*, G*, H* cần block.timestamp >= addedAt + 3 days
    //      sau setBCSMember(..., true) (được kiểm chứng tự động qua time.increase trong test/hardhat/ProjectCore.phase2.test.js).
    // ==========================================

    /// @notice Ca D1: BCS đang hoạt động (>= 3 ngày, đủ >= 3 BCS) tạo đề xuất chi thành công, chốt voterBase = 3 và giữ chỗ số dư
    function testGroupD1_ActiveBCSCreateSpendRequest() public payable {
        depositAsStudent(10 ether); // classFund = 9.9 ETH
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

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
        (, , , , , , , , , uint256 voterBase) = core.spendRequests(reqId);
        require(voterBase == 3, "voterBase snapshot must equal 3 eligible BCS");
    }

    /// @notice Ca D2: Người ngoài không phải BCS không thể tạo đề xuất chi
    function testGroupD2_NonBCSCannotCreateRequest() public payable {
        depositAsStudent(5 ether);
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
        depositAsStudent(1 ether); // classFund = 0.99 ETH
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

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
        depositAsStudent(10 ether); // classFund = 9.9 ETH
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

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
    // NHÓM E — R4 & R5: BIỂU QUYẾT, SNAPSHOT VOTERBASE & NGƯỠNG 51%
    // ==========================================

    /// @notice Ca E1: Bỏ phiếu thuận/chống, chống bỏ phiếu kép, đạt 51% trên voterBase = 3 tự động giải ngân
    function testGroupE1_VoteYesAndNo_AndDoubleVotingReverts() public payable {
        depositAsStudent(10 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true); // activeBCSCount = 3

        uint256 reqId = bcs1.createSpendRequest(
            core,
            payable(address(this)),
            3 ether,
            "Mua ban ghe"
        );
        (, , , , , , , , , uint256 vb) = core.spendRequests(reqId);
        require(vb == 3, "voterBase snapshot must be 3");

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

        // bcs2 bỏ phiếu thuận (2/3 = 66% >= 51% -> Tự động Ready & Tự thực thi thành công vì recipient nhận ETH)
        uint256 balBefore = address(this).balance;
        bcs2.vote(core, reqId, true);
        uint256 balAfter = address(this).balance;

        (, , , , , , uint256 yes2, , ProjectCore.RequestStatus st2) = core.getSpendRequest(reqId);
        require(yes2 == 2, "yesVotes must be 2 (>= 2 invariant)");
        require(st2 == ProjectCore.RequestStatus.Executed, "Status must transition to Executed via auto-execution");
        require(balAfter - balBefore == 3 ether, "Recipient must receive 3 ETH directly from decisive vote tx");
        require(core.reservedSpendAmount() == 0, "reservedSpendAmount must clear to 0 upon auto-execution");
    }

    /// @notice Ca E2: Người ngoài cố tình bỏ phiếu bị từ chối
    function testGroupE2_NonBCSCannotVote() public payable {
        depositAsStudent(5 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);
        uint256 reqId = bcs1.createSpendRequest(core, payable(address(this)), 1 ether, "Hoi khoa");

        (bool success, bytes memory returnData) = outsider.tryVote(core, reqId, true);
        require(!success, "Outsider vote must revert");
        bytes4 actual;
        assembly { actual := mload(add(returnData, 0x20)) }
        require(actual == bytes4(keccak256("NotActiveBCS()")), "Must revert NotActiveBCS()");
    }

    /// @notice Ca E3 (Cập nhật Phase 2 / Mục B): Gỡ BCS giữa chừng KHÔNG thu nhỏ mẫu số voterBase snapshot (giữ nguyên 3)
    /// @dev Trước Phase 2 hàm này kiểm tra mẫu số động; từ Phase 2, voterBase = 3 cố định nên 1/3 < 51% vẫn bị chặn ThresholdNotMet(1, 3)
    function testGroupE3_SnapshotVoterBasePreservedOnRemoval() public payable {
        depositAsStudent(5 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true); // 3 BCS hiện hành -> voterBase = 3

        uint256 reqId = bcs1.createSpendRequest(core, payable(address(this)), 1 ether, "Lop");
        bcs1.vote(core, reqId, true); // 1/3 = 33.3% < 51% -> Pending

        // CVHT gỡ bcs2 & bcs3 giữa chừng -> activeBCSCount giảm còn 1 nhưng voterBase vẫn = 3
        core.setBCSMember(address(bcs2), false);
        core.setBCSMember(address(bcs3), false);
        require(core.activeBCSCount() == 1, "activeBCSCount is now 1");
        (, , , , , , , , , uint256 vb) = core.spendRequests(reqId);
        require(vb == 3, "Snapshot voterBase must remain 3 after removals");

        // Với voterBase = 3, 1 phiếu thuận (33.3%) chưa đạt 51% -> gọi execute phải revert ThresholdNotMet(1, 3)
        (bool sExec, bytes memory rExec) = address(bcs1).call(
            abi.encodeWithSignature("execute(address,uint256)", address(core), reqId)
        );
        require(!sExec, "executeSpendRequest with 1/3 snapshot must revert ThresholdNotMet");
        bytes4 aExec;
        assembly { aExec := mload(add(rExec, 0x20)) }
        require(aExec == bytes4(keccak256("ThresholdNotMet(uint256,uint256)")), "Must revert ThresholdNotMet");
    }

    /// @notice Ca E4: Gọi dọn dẹp hết hạn khi thời hạn 7 ngày vẫn còn hiệu lực thì bị từ chối
    function testGroupE4_ExpireBeforeVotingPeriodReverts() public payable {
        depositAsStudent(5 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);
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

    /// @notice Ca E5 (Phase 2 / Mục B): Thêm BCS mới giữa chừng không làm đổi voterBase của đề xuất đang chạy
    function testGroupE5_SectionB_SnapshotUnchangedWhenBCSAddedMidVote() public payable {
        depositAsStudent(10 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        uint256 reqId = bcs1.createSpendRequest(core, payable(address(this)), 2 ether, "De xuat snapshot");
        BCSActor bcs4 = new BCSActor();
        BCSActor bcs5 = new BCSActor();
        address[] memory studs45 = new address[](2);
        studs45[0] = address(bcs4);
        studs45[1] = address(bcs5);
        core.setStudents(studs45, true);
        core.setBCSMember(address(bcs4), true);
        core.setBCSMember(address(bcs5), true);

        (, , , , , , , , , uint256 vb) = core.spendRequests(reqId);
        require(vb == 3, "voterBase must remain 3 even after adding bcs4 and bcs5");

        // Sau khi bcs4 qua 3 ngày kích hoạt vẫn bị chặn VoterNotEligibleAtCreation trên đề xuất cũ
        (bool sLate, bytes memory rLate) = address(bcs4).call(
            abi.encodeWithSignature("vote(address,uint256,bool)", address(core), reqId, true)
        );
        require(!sLate, "New BCS added after creation cannot vote on existing proposal");
        require(rLate.length >= 4, "Must revert with custom error");
    }

    /// @notice Ca E6 (Phase 2 / Mục B - Gian lận): Cố vấn thêm 3 ví ma ngay trước lúc bỏ phiếu bị chặn ở cả trước và sau 3 ngày
    function testGroupE6_SectionB_PhantomBCSFraudBlocked() public payable {
        depositAsStudent(10 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        uint256 reqId = bcs1.createSpendRequest(core, payable(address(this)), 2 ether, "Chong 3 vi ma");
        bcs1.vote(core, reqId, true);

        BCSActor phantom1 = new BCSActor();
        BCSActor phantom2 = new BCSActor();
        BCSActor phantom3 = new BCSActor();
        address[] memory pStuds = new address[](3);
        pStuds[0] = address(phantom1);
        pStuds[1] = address(phantom2);
        pStuds[2] = address(phantom3);
        core.setStudents(pStuds, true);
        core.setBCSMember(address(phantom1), true);
        core.setBCSMember(address(phantom2), true);
        core.setBCSMember(address(phantom3), true);

        // Chưa qua 3 ngày -> NotActiveBCS; nếu đã qua 3 ngày -> VoterNotEligibleAtCreation
        (bool sP1, ) = address(phantom1).call(
            abi.encodeWithSignature("vote(address,uint256,bool)", address(core), reqId, true)
        );
        require(!sP1, "Phantom wallet 1 must be blocked from voting");

        (, , , , , , uint256 yesVotes, , , uint256 vb) = core.spendRequests(reqId);
        require(yesVotes == 1 && vb == 3, "Phantom wallets must not alter votes or voterBase");
    }

    // ==========================================
    // NHÓM F — R6: GIẢI NGÂN & AN NINH CHUYỂN TIỀN (CEI)
    // ==========================================

    /// @notice Ca F1: Tự giải ngân thành công khi đạt 2/3 (>= 51%) phiếu, cập nhật chính xác số dư không cần tx execute riêng
    function testGroupF1_ExecuteSuccessfulWhenThresholdMet() public payable {
        depositAsStudent(10 ether); // classFund = 9.9 ETH
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        uint256 reqId = bcs1.createSpendRequest(core, payable(address(this)), 3 ether, "Tham quan hoc tap");
        bcs1.vote(core, reqId, true); // 1/3 Pending

        uint256 balBefore = address(this).balance;
        bcs2.vote(core, reqId, true); // 2/3 = 66.6% >= 51% -> Tự giải ngân
        uint256 balAfter = address(this).balance;

        require(balAfter - balBefore == 3 ether, "Recipient must receive exactly 3 ETH from decisive vote tx");
        require(core.classFundBalance() == 6.9 ether, "Class fund must decrease to 6.9 ETH");
        require(core.reservedSpendAmount() == 0, "reservedSpendAmount must decrease back to 0");

        (, , , , , , uint256 yesVotes, , ProjectCore.RequestStatus st) = core.getSpendRequest(reqId);
        require(yesVotes >= 2, "Approved spend must satisfy yesVotes >= 2 invariant");
        require(st == ProjectCore.RequestStatus.Executed, "Status must be Executed immediately without separate execute tx");

        // Gọi execute thủ công sau khi đã auto-execute -> Bắt buộc Revert RequestAlreadyExecuted
        (bool sAgain, bytes memory rAgain) = address(bcs1).call(
            abi.encodeWithSignature("execute(address,uint256)", address(core), reqId)
        );
        require(!sAgain, "Subsequent manual execute must revert RequestAlreadyExecuted");
        bytes4 aAgain;
        assembly { aAgain := mload(add(rAgain, 0x20)) }
        require(aAgain == bytes4(keccak256("RequestAlreadyExecuted(uint256)")), "Must revert RequestAlreadyExecuted");
    }

    /// @notice Ca F2: Chưa đủ ngưỡng 51% thì không được phép giải ngân
    function testGroupF2_CannotExecuteWithoutThreshold() public payable {
        depositAsStudent(5 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

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

    /// @notice Ca F3: Chống thực thi lặp lại sau khi auto-execution đã thành công
    function testGroupF3_DoubleExecutionReverts() public payable {
        depositAsStudent(5 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        uint256 reqId = bcs1.createSpendRequest(core, payable(address(this)), 1 ether, "Chi 1 lan");
        bcs1.vote(core, reqId, true);
        bcs2.vote(core, reqId, true); // 2/3 -> Đã tự giải ngân thành công

        // Cố thực thi thủ công lần 1 (sau auto-exec) -> REVERT
        (bool s1, bytes memory r1) = address(bcs1).call(
            abi.encodeWithSignature("execute(address,uint256)", address(core), reqId)
        );
        require(!s1, "Manual execution after auto-exec must revert");
        bytes4 a1;
        assembly { a1 := mload(add(r1, 0x20)) }
        require(a1 == bytes4(keccak256("RequestAlreadyExecuted(uint256)")), "Must revert RequestAlreadyExecuted");
    }

    /// @notice Ca F4: Người nhận từ chối ETH thì vote cuối vẫn được ghi nhận, đề xuất ở trạng thái Ready (không revert vote) và cho phép fallback execute
    function testGroupF4_ExecuteRevertsIfRecipientRefusesETH() public payable {
        depositAsStudent(5 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        RejectingRecipient rejector = new RejectingRecipient();
        uint256 reqId = bcs1.createSpendRequest(core, payable(address(rejector)), 1 ether, "Nguoi nhan tu choi");

        // 1. Hai lá phiếu thuận (2/3 >= 51%) vẫn thành công (KHÔNG revert giao dịch vote)
        bcs1.vote(core, reqId, true);
        bcs2.vote(core, reqId, true);
        require(core.hasMemberVoted(reqId, address(bcs2)), "Vote must be recorded even if recipient rejects ETH");

        // 2. Trạng thái đề xuất được giữ ở Ready (không phải Executed)
        (, , , , , , uint256 yesVotes, , ProjectCore.RequestStatus st) = core.getSpendRequest(reqId);
        require(yesVotes == 2, "yesVotes must be recorded");
        require(st == ProjectCore.RequestStatus.Ready, "Status must remain Ready for fallback");

        // 3. Số dư quỹ và tiền giữ chỗ được rollback bảo toàn
        require(core.classFundBalance() == 4.95 ether, "Class fund must remain 4.95 ETH");
        require(core.reservedSpendAmount() == 1 ether, "Reserved spend amount must remain intact");

        // 4. Khi gọi execute thủ công, do rejector vẫn từ chối ETH nên lệnh call thất bại -> Revert ETHTransferFailed
        (bool success, bytes memory returnData) = address(bcs1).call(
            abi.encodeWithSignature("execute(address,uint256)", address(core), reqId)
        );
        require(!success, "Execution to rejecting recipient must revert");
        bytes4 actual;
        assembly { actual := mload(add(returnData, 0x20)) }
        require(actual == bytes4(keccak256("ETHTransferFailed()")), "Must revert ETHTransferFailed()");
    }

    /// @notice Ca F5: Chống Reentrancy khi giải ngân nhờ CEI, đồng thời chặn recipient là BCS tự bỏ phiếu (Mục C)
    /// @dev Có 4 BCS (bcs1, bcs2, bcs3, attackerRecipient) -> voterBase = 3; attacker bị ConflictOfInterest nếu tự vote;
    ///      khi bcs1 + bcs2 vote 2/3, ETH chuyển tới attacker kích hoạt tái nhập vào executeSpendRequest và bị chặn bởi RequestAlreadyExecuted
    function testGroupF5_ReentrancyDuringExecuteIsBlockedByCEI() public payable {
        depositAsStudent(5 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        MaliciousBCSRecipient attackerRecipient = new MaliciousBCSRecipient(payable(address(core)));
        address[] memory aStuds = new address[](1);
        aStuds[0] = address(attackerRecipient);
        core.setStudents(aStuds, true);
        core.setBCSMember(address(attackerRecipient), true); // BCS thứ 4 -> eligible = 4, voterBase = 3

        uint256 reqId = bcs1.createSpendRequest(core, payable(address(attackerRecipient)), 1 ether, "Ke tan cong co quyen BCS");

        // Xác minh xung đột lợi ích: attackerRecipient không thể tự vote cho mình
        (bool sSelf, bytes memory rSelf) = address(attackerRecipient).call(
            abi.encodeWithSignature("vote(uint256,bool)", reqId, true)
        );
        require(!sSelf, "Recipient BCS must be blocked by ConflictOfInterest");
        bytes4 aSelf;
        assembly { aSelf := mload(add(rSelf, 0x20)) }
        require(aSelf == bytes4(keccak256("ConflictOfInterest()")), "Must revert ConflictOfInterest()");

        // bcs1 + bcs2 bỏ phiếu (2/3 >= 51%) -> TỰ THỰC THI -> kích hoạt receive() tái nhập!
        bcs1.vote(core, reqId, true);
        bcs2.vote(core, reqId, true);

        require(attackerRecipient.attackAttempts() == 1, "Attacker must have attempted reentrancy during auto-exec vote");
        require(attackerRecipient.reentrancyBlocked(), "Reentrancy must be blocked by CEI");
        require(
            attackerRecipient.reentrancyRevertSelector() == bytes4(keccak256("RequestAlreadyExecuted(uint256)")),
            "Reentrancy must be blocked specifically by RequestAlreadyExecuted custom error"
        );
        require(core.classFundBalance() == 3.95 ether, "Class fund must decrease only once to 3.95 ETH");
        require(address(attackerRecipient).balance == 1 ether, "Attacker must receive exactly 1 ETH without double spending");
    }

    // ==========================================
    // NHÓM G — TÍNH BẤT BIẾN & KẾ TOÁN (INVARIANTS)
    // ==========================================

    /// @notice Ca G1: Tính bất biến kế toán bảo toàn tuyệt đối qua chuỗi thao tác liên hoàn
    function testGroupG1_AccountingConservationAndIsolation() public payable {
        // 1. Nạp 10 ETH
        depositAsStudent(10 ether);
        require(core.getTotalContractBalance() == core.classFundBalance() + core.adminFeePool(), "Invariant 1: Total balance matches sum of pools");

        // 2. CVHT chuyển 0.05 ETH phí sang Quỹ lớp
        core.moveFeeToClassFund(0.05 ether);
        require(core.getTotalContractBalance() == core.classFundBalance() + core.adminFeePool(), "Invariant 2: Balance conserved after fee moved");

        // 3. BCS tạo đề xuất 4 ETH (cần >= 3 BCS hoạt động)
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);
        uint256 reqId = bcs1.createSpendRequest(core, payable(address(this)), 4 ether, "Ke toan bat bien");
        require(core.classFundBalance() == core.getAvailableClassFund() + core.reservedSpendAmount(), "Invariant 3: Class fund = Available + Reserved");

        // 4. Giải ngân 4 ETH qua 2/3 phiếu thuận (auto-execution)
        bcs1.vote(core, reqId, true);
        bcs2.vote(core, reqId, true);
        require(core.getTotalContractBalance() == core.classFundBalance() + core.adminFeePool(), "Invariant 4: Total balance conserved after spend execution");
        require(core.reservedSpendAmount() == 0, "Invariant 5: Reserved returns to 0 after execution");
    }

    // ==========================================
    // NHÓM H — TỰ ĐỘNG THỰC THI HOÀN TIỀN (AUTO-EXECUTION REFUND & SECTION C)
    // ==========================================

    /// @notice Ca H1: Hoàn tiền tự động thành công khi BCS bỏ phiếu thuận đạt 2/3 (>= 51%), không cần gọi execute riêng
    function testGroupH1_RefundAutoExecutesOnThreshold() public payable {
        depositAsStudent(5 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        // Tạo yêu cầu hoàn 2 ETH
        uint256 refId = student1.createRefund(core, 2 ether, "Hoan tien tu dong");
        require(core.reservedRefundAmount() == 2 ether, "Reserved refund is 2 ETH");

        uint256 balBefore = address(student1).balance;
        // bcs1 & bcs2 bỏ phiếu thuận (2/3 = 66.6% >= 51% -> Tự động hoàn tiền ngay)
        bcs1.voteRefund(core, refId, true);
        bcs2.voteRefund(core, refId, true);
        uint256 balAfter = address(student1).balance;

        require(balAfter - balBefore == 2 ether, "Applicant must receive 2 ETH refund directly from vote tx");
        require(core.reservedRefundAmount() == 0, "Reserved refund cleared to 0");
        require(core.pendingStudentRefundAmount(address(student1)) == 0, "Pending student refund cleared to 0");
        require(core.studentContributions(address(student1)) == 2.95 ether, "Net contributions decreased by 2 ETH from 4.95 to 2.95 ETH");
        require(core.studentTotalDeposited(address(student1)) == 5 ether, "Total deposited remains 5 ETH after refund");
        require(core.classFundBalance() == 2.95 ether, "Class fund decreased by 2 ETH to 2.95 ETH");

        (, , , , , uint256 refYes, , ProjectCore.RequestStatus st) = core.getRefundRequest(refId);
        require(refYes >= 2, "Approved refund must satisfy yesVotes >= 2 invariant");
        require(st == ProjectCore.RequestStatus.Executed, "Refund status must be Executed immediately");

        // Cố gọi executeRefundRequest thủ công sau khi đã auto-execute -> Revert RefundAlreadyExecuted
        (bool sAgain, bytes memory rAgain) = address(student1).call(
            abi.encodeWithSignature("executeRefund(address,uint256)", address(core), refId)
        );
        require(!sAgain, "Subsequent executeRefundRequest must revert RefundAlreadyExecuted");
        bytes4 aAgain;
        assembly { aAgain := mload(add(rAgain, 0x20)) }
        require(aAgain == bytes4(keccak256("RefundAlreadyExecuted(uint256)")), "Must revert RefundAlreadyExecuted");
    }

    /// @notice Ca H2: Sinh viên từ chối nhận ETH thì vote duyệt hoàn tiền vẫn thành công (không revert vote), fallback giữ Ready
    function testGroupH2_RefundRejectingRecipientFallback() public payable {
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        RejectingStudentTestActor rejecter = new RejectingStudentTestActor(payable(address(core)));
        address[] memory rStuds = new address[](1);
        rStuds[0] = address(rejecter);
        core.setStudents(rStuds, true);
        rejecter.fund{value: 5 ether}();

        rejecter.deposit(3 ether);
        uint256 refId = rejecter.createRefund(1 ether, "Rollback test");

        uint256 fundBefore = core.classFundBalance();
        uint256 contribBefore = core.studentContributions(address(rejecter));

        // 2/3 bỏ phiếu thuận. Do rejecter từ chối ETH nên auto-execution thất bại
        // NHƯNG giao dịch vote vẫn THÀNH CÔNG, phiếu bầu được ghi nhận đầy đủ
        bcs1.voteRefund(core, refId, true);
        bcs2.voteRefund(core, refId, true);
        require(core.hasMemberVotedRefund(refId, address(bcs2)), "Vote must be recorded despite transfer failure");

        // Trạng thái giữ nguyên là Ready (chưa Executed) để cho phép thử lại
        (, , , , , , , ProjectCore.RequestStatus st) = core.getRefundRequest(refId);
        require(st == ProjectCore.RequestStatus.Ready, "Refund status must stay Ready for fallback");

        // Kế toán được rollback nguyên vẹn
        require(core.classFundBalance() == fundBefore, "Class fund must remain unchanged");
        require(core.studentContributions(address(rejecter)) == contribBefore, "Student contribution must remain unchanged");
        require(core.reservedRefundAmount() == 1 ether, "Reserved refund must remain intact");

        // Gọi executeRefundRequest thủ công -> Revert ETHTransferFailed()
        (bool sAgain, bytes memory rAgain) = address(core).call(
            abi.encodeWithSignature("executeRefundRequest(uint256)", refId)
        );
        require(!sAgain, "Manual execute must revert when recipient refuses ETH");
        bytes4 aAgain;
        assembly { aAgain := mload(add(rAgain, 0x20)) }
        require(aAgain == bytes4(keccak256("ETHTransferFailed()")), "Must revert ETHTransferFailed");
    }

    /// @notice Ca H3: Đề xuất chi đã đạt ngưỡng Ready thì KHÔNG thể bị dọn dẹp bằng expireSpendRequest
    function testGroupH3_CannotExpireReadySpendRequest() public payable {
        depositAsStudent(5 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        RejectingRecipient rejector = new RejectingRecipient();
        uint256 reqId = bcs1.createSpendRequest(core, payable(address(rejector)), 1 ether, "Ready spend");
        bcs1.vote(core, reqId, true);
        bcs2.vote(core, reqId, true);

        // Đề xuất đang ở Ready. Cố gọi expireSpendRequest -> Bị revert InvalidRequestStatus
        (bool success, bytes memory returnData) = address(core).call(
            abi.encodeWithSignature("expireSpendRequest(uint256)", reqId)
        );
        require(!success, "expireSpendRequest must revert on Ready request");
        bytes4 actual;
        assembly { actual := mload(add(returnData, 0x20)) }
        require(actual == bytes4(keccak256("InvalidRequestStatus(uint256)")), "Must revert InvalidRequestStatus");
    }

    /// @notice Ca H4: Yêu cầu hoàn tiền đã đạt ngưỡng Ready thì KHÔNG thể bị dọn dẹp bằng expireRefundRequest
    function testGroupH4_CannotExpireReadyRefundRequest() public payable {
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        RejectingStudentTestActor rejecter = new RejectingStudentTestActor(payable(address(core)));
        address[] memory rStuds = new address[](1);
        rStuds[0] = address(rejecter);
        core.setStudents(rStuds, true);
        rejecter.fund{value: 5 ether}();

        rejecter.deposit(3 ether);
        uint256 refId = rejecter.createRefund(1 ether, "Ready refund");
        bcs1.voteRefund(core, refId, true);
        bcs2.voteRefund(core, refId, true);

        // Yêu cầu đang ở Ready. Cố gọi expireRefundRequest -> Bị revert InvalidRefundStatus
        (bool success, bytes memory returnData) = address(core).call(
            abi.encodeWithSignature("expireRefundRequest(uint256)", refId)
        );
        require(!success, "expireRefundRequest must revert on Ready refund");
        bytes4 actual;
        assembly { actual := mload(add(returnData, 0x20)) }
        require(actual == bytes4(keccak256("InvalidRefundStatus(uint256)")), "Must revert InvalidRefundStatus");
    }

    /// @notice Ca H5 (Phase 1 / Nhóm A): Hoàn toàn bộ 99% net đưa hạn mức về 0 nhưng vẫn giữ studentTotalDeposited; chặn hoàn quá net
    function testGroupH5_SectionA_FullNetRefundAndCrossStudentDrainBlocked() public payable {
        depositAsStudent(10 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        // Nộp thêm từ RejectingStudentTestActor (chỉ dùng như ví thứ 2) 10 ETH -> classFundBalance = 19.8 ETH
        RejectingStudentTestActor student2 = new RejectingStudentTestActor(payable(address(core)));
        address[] memory s2Studs = new address[](1);
        s2Studs[0] = address(student2);
        core.setStudents(s2Studs, true);
        student2.fund{value: 10 ether}();
        student2.deposit(10 ether);

        require(core.classFundBalance() == 19.8 ether, "Total net class fund must be 19.8 ETH");
        require(core.studentContributions(address(student1)) == 9.9 ether, "This net contribution limit must be 9.9 ETH");
        require(core.studentTotalDeposited(address(student1)) == 10 ether, "This total deposited must be 10 ETH");
        require(core.getStudentMaxRefund(address(student1)) == 9.9 ether, "Max refund must be 9.9 ETH");

        // Cố đòi 10 ETH (rút lấn 0.1 ETH từ người khác) -> Revert InsufficientContribution
        (bool sOver, bytes memory rOver) = address(student1).call(
            abi.encodeWithSignature("createRefund(address,uint256,string)", address(core), 10 ether, "Cross student drain")
        );
        require(!sOver, "Claiming 10 ETH gross must revert");
        bytes4 selOver;
        assembly { selOver := mload(add(rOver, 0x20)) }
        require(selOver == bytes4(keccak256("InsufficientContribution(uint256,uint256)")), "Must revert InsufficientContribution");

        // Hoàn đúng 9.9 ETH net (2/3 auto-exec) -> studentContributions về 0, studentTotalDeposited vẫn = 10 ETH
        uint256 refId = student1.createRefund(core, 9.9 ether, "Hoan full 9.9 ETH");
        bcs1.voteRefund(core, refId, true);
        bcs2.voteRefund(core, refId, true);

        require(core.studentContributions(address(student1)) == 0, "Net contribution after full refund must be 0");
        require(core.studentTotalDeposited(address(student1)) == 10 ether, "Total deposited must remain 10 ETH");
        require(core.getStudentMaxRefund(address(student1)) == 0, "Max refund must be 0 after full net refund");
        require(core.classFundBalance() == 9.9 ether, "Class fund preserves student2 9.9 ETH intact");
    }

    /// @notice Ca H6 (Phase 2 / Mục C - Gian lận): BCS tự xin hoàn tiền: voterBase = 2, tự vote revert ConflictOfInterest(), cần 2 phiếu còn lại
    function testGroupH6_SectionC_BCSSelfRefundConflictOfInterest() public payable {
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        bcs1.depositToCore{value: 5 ether}(core);
        uint256 refId = bcs1.createRefundRequest(core, 2 ether, "BCS1 tu xin hoan");

        (, , , , , , , , uint256 vb) = core.refundRequests(refId);
        require(vb == 2, "voterBase must be eligible - 1 (2) when applicant is eligible BCS");

        // Gian lận: bcs1 tự bỏ phiếu thuận cho đơn hoàn tiền của mình -> ConflictOfInterest()
        (bool sSelf, bytes memory rSelf) = address(bcs1).call(
            abi.encodeWithSignature("voteRefund(address,uint256,bool)", address(core), refId, true)
        );
        require(!sSelf, "BCS applicant voting on own refund must revert ConflictOfInterest");
        bytes4 aSelf;
        assembly { aSelf := mload(add(rSelf, 0x20)) }
        require(aSelf == bytes4(keccak256("ConflictOfInterest()")), "Must revert ConflictOfInterest()");

        // bcs2 vote -> 1/2 = 50% < 51% -> Pending
        bcs2.voteRefund(core, refId, true);
        (, , , , , uint256 y1, , ProjectCore.RequestStatus st1) = core.getRefundRequest(refId);
        require(y1 == 1 && st1 == ProjectCore.RequestStatus.Pending, "1/2 must remain Pending");

        // bcs3 vote -> 2/2 = 100% -> Executed (yesVotes == 2)
        uint256 balBefore = address(bcs1).balance;
        bcs3.voteRefund(core, refId, true);
        uint256 balAfter = address(bcs1).balance;
        (, , , , , uint256 y2, , ProjectCore.RequestStatus st2) = core.getRefundRequest(refId);
        require(y2 == 2 && st2 == ProjectCore.RequestStatus.Executed, "2/2 remaining BCS votes execute refund");
        require(balAfter - balBefore == 2 ether, "bcs1 must receive 2 ETH refund");
    }

    /// @notice Ca H7 (Phase 2 / Mục C): Recipient là BCS bị chặn ConflictOfInterest() với voterBase = 2; Recipient không phải BCS giữ voterBase = 3
    function testGroupH7_SectionC_SpendBCSRecipientConflictVsNonBCSRecipient() public payable {
        depositAsStudent(10 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        // Trường hợp 1: recipient là BCS (bcs3) -> voterBase = 2, bcs3 bị ConflictOfInterest()
        uint256 reqBcsId = bcs1.createSpendRequest(core, payable(address(bcs3)), 1 ether, "Hoan phi cho bcs3");
        (, , , , , , , , , uint256 vbBcs) = core.spendRequests(reqBcsId);
        require(vbBcs == 2, "voterBase must equal eligible - 1 when recipient is eligible BCS");

        (bool sSelfVote, bytes memory rSelfVote) = address(bcs3).call(
            abi.encodeWithSignature("vote(address,uint256,bool)", address(core), reqBcsId, true)
        );
        require(!sSelfVote, "BCS recipient voting on own spend request must revert ConflictOfInterest");
        bytes4 aSelfVote;
        assembly { aSelfVote := mload(add(rSelfVote, 0x20)) }
        require(aSelfVote == bytes4(keccak256("ConflictOfInterest()")), "Must revert ConflictOfInterest()");

        bcs1.vote(core, reqBcsId, true); // 1/2 = 50% < 51% -> Pending
        (, , , , , , uint256 yesMid, , ProjectCore.RequestStatus stMid) = core.getSpendRequest(reqBcsId);
        require(yesMid == 1 && stMid == ProjectCore.RequestStatus.Pending, "1/2 votes must remain Pending");

        bcs2.vote(core, reqBcsId, true); // 2/2 = 100% -> Executed (yesVotes == 2)
        (, , , , , , uint256 yesEnd, , ProjectCore.RequestStatus stEnd) = core.getSpendRequest(reqBcsId);
        require(yesEnd == 2 && stEnd == ProjectCore.RequestStatus.Executed, "Approved spend must have yesVotes >= 2");

        // Trường hợp 2: recipient KHÔNG phải BCS -> voterBase = 3, mọi BCS (gồm cả creator bcs1) vote bình thường
        uint256 reqNonBcsId = bcs1.createSpendRequest(core, payable(address(this)), 1 ether, "Nha cung cap ngoai");
        (, , , , , , , , , uint256 vbNonBcs) = core.spendRequests(reqNonBcsId);
        require(vbNonBcs == 3, "voterBase must remain 3 for non-BCS recipient");
        bcs1.vote(core, reqNonBcsId, true);
        bcs2.vote(core, reqNonBcsId, true);
        (, , , , , , uint256 yesExt, , ProjectCore.RequestStatus stExt) = core.getSpendRequest(reqNonBcsId);
        require(yesExt == 2 && stExt == ProjectCore.RequestStatus.Executed, "Non-BCS spend must execute with 2/3 votes");
    }

    // ==========================================
    // NHÓM I — PHASE 3 (MỤC D): DANH SÁCH SINH VIÊN ON-CHAIN & CAM KẾT ROSTER HASH
    // ==========================================

    /// @notice Ca I1: Người ngoài và Cố vấn không thể nạp qua deposit() hoặc direct transfer -> Revert NotEnrolledStudent
    function testGroupI1_StrangerAndAdvisorCannotDeposit() public payable {
        // Cố vấn học tập (address(this)) gọi deposit -> Revert NotEnrolledStudent
        (bool sAdv, bytes memory rAdv) = address(core).call{value: 1 ether}(
            abi.encodeWithSignature("deposit()")
        );
        require(!sAdv, "Advisor deposit must revert NotEnrolledStudent");
        bytes4 aAdv;
        assembly { aAdv := mload(add(rAdv, 0x20)) }
        require(aAdv == bytes4(keccak256("NotEnrolledStudent(address)")), "Must revert NotEnrolledStudent");

        // Người ngoài (outsider) gọi deposit -> Revert NotEnrolledStudent
        (bool sOut, bytes memory rOut) = address(core).call{value: 1 ether}(
            abi.encodeWithSignature("deposit()")
        );
        require(!sOut, "Outsider deposit must revert NotEnrolledStudent");
        bytes4 aOut;
        assembly { aOut := mload(add(rOut, 0x20)) }
        require(aOut == bytes4(keccak256("NotEnrolledStudent(address)")), "Must revert NotEnrolledStudent");
    }

    /// @notice Ca I2: Cố vấn học tập không thể tự ghi danh làm sinh viên -> Revert AdvisorCannotBeStudent
    function testGroupI2_AdvisorCannotBeStudent() public {
        address[] memory advArr = new address[](1);
        advArr[0] = address(this);
        (bool success, bytes memory returnData) = address(core).call(
            abi.encodeWithSignature("setStudents(address[],bool)", advArr, true)
        );
        require(!success, "Advisor enrolling self as student must revert");
        bytes4 actual;
        assembly { actual := mload(add(returnData, 0x20)) }
        require(actual == bytes4(keccak256("AdvisorCannotBeStudent()")), "Must revert AdvisorCannotBeStudent()");
    }

    /// @notice Ca I3: Không thể cấp quyền BCS cho người chưa là sinh viên -> Revert BCSMustBeEnrolledStudent
    function testGroupI3_BCSMustBeStudent() public {
        address nonStudent = address(0x9991);
        (bool success, bytes memory returnData) = address(core).call(
            abi.encodeWithSignature("setBCSMember(address,bool)", nonStudent, true)
        );
        require(!success, "Non-student cannot become BCS");
        bytes4 actual;
        assembly { actual := mload(add(returnData, 0x20)) }
        require(actual == bytes4(keccak256("BCSMustBeEnrolledStudent()")), "Must revert BCSMustBeEnrolledStudent()");
    }

    /// @notice Ca I4: Không thể xóa sinh viên nếu sinh viên đó đang là BCS -> Revert StudentIsBCS
    function testGroupI4_CannotRemoveStudentIfActiveBCS() public {
        // bcs1 đang là sinh viên và là BCS
        address[] memory arr = new address[](1);
        arr[0] = address(bcs1);
        core.setBCSMember(address(bcs1), true);

        (bool success, bytes memory returnData) = address(core).call(
            abi.encodeWithSignature("setStudents(address[],bool)", arr, false)
        );
        require(!success, "Cannot remove student who is active BCS");
        bytes4 actual;
        assembly { actual := mload(add(returnData, 0x20)) }
        require(actual == bytes4(keccak256("StudentIsBCS()")), "Must revert StudentIsBCS()");
    }

    /// @notice Ca I5: Sinh viên bị xóa khỏi danh sách vẫn tạo và nhận hoàn tiền thành công nếu còn studentContributions > 0
    function testGroupI5_RemovedStudentCanRefund() public payable {
        depositAsStudent(5 ether);
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        // Gỡ student1 khỏi danh sách sinh viên
        address[] memory remArr = new address[](1);
        remArr[0] = address(student1);
        core.setStudents(remArr, false);
        require(!core.isStudent(address(student1)), "student1 must be unenrolled");

        // student1 vẫn tạo được yêu cầu hoàn tiền và nhận auto-execution
        uint256 refId = student1.createRefund(core, 2 ether, "Hoan tien sau thoi hoc");
        uint256 balBefore = address(student1).balance;
        bcs1.voteRefund(core, refId, true);
        bcs2.voteRefund(core, refId, true);
        uint256 balAfter = address(student1).balance;

        require(balAfter - balBefore == 2 ether, "Must receive 2 ETH refund");
        require(core.studentContributions(address(student1)) == 2.95 ether, "Remaining net 2.95 ETH");
    }

    /// @notice Ca I6: Cam kết Roster Hash chỉ dành cho Cố vấn học tập
    function testGroupI6_CommitRosterHash() public {
        bytes32 sampleHash = keccak256("CANONICAL_ROSTER_V1");
        core.commitRoster(sampleHash);
        require(core.rosterHash() == sampleHash, "Roster hash must match");
    }

    /// @notice Ca I7: Bất biến số dư và getUnaccountedBalance() khi có tiền nộp hợp lệ
    function testGroupI7_UnaccountedBalanceInvariant() public payable {
        depositAsStudent(10 ether);
        require(core.getUnaccountedBalance() == 0, "No unaccounted balance initially");
        require(core.getTotalContractBalance() == core.classFundBalance() + core.adminFeePool(), "Balance invariant holds");
    }

    // ==========================================
    // NHÓM J: PHASE 4 (MỤC E) — ĐỢT THU NỘP QUỸ TRÊN CHUỖI
    // ==========================================

    /// @notice Ca J1: BCS active tạo đợt thu hợp lệ, expectedPayers = enrolledCount
    function testGroupJ1_CreateCollectionAndValidation() public {
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        uint64 deadline = uint64(block.timestamp + 7 days);
        uint256 cid = bcs1.createCollection(core, 1 ether, deadline, "Dot thu hoc ky 1");
        require(cid == 1, "First collection ID must be 1");
        require(core.collectionCount() == 1, "collectionCount must be 1");
        require(core.activeCollectionId() == 1, "activeCollectionId must be 1");
        require(core.getActiveCollectionId() == 1, "getActiveCollectionId must be 1");

        (
            uint256 id,
            uint256 targetWei,
            uint64 dline,
            string memory purpose,
            address creator,
            ,
            bool closed,
            ,
            uint256 expectedPayers,
            uint256 paidCount
        ) = core.collections(cid);

        require(id == 1, "ID match");
        require(targetWei == 1 ether, "Target match");
        require(dline == deadline, "Deadline match");
        require(keccak256(bytes(purpose)) == keccak256(bytes("Dot thu hoc ky 1")), "Purpose match");
        require(creator == address(bcs1), "Creator match");
        require(!closed, "Must be open");
        require(expectedPayers == core.enrolledCount(), "expectedPayers must equal enrolledCount");
        require(paidCount == 0, "paidCount starts at 0");
    }

    /// @notice Ca J2: Chỉ 1 đợt thu mở tại 1 thời điểm; đóng đợt cũ mới được tạo đợt mới
    function testGroupJ2_OnlyOneCollectionOpenAtATime() public {
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        uint64 deadline = uint64(block.timestamp + 7 days);
        uint256 cid1 = bcs1.createCollection(core, 1 ether, deadline, "Dot 1");

        // Cố tạo đợt 2 khi đợt 1 chưa đóng -> Revert CollectionStillOpen
        (bool s1, ) = address(bcs2).call(
            abi.encodeWithSignature(
                "createCollection(address,uint256,uint64,string)",
                address(core),
                2 ether,
                deadline + 1000,
                "Dot 2 bat hop phap"
            )
        );
        require(!s1, "Cannot create second collection while first is open");

        // Đóng đợt 1
        bcs1.closeCollection(core, cid1, "Hoan thanh dot 1");
        require(core.activeCollectionId() == 0, "activeCollectionId must be 0 after close");

        // Giờ có thể tạo đợt 2
        uint256 cid2 = bcs2.createCollection(core, 2 ether, deadline + 2000, "Dot 2 hop le");
        require(cid2 == 2, "Second collection ID must be 2");
        require(core.activeCollectionId() == 2, "activeCollectionId must be 2");
    }

    /// @notice Ca J3: Nạp tiền vào đợt thu theo ngưỡng targetWei và tăng paidCount đúng 1 lần
    function testGroupJ3_DepositToCollectionThresholds() public payable {
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        uint64 deadline = uint64(block.timestamp + 7 days);
        uint256 cid = bcs1.createCollection(core, 1 ether, deadline, "Dot thu hoc ky");

        // Nạp từng phần: 0.4 ETH -> chưa đạt
        student1.depositToCollection{value: 0.4 ether}(core, cid);
        require(!core.hasPaidInCollection(cid, address(student1)), "Not paid yet");
        require(core.paidInCollection(cid, address(student1)) == 0.4 ether, "Paid 0.4 ETH");

        // Nạp tiếp 0.6 ETH -> đạt 1.0 ETH
        student1.depositToCollection{value: 0.6 ether}(core, cid);
        require(core.hasPaidInCollection(cid, address(student1)), "Must be marked paid");
        require(core.paidInCollection(cid, address(student1)) == 1.0 ether, "Paid 1.0 ETH");
        (, , , , , , , , , uint256 paidCount1) = core.collections(cid);
        require(paidCount1 == 1, "paidCount must be 1");

        // Nạp thêm 0.5 ETH -> paidCount không tăng thêm
        student1.depositToCollection{value: 0.5 ether}(core, cid);
        require(core.paidInCollection(cid, address(student1)) == 1.5 ether, "Paid 1.5 ETH");
        (, , , , , , , , , uint256 paidCount2) = core.collections(cid);
        require(paidCount2 == 1, "paidCount remains 1");
    }

    /// @notice Ca J4: Nạp vào đợt thu đã đóng bị revert CollectionIsClosed
    function testGroupJ4_DepositToClosedCollectionReverts() public payable {
        core.setBCSMember(address(bcs1), true);
        core.setBCSMember(address(bcs2), true);
        core.setBCSMember(address(bcs3), true);

        uint64 deadline = uint64(block.timestamp + 7 days);
        uint256 cid = bcs1.createCollection(core, 1 ether, deadline, "Dot thu dong");
        bcs1.closeCollection(core, cid, "Dong som");

        (bool success, bytes memory returnData) = address(student1).call{value: 1 ether}(
            abi.encodeWithSignature("depositToCollection(address,uint256)", address(core), cid)
        );
        require(!success, "Deposit to closed collection must revert");
        bytes4 actual;
        assembly { actual := mload(add(returnData, 0x20)) }
        require(actual == bytes4(keccak256("CollectionIsClosed(uint256)")), "Must revert CollectionIsClosed");
    }

    /// @notice Ca J5 (Gian lận): Người ngoài hoặc Cố vấn gọi createCollection/closeCollection bị từ chối
    function testGroupJ5_NonBCSCannotCreateOrCloseCollection() public {
        uint64 deadline = uint64(block.timestamp + 7 days);

        // Advisor gọi createCollection -> Revert NotActiveBCS
        (bool sAdv, ) = address(core).call(
            abi.encodeWithSignature("createCollection(uint256,uint64,string)", 1 ether, deadline, "Advisor hack")
        );
        require(!sAdv, "Advisor cannot create collection");

        // Người ngoài gọi createCollection -> Revert NotActiveBCS
        (bool sOut, ) = address(outsider).call(
            abi.encodeWithSignature(
                "createCollection(address,uint256,uint64,string)",
                address(core),
                1 ether,
                deadline,
                "Outsider hack"
            )
        );
        require(!sOut, "Outsider cannot create collection");
    }
}

