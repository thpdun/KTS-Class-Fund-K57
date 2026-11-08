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
        uint256 voterBase;          // Mẫu số biểu quyết được chốt cố định (snapshot) tại thời điểm tạo
    }

    /// @notice Cấu trúc thông tin của một yêu cầu hoàn tiền nộp nhầm (R7)
    struct RefundRequest {
        uint256 id;                 // Mã định danh duy nhất của yêu cầu hoàn tiền
        address payable applicant;  // Địa chỉ ví sinh viên nộp đơn yêu cầu hoàn tiền
        uint256 amount;             // Số tiền yêu cầu hoàn lại (wei)
        string reason;              // Lý do chi tiết nộp kèm yêu cầu hoàn tiền
        uint256 createdAt;          // Thời điểm tạo yêu cầu (block.timestamp)
        uint256 yesVotes;           // Số phiếu thuận từ Ban cán sự
        uint256 noVotes;            // Số phiếu chống từ Ban cán sự
        RequestStatus status;       // Trạng thái hiện tại của yêu cầu
        uint256 voterBase;          // Mẫu số biểu quyết được chốt cố định (snapshot) tại thời điểm tạo
    }

    /// @notice Cấu trúc thông tin của một đợt thu nộp quỹ trên chuỗi (Nhóm E)
    struct Collection {
        uint256 id;                 // Mã định danh duy nhất của đợt thu nộp
        uint256 targetWei;          // Mức đóng mục tiêu quy định cho mỗi sinh viên (wei)
        uint64 deadline;            // Thời hạn chót nộp quỹ (block.timestamp)
        string purpose;             // Mục đích, nội dung đợt thu quỹ
        address creator;            // Thành viên BCS tạo đợt thu
        uint64 createdAt;           // Thời điểm tạo đợt thu (block.timestamp)
        bool closed;                // Trạng thái đã đóng sổ hay chưa
        uint64 closedAt;            // Thời điểm đợt thu được đóng sổ
        uint256 expectedPayers;     // Sĩ số sinh viên tại thời điểm tạo (= enrolledCount)
        uint256 paidCount;          // Số lượng sinh viên đã nộp đủ mức (paidInCollection >= targetWei)
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

    /// @notice Thời gian chờ kích hoạt quyền biểu quyết sau khi thêm BCS mới (3 giây)
    uint256 public constant BCS_ACTIVATION_DELAY = 3 seconds;

    /// @notice Số thành viên BCS đủ điều kiện tối thiểu để tạo đề xuất chi hoặc yêu cầu hoàn tiền
    uint256 public constant MIN_BCS_FOR_PROPOSAL = 3;

    /// @notice Số thành viên BCS tối đa nhằm giới hạn chi phí vòng lặp và tránh tràn gas
    uint256 public constant MAX_BCS = 15;

    /// @notice Số lượng địa chỉ sinh viên tối đa trong một lần gọi setStudents theo lô (Nhóm D)
    uint256 public constant MAX_BATCH = 100;

    /// @notice Độ dài tối đa của mục đích đợt thu quỹ nhằm tiết kiệm calldata/lưu trữ (Nhóm E)
    uint256 public constant MAX_PURPOSE_LENGTH = 256;

    /// @notice Độ dài tối đa của lý do đóng đợt thu quỹ (Nhóm E)
    uint256 public constant MAX_REASON_LENGTH = 256;

    /// @notice Số lượng đề xuất chi đang mở (Pending/Ready) tối đa mỗi người tạo có thể duy trì đồng thời
    uint256 public constant MAX_OPEN_SPEND_PER_CREATOR = 3;

    /// @notice Lượng gas bù đắp ước tính cho chi phí giao dịch cơ bản 21.000 gas và dữ liệu calldata (Nhóm F)
    uint256 public constant GAS_REFUND_OVERHEAD = 30_000;

    /// @notice Giới hạn tối đa số đơn vị gas được hoàn trả trong một hành động quản trị (Nhóm F)
    uint256 public constant MAX_REFUND_GAS_UNITS = 500_000;

    /// @notice Mức phụ phí gas tối đa cho phép hoàn trên block.basefee (2 gwei = 2 * 10^9 wei) (Nhóm F)
    uint256 public constant MAX_GAS_PRICE_PREMIUM = 2 gwei;

    // ==========================================
    // BIẾN TRẠNG THÁI (STATE VARIABLES)
    // ==========================================

    /// @notice Địa chỉ Cố vấn học tập (CVHT / Owner) - người khởi tạo hợp đồng (R1)
    address public immutable advisor;

    /// @notice Khóa bảo vệ chống tái nhập (Reentrancy Guard) bao trùm cả hàm và bước hoàn gas (Nhóm F)
    bool private _reentrancyLocked;

    /// @notice Cờ hiệu nội bộ báo hiệu bỏ qua bước hoàn gas trong modifier governanceAction
    bool private _skipGasRefund;

    /// @notice Số dư khả dụng của Quỹ lớp chính (sau khi trích 1% phí dịch vụ vận hành)
    uint256 public classFundBalance;

    /// @notice Số dư Quỹ dịch vụ vận hành (1% trích từ tiền nạp) để CVHT bù đắp chi phí Gas (R2, R11)
    uint256 public adminFeePool;

    /// @notice Tổng số tiền đang được giữ chỗ cho các đề xuất chi đang chờ/sẵn sàng thực thi
    uint256 public reservedSpendAmount;

    /// @notice Hạn mức đóng góp net còn lại trong Quỹ lớp của từng sinh viên (99% sau trừ 1% phí và trừ các khoản đã hoàn)
    mapping(address => uint256) public studentContributions;

    /// @notice Tổng số tiền gốc (100% wei) từng sinh viên đã nạp vào hợp đồng (chỉ phục vụ hiển thị, không bị trừ khi hoàn tiền)
    mapping(address => uint256) public studentTotalDeposited;

    /// @notice Bảng theo dõi tư cách thành viên Ban cán sự (BCS) (R1)
    mapping(address => bool) public isBCSMember;

    /// @notice Danh sách địa chỉ ví các thành viên Ban cán sự hiện tại (tối đa MAX_BCS)
    address[] public bcsList;

    /// @notice Chỉ mục 1-based của thành viên trong bcsList để hỗ trợ gỡ O(1) bằng swap-and-pop (0 = không có mặt)
    mapping(address => uint256) private _bcsIndexPlusOne;

    /// @notice Mốc thời gian kích hoạt quyền biểu quyết của từng thành viên BCS (addedAt + BCS_ACTIVATION_DELAY)
    mapping(address => uint256) public memberSince;

    /// @notice Tổng số lượng thành viên Ban cán sự hiện có trong danh sách
    uint256 public activeBCSCount;

    /// @notice Bảng theo dõi sinh viên hợp lệ đã được Cố vấn học tập ghi danh trong danh sách lớp (Nhóm D)
    mapping(address => bool) public isStudent;

    /// @notice Tổng số lượng sinh viên hiện đang có trong danh sách lớp on-chain (Nhóm D)
    uint256 public enrolledCount;

    /// @notice Mã băm chuẩn hóa của danh bạ lớp off-chain được Cố vấn học tập xác nhận lên chuỗi (Nhóm D)
    bytes32 public rosterHash;

    /// @notice Tổng số đề xuất chi đã được tạo trong hợp đồng
    uint256 public spendRequestCount;

    /// @notice Bảng lưu trữ thông tin các đề xuất chi tiêu theo mã định danh (requestId)
    mapping(uint256 => SpendRequest) public spendRequests;

    /// @notice Số lượng đề xuất chi đang mở (Pending hoặc Ready) của từng thành viên BCS tạo đề xuất
    mapping(address => uint256) public openSpendRequestCount;

    /// @notice Bảng ghi nhận trạng thái đã bỏ phiếu của thành viên BCS cho từng đề xuất (requestId => member => bool) (R4)
    mapping(uint256 => mapping(address => bool)) public hasVoted;

    /// @notice Tổng số tiền đang được giữ chỗ cho các yêu cầu hoàn tiền đang chờ hoặc sẵn sàng thực thi
    uint256 public reservedRefundAmount;

    /// @notice Bảng theo dõi tổng số tiền đang nằm trong các yêu cầu hoàn tiền đang chờ/sẵn sàng của từng sinh viên
    mapping(address => uint256) public pendingStudentRefundAmount;

    /// @notice Tổng số yêu cầu hoàn tiền đã được tạo trong hợp đồng
    uint256 public refundRequestCount;

    /// @notice Bảng lưu trữ thông tin các yêu cầu hoàn tiền theo mã định danh (refundId => RefundRequest)
    mapping(uint256 => RefundRequest) public refundRequests;

    /// @notice Bảng ghi nhận trạng thái đã bỏ phiếu của thành viên BCS cho từng yêu cầu hoàn tiền (refundId => member => bool)
    mapping(uint256 => mapping(address => bool)) public hasVotedRefund;

    /// @notice Tổng số đợt thu nộp quỹ đã được khởi tạo trong hợp đồng (Nhóm E)
    uint256 public collectionCount;

    /// @notice Mã định danh của đợt thu đang mở hiện tại (0 nếu không có đợt thu nào đang mở) (Nhóm E)
    uint256 public activeCollectionId;

    /// @notice Bảng lưu trữ thông tin các đợt thu nộp quỹ theo mã định danh (id => Collection) (Nhóm E)
    mapping(uint256 => Collection) public collections;

    /// @notice Số tiền gốc (wei) từng sinh viên đã nộp theo từng đợt thu (id => student => paidWei) (Nhóm E)
    mapping(uint256 => mapping(address => uint256)) public paidInCollection;

    // ==========================================
    // SỰ KIỆN (EVENTS)
    // ==========================================

    /// @notice Phát ra khi cập nhật tư cách thành viên Ban cán sự (R1)
    event BCSMemberUpdated(address indexed member, bool status);

    /// @notice Phát ra khi Cố vấn học tập cập nhật tư cách sinh viên trong danh sách lớp on-chain (Nhóm D)
    event StudentEnrollmentUpdated(address indexed student, bool status);

    /// @notice Phát ra khi Cố vấn học tập ghi nhận mã băm danh bạ chuẩn hóa lên chuỗi (Nhóm D)
    event RosterCommitted(bytes32 indexed rosterHash, address indexed committedBy, uint256 timestamp);

    /// @notice Phát ra khi sinh viên nạp tiền vào quỹ thành công (R2)
    event FundDeposited(address indexed student, uint256 amount);

    /// @notice Phát ra khi trích phí dịch vụ vận hành vào adminFeePool (R2)
    event AdminFeeCollected(address indexed student, uint256 feeAmount);

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

    /// @notice Phát ra khi tự thực thi chi tiền thất bại do địa chỉ nhận từ chối ETH
    event SpendExecutionFailed(uint256 indexed requestId, address indexed recipient, uint256 amount);

    /// @notice Phát ra khi đề xuất chi bị đánh dấu hết hạn sau 7 ngày mà chưa đạt đủ 51% (R5, R9)
    event SpendRequestExpired(uint256 indexed requestId);

    /// @notice Phát ra khi đề xuất chi bị bác bỏ do số phiếu chống khiến đề xuất không thể đạt 51% (R4, R5)
    event SpendRequestRejected(uint256 indexed requestId);

    /// @notice Phát ra khi sinh viên tạo mới một yêu cầu hoàn tiền (R7)
    event RefundRequestCreated(
        uint256 indexed refundId,
        address indexed applicant,
        uint256 amount,
        string reason,
        uint256 createdAt
    );

    /// @notice Phát ra khi một thành viên BCS bỏ phiếu cho yêu cầu hoàn tiền (R7)
    event RefundRequestVoted(
        uint256 indexed refundId,
        address indexed voter,
        bool support,
        uint256 yesVotes,
        uint256 noVotes
    );

    /// @notice Phát ra khi yêu cầu hoàn tiền đạt đủ 51% phiếu thuận và chuyển sang trạng thái Sẵn sàng thực thi (R7)
    event RefundRequestReady(uint256 indexed refundId);

    /// @notice Phát ra khi yêu cầu hoàn tiền được thực thi chuyển ETH thành công cho sinh viên (R7)
    event RefundRequestExecuted(uint256 indexed refundId, address indexed applicant, uint256 amount);

    /// @notice Phát ra khi tự thực thi hoàn tiền thất bại do ví sinh viên từ chối ETH
    event RefundExecutionFailed(uint256 indexed refundId, address indexed applicant, uint256 amount);

    /// @notice Phát ra khi yêu cầu hoàn tiền bị đánh dấu hết hạn sau 7 ngày mà chưa đạt đủ 51% phiếu thuận (R7)
    event RefundRequestExpired(uint256 indexed refundId);

    /// @notice Phát ra khi yêu cầu hoàn tiền bị bác bỏ do số phiếu chống khiến yêu cầu không thể đạt 51% (R7)
    event RefundRequestRejected(uint256 indexed refundId);

    /// @notice Phát ra khi hoàn tiền nộp nhầm thành công cho sinh viên (R7 - tương thích)
    event RefundProcessed(address indexed student, uint256 amount);

    /// @notice Phát ra khi thành viên BCS khởi tạo đợt thu nộp quỹ mới trên chuỗi (Nhóm E)
    event CollectionCreated(
        uint256 indexed id,
        uint256 targetWei,
        uint64 deadline,
        string purpose,
        address indexed creator,
        uint256 expectedPayers
    );

    /// @notice Phát ra khi đợt thu nộp quỹ được đóng sổ bởi thành viên BCS (Nhóm E)
    event CollectionClosed(
        uint256 indexed id,
        string reason,
        address indexed closedBy,
        uint64 closedAt
    );

    /// @notice Phát ra khi sinh viên nộp tiền thành công vào một đợt thu cụ thể (Nhóm E)
    event CollectionDeposited(
        uint256 indexed id,
        address indexed student,
        uint256 amount,
        uint256 totalPaidInCollection,
        uint256 paidCount
    );

    /// @notice Phát ra khi hoàn phí gas tự động cho người thực thi quản trị (Nhóm F)
    event GasRefunded(
        address indexed to,
        uint256 gasUnits,
        uint256 gasPrice,
        uint256 paid,
        uint256 shortfall
    );

    /// @notice Phát ra khi việc chuyển ETH hoàn gas thất bại do ví người gọi từ chối ETH (Nhóm F)
    event GasRefundFailed(address indexed to, uint256 amount);

    /// @notice Phát ra khi Cố vấn học tập chuyển số dư phí vận hành sang Quỹ lớp chính (Nhóm F)
    event FeeMovedToClassFund(address indexed advisor, uint256 amount);

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

    /// @notice Số tiền yêu cầu hoàn vượt quá số tiền sinh viên đã đóng góp còn lại
    error InsufficientContribution(uint256 requested, uint256 available);

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

    /// @notice Không có thành viên Ban cán sự nào hợp lệ làm mẫu số biểu quyết
    error NoActiveBCS();

    /// @notice Số lượng thành viên BCS đạt điều kiện đã chạm trần tối đa MAX_BCS
    error MaxBCSReached();

    /// @notice Số lượng thành viên BCS đã kích hoạt chưa đạt mức tối thiểu để tạo đề xuất
    error NotEnoughBCS(uint256 eligible, uint256 required);

    /// @notice Người tạo đề xuất đã đạt giới hạn tối đa số đề xuất chi đang mở (MAX_OPEN_SPEND_PER_CREATOR = 3)
    error TooManyOpenRequests();

    /// @notice Người gọi có xung đột lợi ích (là recipient đề xuất chi hoặc applicant yêu cầu hoàn tiền)
    error ConflictOfInterest();

    /// @notice Thành viên BCS chưa đủ điều kiện tại thời điểm tạo đề xuất (tránh ví ma được thêm sau khi tạo)
    error VoterNotEligibleAtCreation(uint256 requestId, address voter);

    /// @notice Đề xuất chưa đạt ngưỡng đồng thuận tối thiểu 51% trên voterBase
    error ThresholdNotMet(uint256 yesVotes, uint256 voterBase);

    /// @notice Không tìm thấy yêu cầu hoàn tiền với mã định danh được cung cấp
    error RefundRequestNotFound(uint256 refundId);

    /// @notice Yêu cầu hoàn tiền đã được thực thi giải ngân trước đó
    error RefundAlreadyExecuted(uint256 refundId);

    /// @notice Yêu cầu hoàn tiền đã hết hạn (quá 7 ngày và chưa đạt 51%)
    error RefundExpired(uint256 refundId);

    /// @notice Trạng thái của yêu cầu hoàn tiền không hợp lệ cho thao tác yêu cầu
    error InvalidRefundStatus(uint256 refundId);

    /// @notice Thành viên Ban cán sự đã bỏ phiếu cho yêu cầu hoàn tiền này trước đó
    error AlreadyVotedRefund(uint256 refundId, address voter);

    /// @notice Thời hạn bỏ phiếu yêu cầu hoàn tiền 7 ngày đã kết thúc
    error RefundVotingPeriodEnded(uint256 refundId);

    /// @notice Thời hạn bỏ phiếu yêu cầu hoàn tiền 7 ngày vẫn còn hiệu lực, chưa thể đánh dấu hết hạn
    error RefundVotingStillActive(uint256 refundId);

    /// @notice Lệnh chuyển ETH bằng low-level call thất bại
    error ETHTransferFailed();

    /// @notice Số lượng địa chỉ truyền vào setStudents vượt quá giới hạn MAX_BATCH (100) (Nhóm D)
    error BatchTooLarge();

    /// @notice Địa chỉ ví chưa được ghi danh trong danh sách sinh viên lớp (Nhóm D)
    error NotEnrolledStudent(address account);

    /// @notice Thành viên Ban cán sự bắt buộc phải là sinh viên đã có trong danh sách lớp (Nhóm D)
    error BCSMustBeEnrolledStudent();

    /// @notice Không thể gỡ tư cách sinh viên khi người đó vẫn đang giữ vai trò Ban cán sự (Nhóm D)
    error StudentIsBCS();

    /// @notice Cố vấn học tập không thể tự ghi danh làm sinh viên trong danh sách lớp (Nhóm D)
    error AdvisorCannotBeStudent();

    /// @notice Không tìm thấy đợt thu nộp quỹ với mã định danh được cung cấp (Nhóm E)
    error CollectionNotFound(uint256 collectionId);

    /// @notice Đã có một đợt thu nộp quỹ đang mở, không thể tạo đợt thu mới cho đến khi đợt cũ được đóng sổ (Nhóm E)
    error CollectionStillOpen(uint256 activeCollectionId);

    /// @notice Đợt thu nộp quỹ đã được đóng sổ, từ chối nhận thêm tiền nạp (Nhóm E)
    error CollectionIsClosed(uint256 collectionId);

    /// @notice Đợt thu nộp quỹ đã quá hạn nộp, từ chối nhận tiền nạp (Nhóm E)
    error CollectionExpired(uint256 collectionId, uint64 deadline, uint256 currentTimestamp);

    /// @notice Đợt thu nộp quỹ đã ở trạng thái đóng trước đó (Nhóm E)
    error CollectionAlreadyClosed(uint256 collectionId);

    /// @notice Thời hạn chót nộp quỹ không hợp lệ (phải sau thời điểm hiện tại) (Nhóm E)
    error InvalidDeadline(uint64 deadline, uint256 currentTimestamp);

    /// @notice Mục đích của đợt thu nộp quỹ không được để trống (Nhóm E)
    error EmptyPurpose();

    /// @notice Mục đích đợt thu nộp quỹ vượt quá độ dài tối đa cho phép (Nhóm E)
    error PurposeTooLong(uint256 length, uint256 maxLength);

    /// @notice Lý do đóng đợt thu nộp quỹ không được để trống (Nhóm E)
    error EmptyReason();

    /// @notice Lý do đóng đợt thu nộp quỹ vượt quá độ dài tối đa cho phép (Nhóm E)
    error ReasonTooLong(uint256 length, uint256 maxLength);

    /// @notice Phát hiện hành vi gọi lại đệ quy khi đang trong phiên thực thi quản trị (Nhóm F)
    error ReentrancyGuardReentrantCall();

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

    /// @notice Chỉ cho phép thành viên Ban cán sự đã qua thời gian chờ kích hoạt (3 ngày) thực thi (R3, R4, R6)
    modifier onlyActiveBCS() {
        if (!isBCSMember[msg.sender] || block.timestamp < memberSince[msg.sender]) {
            revert NotActiveBCS();
        }
        _;
    }

    /// @notice Bộ điều chỉnh quản trị: đo gas tiêu hao, bảo vệ chống tái nhập (CEI) và hoàn gas tự động từ adminFeePool (Nhóm F)
    modifier governanceAction() {
        if (_reentrancyLocked) {
            revert ReentrancyGuardReentrantCall();
        }
        _reentrancyLocked = true;
        uint256 gasStart = gasleft();

        _;

        if (!_skipGasRefund) {
            _handleGasRefund(gasStart);
        } else {
            _skipGasRefund = false;
        }
        _reentrancyLocked = false;
    }

    /// @notice Xử lý tính toán và hoàn gas tự động cho người thực thi hành động quản trị (Nhóm F)
    /// @dev Tuân thủ nghiêm ngặt CEI: trừ adminFeePool trước khi gọi call{value: paid}(""), rollback quỹ phí nếu call thất bại
    /// @param gasStart Mốc gasleft() được ghi nhận ở đầu modifier governanceAction
    function _handleGasRefund(uint256 gasStart) internal {
        // Chỉ hoàn gas khi người gọi là Cố vấn hoặc BCS đã kích hoạt (không dùng tx.origin)
        if (msg.sender != advisor && (!isBCSMember[msg.sender] || block.timestamp < memberSince[msg.sender])) {
            return;
        }

        uint256 gasConsumed = gasStart > gasleft() ? (gasStart - gasleft()) : 0;
        uint256 gasUsed = gasConsumed + GAS_REFUND_OVERHEAD;
        uint256 units = gasUsed < MAX_REFUND_GAS_UNITS ? gasUsed : MAX_REFUND_GAS_UNITS;

        uint256 maxPrice = block.basefee + MAX_GAS_PRICE_PREMIUM;
        uint256 price = tx.gasprice < maxPrice ? tx.gasprice : maxPrice;

        uint256 owed = units * price;
        uint256 paid = owed < adminFeePool ? owed : adminFeePool;
        uint256 shortfall = owed - paid;

        if (paid > 0) {
            // Effects trước: cập nhật sổ sách kế toán trước khi gọi ngoại vi (CEI)
            adminFeePool -= paid;

            // Interactions: chuyển ETH hoàn gas
            (bool success, ) = msg.sender.call{value: paid}("");
            if (!success) {
                // Rollback sổ kế toán và phát sự kiện GasRefundFailed, không revert giao dịch chính
                adminFeePool += paid;
                emit GasRefundFailed(msg.sender, paid);
                emit GasRefunded(msg.sender, units, price, 0, owed);
                return;
            }
        }

        emit GasRefunded(msg.sender, units, price, paid, shortfall);
    }

    // ==========================================
    // KHỞI TẠO (CONSTRUCTOR)
    // ==========================================

    /// @notice Khởi tạo hợp đồng và gán quyền Cố vấn học tập cho người triển khai
    constructor() {
        advisor = msg.sender;
    }

    // ==========================================
    // R1 & D: QUẢN TRỊ DANH SÁCH SINH VIÊN, ROSTER HASH VÀ BAN CÁN SỰ (CVHT)
    // ==========================================

    /// @notice Cố vấn học tập thêm hoặc gỡ nhiều địa chỉ ví sinh viên khỏi danh sách lớp on-chain theo lô (Nhóm D)
    /// @dev Giới hạn tối đa MAX_BATCH (100) địa chỉ mỗi giao dịch để tránh vượt giới hạn gas block; chỉ phát event và đếm khi trạng thái thực sự thay đổi
    /// @param members Mảng địa chỉ ví sinh viên
    /// @param status true để ghi danh, false để gỡ khỏi danh sách lớp
    function setStudents(address[] calldata members, bool status) external onlyAdvisor governanceAction {
        uint256 len = members.length;
        if (len > MAX_BATCH) {
            revert BatchTooLarge();
        }

        for (uint256 i = 0; i < len; i++) {
            address student = members[i];
            if (student == address(0)) {
                revert InvalidAddress();
            }
            if (status && student == advisor) {
                revert AdvisorCannotBeStudent();
            }
            if (!status && isBCSMember[student]) {
                revert StudentIsBCS();
            }
            if (isStudent[student] != status) {
                isStudent[student] = status;
                if (status) {
                    enrolledCount++;
                } else {
                    enrolledCount--;
                }
                emit StudentEnrollmentUpdated(student, status);
            }
        }
    }

    /// @notice Cố vấn học tập ghi nhận mã băm chuẩn hóa (keccak256) của danh bạ lớp off-chain lên chuỗi để đối soát (Nhóm D)
    /// @dev Không lưu Họ tên hay MSSV lên blockchain nhằm bảo vệ quyền riêng tư theo thiết kế của hệ thống
    /// @param hash Mã băm 32 byte của danh bạ lớp đã chuẩn hóa
    function commitRoster(bytes32 hash) external onlyAdvisor governanceAction {
        rosterHash = hash;
        emit RosterCommitted(hash, msg.sender, block.timestamp);
    }

    /// @notice Thêm mới, kích hoạt (với độ trễ 3 ngày) hoặc gỡ bỏ tư cách thành viên Ban cán sự (R1)
    /// @dev Chỉ Cố vấn học tập mới có quyền gọi hàm này. Sử dụng swap-and-pop O(1) trên bcsList và yêu cầu isStudent[member] (Nhóm D)
    /// @param member Địa chỉ ví của thành viên Ban cán sự
    /// @param status Trạng thái hoạt động (true: thêm/kích hoạt sau 3 ngày, false: gỡ bỏ)
    function setBCSMember(address member, bool status) external onlyAdvisor governanceAction {
        if (member == address(0)) {
            revert InvalidAddress();
        }

        bool currentStatus = isBCSMember[member];
        if (currentStatus == status) {
            _skipGasRefund = true;
            return; // Trạng thái không đổi, không cập nhật và không hoàn gas
        }

        if (status) {
            if (!isStudent[member]) {
                revert BCSMustBeEnrolledStudent();
            }
            if (bcsList.length >= MAX_BCS) {
                revert MaxBCSReached();
            }
            isBCSMember[member] = true;
            bcsList.push(member);
            _bcsIndexPlusOne[member] = bcsList.length;
            memberSince[member] = block.timestamp + BCS_ACTIVATION_DELAY;
            activeBCSCount = bcsList.length;
        } else {
            uint256 idxPlusOne = _bcsIndexPlusOne[member];
            if (idxPlusOne != 0) {
                uint256 idx = idxPlusOne - 1;
                uint256 lastIdx = bcsList.length - 1;
                if (idx != lastIdx) {
                    address lastMember = bcsList[lastIdx];
                    bcsList[idx] = lastMember;
                    _bcsIndexPlusOne[lastMember] = idx + 1;
                }
                bcsList.pop();
                delete _bcsIndexPlusOne[member];
            }
            isBCSMember[member] = false;
            memberSince[member] = 0;
            activeBCSCount = bcsList.length;
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
        // 1. Checks: Chỉ sinh viên có tên trong danh sách lớp mới được nạp quỹ (Nhóm D); từ chối nếu số tiền nạp bằng 0
        if (!isStudent[sender]) {
            revert NotEnrolledStudent(sender);
        }
        if (amount == 0) {
            revert ZeroAmount();
        }

        // 2. Tính toán phân bổ số nguyên theo basis points (R2)
        // adminFee = amount * 100 / 10,000 (1%)
        // classFundAmount = amount - adminFee (99% và bảo toàn toàn bộ sai số làm tròn số nguyên)
        uint256 adminFee = (amount * FEE_BPS) / BPS_DENOMINATOR;
        uint256 classFundAmount = amount - adminFee;

        // 3. Effects: Cập nhật các biến trạng thái (hạn mức hoàn ghi 99% net; tổng nạp gốc ghi chỉ để hiển thị)
        studentContributions[sender] += classFundAmount;
        studentTotalDeposited[sender] += amount;
        classFundBalance += classFundAmount;
        adminFeePool += adminFee;

        // 4. Phát sự kiện lưu vết on-chain theo quy ước AGENTS.md
        emit FundDeposited(sender, amount);
        emit AdminFeeCollected(sender, adminFee);

        // 5. Interactions: ETH đã được tiếp nhận qua từ khóa payable, không gọi ngoại vi
    }

    // ==========================================
    // NHÓM E: QUẢN LÝ ĐỢT THU NỘP QUỸ TRÊN CHUỖI VÀ NẠP THEO ĐỢT (BCS & SINH VIÊN)
    // ==========================================

    /// @notice Ban cán sự khởi tạo một đợt thu nộp quỹ mới trên chuỗi (Nhóm E)
    /// @dev Chỉ cho phép tối đa 1 đợt thu đang mở tại một thời điểm; ghi nhận expectedPayers = enrolledCount
    /// @param targetWei Mức tiền đóng mục tiêu quy định cho mỗi sinh viên (wei)
    /// @param deadline Thời hạn chót nộp quỹ (timestamp tính bằng giây)
    /// @param purpose Mục đích, lý do của đợt thu
    /// @return id Mã định danh duy nhất của đợt thu vừa tạo
    function createCollection(
        uint256 targetWei,
        uint64 deadline,
        string calldata purpose
    ) external onlyActiveBCS governanceAction returns (uint256 id) {
        if (targetWei == 0) {
            revert ZeroAmount();
        }
        if (deadline <= block.timestamp) {
            revert InvalidDeadline(deadline, block.timestamp);
        }
        uint256 purposeLen = bytes(purpose).length;
        if (purposeLen == 0) {
            revert EmptyPurpose();
        }
        if (purposeLen > MAX_PURPOSE_LENGTH) {
            revert PurposeTooLong(purposeLen, MAX_PURPOSE_LENGTH);
        }
        if (activeCollectionId != 0 && !collections[activeCollectionId].closed) {
            Collection storage oldCol = collections[activeCollectionId];
            if (block.timestamp > oldCol.deadline) {
                oldCol.closed = true;
                oldCol.closedAt = uint64(block.timestamp);
                emit CollectionClosed(activeCollectionId, unicode"Hết hạn tự động", msg.sender, uint64(block.timestamp));
            } else {
                revert CollectionStillOpen(activeCollectionId);
            }
        }

        collectionCount++;
        id = collectionCount;
        activeCollectionId = id;

        collections[id] = Collection({
            id: id,
            targetWei: targetWei,
            deadline: deadline,
            purpose: purpose,
            creator: msg.sender,
            createdAt: uint64(block.timestamp),
            closed: false,
            closedAt: 0,
            expectedPayers: enrolledCount,
            paidCount: 0
        });

        emit CollectionCreated(id, targetWei, deadline, purpose, msg.sender, enrolledCount);
    }

    /// @notice Ban cán sự đóng sổ đợt thu nộp quỹ (Nhóm E)
    /// @dev Đợt thu không có hàm sửa thông tin sau khi tạo, chỉ có đóng sổ; sau khi đóng cho phép mở đợt mới
    /// @param id Mã định danh của đợt thu cần đóng
    /// @param reason Lý do đóng đợt thu
    function closeCollection(uint256 id, string calldata reason) external onlyActiveBCS governanceAction {
        if (id == 0 || id > collectionCount) {
            revert CollectionNotFound(id);
        }
        Collection storage col = collections[id];
        if (col.closed) {
            revert CollectionAlreadyClosed(id);
        }
        uint256 reasonLen = bytes(reason).length;
        if (reasonLen == 0) {
            revert EmptyReason();
        }
        if (reasonLen > MAX_REASON_LENGTH) {
            revert ReasonTooLong(reasonLen, MAX_REASON_LENGTH);
        }

        col.closed = true;
        col.closedAt = uint64(block.timestamp);

        if (activeCollectionId == id) {
            activeCollectionId = 0;
        }

        emit CollectionClosed(id, reason, msg.sender, uint64(block.timestamp));
    }

    /// @notice Sinh viên nộp tiền vào một đợt thu nộp quỹ cụ thể trên chuỗi (Nhóm E)
    /// @dev Giữ nguyên cơ chế phí 1% và net 99%; ghi nhận số tiền gốc vào paidInCollection và tăng paidCount khi lần đầu đạt >= targetWei
    /// @param id Mã định danh của đợt thu nộp quỹ
    function depositToCollection(uint256 id) external payable {
        if (id == 0 || id > collectionCount) {
            revert CollectionNotFound(id);
        }
        Collection storage col = collections[id];
        if (col.closed) {
            revert CollectionIsClosed(id);
        }
        if (block.timestamp > col.deadline) {
            revert CollectionExpired(id, col.deadline, block.timestamp);
        }

        // Thực hiện xử lý nạp tiền, kiểm tra sinh viên và phân bổ phí (CEI)
        _processDeposit(msg.sender, msg.value);

        // Ghi nhận đóng góp theo đợt thu (theo số tiền gốc msg.value)
        uint256 prevPaid = paidInCollection[id][msg.sender];
        uint256 newPaid = prevPaid + msg.value;
        paidInCollection[id][msg.sender] = newPaid;

        if (prevPaid < col.targetWei && newPaid >= col.targetWei) {
            col.paidCount++;
        }

        emit CollectionDeposited(id, msg.sender, msg.value, newPaid, col.paidCount);
    }

    /// @notice Lấy toàn bộ thông tin chi tiết của một đợt thu nộp quỹ (Nhóm E)
    /// @param id Mã định danh của đợt thu
    /// @return Thông tin chi tiết đợt thu (struct Collection)
    function getCollection(uint256 id) external view returns (Collection memory) {
        if (id == 0 || id > collectionCount) {
            revert CollectionNotFound(id);
        }
        return collections[id];
    }

    /// @notice Kiểm tra sinh viên đã nộp đủ mức quy định của đợt thu hay chưa (Nhóm E)
    /// @param id Mã định danh của đợt thu
    /// @param student Địa chỉ ví của sinh viên cần tra cứu
    /// @return true nếu số tiền đã nộp vào đợt >= targetWei, ngược lại false
    function hasPaidInCollection(uint256 id, address student) external view returns (bool) {
        if (id == 0 || id > collectionCount) {
            return false;
        }
        return collections[id].targetWei > 0 && paidInCollection[id][student] >= collections[id].targetWei;
    }

    /// @notice Trả về mã định danh của đợt thu đang thực sự mở (chưa đóng và chưa quá hạn) (Nhóm E)
    /// @return Mã định danh đợt thu đang mở, hoặc 0 nếu không có đợt thu nào đang hoạt động
    function getActiveCollectionId() external view returns (uint256) {
        if (activeCollectionId != 0) {
            Collection storage col = collections[activeCollectionId];
            if (!col.closed && block.timestamp <= col.deadline) {
                return activeCollectionId;
            }
        }
        return 0;
    }

    // ==========================================
    // NHÓM F: ĐIỀU CHUYỂN PHÍ VẬN HÀNH DƯ THỪA (CVHT)
    // ==========================================

    /// @notice Cố vấn học tập chuyển số dư phí vận hành dư thừa vào Quỹ lớp chính (Nhóm F)
    /// @dev Chỉ đổi số dư kế toán nội bộ (adminFeePool -> classFundBalance), không có ETH rời khỏi hợp đồng
    /// @param amount Số lượng ETH (wei) muốn chuyển sang Quỹ lớp chính
    function moveFeeToClassFund(uint256 amount) external onlyAdvisor {
        if (amount == 0) {
            revert ZeroAmount();
        }
        if (amount > adminFeePool) {
            revert InsufficientAdminFee(amount, adminFeePool);
        }

        adminFeePool -= amount;
        classFundBalance += amount;

        emit FeeMovedToClassFund(advisor, amount);
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
    ) external onlyActiveBCS governanceAction returns (uint256 requestId) {
        // 1. Checks
        if (openSpendRequestCount[msg.sender] >= MAX_OPEN_SPEND_PER_CREATOR) {
            revert TooManyOpenRequests();
        }
        if (recipient == address(0)) {
            revert InvalidAddress();
        }
        if (amount == 0) {
            revert ZeroAmount();
        }

        uint256 eligible = eligibleBCSCount(block.timestamp);
        if (eligible < MIN_BCS_FOR_PROPOSAL) {
            revert NotEnoughBCS(eligible, MIN_BCS_FOR_PROPOSAL);
        }

        uint256 availableFund = getAvailableClassFund();
        if (amount > availableFund) {
            revert InsufficientAvailableFund(amount, availableFund);
        }

        uint256 voterBase = isEligibleVoterAt(recipient, block.timestamp) ? eligible - 1 : eligible;

        // 2. Effects: Khởi tạo đề xuất, chốt voterBase và giữ chỗ số dư
        requestId = ++spendRequestCount;
        openSpendRequestCount[msg.sender]++;
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
            status: RequestStatus.Pending,
            voterBase: voterBase
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

    /// @notice Giảm biến đếm số đề xuất chi đang mở của người tạo khi đề xuất kết thúc (Executed, Expired, Rejected)
    function _decrementOpenSpend(address creator) internal {
        if (openSpendRequestCount[creator] > 0) {
            openSpendRequestCount[creator]--;
        }
    }

    // ==========================================
    // R4 & R5: BỎ PHIẾU ĐỀ XUẤT CHI TIÊU (BCS)
    // ==========================================

    /// @notice Thành viên Ban cán sự bỏ phiếu cho một đề xuất chi tiêu (R4, R5)
    /// @dev Mỗi thành viên chỉ bỏ phiếu 1 lần; tự động chuyển sang Ready khi đạt >= 51% trên tổng số BCS
    /// @param requestId Mã định danh của đề xuất cần bỏ phiếu
    /// @param support true nếu đồng ý, false nếu không đồng ý
    function voteSpendRequest(uint256 requestId, bool support) external onlyActiveBCS governanceAction {
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
                _decrementOpenSpend(req.creator);
                emit SpendRequestExpired(requestId);
            }
            revert VotingPeriodEnded(requestId);
        }

        // Chặn xung đột lợi ích: recipient là BCS không được bỏ phiếu cho đề xuất chi cho chính mình
        if (msg.sender == req.recipient) {
            revert ConflictOfInterest();
        }

        // Chặn ví BCS được thêm/kích hoạt sau thời điểm tạo đề xuất
        if (!isEligibleVoterAt(msg.sender, req.createdAt)) {
            revert VoterNotEligibleAtCreation(requestId, msg.sender);
        }

        // Chống bỏ phiếu trùng (Double Voting)
        if (hasVoted[requestId][msg.sender]) {
            revert AlreadyVoted(requestId, msg.sender);
        }

        // Bảo vệ mẫu số biểu quyết snapshot khác 0
        if (req.voterBase == 0) {
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

        // Kiểm tra ngưỡng đồng thuận >= 51% trên mẫu số voterBase cố định tại thời điểm tạo (R4)
        uint256 approvalBps = (req.yesVotes * BPS_DENOMINATOR) / req.voterBase;
        if (approvalBps >= PASSING_THRESHOLD_BPS && req.status == RequestStatus.Pending) {
            req.status = RequestStatus.Ready;
            emit SpendRequestReady(requestId);

            // AUTO-EXECUTION: Thử tự động giải ngân ngay trong cùng giao dịch với lá phiếu cuối
            _tryExecuteSpend(req, requestId);
        } else if (req.status == RequestStatus.Pending) {
            uint256 maxPossibleYes = req.voterBase > req.noVotes ? (req.voterBase - req.noVotes) : 0;
            if (((maxPossibleYes * BPS_DENOMINATOR) / req.voterBase) < PASSING_THRESHOLD_BPS) {
                req.status = RequestStatus.Rejected;
                reservedSpendAmount -= req.amount;
                _decrementOpenSpend(req.creator);
                emit SpendRequestRejected(requestId);
            }
        }
    }

    /// @notice Hàm nội bộ thử tự động giải ngân cho đề xuất chi tiêu khi đạt ngưỡng
    /// @dev Áp dụng nghiêm ngặt CEI; nếu chuyển ETH thất bại, rollback trạng thái về Ready để không revert vote
    /// @param req Con trỏ lưu trữ tới đề xuất chi
    /// @param requestId Mã định danh của đề xuất
    /// @return success true nếu giải ngân thành công, false nếu chuyển ETH thất bại
    function _tryExecuteSpend(SpendRequest storage req, uint256 requestId) internal returns (bool) {
        // Kiểm tra số dư Quỹ lớp chính
        if (req.amount > classFundBalance) {
            return false;
        }

        // Effects: Cập nhật toàn bộ trạng thái trước tương tác ngoại vi (CEI)
        req.status = RequestStatus.Executed;
        classFundBalance -= req.amount;
        reservedSpendAmount -= req.amount;
        _decrementOpenSpend(req.creator);

        // Interactions: Chuyển ETH cho người thụ hưởng
        (bool success, ) = req.recipient.call{value: req.amount}("");
        if (!success) {
            // Rollback effects nếu thất bại, giữ trạng thái Ready cho đề xuất
            req.status = RequestStatus.Ready;
            classFundBalance += req.amount;
            reservedSpendAmount += req.amount;
            openSpendRequestCount[req.creator]++;

            emit SpendExecutionFailed(requestId, req.recipient, req.amount);
            return false;
        }

        // Chỉ phát sự kiện hoàn tất khi chuyển ETH thực sự thành công
        emit SpendRequestExecuted(requestId, req.recipient, req.amount);
        return true;
    }

    // ==========================================
    // R6: THỰC THI GIẢI NGÂN (BCS)
    // ==========================================

    /// @notice Thực thi giải ngân cho đề xuất chi tiêu đã đạt đủ điều kiện biểu quyết >= 51% (R6)
    /// @dev Bất kỳ thành viên BCS đang hoạt động nào cũng có thể gọi; áp dụng nghiêm ngặt CEI chống Reentrancy.
    ///      Đóng vai trò cơ chế giải ngân thủ công hoặc fallback khi auto-execution trước đó thất bại.
    /// @param requestId Mã định danh của đề xuất cần giải ngân
    function executeSpendRequest(uint256 requestId) external onlyActiveBCS governanceAction {
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

        // Bảo vệ mẫu số biểu quyết snapshot khác 0
        if (req.voterBase == 0) {
            revert NoActiveBCS();
        }

        // Kiểm tra điều kiện đồng thuận >= 51% trên mẫu số voterBase cố định
        uint256 approvalBps = (req.yesVotes * BPS_DENOMINATOR) / req.voterBase;
        if (approvalBps < PASSING_THRESHOLD_BPS) {
            revert ThresholdNotMet(req.yesVotes, req.voterBase);
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
        _decrementOpenSpend(req.creator);

        // 3. Interactions: Chuyển ETH trực tiếp cho người thụ hưởng qua low-level .call
        (bool success, ) = req.recipient.call{value: req.amount}("");
        if (!success) {
            revert ETHTransferFailed();
        }

        // Chỉ phát sự kiện hoàn tất sau khi chuyển ETH thành công
        emit SpendRequestExecuted(requestId, req.recipient, req.amount);
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

        // Chỉ đề xuất chưa đạt ngưỡng (Pending) mới được phép hết hạn sau thời hạn biểu quyết
        if (req.status != RequestStatus.Pending) {
            revert InvalidRequestStatus(requestId);
        }

        if (block.timestamp <= req.createdAt + VOTING_PERIOD) {
            revert VotingStillActive(requestId);
        }

        // Cập nhật trạng thái và giải phóng số tiền giữ chỗ
        req.status = RequestStatus.Expired;
        reservedSpendAmount -= req.amount;
        _decrementOpenSpend(req.creator);

        emit SpendRequestExpired(requestId);
    }

    // ==========================================
    // R7: QUY TRÌNH HOÀN TIỀN CÓ BIỂU QUYẾT BAN CÁN SỰ (R7 V0.1)
    // ==========================================

    /// @notice Sinh viên tạo yêu cầu xin hoàn lại tiền nộp nhầm/thừa vào Quỹ lớp (R7)
    /// @dev Bước 1: Yêu cầu được ghi nhận và giữ chỗ ngân sách, KHÔNG tự động chuyển ETH ra khỏi hợp đồng
    /// @param amount Số lượng ETH yêu cầu hoàn lại (wei)
    /// @param reason Lý do chi tiết gửi kèm yêu cầu
    /// @return refundId Mã định danh duy nhất của yêu cầu hoàn tiền vừa tạo
    function createRefundRequest(uint256 amount, string calldata reason) external returns (uint256) {
        // 1. Checks: Kiểm tra đầu vào hợp lệ và số lượng BCS đã kích hoạt >= MIN_BCS_FOR_PROPOSAL
        if (amount == 0) {
            revert ZeroAmount();
        }

        uint256 eligible = eligibleBCSCount(block.timestamp);
        if (eligible < MIN_BCS_FOR_PROPOSAL) {
            revert NotEnoughBCS(eligible, MIN_BCS_FOR_PROPOSAL);
        }

        // Kiểm tra hạn mức đóng góp khả dụng của chính sinh viên (trừ đi các yêu cầu đang chờ duyệt)
        uint256 availableContrib = getStudentAvailableContribution(msg.sender);
        if (amount > availableContrib) {
            revert InsufficientContribution(amount, availableContrib);
        }

        // Kiểm tra số dư quỹ lớp khả dụng (đã trừ cả đề xuất chi và yêu cầu hoàn tiền đang giữ chỗ)
        uint256 availableFund = getAvailableClassFund();
        if (amount > availableFund) {
            revert InsufficientAvailableFund(amount, availableFund);
        }

        uint256 voterBase = isEligibleVoterAt(msg.sender, block.timestamp) ? eligible - 1 : eligible;

        // 2. Effects: Ghi nhận yêu cầu, chốt voterBase và giữ chỗ số dư
        refundRequestCount++;
        uint256 refundId = refundRequestCount;

        pendingStudentRefundAmount[msg.sender] += amount;
        reservedRefundAmount += amount;

        refundRequests[refundId] = RefundRequest({
            id: refundId,
            applicant: payable(msg.sender),
            amount: amount,
            reason: reason,
            createdAt: block.timestamp,
            yesVotes: 0,
            noVotes: 0,
            status: RequestStatus.Pending,
            voterBase: voterBase
        });

        emit RefundRequestCreated(refundId, msg.sender, amount, reason, block.timestamp);
        return refundId;
    }

    /// @notice Thành viên Ban cán sự bỏ phiếu cho một yêu cầu hoàn tiền (R7)
    /// @dev Bước 2: Mỗi thành viên BCS chỉ bỏ phiếu 1 lần; tự động sang Ready khi đạt >= 51% trên tổng số BCS
    /// @param refundId Mã định danh của yêu cầu hoàn tiền cần bỏ phiếu
    /// @param support true nếu đồng ý duyệt hoàn tiền, false nếu từ chối/bác bỏ
    function voteRefundRequest(uint256 refundId, bool support) external onlyActiveBCS governanceAction {
        // 1. Checks: Yêu cầu tồn tại
        if (refundId == 0 || refundId > refundRequestCount) {
            revert RefundRequestNotFound(refundId);
        }

        RefundRequest storage req = refundRequests[refundId];

        // Kiểm tra trạng thái yêu cầu
        if (req.status == RequestStatus.Executed) {
            revert RefundAlreadyExecuted(refundId);
        }
        if (req.status == RequestStatus.Expired) {
            revert RefundExpired(refundId);
        }
        if (req.status != RequestStatus.Pending && req.status != RequestStatus.Ready) {
            revert InvalidRefundStatus(refundId);
        }

        // Kiểm tra thời hạn biểu quyết 7 ngày
        if (block.timestamp > req.createdAt + VOTING_PERIOD) {
            if (req.status == RequestStatus.Pending) {
                req.status = RequestStatus.Expired;
                reservedRefundAmount -= req.amount;
                pendingStudentRefundAmount[req.applicant] -= req.amount;
                emit RefundRequestExpired(refundId);
            }
            revert RefundVotingPeriodEnded(refundId);
        }

        // Chặn xung đột lợi ích: người nộp đơn hoàn tiền (kể cả là BCS) không được bỏ phiếu cho đơn của mình
        if (msg.sender == req.applicant) {
            revert ConflictOfInterest();
        }

        // Chặn ví BCS được thêm/kích hoạt sau thời điểm tạo yêu cầu
        if (!isEligibleVoterAt(msg.sender, req.createdAt)) {
            revert VoterNotEligibleAtCreation(refundId, msg.sender);
        }

        // Chống bỏ phiếu trùng
        if (hasVotedRefund[refundId][msg.sender]) {
            revert AlreadyVotedRefund(refundId, msg.sender);
        }

        // Bảo vệ mẫu số biểu quyết snapshot khác 0
        if (req.voterBase == 0) {
            revert NoActiveBCS();
        }

        // 2. Effects: Ghi nhận phiếu bầu
        hasVotedRefund[refundId][msg.sender] = true;
        if (support) {
            req.yesVotes++;
        } else {
            req.noVotes++;
        }

        emit RefundRequestVoted(refundId, msg.sender, support, req.yesVotes, req.noVotes);

        // Kiểm tra ngưỡng thông qua >= 51% trên mẫu số voterBase cố định tại thời điểm tạo
        uint256 approvalBps = (req.yesVotes * BPS_DENOMINATOR) / req.voterBase;
        if (approvalBps >= PASSING_THRESHOLD_BPS && req.status == RequestStatus.Pending) {
            req.status = RequestStatus.Ready;
            emit RefundRequestReady(refundId);

            // AUTO-EXECUTION: Thử tự động thực thi hoàn tiền ngay trong cùng giao dịch với lá phiếu cuối
            _tryExecuteRefund(req, refundId);
        } else if (req.status == RequestStatus.Pending) {
            uint256 maxPossibleYes = req.voterBase > req.noVotes ? (req.voterBase - req.noVotes) : 0;
            if (((maxPossibleYes * BPS_DENOMINATOR) / req.voterBase) < PASSING_THRESHOLD_BPS) {
                req.status = RequestStatus.Rejected;
                reservedRefundAmount -= req.amount;
                pendingStudentRefundAmount[req.applicant] -= req.amount;
                emit RefundRequestRejected(refundId);
            }
        }
    }

    /// @notice Hàm nội bộ thử tự động hoàn tiền cho yêu cầu hoàn tiền khi đạt ngưỡng
    /// @dev Áp dụng nghiêm ngặt CEI; nếu chuyển ETH thất bại, rollback trạng thái về Ready để không revert vote
    /// @param req Con trỏ lưu trữ tới yêu cầu hoàn tiền
    /// @param refundId Mã định danh của yêu cầu hoàn tiền
    /// @return success true nếu hoàn tiền thành công, false nếu chuyển ETH thất bại
    function _tryExecuteRefund(RefundRequest storage req, uint256 refundId) internal returns (bool) {
        // Kiểm tra hạn mức đóng góp và số dư Quỹ lớp chính
        if (req.amount > studentContributions[req.applicant] || req.amount > classFundBalance) {
            return false;
        }

        // Effects: Cập nhật toàn bộ trạng thái trước khi tương tác ngoại vi (CEI)
        req.status = RequestStatus.Executed;
        reservedRefundAmount -= req.amount;
        pendingStudentRefundAmount[req.applicant] -= req.amount;
        studentContributions[req.applicant] -= req.amount;
        classFundBalance -= req.amount;

        // Interactions: Chuyển ETH về ví sinh viên đã tạo yêu cầu
        (bool success, ) = req.applicant.call{value: req.amount}("");
        if (!success) {
            // Rollback effects nếu thất bại, giữ trạng thái Ready cho yêu cầu
            req.status = RequestStatus.Ready;
            reservedRefundAmount += req.amount;
            pendingStudentRefundAmount[req.applicant] += req.amount;
            studentContributions[req.applicant] += req.amount;
            classFundBalance += req.amount;

            emit RefundExecutionFailed(refundId, req.applicant, req.amount);
            return false;
        }

        // Chỉ phát sự kiện hoàn tất khi chuyển ETH thực sự thành công
        emit RefundRequestExecuted(refundId, req.applicant, req.amount);
        emit RefundProcessed(req.applicant, req.amount);
        return true;
    }

    /// @notice Thực thi hoàn trả ETH cho yêu cầu hoàn tiền đã được Ban cán sự thông qua >= 51% (R7)
    /// @dev Bước 3: Áp dụng nghiêm ngặt Checks-Effects-Interactions (CEI), chuyển ETH trực tiếp cho applicant.
    ///      Đóng vai trò cơ chế hoàn tiền thủ công hoặc fallback khi auto-execution trước đó thất bại.
    /// @param refundId Mã định danh của yêu cầu hoàn tiền cần thực thi
    function executeRefundRequest(uint256 refundId) external governanceAction {
        // 1. Checks: Yêu cầu tồn tại
        if (refundId == 0 || refundId > refundRequestCount) {
            revert RefundRequestNotFound(refundId);
        }

        RefundRequest storage req = refundRequests[refundId];

        if (req.status == RequestStatus.Executed) {
            revert RefundAlreadyExecuted(refundId);
        }
        if (req.status == RequestStatus.Expired) {
            revert RefundExpired(refundId);
        }
        if (req.status == RequestStatus.Cancelled || req.status == RequestStatus.Rejected) {
            revert InvalidRefundStatus(refundId);
        }

        // Bảo vệ mẫu số biểu quyết snapshot khác 0
        if (req.voterBase == 0) {
            revert NoActiveBCS();
        }

        // Kiểm tra ngưỡng đồng thuận >= 51% trên mẫu số voterBase cố định
        uint256 approvalBps = (req.yesVotes * BPS_DENOMINATOR) / req.voterBase;
        if (approvalBps < PASSING_THRESHOLD_BPS) {
            revert ThresholdNotMet(req.yesVotes, req.voterBase);
        }

        // Tự động chuyển Ready nếu trước đó là Pending
        if (req.status == RequestStatus.Pending) {
            req.status = RequestStatus.Ready;
            emit RefundRequestReady(refundId);
        }

        // Xác minh lại hạn mức đóng góp và số dư quỹ lớp
        if (req.amount > studentContributions[req.applicant]) {
            revert InsufficientContribution(req.amount, studentContributions[req.applicant]);
        }

        if (req.amount > classFundBalance) {
            revert InsufficientFund(req.amount, classFundBalance);
        }

        // 2. Effects (Cập nhật toàn bộ trạng thái trước khi tương tác ngoại vi - CEI)
        req.status = RequestStatus.Executed;
        reservedRefundAmount -= req.amount;
        pendingStudentRefundAmount[req.applicant] -= req.amount;
        studentContributions[req.applicant] -= req.amount;
        classFundBalance -= req.amount;

        // 3. Interactions: Chuyển ETH về chính ví sinh viên đã tạo yêu cầu
        (bool success, ) = req.applicant.call{value: req.amount}("");
        if (!success) {
            revert ETHTransferFailed();
        }

        // Chỉ phát sự kiện hoàn tất sau khi chuyển ETH thành công
        emit RefundRequestExecuted(refundId, req.applicant, req.amount);
        emit RefundProcessed(req.applicant, req.amount);
    }

    /// @notice Đánh dấu hết hạn yêu cầu hoàn tiền quá hạn 7 ngày mà chưa đạt đủ 51% phiếu thuận (R7)
    /// @dev Bất kỳ ai cũng có thể gọi sau 7 ngày để giải phóng hạn mức giữ chỗ cho sinh viên và quỹ lớp
    /// @param refundId Mã định danh của yêu cầu hoàn tiền cần đánh dấu hết hạn
    function expireRefundRequest(uint256 refundId) external {
        if (refundId == 0 || refundId > refundRequestCount) {
            revert RefundRequestNotFound(refundId);
        }

        RefundRequest storage req = refundRequests[refundId];

        // Chỉ yêu cầu hoàn tiền chưa đạt ngưỡng (Pending) mới được phép hết hạn sau thời hạn biểu quyết
        if (req.status != RequestStatus.Pending) {
            revert InvalidRefundStatus(refundId);
        }

        if (block.timestamp <= req.createdAt + VOTING_PERIOD) {
            revert RefundVotingStillActive(refundId);
        }

        // Cập nhật trạng thái và giải phóng giữ chỗ cho cả sinh viên lẫn quỹ lớp
        req.status = RequestStatus.Expired;
        reservedRefundAmount -= req.amount;
        pendingStudentRefundAmount[req.applicant] -= req.amount;

        emit RefundRequestExpired(refundId);
    }

    // ==========================================
    // HÀM TRA CỨU (VIEW / GETTERS)
    // ==========================================

    /// @notice Kiểm tra một địa chỉ có phải là BCS đủ điều kiện biểu quyết tại mốc thời gian `atTimestamp` hay không
    function isEligibleVoterAt(address member, uint256 atTimestamp) public view returns (bool) {
        return isBCSMember[member] && memberSince[member] != 0 && memberSince[member] <= atTimestamp;
    }

    /// @notice Đếm số thành viên BCS đủ điều kiện biểu quyết tại mốc thời gian `atTimestamp`
    /// @dev Vòng lặp bị chặn tối đa bởi MAX_BCS (15) nên chi phí gas luôn hữu hạn
    function eligibleBCSCount(uint256 atTimestamp) public view returns (uint256 count) {
        uint256 len = bcsList.length;
        for (uint256 i = 0; i < len; i++) {
            address member = bcsList[i];
            if (isBCSMember[member] && memberSince[member] != 0 && memberSince[member] <= atTimestamp) {
                count++;
            }
        }
    }

    /// @notice Trả về toàn bộ danh sách địa chỉ BCS hiện có trong hợp đồng
    function getBCSList() external view returns (address[] memory) {
        return bcsList;
    }

    /// @notice Tra cứu số dư Quỹ lớp chính (sau khi trích 1% phí dịch vụ vận hành)
    function getFundBalance() external view returns (uint256) {
        return classFundBalance;
    }

    /// @notice Tra cứu số dư Quỹ lớp chính khả dụng thực tế để tạo đề xuất chi hoặc hoàn tiền mới
    /// @dev Đã trừ đồng thời cả reservedSpendAmount và reservedRefundAmount để chống chiếm dụng ngân sách
    function getAvailableClassFund() public view returns (uint256) {
        uint256 totalReserved = reservedSpendAmount + reservedRefundAmount;
        if (classFundBalance <= totalReserved) {
            return 0;
        }
        return classFundBalance - totalReserved;
    }

    /// @notice Tra cứu tổng số dư ETH thực tế hiện có trong hợp đồng (bao gồm cả adminFeePool)
    function getTotalContractBalance() external view returns (uint256) {
        return address(this).balance;
    }

    /// @notice Phát hiện lượng ETH dư không nằm trong sổ kế toán (ví dụ ETH bị ép gửi qua selfdestruct) (Nhóm D)
    /// @dev Chỉ cung cấp góc nhìn kiểm toán, không xử lý/rút phần dư trong hợp đồng
    function getUnaccountedBalance() external view returns (uint256) {
        uint256 accounted = classFundBalance + adminFeePool;
        uint256 total = address(this).balance;
        if (total <= accounted) {
            return 0;
        }
        return total - accounted;
    }

    /// @notice Tra cứu hạn mức đóng góp net còn lại trong Quỹ lớp của một sinh viên (99% sau trừ 1% phí và các khoản đã hoàn)
    function getStudentContribution(address student) external view returns (uint256) {
        return studentContributions[student];
    }

    /// @notice Tra cứu hạn mức đóng góp còn khả dụng của sinh viên (đã trừ các yêu cầu hoàn tiền đang chờ duyệt)
    function getStudentAvailableContribution(address student) public view returns (uint256) {
        uint256 totalContrib = studentContributions[student];
        uint256 pending = pendingStudentRefundAmount[student];
        if (totalContrib <= pending) {
            return 0;
        }
        return totalContrib - pending;
    }

    /// @notice Tra cứu số tiền tối đa sinh viên có thể yêu cầu hoàn tại thời điểm hiện tại
    /// @dev Trả về giá trị nhỏ hơn giữa hạn mức đóng góp net khả dụng của sinh viên và số dư Quỹ lớp khả dụng
    function getStudentMaxRefund(address student) external view returns (uint256) {
        uint256 availableContrib = getStudentAvailableContribution(student);
        uint256 availableFund = getAvailableClassFund();
        return availableContrib < availableFund ? availableContrib : availableFund;
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

    /// @notice Kiểm tra một thành viên Ban cán sự đã bỏ phiếu cho đề xuất chi hay chưa
    function hasMemberVoted(uint256 requestId, address member) external view returns (bool) {
        return hasVoted[requestId][member];
    }

    /// @notice Tra cứu chi tiết một yêu cầu hoàn tiền
    function getRefundRequest(uint256 refundId)
        external
        view
        returns (
            uint256 id,
            address applicant,
            uint256 amount,
            string memory reason,
            uint256 createdAt,
            uint256 yesVotes,
            uint256 noVotes,
            RequestStatus status
        )
    {
        if (refundId == 0 || refundId > refundRequestCount) {
            revert RefundRequestNotFound(refundId);
        }
        RefundRequest storage req = refundRequests[refundId];
        return (
            req.id,
            req.applicant,
            req.amount,
            req.reason,
            req.createdAt,
            req.yesVotes,
            req.noVotes,
            req.status
        );
    }

    /// @notice Kiểm tra một thành viên Ban cán sự đã bỏ phiếu cho yêu cầu hoàn tiền hay chưa
    function hasMemberVotedRefund(uint256 refundId, address member) external view returns (bool) {
        return hasVotedRefund[refundId][member];
    }
}