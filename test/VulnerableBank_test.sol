// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;


/// @title FixedBank - Phiên bản ngân hàng đã vá lỗi Reentrancy bằng mô hình CEI (Lab 13)
/// @notice Áp dụng nguyên tắc Checks - Effects - Interactions theo AGENTS.md
contract FixedBank {
    mapping(address => uint256) public balances;

    event Deposited(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount);

    function deposit() external payable {
        require(msg.value > 0, "Tien nap phai > 0");
        balances[msg.sender] += msg.value;
        emit Deposited(msg.sender, msg.value);
    }

    function withdraw() external {
        // 1. Checks: Kiểm tra điều kiện tiên quyết
        uint256 balance = balances[msg.sender];
        require(balance > 0, "Khong co so du");

        // 2. Effects: Cập nhật trạng thái TRƯỚC KHI tương tác ngoại vi (CEI)
        balances[msg.sender] = 0;

        // 3. Interactions: Chuyển ETH sau khi trạng thái nội bộ đã an toàn
        (bool ok, ) = msg.sender.call{value: balance}("");
        require(ok, "Chuyen that bai");

        emit Withdrawn(msg.sender, balance);
    }

    function bankBalance() external view returns (uint256) {
        return address(this).balance;
    }
}