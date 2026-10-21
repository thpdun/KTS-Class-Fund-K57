// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../contracts/project/ProjectCore.sol";

/// @title ProjectCoreTest - Bộ kiểm thử tự động quy tắc kinh tế R2 (Lab 11)
/// @notice Kiểm thử tự động trên Remix IDE (Solidity Unit Testing) hoặc bất kỳ EVM test runner nào
contract ProjectCoreTest {
    ProjectCore core;

    /// @notice Chuẩn bị môi trường trước mỗi lần chạy
    function beforeEach() public {
        core = new ProjectCore();
    }

    /// @notice Ca 1 – Hợp lệ: Nạp 1 ETH -> 99% vào Quỹ lớp chính, 1% vào adminFeePool
    function testCase1_ValidDeposit1ETH() public payable {
        uint256 depositAmount = 1 ether;
        core.deposit{value: depositAmount}();

        // Phân bổ kỳ vọng:
        // 1% của 1 ETH = 0.01 ETH (10^16 wei)
        // 99% của 1 ETH = 0.99 ETH (99 * 10^16 wei)
        uint256 expectedFee = 0.01 ether;
        uint256 expectedClass = 0.99 ether;

        require(core.classFundBalance() == expectedClass, "Class fund balance must increase by 0.99 ETH");
        require(core.adminFeePool() == expectedFee, "Admin fee pool must increase by 0.01 ETH");
        require(core.getFundBalance() == expectedClass, "getFundBalance() must return available class fund");
        require(core.studentContributions(address(this)) == depositAmount, "Student contributions must record full 1 ETH");
        require(core.classFundBalance() + core.adminFeePool() == depositAmount, "Sum of two pools must equal deposit amount");
        require(core.getTotalContractBalance() == depositAmount, "Total contract balance must match exactly");
    }

    /// @notice Ca 2 – Vi phạm: Nạp 0 ETH bị revert với lỗi tùy biến ZeroAmount()
    function testCase2_ZeroAmountReverts() public {
        (bool success, bytes memory returnData) = address(core).call{value: 0}(
            abi.encodeWithSignature("deposit()")
        );
        require(!success, "Transaction with 0 ETH must revert");

        // Kiểm tra đúng custom error ZeroAmount()
        bytes4 expectedSelector = bytes4(keccak256("ZeroAmount()"));
        bytes4 actualSelector;
        if (returnData.length >= 4) {
            assembly {
                actualSelector := mload(add(returnData, 0x20))
            }
            require(actualSelector == expectedSelector, "Revert reason must be ZeroAmount()");
        }

        // Đảm bảo không có trạng thái rác nào được lưu lại sau revert
        require(core.classFundBalance() == 0, "Class fund must remain 0 after revert");
        require(core.adminFeePool() == 0, "Admin fee pool must remain 0 after revert");
        require(core.studentContributions(address(this)) == 0, "No contribution recorded after revert");
    }

    /// @notice Ca 3 – Kiểm tra đường nạp trực tiếp qua receive()
    function testCase3_DirectReceive() public payable {
        uint256 depositAmount = 0.5 ether;
        (bool success, ) = address(core).call{value: depositAmount}("");
        require(success, "Direct ETH transfer to receive() must succeed");

        uint256 expectedFee = 0.005 ether;
        uint256 expectedClass = 0.495 ether;

        require(core.classFundBalance() == expectedClass, "Class fund must be 0.495 ETH");
        require(core.adminFeePool() == expectedFee, "Admin fee pool must be 0.005 ETH");
        require(core.studentContributions(address(this)) == depositAmount, "Student contributions must record 0.5 ETH");
        require(core.classFundBalance() + core.adminFeePool() == depositAmount, "Sum must be conserved");
    }

    /// @notice Ca 4 – Phép tính số nguyên và các giá trị biên (< 100 wei)
    function testCase4_IntegerMathEdgeCases() public payable {
        // Nạp 99 wei (< 100 wei)
        uint256 smallAmount = 99;
        core.deposit{value: smallAmount}();

        // 99 * 100 / 10000 = 0 wei phí
        // Quỹ lớp nhận đủ 99 wei
        require(core.adminFeePool() == 0, "Fee for 99 wei must be 0 wei due to integer division");
        require(core.classFundBalance() == smallAmount, "Class fund must receive 99 wei");
        require(core.classFundBalance() + core.adminFeePool() == smallAmount, "Total must be conserved for 99 wei");

        // Nạp tiếp 101 wei
        uint256 oddAmount = 101;
        core.deposit{value: oddAmount}();

        // 101 * 100 / 10000 = 1 wei phí
        // Quỹ lớp nhận 100 wei
        require(core.adminFeePool() == 1, "Cumulative fee must be 1 wei");
        require(core.classFundBalance() == 99 + 100, "Cumulative class fund must be 199 wei");
        require(core.classFundBalance() + core.adminFeePool() == smallAmount + oddAmount, "Sum must equal 200 wei");
    }

    /// @notice Hàm hỗ trợ nhận ETH cho contract kiểm thử
    receive() external payable {}
}
