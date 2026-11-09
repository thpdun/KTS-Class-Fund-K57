const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

describe("Phase 2C — Hoàn tiền khi nộp nhầm số tiền (Keep Amount Policy)", function () {
  const THREE_DAYS = 3 * 24 * 60 * 60;

  async function deployFixture() {
    const [advisor, bcs1, bcs2, bcs3, studentA, studentB, recipient, outsider] =
      await ethers.getSigners();
    const Factory = await ethers.getContractFactory("ProjectCore", advisor);
    const core = await Factory.deploy();
    await core.waitForDeployment();

    // Whitelist students
    await core.connect(advisor).setStudents(
      [bcs1.address, bcs2.address, bcs3.address, studentA.address, studentB.address, recipient.address],
      true
    );

    // Setup 3 active BCS members (delay 3 days)
    await core.connect(advisor).setBCSMember(bcs1.address, true);
    await core.connect(advisor).setBCSMember(bcs2.address, true);
    await core.connect(advisor).setBCSMember(bcs3.address, true);
    await time.increase(THREE_DAYS);

    return { core, advisor, bcs1, bcs2, bcs3, studentA, studentB, recipient, outsider };
  }

  it("Test 1: Nộp 10 ETH, keep 1 ETH -> refundAmount = 8.91 ETH; sau thực thi quỹ lớp 0.99 ETH, adminFeePool 0.1 ETH, SV nhận đúng 8.91 ETH", async function () {
    const { core, bcs1, bcs2, studentA } = await deployFixture();

    const tenEth = ethers.parseEther("10");
    const oneEth = ethers.parseEther("1");
    const expectedKeepNet = ethers.parseEther("0.99");
    const expectedRefund = ethers.parseEther("8.91");
    const expectedFee = ethers.parseEther("0.1");

    // Student A deposits 10 ETH
    await core.connect(studentA).deposit({ value: tenEth });
    expect(await core.getRefundable(studentA.address)).to.equal(ethers.parseEther("9.9"));

    // Preview
    const [previewRefund, previewKeepNet] = await core.previewRefundKeeping(studentA.address, oneEth);
    expect(previewRefund).to.equal(expectedRefund);
    expect(previewKeepNet).to.equal(expectedKeepNet);

    // Create refund request keeping 1 ETH
    const tx = await core.connect(studentA).createRefundRequestKeeping(oneEth, "Nop nham 10 ETH thay vi 1 ETH");
    await expect(tx)
      .to.emit(core, "RefundKeepingRequested")
      .withArgs(1n, studentA.address, oneEth, expectedKeepNet, expectedRefund);
    await expect(tx)
      .to.emit(core, "RefundRequestCreated");

    // BCS 1 & 2 vote yes (2/3 >= 51% -> auto execute)
    await core.connect(bcs1).voteRefundRequest(1n, true);

    await expect(() => core.connect(bcs2).voteRefundRequest(1n, true)).to.changeEtherBalance(
      studentA,
      expectedRefund
    );

    // Class fund balance has exact 0.99 ETH remaining
    expect(await core.classFundBalance()).to.equal(expectedKeepNet);
    expect(await core.studentContributions(studentA.address)).to.equal(expectedKeepNet);
    // adminFeePool retains initial 0.1 ETH minus governance gas refund
    const feePool = await core.adminFeePool();
    expect(feePool).to.be.lte(expectedFee);
    expect(feePool).to.be.gt(0n);

    // Invariant
    expect(await core.getTotalContractBalance()).to.equal(
      (await core.classFundBalance()) + (await core.adminFeePool())
    );
  });

  it("Test 2: keep 0 -> hoàn toàn bộ 9.9 ETH net khả dụng", async function () {
    const { core, bcs1, bcs2, studentA } = await deployFixture();

    const tenEth = ethers.parseEther("10");
    const ninePointNine = ethers.parseEther("9.9");

    await core.connect(studentA).deposit({ value: tenEth });

    const [previewRefund, previewKeepNet] = await core.previewRefundKeeping(studentA.address, 0n);
    expect(previewRefund).to.equal(ninePointNine);
    expect(previewKeepNet).to.equal(0n);

    await expect(core.connect(studentA).createRefundRequestKeeping(0n, "Hoan toan bo 100% net"))
      .to.emit(core, "RefundKeepingRequested")
      .withArgs(1n, studentA.address, 0n, 0n, ninePointNine);

    await core.connect(bcs1).voteRefundRequest(1n, true);
    await expect(() => core.connect(bcs2).voteRefundRequest(1n, true)).to.changeEtherBalance(
      studentA,
      ninePointNine
    );

    expect(await core.classFundBalance()).to.equal(0n);
    expect(await core.studentContributions(studentA.address)).to.equal(0n);
    expect(await core.getRefundable(studentA.address)).to.equal(0n);
  });

  it("Test 3 (Gian lận / Fraud): keep lớn hơn số đã nộp -> revert KeepExceedsContribution", async function () {
    const { core, studentA } = await deployFixture();

    const tenEth = ethers.parseEther("10");
    const elevenEth = ethers.parseEther("11");
    const refundable = ethers.parseEther("9.9");
    const keepNetEleven = ethers.parseEther("10.89"); // 11 - 1% = 10.89 ETH

    await core.connect(studentA).deposit({ value: tenEth });

    // previewRefundKeeping reverts KeepExceedsContribution
    await expect(core.previewRefundKeeping(studentA.address, elevenEth))
      .to.be.revertedWithCustomError(core, "KeepExceedsContribution")
      .withArgs(keepNetEleven, refundable);

    // createRefundRequestKeeping also reverts KeepExceedsContribution
    await expect(core.connect(studentA).createRefundRequestKeeping(elevenEth, "Gian lan giu qua so da nop"))
      .to.be.revertedWithCustomError(core, "KeepExceedsContribution")
      .withArgs(keepNetEleven, refundable);
  });

  it("Test 4: Đang có yêu cầu pending thì refundAmount tính trên phần còn lại", async function () {
    const { core, studentA } = await deployFixture();

    const tenEth = ethers.parseEther("10");
    await core.connect(studentA).deposit({ value: tenEth });

    // Create a regular pending refund request of 2 ETH
    const twoEth = ethers.parseEther("2");
    await core.connect(studentA).createRefundRequest(twoEth, "Yeu cau hoan truoc 2 ETH");

    // Remaining refundable is 9.9 - 2 = 7.9 ETH
    const remainingRefundable = ethers.parseEther("7.9");
    expect(await core.getRefundable(studentA.address)).to.equal(remainingRefundable);

    // With keepAmount = 1 ETH (keepNet = 0.99 ETH), refundAmount = 7.9 - 0.99 = 6.91 ETH
    const oneEth = ethers.parseEther("1");
    const expectedKeepNet = ethers.parseEther("0.99");
    const expectedRefund = ethers.parseEther("6.91");

    const [refundAmount, keepNet] = await core.previewRefundKeeping(studentA.address, oneEth);
    expect(refundAmount).to.equal(expectedRefund);
    expect(keepNet).to.equal(expectedKeepNet);

    await expect(core.connect(studentA).createRefundRequestKeeping(oneEth, "Hoan tiep tren phan con lai"))
      .to.emit(core, "RefundKeepingRequested")
      .withArgs(2n, studentA.address, oneEth, expectedKeepNet, expectedRefund);

    // Now remaining refundable is 7.9 - 6.91 = 0.99 ETH
    expect(await core.getRefundable(studentA.address)).to.equal(expectedKeepNet);
  });

  it("Test 5: Số lẻ wei (keep 99 wei, 101 wei, 1999 wei): Σ net + adminFeePool == Σ gross", async function () {
    const { core, studentA } = await deployFixture();

    // 1. previewDeposit on 99 wei: fee = 0, net = 99
    const [net99, fee99] = await core.previewDeposit(99n);
    expect(fee99).to.equal(0n);
    expect(net99).to.equal(99n);
    expect(net99 + fee99).to.equal(99n);

    // 2. previewDeposit on 101 wei: fee = 1, net = 100
    const [net101, fee101] = await core.previewDeposit(101n);
    expect(fee101).to.equal(1n);
    expect(net101).to.equal(100n);
    expect(net101 + fee101).to.equal(101n);

    // 3. previewDeposit on 1999 wei: fee = 19, net = 1980
    const [net1999, fee1999] = await core.previewDeposit(1999n);
    expect(fee1999).to.equal(19n);
    expect(net1999).to.equal(1980n);
    expect(net1999 + fee1999).to.equal(1999n);

    // 4. End-to-end deposit 10,000 wei and keep 1999 wei
    await core.connect(studentA).deposit({ value: 10000n });
    // fee on 10000 = 100, net = 9900
    expect(await core.getRefundable(studentA.address)).to.equal(9900n);

    const [refundAmount, keepNet] = await core.previewRefundKeeping(studentA.address, 1999n);
    expect(keepNet).to.equal(1980n);
    // refund = 9900 - 1980 = 7920 wei
    expect(refundAmount).to.equal(7920n);

    // Total conservation: refundAmount (7920) + keepNet (1980) + adminFeePool (100) = 10,000 wei gross!
    const totalAdminFee = await core.adminFeePool();
    expect(refundAmount + keepNet + totalAdminFee).to.equal(10000n);
  });

  it("Test 6: Bất biến address(this).balance == classFundBalance + adminFeePool sau mọi bước", async function () {
    const { core, advisor, bcs1, bcs2, studentA } = await deployFixture();

    const tenEth = ethers.parseEther("10");
    const oneEth = ethers.parseEther("1");

    // Invariant before any action
    expect(await core.getTotalContractBalance()).to.equal(0n);

    // Step 1: Deposit 10 ETH
    await core.connect(studentA).deposit({ value: tenEth });
    expect(await core.getTotalContractBalance()).to.equal(
      (await core.classFundBalance()) + (await core.adminFeePool())
    );

    // Step 2: Create refund request keeping 1 ETH
    await core.connect(studentA).createRefundRequestKeeping(oneEth, "Giữ 1 ETH");
    expect(await core.getTotalContractBalance()).to.equal(
      (await core.classFundBalance()) + (await core.adminFeePool())
    );

    // Step 3: Vote 1
    await core.connect(bcs1).voteRefundRequest(1n, true);
    expect(await core.getTotalContractBalance()).to.equal(
      (await core.classFundBalance()) + (await core.adminFeePool())
    );

    // Step 4: Vote 2 (triggers execution and ETH transfer)
    await core.connect(bcs2).voteRefundRequest(1n, true);
    expect(await core.getTotalContractBalance()).to.equal(
      (await core.classFundBalance()) + (await core.adminFeePool())
    );
  });

  it("Test 7: CVHT đã rút/chuyển hết adminFeePool trước đó vẫn hoàn được 8.91 ETH", async function () {
    const { core, advisor, bcs1, bcs2, studentA } = await deployFixture();

    const tenEth = ethers.parseEther("10");
    const oneEth = ethers.parseEther("1");
    const expectedRefund = ethers.parseEther("8.91");

    // Student A deposits 10 ETH
    await core.connect(studentA).deposit({ value: tenEth });
    const feeAvailable = await core.adminFeePool();
    expect(feeAvailable).to.equal(ethers.parseEther("0.1"));

    // Advisor moves the entire adminFeePool into classFundBalance (adminFeePool = 0)
    await core.connect(advisor).moveFeeToClassFund(feeAvailable);
    expect(await core.adminFeePool()).to.equal(0n);
    expect(await core.classFundBalance()).to.equal(ethers.parseEther("10"));

    // Student A requests refund keeping 1 ETH (refundAmount = 8.91 ETH)
    await core.connect(studentA).createRefundRequestKeeping(oneEth, "Hoan 8.91 ETH du phi da bi rut/chuyen het");

    // BCS votes
    await core.connect(bcs1).voteRefundRequest(1n, true);
    await expect(() => core.connect(bcs2).voteRefundRequest(1n, true)).to.changeEtherBalance(
      studentA,
      expectedRefund
    );

    // Refund completed successfully!
    expect(await core.studentContributions(studentA.address)).to.equal(ethers.parseEther("0.99"));
    // Class fund balance has 10 - 8.91 = 1.09 ETH (0.99 net keep + 0.1 fee moved)
    expect(await core.classFundBalance()).to.equal(ethers.parseEther("1.09"));
    expect(await core.adminFeePool()).to.equal(0n);
    expect(await core.getTotalContractBalance()).to.equal(ethers.parseEther("1.09"));
  });
});
