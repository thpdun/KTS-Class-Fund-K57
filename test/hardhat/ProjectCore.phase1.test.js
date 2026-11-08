const fs = require("fs");
const path = require("path");
const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

describe("Phase 0B & Phase 1 (Section A - Net Refund Accounting)", function () {
  const MAX_CONTRACT_BYTES = 24576;
  const SEVEN_DAYS = 7 * 24 * 60 * 60;
  const THREE_DAYS = 3 * 24 * 60 * 60;

  async function deployFixture() {
    const [advisor, bcs1, bcs2, bcs3, studentA, studentB, recipient, outsider] =
      await ethers.getSigners();
    const Factory = await ethers.getContractFactory("ProjectCore", advisor);
    const core = await Factory.deploy();
    await core.waitForDeployment();
    await core.connect(advisor).setStudents(
      [bcs1.address, bcs2.address, bcs3.address, studentA.address, studentB.address, recipient.address],
      true
    );
    return { core, advisor, bcs1, bcs2, bcs3, studentA, studentB, recipient, outsider };
  }

  it("Contract deployed bytecode size stays under 24,576-byte EIP-170 limit", async function () {
    const artifactPath = path.join(
      __dirname,
      "../../artifacts/contracts/project/ProjectCore.sol/ProjectCore.json"
    );
    const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
    const deployedBytes = (artifact.deployedBytecode.length - 2) / 2;
    const initBytes = (artifact.bytecode.length - 2) / 2;
    const pct = ((deployedBytes / MAX_CONTRACT_BYTES) * 100).toFixed(2);
    console.log(
      `    [Bytecode Size] deployed=${deployedBytes} / ${MAX_CONTRACT_BYTES} bytes (${pct}%), initcode=${initBytes} bytes`
    );
    expect(deployedBytes).to.be.greaterThan(0);
    expect(deployedBytes).to.be.lessThanOrEqual(MAX_CONTRACT_BYTES);
  });

  it("Section A1: deposit 10 ETH -> net 9.9 ETH, gross 10 ETH, full 9.9 ETH refund clears limit to 0 and preserves totalDeposited", async function () {
    const { core, advisor, bcs1, bcs2, bcs3, studentA } = await deployFixture();
    await core.connect(advisor).setBCSMember(bcs1.address, true);
    await core.connect(advisor).setBCSMember(bcs2.address, true);
    await core.connect(advisor).setBCSMember(bcs3.address, true);
    await time.increase(THREE_DAYS);

    const tenEth = ethers.parseEther("10");
    const ninePointNine = ethers.parseEther("9.9");

    await expect(core.connect(studentA).deposit({ value: tenEth }))
      .to.emit(core, "FundDeposited")
      .withArgs(studentA.address, tenEth)
      .and.to.emit(core, "AdminFeeCollected")
      .withArgs(studentA.address, ethers.parseEther("0.1"));

    expect(await core.studentContributions(studentA.address)).to.equal(ninePointNine);
    expect(await core.getStudentContribution(studentA.address)).to.equal(ninePointNine);
    expect(await core.studentTotalDeposited(studentA.address)).to.equal(tenEth);
    expect(await core.getStudentMaxRefund(studentA.address)).to.equal(ninePointNine);

    // Refund exact 9.9 ETH net (2/3 >= 51% auto-executes)
    await core.connect(studentA).createRefundRequest(ninePointNine, "Full 99% net refund");
    await core.connect(bcs1).voteRefundRequest(1, true);
    await expect(() => core.connect(bcs2).voteRefundRequest(1, true)).to.changeEtherBalance(
      studentA,
      ninePointNine
    );

    expect(await core.studentContributions(studentA.address)).to.equal(0n);
    expect(await core.getStudentAvailableContribution(studentA.address)).to.equal(0n);
    expect(await core.studentTotalDeposited(studentA.address)).to.equal(tenEth);
    expect(await core.getStudentMaxRefund(studentA.address)).to.equal(0n);
    expect(await core.classFundBalance()).to.equal(0n);
    // adminFeePool has gas refund deducted for the 2 BCS votes
    expect(await core.adminFeePool()).to.be.lte(ethers.parseEther("0.1"));
    expect(await core.adminFeePool()).to.be.gt(0n);

    // Additional 1 wei refund reverts InsufficientContribution
    await expect(core.connect(studentA).createRefundRequest(1n, "Extra 1 wei"))
      .to.be.revertedWithCustomError(core, "InsufficientContribution")
      .withArgs(1n, 0n);

    expect(await core.getTotalContractBalance()).to.equal(
      (await core.classFundBalance()) + (await core.adminFeePool())
    );
  });

  it("Section A2: small integer rounding (99 wei -> 99 net, 101 wei -> 100 net / 200 totalDeposited)", async function () {
    const { core, studentA } = await deployFixture();

    await core.connect(studentA).deposit({ value: 99n });
    expect(await core.studentContributions(studentA.address)).to.equal(99n);
    expect(await core.studentTotalDeposited(studentA.address)).to.equal(99n);

    await core.connect(studentA).deposit({ value: 101n });
    expect(await core.studentContributions(studentA.address)).to.equal(199n);
    expect(await core.studentTotalDeposited(studentA.address)).to.equal(200n);
    expect(await core.adminFeePool()).to.equal(1n);
    expect(await core.classFundBalance()).to.equal(199n);
  });

  it("Section A3 (Fraud): A & B each deposit 10 ETH; A trying to refund 10 ETH reverts InsufficientContribution and protects B's funds", async function () {
    const { core, advisor, bcs1, bcs2, bcs3, studentA, studentB } = await deployFixture();
    await core.connect(advisor).setBCSMember(bcs1.address, true);
    await core.connect(advisor).setBCSMember(bcs2.address, true);
    await core.connect(advisor).setBCSMember(bcs3.address, true);
    await time.increase(THREE_DAYS);

    const tenEth = ethers.parseEther("10");

    await core.connect(studentA).deposit({ value: tenEth });
    await core.connect(studentB).deposit({ value: tenEth });

    expect(await core.classFundBalance()).to.equal(ethers.parseEther("19.8"));
    expect(await core.getStudentMaxRefund(studentA.address)).to.equal(ethers.parseEther("9.9"));

    await expect(core.connect(studentA).createRefundRequest(tenEth, "Attempt cross-student drain"))
      .to.be.revertedWithCustomError(core, "InsufficientContribution")
      .withArgs(tenEth, ethers.parseEther("9.9"));
  });

  it("Section A4: multiple partial refunds sum <= 99% net, expired refund releases limit, and getStudentMaxRefund tracks spend reservations", async function () {
    const { core, advisor, bcs1, bcs2, bcs3, studentA, recipient } = await deployFixture();
    await core.connect(advisor).setBCSMember(bcs1.address, true);
    await core.connect(advisor).setBCSMember(bcs2.address, true);
    await core.connect(advisor).setBCSMember(bcs3.address, true);
    await time.increase(THREE_DAYS);

    await core.connect(studentA).deposit({ value: ethers.parseEther("10") }); // net 9.9 ETH

    // Spend request reserves 4 ETH -> available class fund = 5.9 ETH, while student avail = 9.9 ETH
    await core.connect(bcs1).createSpendRequest(recipient.address, ethers.parseEther("4"), "Reserve 4");
    expect(await core.getStudentMaxRefund(studentA.address)).to.equal(ethers.parseEther("5.9"));

    // Partial refund 1: 4 ETH (2/3 auto-executed) -> student avail becomes 5.9 ETH, classFund = 5.9, availableFund = 1.9 ETH
    await core.connect(studentA).createRefundRequest(ethers.parseEther("4"), "Part 1");
    await core.connect(bcs1).voteRefundRequest(1, true);
    await core.connect(bcs2).voteRefundRequest(1, true);
    expect(await core.studentContributions(studentA.address)).to.equal(ethers.parseEther("5.9"));
    expect(await core.getStudentMaxRefund(studentA.address)).to.equal(ethers.parseEther("1.9"));

    // Expire unvoted spend request after 7 days -> availableFund & getStudentMaxRefund recover to 5.9 ETH
    await time.increase(SEVEN_DAYS + 1);
    await core.expireSpendRequest(1);
    expect(await core.getStudentMaxRefund(studentA.address)).to.equal(ethers.parseEther("5.9"));

    // Partial refund 2 (5 ETH) + Partial refund 3 (0.9 ETH) = remaining 5.9 ETH net
    await core.connect(studentA).createRefundRequest(ethers.parseEther("5"), "Part 2");
    await core.connect(studentA).createRefundRequest(ethers.parseEther("0.9"), "Part 3");
    expect(await core.getStudentMaxRefund(studentA.address)).to.equal(0n);

    await expect(
      core.connect(studentA).createRefundRequest(1n, "Exceed net by 1 wei")
    ).to.be.revertedWithCustomError(core, "InsufficientContribution");

    // Execute Part 2 (2/3 auto-executes), let Part 3 expire -> 0.9 ETH limit restored and refundable again
    await core.connect(bcs1).voteRefundRequest(2, true);
    await core.connect(bcs2).voteRefundRequest(2, true);
    expect(await core.studentContributions(studentA.address)).to.equal(ethers.parseEther("0.9"));

    await time.increase(SEVEN_DAYS + 1);
    await core.expireRefundRequest(3);
    expect(await core.getStudentMaxRefund(studentA.address)).to.equal(ethers.parseEther("0.9"));
  });

  it("Section A5: fallback execution on rejecting receiver and CEI reentrancy defense preserve net accounting invariant", async function () {
    const { core, advisor, bcs1, bcs2, bcs3 } = await deployFixture();
    await core.connect(advisor).setBCSMember(bcs1.address, true);
    await core.connect(advisor).setBCSMember(bcs2.address, true);
    await core.connect(advisor).setBCSMember(bcs3.address, true);
    await time.increase(THREE_DAYS);
    const coreAddr = await core.getAddress();

    // 1. ToggleRejectReceiver rolls back auto-exec cleanly, preserves Ready + 99% net limit, then succeeds manually
    const Toggle = await ethers.getContractFactory("MockToggleReceiver");
    const studentMock = await Toggle.deploy(true);
    await studentMock.waitForDeployment();
    const mockAddr = await studentMock.getAddress();
    await core.connect(advisor).setStudents([mockAddr], true);

    await studentMock.depositTo(coreAddr, { value: ethers.parseEther("5") }); // net 4.95
    await studentMock.requestRefundFrom(coreAddr, ethers.parseEther("4.95"), "Mock fallback");

    await core.connect(bcs1).voteRefundRequest(1, true);
    await expect(core.connect(bcs2).voteRefundRequest(1, true)).to.emit(core, "RefundExecutionFailed");
    expect(await core.studentContributions(mockAddr)).to.equal(ethers.parseEther("4.95"));

    await studentMock.setRejectETH(false);
    await expect(() => studentMock.executeRefundOn(coreAddr, 1)).to.changeEtherBalance(
      studentMock,
      ethers.parseEther("4.95")
    );
    expect(await core.studentContributions(mockAddr)).to.equal(0n);
    expect(await core.studentTotalDeposited(mockAddr)).to.equal(ethers.parseEther("5"));

    // 2. Reentrancy attack blocked by CEI
    const Attacker = await ethers.getContractFactory("MockRefundReentrantAttacker");
    const attacker = await Attacker.deploy(coreAddr);
    await attacker.waitForDeployment();
    const atkAddr = await attacker.getAddress();
    await core.connect(advisor).setStudents([atkAddr], true);

    await attacker.depositToCore({ value: ethers.parseEther("4") }); // net 3.96
    await attacker.requestRefund(ethers.parseEther("3.96"), "Reentrancy net limit");
    await core.connect(bcs1).voteRefundRequest(2, true);
    await core.connect(bcs2).voteRefundRequest(2, true);

    expect(await attacker.attackAttempts()).to.equal(1n);
    expect(await attacker.reentrancyBlocked()).to.equal(true);
    expect(await core.studentContributions(atkAddr)).to.equal(0n);
    expect(await core.studentTotalDeposited(atkAddr)).to.equal(ethers.parseEther("4"));
    expect(await core.getTotalContractBalance()).to.equal(
      (await core.classFundBalance()) + (await core.adminFeePool())
    );
  });
});
