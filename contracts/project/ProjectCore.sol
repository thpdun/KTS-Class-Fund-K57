// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title ProjectCore - Hệ thống Quản lý Quỹ lớp KTS-Class-Fund
/// @notice Hợp đồng thông minh quản lý quỹ lớp phi tập trung cho sinh viên ngành Kinh tế Số (v0.1)
/// @dev Thực hiện luồng cốt lõi đầu tiên: Sinh viên nạp quỹ lớp tuân thủ docs/SPEC.md và AGENTS.md
contract ProjectCore {
    /// @notice Địa chỉ Cố vấn học tập (CVHT / Owner) - người khởi tạo hợp đồng
    address public immutable advisor;

    /// @notice Bảng theo dõi tổng số tiền tích lũy từng sinh viên đã đóng góp vào quỹ
    mapping(address => uint256) public studentContributions;

    /// @notice Sự kiện phát ra khi sinh viên nạp tiền vào quỹ thành công (R2, R5, Mục 4 SPEC)
    event FundDeposited(address indexed student, uint256 amount);

    /// @notice Lỗi kích hoạt khi số tiền nạp bằng 0 (R2, Ngoại lệ Mục 5 SPEC)
    error ZeroAmount();

    /// @notice Khởi tạo hợp đồng và gán quyền Cố vấn học tập cho người triển khai
    constructor() {
        advisor = msg.sender;
    }

    /// @notice Hàm cho phép bất kỳ sinh viên nào nạp ETH vào quỹ lớp qua DApp (R2, R5)
    /// @dev Áp dụng mô hình Checks - Effects - Interactions (CEI)
    function deposit() external payable {
        // 1. Checks: Kiểm tra giá trị nạp phải lớn hơn 0
        if (msg.value == 0) {
            revert ZeroAmount();
        }

        // 2. Effects: Ghi nhận số tiền đóng góp cá nhân và phát sự kiện lưu vết
        studentContributions[msg.sender] += msg.value;
        emit FundDeposited(msg.sender, msg.value);

        // 3. Interactions: ETH đã được nhận trực tiếp vào hợp đồng qua từ khóa payable
    }

    /// @notice Tự động tiếp nhận và ghi nhận khi sinh viên chuyển ETH trực tiếp từ ví cá nhân
    /// @dev Áp dụng mô hình Checks - Effects - Interactions (CEI)
    receive() external payable {
        // 1. Checks: Kiểm tra giá trị nạp phải lớn hơn 0
        if (msg.value == 0) {
            revert ZeroAmount();
        }

        // 2. Effects: Ghi nhận số tiền đóng góp cá nhân và phát sự kiện lưu vết
        studentContributions[msg.sender] += msg.value;
        emit FundDeposited(msg.sender, msg.value);

        // 3. Interactions: ETH đã được nhận trực tiếp vào hợp đồng qua từ khóa payable
    }

    /// @notice Tra cứu số dư ETH thực tế hiện có trong quỹ lớp
    function getFundBalance() external view returns (uint256) {
        return address(this).balance;
    }

    /// @notice Tra cứu tổng số tiền đã đóng góp của một sinh viên cụ thể
    function getStudentContribution(address student) external view returns (uint256) {
        return studentContributions[student];
    }
}