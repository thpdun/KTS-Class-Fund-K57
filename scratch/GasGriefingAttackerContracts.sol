// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../contracts/project/ProjectCore.sol";

/// @notice Recipient luôn luôn chủ động revert khi nhận ETH
contract AlwaysRevertingRecipient {
    uint256 public receiveCount;
    receive() external payable {
        receiveCount++;
        revert("AlwaysRevertingRecipient: ETH_REJECTED");
    }
}

/// @notice Recipient không có hàm receive() hoặc fallback() -> EVM tự động revert khi nhận ETH
contract EmptyFallbackRecipient {
    // Không có receive() hay fallback()
}

/// @notice Recipient cố tình đốt gas nhưng chấp nhận ETH mà không revert
contract GasBurningConsumer {
    uint256 public burnIterations;
    uint256 public dummySum;

    receive() external payable {
        while (gasleft() > 4000) {
            dummySum += burnIterations;
            burnIterations++;
        }
    }
}

/// @notice Recipient cố tình chạy vòng lặp vô hạn gây cạn kiệt gas (Out-of-Gas bên trong subcall)
contract InfiniteLoopAttacker {
    uint256 public dummy;
    receive() external payable {
        while (true) {
            dummy++;
        }
    }
}


/// @notice Recipient độc hại cố tình thử tái nhập (Reentrancy) vào toàn bộ các hàm nhạy cảm của ProjectCore
contract ComprehensiveReentrancyAttacker {
    ProjectCore public target;
    uint256 public targetRequestId;
    uint256 public targetRefundId;

    bool public voteSpendReverted;
    bool public executeSpendReverted;
    bool public createSpendReverted;
    bool public createRefundReverted;
    bool public voteRefundReverted;
    bool public executeRefundReverted;
    uint256 public callbackCount;

    constructor(address payable _target) {
        target = ProjectCore(_target);
    }

    function setTargets(uint256 _reqId, uint256 _refId) external {
        targetRequestId = _reqId;
        targetRefundId = _refId;
    }

    receive() external payable {
        callbackCount++;

        // 1. Thử gọi voteSpendRequest
        (bool s1, ) = address(target).call(
            abi.encodeWithSignature("voteSpendRequest(uint256,bool)", targetRequestId, true)
        );
        voteSpendReverted = !s1;

        // 2. Thử gọi executeSpendRequest
        (bool s2, ) = address(target).call(
            abi.encodeWithSignature("executeSpendRequest(uint256)", targetRequestId)
        );
        executeSpendReverted = !s2;

        // 3. Thử gọi createSpendRequest
        (bool s3, ) = address(target).call(
            abi.encodeWithSignature("createSpendRequest(address,uint256,string)", address(this), 0.1 ether, "reenter")
        );
        createSpendReverted = !s3;

        // 4. Thử gọi createRefundRequest
        (bool s4, ) = address(target).call(
            abi.encodeWithSignature("createRefundRequest(uint256,string)", 0.1 ether, "reenter")
        );
        createRefundReverted = !s4;

        // 5. Thử gọi voteRefundRequest
        (bool s5, ) = address(target).call(
            abi.encodeWithSignature("voteRefundRequest(uint256,bool)", targetRefundId, true)
        );
        voteRefundReverted = !s5;

        // 6. Thử gọi executeRefundRequest
        (bool s6, ) = address(target).call(
            abi.encodeWithSignature("executeRefundRequest(uint256)", targetRefundId)
        );
        executeRefundReverted = !s6;
    }
}

/// @notice Sinh viên độc hại nộp đơn hoàn tiền và cố tình đốt gas khi nhận lại tiền hoàn
contract GasBurningRefundStudent {
    ProjectCore public target;
    uint256 public dummySum;
    uint256 public burnCount;

    constructor(address payable _target) {
        target = ProjectCore(_target);
    }

    function deposit(uint256 amount) external payable {
        target.deposit{value: amount}();
    }

    function createRefund(uint256 amount, string memory reason) external returns (uint256) {
        return target.createRefundRequest(amount, reason);
    }

    receive() external payable {
        while (gasleft() > 4000) {
            dummySum += burnCount;
            burnCount++;
        }
    }
}

/// @notice Sinh viên từ chối nhận hoàn tiền để kiểm tra nhánh rollback của voteRefundRequest
contract AlwaysRevertingRefundStudent {
    ProjectCore public target;

    constructor(address payable _target) {
        target = ProjectCore(_target);
    }

    function deposit(uint256 amount) external payable {
        target.deposit{value: amount}();
    }

    function createRefund(uint256 amount, string memory reason) external returns (uint256) {
        return target.createRefundRequest(amount, reason);
    }

    receive() external payable {
        revert("AlwaysRevertingRefundStudent: REFUND_REJECTED");
    }
}

/// @notice Sinh viên chạy vòng lặp vô hạn khi nhận hoàn tiền
contract InfiniteLoopRefundStudent {
    ProjectCore public target;
    uint256 public dummy;

    constructor(address payable _target) {
        target = ProjectCore(_target);
    }

    function deposit(uint256 amount) external payable {
        target.deposit{value: amount}();
    }

    function createRefund(uint256 amount, string memory reason) external returns (uint256) {
        return target.createRefundRequest(amount, reason);
    }

    receive() external payable {
        while (true) {
            dummy++;
        }
    }
}

/// @notice Sinh viên không có receive/fallback khi nhận hoàn tiền
contract EmptyFallbackRefundStudent {
    ProjectCore public target;

    constructor(address payable _target) {
        target = ProjectCore(_target);
    }

    function deposit(uint256 amount) external payable {
        target.deposit{value: amount}();
    }

    function createRefund(uint256 amount, string memory reason) external returns (uint256) {
        return target.createRefundRequest(amount, reason);
    }
}

/// @notice Hợp đồng Cố vấn học tập (Advisor) dùng để test withdrawAdminFee
contract ContractAdvisor {
    ProjectCore public target;
    enum Behavior { Accept, Revert, BurnGas, InfiniteLoop, Reenter }
    Behavior public currentBehavior;
    uint256 public dummy;
    bool public reenterReverted;

    constructor(address payable _target) {
        target = ProjectCore(_target);
        currentBehavior = Behavior.Accept;
    }

    function setBehavior(Behavior b) external {
        currentBehavior = b;
    }

    function withdraw(uint256 amount) external {
        target.withdrawAdminFee(amount);
    }

    receive() external payable {
        if (currentBehavior == Behavior.Revert) {
            revert("ContractAdvisor: REVERTED");
        } else if (currentBehavior == Behavior.BurnGas) {
            while (gasleft() > 4000) {
                dummy++;
            }
        } else if (currentBehavior == Behavior.InfiniteLoop) {
            while (true) {
                dummy++;
            }
        } else if (currentBehavior == Behavior.Reenter) {
            // Thử tái nhập gọi lại withdrawAdminFee
            (bool s, ) = address(target).call(
                abi.encodeWithSignature("withdrawAdminFee(uint256)", 0.01 ether)
            );
            reenterReverted = !s;
        }
    }
}

