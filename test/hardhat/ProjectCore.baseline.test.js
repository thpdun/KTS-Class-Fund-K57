const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time, setNextBlockBaseFeePerGas } = require("@nomicfoundation/hardhat-network-helpers");

describe("ProjectCore Baseline (Pre-Upgrade Current Contract)", function () {
  const SEVEN_DAYS = 7 * 24 * 60 * 60;
  const THREE_DAYS = 3 * 24 * 60 * 60;

  async function deployFixture() {
    const [advisor, bcs1, bcs2, bcs3, student1, student2, recipient, outsider] =
      await ethers.getSigners();
    const Factory = await ethers.getContractFactory("ProjectCore", advisor);
    const core = await Factory.deploy();
    await core.waitForDeployment();
    await core.connect(advisor).setStudents(
      [bcs1.address, bcs2.address, bcs3.address, student1.address, student2.address, recipient.address],
      true
    );
    return { core, advisor, bcs1, bcs2, bcs3, student1, student2, recipient, outsider };
  }

  it("sets advisor immutable and initializes balances to zero", async function () {
    const { core, advisor } = await deployFixture();
    expect(await core.advisor()).to.equal(advisor.address);
    expect(await core.classFundBalance()).to.equal(0n);
    expect(await core.adminFeePool()).to.equal(0n);
    expect(await core.activeBCSCount()).to.equal(0n);
    expect(await core.getTotalContractBalance()).to.equal(0n);
  });

  it("R1: enforces advisor-only setBCSMember and tracks activeBCSCount", async function () {
    const { core, advisor, bcs1, bcs2, outsider } = await deployFixture();

    await expect(
      core.connect(outsider).setBCSMember(bcs1.address, true)
    ).to.be.revertedWithCustomError(core, "NotAdvisor");

    await expect(
      core.connect(advisor).setBCSMember(ethers.ZeroAddress, true)
    ).to.be.revertedWithCustomError(core, "InvalidAddress");

    await expect(core.connect(advisor).setBCSMember(bcs1.address, true))
      .to.emit(core, "BCSMemberUpdated")
      .withArgs(bcs1.address, true);

    await core.connect(advisor).setBCSMember(bcs2.address, true);
    expect(await core.isBCSMember(bcs1.address)).to.equal(true);
    expect(await core.activeBCSCount()).to.equal(2n);

    // No-op update does not change count
    await core.connect(advisor).setBCSMember(bcs1.address, true);
    expect(await core.activeBCSCount()).to.equal(2n);

    await core.connect(advisor).setBCSMember(bcs1.address, false);
    expect(await core.isBCSMember(bcs1.address)).to.equal(false);
    expect(await core.activeBCSCount()).to.equal(1n);
  });

  it("R2 (Phase 1 net accounting): splits 99%/1% on deposit() and receive(), records 99% net limit and 100% total deposited", async function () {
    const { core, student1, student2 } = await deployFixture();

    const tenEth = ethers.parseEther("10");
    const ninePointNineEth = ethers.parseEther("9.9");
    await expect(core.connect(student1).deposit({ value: tenEth }))
      .to.emit(core, "FundDeposited")
      .withArgs(student1.address, tenEth)
      .and.to.emit(core, "AdminFeeCollected")
      .withArgs(student1.address, ethers.parseEther("0.1"));

    expect(await core.classFundBalance()).to.equal(ninePointNineEth);
    expect(await core.adminFeePool()).to.equal(ethers.parseEther("0.1"));
    // Phase 1 / Section A: studentContributions records 99% net limit; studentTotalDeposited records 100% gross
    expect(await core.studentContributions(student1.address)).to.equal(ninePointNineEth);
    expect(await core.studentTotalDeposited(student1.address)).to.equal(tenEth);
    expect(await core.getStudentMaxRefund(student1.address)).to.equal(ninePointNineEth);

    // Direct ETH transfer via receive()
    const oneEth = ethers.parseEther("1");
    await student2.sendTransaction({ to: await core.getAddress(), value: oneEth });
    expect(await core.studentContributions(student2.address)).to.equal(ethers.parseEther("0.99"));
    expect(await core.studentTotalDeposited(student2.address)).to.equal(oneEth);
    expect(await core.classFundBalance()).to.equal(ethers.parseEther("10.89"));
    expect(await core.adminFeePool()).to.equal(ethers.parseEther("0.11"));

    // Integer rounding edge cases: 99 wei (0 fee) and 101 wei (1 wei fee)
    await core.connect(student1).deposit({ value: 99n });
    await core.connect(student1).deposit({ value: 101n });
    expect(await core.adminFeePool()).to.equal(ethers.parseEther("0.11") + 1n);
    expect(await core.classFundBalance()).to.equal(ethers.parseEther("10.89") + 199n);

    // Zero deposit reverts
    await expect(
      core.connect(student1).deposit({ value: 0n })
    ).to.be.revertedWithCustomError(core, "ZeroAmount");
  });

  it("R3/R4/R5/R6/R9: spend request voting >= 51% auto-executes, or expires after 7 days via time.increase", async function () {
    const { core, advisor, bcs1, bcs2, bcs3, student1, recipient } = await deployFixture();

    await core.connect(advisor).setBCSMember(bcs1.address, true);
    await core.connect(advisor).setBCSMember(bcs2.address, true);
    await core.connect(advisor).setBCSMember(bcs3.address, true);
    await time.increase(THREE_DAYS);
    await core.connect(student1).deposit({ value: ethers.parseEther("10") });

    // Request 1: 2 ETH, 2/3 votes -> auto-execute
    const twoEth = ethers.parseEther("2");
    await expect(core.connect(bcs1).createSpendRequest(recipient.address, twoEth, "Mua thiet bi"))
      .to.emit(core, "SpendRequestCreated");

    expect(await core.reservedSpendAmount()).to.equal(twoEth);
    expect(await core.getAvailableClassFund()).to.equal(ethers.parseEther("7.9"));

    await core.connect(bcs1).voteSpendRequest(1, true);
    await expect(
      core.connect(bcs1).voteSpendRequest(1, true)
    ).to.be.revertedWithCustomError(core, "AlreadyVoted");

    const recBalBefore = await ethers.provider.getBalance(recipient.address);
    await expect(core.connect(bcs2).voteSpendRequest(1, true))
      .to.emit(core, "SpendRequestReady")
      .withArgs(1n)
      .and.to.emit(core, "SpendRequestExecuted")
      .withArgs(1n, recipient.address, twoEth);
    const recBalAfter = await ethers.provider.getBalance(recipient.address);
    expect(recBalAfter - recBalBefore).to.equal(twoEth);
    expect(await core.reservedSpendAmount()).to.equal(0n);

    // Request 2: expire after 7 days using Hardhat time.increase
    await core.connect(bcs1).createSpendRequest(recipient.address, twoEth, "Het han");
    await core.connect(bcs1).voteSpendRequest(2, true); // 1/3 = 33.33% < 51%

    await expect(
      core.connect(student1).expireSpendRequest(2)
    ).to.be.revertedWithCustomError(core, "VotingStillActive");

    await time.increase(SEVEN_DAYS + 1);

    await expect(core.connect(student1).expireSpendRequest(2))
      .to.emit(core, "SpendRequestExpired")
      .withArgs(2n);
    const req2 = await core.getSpendRequest(2);
    expect(req2.status).to.equal(4n); // RequestStatus.Expired
    expect(await core.reservedSpendAmount()).to.equal(0n);
  });

  it("R7: refund request voting auto-executes, dual reservation blocks excess, and expires after 7 days", async function () {
    const { core, advisor, bcs1, bcs2, bcs3, student1 } = await deployFixture();

    await core.connect(advisor).setBCSMember(bcs1.address, true);
    await core.connect(advisor).setBCSMember(bcs2.address, true);
    await core.connect(advisor).setBCSMember(bcs3.address, true);
    await time.increase(THREE_DAYS);
    await core.connect(student1).deposit({ value: ethers.parseEther("5") });

    // Dual reservation check: create 4 ETH refund -> cannot create another 2 ETH (> 4.95 - 4)
    const fourEth = ethers.parseEther("4");
    await core.connect(student1).createRefundRequest(fourEth, "Nop nham dot 1");
    await expect(
      core.connect(student1).createRefundRequest(ethers.parseEther("2"), "Vuot han muc")
    ).to.be.revertedWithCustomError(core, "InsufficientContribution");

    // 2/3 vote expires after 7 days if only 1 vote
    await core.connect(bcs1).voteRefundRequest(1, true);
    await expect(
      core.expireRefundRequest(1)
    ).to.be.revertedWithCustomError(core, "RefundVotingStillActive");

    await time.increase(SEVEN_DAYS + 1);
    await expect(core.expireRefundRequest(1))
      .to.emit(core, "RefundRequestExpired")
      .withArgs(1n);
    expect(await core.pendingStudentRefundAmount(student1.address)).to.equal(0n);
    expect(await core.reservedRefundAmount()).to.equal(0n);

    // New refund 2 ETH approved by 2/3 BCS -> auto-executes directly to student1
    const twoEth = ethers.parseEther("2");
    await core.connect(student1).createRefundRequest(twoEth, "Hoan 2 ETH");
    await core.connect(bcs1).voteRefundRequest(2, true);

    await expect(() =>
      core.connect(bcs2).voteRefundRequest(2, true)
    ).to.changeEtherBalance(student1, twoEth);

    expect(await core.classFundBalance()).to.equal(ethers.parseEther("2.95"));
    expect(await core.studentContributions(student1.address)).to.equal(ethers.parseEther("2.95"));
    expect(await core.studentTotalDeposited(student1.address)).to.equal(ethers.parseEther("5"));
  });

  it("R11 + invariant + custom basefee/gasPrice measurement readiness", async function () {
    const { core, advisor, bcs1, student1, outsider } = await deployFixture();

    await core.connect(student1).deposit({ value: ethers.parseEther("10") });

    await expect(
      core.connect(outsider).moveFeeToClassFund(ethers.parseEther("0.01"))
    ).to.be.revertedWithCustomError(core, "NotAdvisor");

    // Set explicit EIP-1559 basefee & custom gasPrice to verify Hardhat EVM controls for Phase 5
    const baseFee = ethers.parseUnits("2", "gwei");
    const customGasPrice = ethers.parseUnits("5", "gwei");
    await setNextBlockBaseFeePerGas(baseFee);

    const tx = await core
      .connect(advisor)
      .moveFeeToClassFund(ethers.parseEther("0.04"), { gasPrice: customGasPrice });
    const receipt = await tx.wait();
    const block = await ethers.provider.getBlock(receipt.blockNumber);

    expect(block.baseFeePerGas).to.equal(baseFee);
    expect(receipt.gasPrice).to.equal(customGasPrice);
    expect(receipt.gasUsed).to.be.greaterThan(21000n);

    expect(await core.adminFeePool()).to.equal(ethers.parseEther("0.06"));
    expect(await core.classFundBalance()).to.equal(ethers.parseEther("9.94"));
    expect(await core.getTotalContractBalance()).to.equal(
      (await core.classFundBalance()) + (await core.adminFeePool())
    );

    // Ensure gas tracking can benchmark admin operations
    await core.connect(advisor).setBCSMember(bcs1.address, true);
    expect(await core.activeBCSCount()).to.equal(1n);
  });
});

