// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../ProjectCore.sol";

/// @title MockToggleReceiver - Hợp đồng giả lập có thể bật/tắt từ chối nhận ETH (dùng cho test Hardhat fallback & gas)
contract MockToggleReceiver {
    bool public rejectETH;
    uint256 public rejectedCount;

    error MockETHRejected();

    event RejectModeUpdated(bool rejectETH);

    constructor(bool _rejectETH) {
        rejectETH = _rejectETH;
    }

    function setRejectETH(bool _rejectETH) external {
        rejectETH = _rejectETH;
        emit RejectModeUpdated(_rejectETH);
    }

    function depositTo(ProjectCore target) external payable {
        target.deposit{value: msg.value}();
    }

    function requestRefundFrom(
        ProjectCore target,
        uint256 amount,
        string calldata reason
    ) external returns (uint256) {
        return target.createRefundRequest(amount, reason);
    }

    function executeRefundOn(ProjectCore target, uint256 refundId) external {
        target.executeRefundRequest(refundId);
    }

    receive() external payable {
        if (rejectETH) {
            rejectedCount++;
            revert MockETHRejected();
        }
    }
}

/// @title MockRefundReentrantAttacker - Hợp đồng tấn công reentrancy khi nhận ETH hoàn tiền
contract MockRefundReentrantAttacker {
    ProjectCore public immutable target;
    uint256 public attackRefundId;
    uint256 public attackAttempts;
    bool public reentrancyBlocked;
    bytes4 public lastRevertSelector;

    constructor(ProjectCore _target) {
        target = _target;
    }

    function depositToCore() external payable {
        target.deposit{value: msg.value}();
    }

    function requestRefund(uint256 amount, string calldata reason) external returns (uint256) {
        attackRefundId = target.createRefundRequest(amount, reason);
        return attackRefundId;
    }

    receive() external payable {
        if (attackRefundId != 0 && attackAttempts == 0) {
            attackAttempts++;
            (bool ok, bytes memory ret) = address(target).call(
                abi.encodeWithSignature("executeRefundRequest(uint256)", attackRefundId)
            );
            if (!ok) {
                reentrancyBlocked = true;
                if (ret.length >= 4) {
                    bytes4 sel;
                    assembly {
                        sel := mload(add(ret, 0x20))
                    }
                    lastRevertSelector = sel;
                }
            }
        }
    }
}

/// @title MockGasRefundActor - Giả lập hành vi của thành viên BCS/Cố vấn khi nhận hoàn gas
contract MockGasRefundActor {
    ProjectCore public target;
    bool public rejectGasRefund;
    bool public attemptReentrancy;
    bool public reentrancyBlocked;
    bytes4 public reentrancyRevertSelector;

    constructor(ProjectCore _target) {
        target = _target;
    }

    function setRejectGasRefund(bool _reject) external {
        rejectGasRefund = _reject;
    }

    function setAttemptReentrancy(bool _attempt) external {
        attemptReentrancy = _attempt;
    }

    function callCreateCollection(uint256 targetWei, uint64 deadline, string calldata purpose) external returns (uint256) {
        return target.createCollection(targetWei, deadline, purpose);
    }

    function callCloseCollection(uint256 collectionId, string calldata reason) external {
        target.closeCollection(collectionId, reason);
    }

    receive() external payable {
        if (rejectGasRefund) {
            revert("MockGasRefundActor: reject ETH");
        }
        if (attemptReentrancy) {
            attemptReentrancy = false;
            (bool ok, bytes memory ret) = address(target).call(
                abi.encodeWithSignature("closeCollection(uint256,string)", 1, "Reentrant close")
            );
            if (!ok) {
                reentrancyBlocked = true;
                if (ret.length >= 4) {
                    bytes4 sel;
                    assembly {
                        sel := mload(add(ret, 0x20))
                    }
                    reentrancyRevertSelector = sel;
                }
            }
        }
    }
}


