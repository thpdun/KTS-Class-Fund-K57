// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title ProjectCore - Hệ thống Quản lý Quỹ lớp KTS-Class-Fund
/// @notice Hợp đồng thông minh quản lý quỹ lớp phi tập trung cho sinh viên ngành Kinh tế Số (v0.1)
/// @dev Triển khai các quy tắc kinh tế R1, R2, R3, R4, R5, R6, R11 tuân thủ docs/SPEC.md và AGENTS.md
contract ProjectCore {
    // ==========================================
    // ENUMS & STRUCTS (CẤU TRÚC DỮ LIỆU)
    // ==========================================

    /// @notice Trạng thái vòng đời của một yêu cầu chi tiêu
    enum RequestStatus {
        Pending,   // Đang chờ Ban cán sự biểu quyết
        Ready,     // Đã đạt tối thiểu 51% phiếu thuận, sẵn sàng thực thi giải ngân
        Executed,  // Đã giải ngân thành công
        Rejected,  // Bị bác bỏ
        Expired,   // Đã quá hạn 7 ngày mà không đạt đủ 51% phiếu
        Cancelled  // Bị hủy
    }

    /// @notice Cấu trúc thông tin của một đề xuất chi tiêu quỹ lớp (R3)
    struct SpendRequest {
        uint256 id;                 // Mã định danh duy nhất của đề xuất
        address payable recipient;  // Địa chỉ ví người thụ hưởng nhận tiền giải ngân
        uint256 amount;             // Số tiền đề xuất chi (wei)
        string description;         // Nội dung, mục đích chi tiêu
        address creator;            // Thành viên BCS tạo đề xuất
        uint256 createdAt;          // Thời điểm tạo đề xuất (block.timestamp)
        uint256 yesVotes;           // Số phiếu thuận
        uint256 noVotes;            // Số phiếu chống
        RequestStatus status;       // Trạng thái hiện tại của đề xuất
    }

    // ==========================================
    // HẰNG SỐ CẤU HÌNH KINH TẾ (BASIS POINTS)
    // ==========================================

    /// @notice Tỷ lệ phí dịch vụ vận hành theo basis points (1% = 100 bps) (R2)
    uint256 public constant FEE_BPS = 100;

    /// @notice Mẫu số chuẩn cho basis points (100% = 10,000 bps)
    uint256 public constant BPS_DENOMINATOR = 10_000;

    /// @notice Ngưỡng biểu quyết thông qua tối thiểu theo basis points (51% = 5,100 bps) (R4, R5)
    uint256 public constant PASSING_THRESHOLD_BPS = 5_100;

    /// @notice Thời hạn hiệu lực tối đa để biểu quyết đề xuất chi (7 ngày) (R5)
    uint256 public constant VOTING_PERIOD = 7 days;

    // ==========================================
    // BIẾN TRẠNG THÁI (STATE VARIABLES)
    // ==========================================

    /// @notice Địa chỉ Cố vấn học tập (CVHT / Owner) - người khởi tạo hợp đồng (R1)
    address public immutable advisor;

    /// @notice Số dư khả dụng của Quỹ lớp chính (sau khi trích 1% phí dịch vụ vận hành)
    uint256 public classFundBalance;

    /// @notice Số dư Quỹ dịch vụ vận hành (1% trích từ tiền nạp) để CVHT bù đắp chi phí Gas (R2, R11)
    uint256 public adminFeePool;

    /// @notice Tổng số tiền đang được giữ chỗ cho các đề xuất chi đang chờ/sẵn sàng thực thi
    uint256 public reservedSpendAmount;

    /// @notice Bảng theo dõi tổng số tiền tích lũy từng sinh viên đã đóng góp (100% tiền gốc)
    mapping(address => uint256) public studentContributions;

    /// @notice Bảng theo dõi tư cách thành viên Ban cán sự (BCS) (R1)
    mapping(address => bool) public isBCSMember;

    /// @notice Tổng số lượng thành viên Ban cán sự đang hoạt động tại thời điểm hiện hành
    uint256 public activeBCSCount;

    /// @notice Tổng số đề xuất chi đã được tạo trong hợp đồng
    uint256 public spendRequestCount;

    /// @notice Bảng lưu trữ thông tin các đề xuất chi tiêu theo mã định danh (requestId)
    mapping(uint256 => SpendRequest) public spendRequests;

    /// @notice Bảng ghi nhận trạng thái đã bỏ phiếu của thành viên BCS cho từng đề xuất (requestId => member => bool) (R4)
    mapping(uint256 => mapping(address => bool)) public hasVoted;

    // ==========================================
    // SỰ KIỆN (EVENTS)
    // ==========================================

    /// @notice Phát ra khi cập nhật tư cách thành viên Ban cán sự (R1)
    event BCSMemberUpdated(address indexed member, bool status);

    /// @notice Phát ra khi sinh viên nạp tiền vào quỹ thành công (R2)
    event FundDeposited(address indexed student, uint256 amount);

    /// @notice Phát ra khi trích phí dịch vụ vận hành vào adminFeePool (R2)
    event AdminFeeCollected(address indexed student, uint256 feeAmount);

    /// @notice Phát ra khi Cố vấn học tập rút phí dịch vụ vận hành (R11)
    event AdminFeeWithdrawn(address indexed advisor, uint256 amount);

    /// @notice Phát ra khi thành viên BCS tạo mới một đề xuất chi tiêu (R3)
    event SpendRequestCreated(
        uint256 indexed requestId,
        address indexed creator,
        address indexed recipient,
        uint256 amount,
        string description,
        uint256 createdAt
    );

    /// @notice Phát ra khi một thành viên BCS bỏ phiếu cho đề xuất chi (R4)
    event SpendRequestVoted(
        uint256 indexed requestId,
        address indexed voter,
        bool support,
        uint256 yesVotes,
        uint256 noVotes
    );

    /// @notice Phát ra khi đề xuất chi đạt đủ 51% phiếu và chuyển sang trạng thái Sẵn sàng thực thi (R4)
    event SpendRequestReady(uint256 indexed requestId);

    /// @notice Phát ra khi đề xuất chi được thực thi giải ngân thành công (R6)
    event SpendRequestExecuted(uint256 indexed requestId, address indexed recipient, uint256 amount);

    /// @notice Phát ra khi đề xuất chi bị đánh dấu hết hạn sau 7 ngày mà chưa đạt đủ 51% (R5, R9)
    event SpendRequestExpired(uint256 indexed requestId);

    // ==========================================
    // LỖI TÙY BIẾN (CUSTOM ERRORS)
    // ==========================================

    /// @notice Người gọi không phải là Cố vấn học tập
    error NotAdvisor();

    /// @notice Người gọi không phải là thành viên Ban cán sự đang hoạt động
    error NotActiveBCS();

    /// @notice Địa chỉ cung cấp không hợp lệ (ví dụ: địa chỉ zero)
    error InvalidAddress();

    /// @notice Số tiền giao dịch phải lớn hơn 0
    error ZeroAmount();

    /// @notice Số tiền rút phí vượt quá số dư Quỹ dịch vụ vận hành hiện có
    error InsufficientAdminFee(uint256 requested, uint256 available);

    /// @notice Số tiền đề xuất vượt quá số dư khả dụng thực tế của Quỹ lớp chính
    error InsufficientAvailableFund(uint256 requested, uint256 available);

    /// @notice Số dư Quỹ lớp chính không đủ để thực hiện giải ngân
    error InsufficientFund(uint256 requested, uint256 available);

    /// @notice Không tìm thấy đề xuất chi tiêu với mã định danh được cung cấp
    error RequestNotFound(uint256 requestId);

    /// @notice Đề xuất chi tiêu đã được thực thi giải ngân trước đó
    error RequestAlreadyExecuted(uint256 requestId);

    /// @notice Đề xuất chi tiêu đã hết hạn (quá 7 ngày và chưa đạt 51%)
    error RequestExpired(uint256 requestId);

    /// @notice Trạng thái của đề xuất không hợp lệ cho thao tác yêu cầu
    error InvalidRequestStatus(uint256 requestId);

    /// @notice Thành viên Ban cán sự đã bỏ phiếu cho đề xuất này trước đó
    error AlreadyVoted(uint256 requestId, address voter);

    /// @notice Thời hạn bỏ phiếu 7 ngày đã kết thúc
    error VotingPeriodEnded(uint256 requestId);

    /// @notice Thời hạn bỏ phiếu 7 ngày vẫn còn hiệu lực, chưa thể đánh dấu hết hạn
    error VotingStillActive(uint256 requestId);

    /// @notice Không có thành viên Ban cán sự nào đang hoạt động để làm mẫu số biểu quyết
    error NoActiveBCS();

    /// @notice Đề xuất chi chưa đạt ngưỡng đồng thuận tối thiểu 51% trên tổng số BCS
    error ThresholdNotMet(uint256 yesVotes, uint256 activeBCSCount);

    /// @notice Lệnh chuyển ETH bằng low-level call thất bại
    error ETHTransferFailed();

    // ==========================================
    // MODIFIERS (BỘ ĐIỀU CHỈNH QUYỀN)
    // ==========================================

    /// @notice Chỉ cho phép Cố vấn học tập (CVHT / Owner) thực thi (R1)
    modifier onlyAdvisor() {
        if (msg.sender != advisor) {
            revert NotAdvisor();
        }
        _;
    }

    /// @notice Chỉ cho phép thành viên Ban cán sự đang hoạt động thực thi (R3, R4, R6)
    modifier onlyActiveBCS() {
        if (!isBCSMember[msg.sender]) {
            revert NotActiveBCS();
        }
        _;
    }

    // ==========================================
    // KHỞI TẠO (CONSTRUCTOR)
    // ==========================================

    /// @notice Khởi tạo hợp đồng và gán quyền Cố vấn học tập cho người triển khai
    constructor() {
        advisor = msg.sender;
    }

    // ==========================================
    // R1: QUẢN TRỊ NHÂN SỰ BAN CÁN SỰ (CVHT)
    // ==========================================

    /// @notice Thêm mới, kích hoạt hoặc vô hiệu hóa tư cách thành viên Ban cán sự (R1)
    /// @dev Chỉ Cố vấn học tập mới có quyền gọi hàm này
    /// @param member Địa chỉ ví của thành viên Ban cán sự
    /// @param status Trạng thái hoạt động (true: kích hoạt, false: vô hiệu hóa)
    function setBCSMember(address member, bool status) external onlyAdvisor {
        if (member == address(0)) {
            revert InvalidAddress();
        }

        bool currentStatus = isBCSMember[member];
        if (currentStatus == status) {
            return; // Trạng thái không đổi, không cập nhật để tiết kiệm gas
        }

        // Cập nhật trạng thái và số lượng BCS hoạt động
        isBCSMember[member] = status;
        if (status) {
            activeBCSCount++;
        } else {
            activeBCSCount--;
        }

        emit BCSMemberUpdated(member, status);
    }

    // ==========================================
    // R2: NẠP TIỀN VÀO QUỸ (DEPOSIT & RECEIVE)
    // ==========================================

    /// @notice Hàm cho phép bất kỳ sinh viên nào nạp ETH vào quỹ lớp qua DApp (R2)
    /// @dev Áp dụng mô hình Checks - Effects - Interactions (CEI)
    function deposit() external payable {
        _processDeposit(msg.sender, msg.value);
    }

    /// @notice Tự động tiếp nhận và ghi nhận khi sinh viên chuyển ETH trực tiếp từ ví cá nhân (R2)
    /// @dev Áp dụng mô hình Checks - Effects - Interactions (CEI)
    receive() external payable {
        _processDeposit(msg.sender, msg.value);
    }

    /// @notice Hàm xử lý nội bộ dùng chung cho cả deposit() và receive()
    /// @dev Đảm bảo kiểm tra và phân bổ tiền nhất quán, tránh trùng lặp mã nguồn
    /// @param sender Địa chỉ người gửi ETH
    /// @param amount Số lượng ETH gửi kèm giao dịch (wei)
    function _processDeposit(address sender, uint256 amount) internal {
        // 1. Checks: Từ chối giao dịch nếu số tiền nạp bằng 0
        if (amount == 0) {
            revert ZeroAmount();
        }

        // 2. Tính toán phân bổ số nguyên theo basis points (R2)
        // adminFee = amount * 100 / 10,000 (1%)
        // classFundAmount = amount - adminFee (99% và bảo toàn toàn bộ sai số làm tròn số nguyên)
        uint256 adminFee = (amount * FEE_BPS) / BPS_DENOMINATOR;
        uint256 classFundAmount = amount - adminFee;

        // 3. Effects: Cập nhật các biến trạng thái
        studentContributions[sender] += amount;
        classFundBalance += classFundAmount;
        adminFeePool += adminFee;

        // 4. Phát sự kiện lưu vết on-chain theo quy ước AGENTS.md
        emit FundDeposited(sender, amount);
        emit AdminFeeCollected(sender, adminFee);

        // 5. Interactions: ETH đã được tiếp nhận qua từ khóa payable, không gọi ngoại vi
    }

    // ==========================================
    // R11: RÚT PHÍ DỊCH VỤ VẬN HÀNH (CVHT)
    // ==========================================

    /// @notice Cố vấn học tập rút tiền từ Quỹ dịch vụ vận hành (adminFeePool) để bù đắp chi phí Gas (R11)
    /// @dev Áp dụng nghiêm ngặt nguyên tắc Checks - Effects - Interactions (CEI)
    /// @param amount Số lượng ETH muốn rút (wei)
    function withdrawAdminFee(uint256 amount) external onlyAdvisor {
        // 1. Checks
        if (amount == 0) {
            revert ZeroAmount();
        }
        if (amount > adminFeePool) {
            revert InsufficientAdminFee(amount, adminFeePool);
        }

        // 2. Effects: Cập nhật số dư trước khi chuyển tiền
        adminFeePool -= amount;
        emit AdminFeeWithdrawn(advisor, amount);

        // 3. Interactions: Chuyển ETH về ví của Cố vấn học tập bằng .call
        (bool success, ) = advisor.call{value: amount}("");
        if (!success) {
            revert ETHTransferFailed();
        }
    }

    // ==========================================
    // R3: TẠO ĐỀ XUẤT CHI TIÊU (BCS)
    // ==========================================

    /// @notice Thành viên Ban cán sự tạo đề xuất chi tiêu từ Quỹ lớp chính (R3)
    /// @dev Số tiền đề xuất chi không được vượt quá số dư khả dụng thực tế (sau khi trừ các khoản đã giữ chỗ)
    /// @param recipient Địa chỉ ví thụ hưởng nhận tiền giải ngân
    /// @param amount Số lượng ETH đề xuất chi (wei)
    /// @param description Nội dung, mục đích chi tiêu
    /// @return requestId Mã định danh duy nhất của đề xuất vừa tạo
    function createSpendRequest(
        address payable recipient,
        uint256 amount,
        string calldata description
    ) external onlyActiveBCS returns (uint256 requestId) {
        // 1. Checks
        if (recipient == address(0)) {
            revert InvalidAddress();
        }
        if (amount == 0) {
            revert ZeroAmount();
        }

        uint256 availableFund = getAvailableClassFund();
        if (amount > availableFund) {
            revert InsufficientAvailableFund(amount, availableFund);
        }

        // 2. Effects: Khởi tạo đề xuất và giữ chỗ số dư
        requestId = ++spendRequestCount;
        reservedSpendAmount += amount;

        spendRequests[requestId] = SpendRequest({
            id: requestId,
            recipient: recipient,
            amount: amount,
            description: description,
            creator: msg.sender,
            createdAt: block.timestamp,
            yesVotes: 0,
            noVotes: 0,
            status: RequestStatus.Pending
        });

        emit SpendRequestCreated(
            requestId,
            msg.sender,
            recipient,
            amount,
            description,
            block.timestamp
        );
    }

    // ==========================================
    // R4 & R5: BỎ PHIẾU ĐỀ XUẤT CHI TIÊU (BCS)
    // ==========================================

    /// @notice Thành viên Ban cán sự bỏ phiếu cho một đề xuất chi tiêu (R4, R5)
    /// @dev Mỗi thành viên chỉ bỏ phiếu 1 lần; tự động chuyển sang Ready khi đạt >= 51% trên tổng số BCS
    /// @param requestId Mã định danh của đề xuất cần bỏ phiếu
    /// @param support true nếu đồng ý, false nếu không đồng ý
    function voteSpendRequest(uint256 requestId, bool support) external onlyActiveBCS {
        // 1. Checks: Kiểm tra đề xuất tồn tại
        if (requestId == 0 || requestId > spendRequestCount) {
            revert RequestNotFound(requestId);
        }

        SpendRequest storage req = spendRequests[requestId];

        // Kiểm tra trạng thái đề xuất
        if (req.status == RequestStatus.Executed) {
            revert RequestAlreadyExecuted(requestId);
        }
        if (req.status == RequestStatus.Expired) {
            revert RequestExpired(requestId);
        }
        if (req.status != RequestStatus.Pending && req.status != RequestStatus.Ready) {
            revert InvalidRequestStatus(requestId);
        }

        // Kiểm tra thời hạn biểu quyết 7 ngày
        if (block.timestamp > req.createdAt + VOTING_PERIOD) {
            // Quá hạn 7 ngày: Nếu chưa từng đạt Ready thì chuyển sang Expired và hoàn lại số tiền giữ chỗ
            if (req.status == RequestStatus.Pending) {
                req.status = RequestStatus.Expired;
                reservedSpendAmount -= req.amount;
                emit SpendRequestExpired(requestId);
            }
            revert VotingPeriodEnded(requestId);
        }

        // Chống bỏ phiếu trùng (Double Voting)
        if (hasVoted[requestId][msg.sender]) {
            revert AlreadyVoted(requestId, msg.sender);
        }

        // Kiểm tra có ít nhất 1 thành viên BCS đang hoạt động
        if (activeBCSCount == 0) {
            revert NoActiveBCS();
        }

        // 2. Effects: Ghi nhận phiếu bầu
        hasVoted[requestId][msg.sender] = true;
        if (support) {
            req.yesVotes++;
        } else {
            req.noVotes++;
        }

        emit SpendRequestVoted(requestId, msg.sender, support, req.yesVotes, req.noVotes);

        // Kiểm tra ngưỡng đồng thuận >= 51% trên tổng số BCS đang hoạt động tại thời điểm kiểm tra (R4)
        uint256 approvalBps = (req.yesVotes * BPS_DENOMINATOR) / activeBCSCount;
        if (approvalBps >= PASSING_THRESHOLD_BPS && req.status == RequestStatus.Pending) {
            req.status = RequestStatus.Ready;
            emit SpendRequestReady(requestId);
        }
    }

    // ==========================================
    // R6: THỰC THI GIẢI NGÂN (BCS)
    // ==========================================

    /// @notice Thực thi giải ngân cho đề xuất chi tiêu đã đạt đủ điều kiện biểu quyết >= 51% (R6)
    /// @dev Bất kỳ thành viên BCS đang hoạt động nào cũng có thể gọi; áp dụng nghiêm ngặt CEI chống Reentrancy
    /// @param requestId Mã định danh của đề xuất cần giải ngân
    function executeSpendRequest(uint256 requestId) external onlyActiveBCS {
        // 1. Checks: Đề xuất tồn tại
        if (requestId == 0 || requestId > spendRequestCount) {
            revert RequestNotFound(requestId);
        }

        SpendRequest storage req = spendRequests[requestId];

        // Chống thực thi lặp lại (Double-spending)
        if (req.status == RequestStatus.Executed) {
            revert RequestAlreadyExecuted(requestId);
        }

        // Kiểm tra trạng thái hợp lệ
        if (req.status == RequestStatus.Expired) {
            revert RequestExpired(requestId);
        }
        if (req.status == RequestStatus.Cancelled || req.status == RequestStatus.Rejected) {
            revert InvalidRequestStatus(requestId);
        }

        // Kiểm tra có thành viên BCS hoạt động
        if (activeBCSCount == 0) {
            revert NoActiveBCS();
        }

        // Kiểm tra điều kiện đồng thuận >= 51% trên tổng số BCS hiện hành
        uint256 approvalBps = (req.yesVotes * BPS_DENOMINATOR) / activeBCSCount;
        if (approvalBps < PASSING_THRESHOLD_BPS) {
            revert ThresholdNotMet(req.yesVotes, activeBCSCount);
        }

        // Xác nhận chuyển trạng thái sang Ready nếu trước đó là Pending
        if (req.status == RequestStatus.Pending) {
            req.status = RequestStatus.Ready;
            emit SpendRequestReady(requestId);
        }

        // Kiểm tra số dư Quỹ lớp chính
        if (req.amount > classFundBalance) {
            revert InsufficientFund(req.amount, classFundBalance);
        }

        // 2. Effects (Cập nhật toàn bộ trạng thái trước khi tương tác ngoại vi - CEI)
        req.status = RequestStatus.Executed;
        classFundBalance -= req.amount;
        reservedSpendAmount -= req.amount;

        emit SpendRequestExecuted(requestId, req.recipient, req.amount);

        // 3. Interactions: Chuyển ETH trực tiếp cho người thụ hưởng qua low-level .call
        (bool success, ) = req.recipient.call{value: req.amount}("");
        if (!success) {
            revert ETHTransferFailed();
        }
    }

    // ==========================================
    // R9: DỌN DẸP ĐỀ XUẤT QUÁ HẠN (PUBLIC)
    // ==========================================

    /// @notice Đánh dấu hết hạn đề xuất chi quá hạn 7 ngày mà chưa giải ngân thành công (R5, R9)
    /// @dev Bất kỳ tài khoản nào cũng có thể gọi hàm này để giải phóng số tiền giữ chỗ (reservedSpendAmount)
    /// @param requestId Mã định danh của đề xuất cần đánh dấu hết hạn
    function expireSpendRequest(uint256 requestId) external {
        if (requestId == 0 || requestId > spendRequestCount) {
            revert RequestNotFound(requestId);
        }

        SpendRequest storage req = spendRequests[requestId];

        if (req.status != RequestStatus.Pending && req.status != RequestStatus.Ready) {
            revert InvalidRequestStatus(requestId);
        }

        if (block.timestamp <= req.createdAt + VOTING_PERIOD) {
            revert VotingStillActive(requestId);
        }

        // Cập nhật trạng thái và giải phóng số tiền giữ chỗ
        req.status = RequestStatus.Expired;
        reservedSpendAmount -= req.amount;

        emit SpendRequestExpired(requestId);
    }

    // ==========================================
    // HÀM TRA CỨU (VIEW / GETTERS)
    // ==========================================

    /// @notice Tra cứu số dư Quỹ lớp chính (sau khi trích 1% phí dịch vụ vận hành)
    function getFundBalance() external view returns (uint256) {
        return classFundBalance;
    }

    /// @notice Tra cứu số dư Quỹ lớp chính khả dụng thực tế để tạo đề xuất chi mới
    function getAvailableClassFund() public view returns (uint256) {
        if (classFundBalance <= reservedSpendAmount) {
            return 0;
        }
        return classFundBalance - reservedSpendAmount;
    }

    /// @notice Tra cứu tổng số dư ETH thực tế hiện có trong hợp đồng (bao gồm cả adminFeePool)
    function getTotalContractBalance() external view returns (uint256) {
        return address(this).balance;
    }

    /// @notice Tra cứu tổng số tiền đã đóng góp của một sinh viên cụ thể
    function getStudentContribution(address student) external view returns (uint256) {
        return studentContributions[student];
    }

    /// @notice Tra cứu chi tiết một đề xuất chi tiêu
    function getSpendRequest(uint256 requestId)
        external
        view
        returns (
            uint256 id,
            address recipient,
            uint256 amount,
            string memory description,
            address creator,
            uint256 createdAt,
            uint256 yesVotes,
            uint256 noVotes,
            RequestStatus status
        )
    {
        if (requestId == 0 || requestId > spendRequestCount) {
            revert RequestNotFound(requestId);
        }
        SpendRequest storage req = spendRequests[requestId];
        return (
            req.id,
            req.recipient,
            req.amount,
            req.description,
            req.creator,
            req.createdAt,
            req.yesVotes,
            req.noVotes,
            req.status
        );
    }

    /// @notice Kiểm tra một thành viên Ban cán sự đã bỏ phiếu cho đề xuất hay chưa
    function hasMemberVoted(uint256 requestId, address member) external view returns (bool) {
        return hasVoted[requestId][member];
    }
}