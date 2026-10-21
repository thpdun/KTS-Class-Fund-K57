// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title ProjectCore - Hệ thống Quản lý Quỹ lớp KTS-Class-Fund
/// @notice Hợp đồng thông minh quản lý quỹ lớp phi tập trung cho sinh viên ngành Kinh tế Số (v0.1)
/// @dev Triển khai quy tắc kinh tế R2 (99% Quỹ lớp chính, 1% Quỹ dịch vụ vận hành) tuân thủ docs/SPEC.md và AGENTS.md
contract ProjectCore {
    // ==========================================
    // HẰNG SỐ CẤU HÌNH KINH TẾ (BASIS POINTS)
    // ==========================================

    /// @notice Tỷ lệ phí dịch vụ vận hành theo basis points (1% = 100 bps)
    uint256 public constant FEE_BPS = 100;

    /// @notice Mẫu số chuẩn cho basis points (100% = 10,000 bps)
    uint256 public constant BPS_DENOMINATOR = 10_000;

    // ==========================================
    // BIẾN TRẠNG THÁI (STATE VARIABLES)
    // ==========================================

    /// @notice Địa chỉ Cố vấn học tập (CVHT / Owner) - người khởi tạo hợp đồng
    address public immutable advisor;

    /// @notice Số dư khả dụng của Quỹ lớp chính (sau khi trích 1% phí dịch vụ vận hành)
    uint256 public classFundBalance;

    /// @notice Số dư Quỹ dịch vụ vận hành (1% trích từ tiền nạp) để CVHT bù đắp chi phí Gas
    uint256 public adminFeePool;

    /// @notice Bảng theo dõi tổng số tiền tích lũy từng sinh viên đã đóng góp (100% tiền gốc)
    mapping(address => uint256) public studentContributions;

    // ==========================================
    // SỰ KIỆN (EVENTS)
    // ==========================================

    /// @notice Sự kiện phát ra khi sinh viên nạp tiền vào quỹ thành công (R2, Mục 4 SPEC)
    /// @param student Địa chỉ ví sinh viên nạp tiền
    /// @param amount Tổng số tiền gốc sinh viên nạp vào hợp đồng (wei)
    event FundDeposited(address indexed student, uint256 amount);

    /// @notice Sự kiện phát ra khi trích phí dịch vụ vận hành vào adminFeePool (R2, Mục 4 SPEC)
    /// @param student Địa chỉ ví sinh viên nạp tiền chịu phí
    /// @param feeAmount Số tiền phí vận hành 1% được trích vào adminFeePool (wei)
    event AdminFeeCollected(address indexed student, uint256 feeAmount);

    // ==========================================
    // LỖI TÙY BIẾN (CUSTOM ERRORS)
    // ==========================================

    /// @notice Lỗi kích hoạt khi số tiền nạp bằng 0 (R2, Ngoại lệ Mục 5 SPEC)
    error ZeroAmount();

    // ==========================================
    // KHỞI TẠO (CONSTRUCTOR)
    // ==========================================

    /// @notice Khởi tạo hợp đồng và gán quyền Cố vấn học tập cho người triển khai
    constructor() {
        advisor = msg.sender;
    }

    // ==========================================
    // HÀM NẠP TIỀN (DEPOSIT & RECEIVE)
    // ==========================================

    /// @notice Hàm cho phép bất kỳ sinh viên nào nạp ETH vào quỹ lớp qua DApp (R2)
    /// @dev Áp dụng mô hình Checks - Effects - Interactions (CEI)
    function deposit() external payable {
        _processDeposit(msg.sender, msg.value);
    }

    /// @notice Tự động tiếp nhận và ghi nhận khi sinh viên chuyển ETH trực tiếp từ ví cá nhân
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
    // HÀM TRA CỨU (VIEW / GETTERS)
    // ==========================================

    /// @notice Tra cứu số dư Quỹ lớp chính khả dụng để chi tiêu (99% từ tiền nạp)
    /// @dev Giữ nguyên tên hàm và chữ ký để tương thích giao diện DApp
    function getFundBalance() external view returns (uint256) {
        return classFundBalance;
    }

    /// @notice Tra cứu tổng số dư ETH thực tế hiện có trong hợp đồng (bao gồm cả adminFeePool)
    function getTotalContractBalance() external view returns (uint256) {
        return address(this).balance;
    }

    /// @notice Tra cứu tổng số tiền đã đóng góp của một sinh viên cụ thể
    function getStudentContribution(address student) external view returns (uint256) {
        return studentContributions[student];
    }
}