// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../contracts/project/ProjectCore.sol";

contract TestEVMVerification_test {
    uint256 public initialBalance = 100 ether;
    ProjectCore core;

    receive() external payable {}

    function beforeEach() public {
        core = new ProjectCore();
    }

    function testConstants() public {
        require(core.BPS_DENOMINATOR() == 10000, "BPS denominator must be 10000");
        require(core.PASSING_THRESHOLD_BPS() == 5100, "Threshold must be 5100");
    }

    function testBalanceCheck() public {
        uint256 bal = address(this).balance;
        require(bal == 0, "Balance is zero in CLI runner");
    }
}
