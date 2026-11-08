const fs = require("fs");
const path = require("path");
const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

describe("Phase 2 (Sections B & C - Governance Snapshot, Delay, Quorum & Conflict of Interest)", function () {
  const MAX_CONTRACT_BYTES = 24576;
  const THREE_DAYS = 3 * 24 * 60 * 60;
  const SEVEN_DAYS = 7 * 24 * 60 * 60;

  async function deployFixture() {
    const signers = await ethers.getSigners();
    const [advisor, bcs1, bcs2, bcs3, bcs4, bcs5, studentA, recipient, outsider] = signers;
    const Factory = await ethers.getContractFactory("ProjectCore", advisor);
    const core = await Factory.deploy();
    await core.waitForDeployment();
    await core.connect(advisor).setStudents(
      signers.slice(1, 10).map((s) => s.address),
      true
    );
    return { core, advisor, bcs1, bcs2, bcs3, bcs4, bcs5, studentA, recipient, outsider, signers };
  }

  async function setupActiveBCS(core, advisor, members) {
    for (const m of members) {
      await core.connect(advisor).setBCSMember(m.address, true);
    }
    await time.increase(THREE_DAYS);
  }

  it("Phase 2 Bytecode Size check stays well within 24,576-byte EIP-170 limit", async function () {
    const artifactPath = path.join(
      __dirname,
      "../../artifacts/contracts/project/ProjectCore.sol/ProjectCore.json"
    );
    const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
    const deployedBytes = (artifact.deployedBytecode.length - 2) / 2;
    const initBytes = (artifact.bytecode.length - 2) / 2;
    const pct = ((deployedBytes / MAX_CONTRACT_BYTES) * 100).toFixed(2);
    console.log(
      `    [Phase 2 Bytecode] deployed=${deployedBytes} / ${MAX_CONTRACT_BYTES} bytes (${pct}%), initcode=${initBytes} bytes`
    );
    expect(deployedBytes).to.be.lessThanOrEqual(MAX_CONTRACT_BYTES);
  });

  it("Section B constants & 3-day activation delay: immature BCS blocked until exact 3-day boundary, re-add resets delay", async function () {
    const { core, advisor, bcs1, bcs2, bcs3, bcs4, studentA, recipient } = await deployFixture();

    expect(await core.BCS_ACTIVATION_DELAY()).to.equal(BigInt(THREE_DAYS));
    expect(await core.MIN_BCS_FOR_PROPOSAL()).to.equal(3n);
    expect(await core.MAX_BCS()).to.equal(15n);
    expect(await core.getBCSList()).to.deep.equal([]);

    await setupActiveBCS(core, advisor, [bcs1, bcs2, bcs3]);
    await core.connect(studentA).deposit({ value: ethers.parseEther("10") });
    await core.connect(bcs1).createSpendRequest(recipient.address, ethers.parseEther("1"), "Existing req");
    await core.connect(studentA).createRefundRequest(ethers.parseEther("1"), "Existing refund");

    // Add bcs4 at tAdd
    const tx = await core.connect(advisor).setBCSMember(bcs4.address, true);
    const receipt = await tx.wait();
    const block = await ethers.provider.getBlock(receipt.blockNumber);
    const tAdd = Number(block.timestamp);

    expect(await core.isBCSMember(bcs4.address)).to.equal(true);
    expect(await core.memberSince(bcs4.address)).to.equal(BigInt(tAdd + THREE_DAYS));
    expect(await core.isEligibleVoterAt(bcs4.address, tAdd + THREE_DAYS - 1)).to.equal(false);
    expect(await core.isEligibleVoterAt(bcs4.address, tAdd + THREE_DAYS)).to.equal(true);
    expect(await core.eligibleBCSCount(tAdd + THREE_DAYS - 1)).to.equal(3n);
    expect(await core.eligibleBCSCount(tAdd + THREE_DAYS)).to.equal(4n);

    // Move through exact pre-boundary seconds (-3, -2, -1) so each mined revert stays < tAdd + THREE_DAYS
    await time.setNextBlockTimestamp(tAdd + THREE_DAYS - 3);
    await expect(
      core.connect(bcs4).voteSpendRequest(1, true)
    ).to.be.revertedWithCustomError(core, "NotActiveBCS");

    await time.setNextBlockTimestamp(tAdd + THREE_DAYS - 2);
    await expect(
      core.connect(bcs4).voteRefundRequest(1, true)
    ).to.be.revertedWithCustomError(core, "NotActiveBCS");

    await time.setNextBlockTimestamp(tAdd + THREE_DAYS - 1);
    await expect(
      core.connect(bcs4).createSpendRequest(recipient.address, ethers.parseEther("1"), "Too early")
    ).to.be.revertedWithCustomError(core, "NotActiveBCS");

    // At exact tAdd + THREE_DAYS -> onlyActiveBCS passes! (New request allowed; existing request still blocks by creation snapshot)
    await time.setNextBlockTimestamp(tAdd + THREE_DAYS);
    await expect(
      core.connect(bcs4).createSpendRequest(recipient.address, ethers.parseEther("1"), "Now active")
    ).to.emit(core, "SpendRequestCreated");

    // Remove and re-add bcs4 -> resets memberSince to tReadd + THREE_DAYS
    await core.connect(advisor).setBCSMember(bcs4.address, false);
    expect(await core.memberSince(bcs4.address)).to.equal(0n);

    const txReadd = await core.connect(advisor).setBCSMember(bcs4.address, true);
    const rReadd = await txReadd.wait();
    const bReadd = await ethers.provider.getBlock(rReadd.blockNumber);
    const tReadd = Number(bReadd.timestamp);
    expect(await core.memberSince(bcs4.address)).to.equal(BigInt(tReadd + THREE_DAYS));

    await expect(
      core.connect(bcs4).createSpendRequest(recipient.address, ethers.parseEther("1"), "Reset delay blocks immediate call")
    ).to.be.revertedWithCustomError(core, "NotActiveBCS");
  });

  it("Section B MAX_BCS = 15 & O(1) swap-and-pop removal from head/middle/tail", async function () {
    const { core, advisor, signers } = await deployFixture();

    const members = signers.slice(1, 16); // 15 accounts
    expect(members.length).to.equal(15);
    await core.connect(advisor).setStudents(members.map((m) => m.address), true);
    for (const m of members) {
      await core.connect(advisor).setBCSMember(m.address, true);
    }
    expect(await core.activeBCSCount()).to.equal(15n);
    expect((await core.getBCSList()).length).to.equal(15);

    const extra = ethers.Wallet.createRandom();
    await core.connect(advisor).setStudents([extra.address], true);
    await expect(core.connect(advisor).setBCSMember(extra.address, true)).to.be.revertedWithCustomError(
      core,
      "MaxBCSReached"
    );

    // Swap-and-pop head (0), middle (6), and current tail
    await core.connect(advisor).setBCSMember(members[0].address, false);
    await core.connect(advisor).setBCSMember(members[6].address, false);
    let list = await core.getBCSList();
    expect(list.length).to.equal(13);
    expect(list).to.not.include(members[0].address);
    expect(list).to.not.include(members[6].address);

    // Remove current last element
    const tailAddr = list[list.length - 1];
    await core.connect(advisor).setBCSMember(tailAddr, false);
    list = await core.getBCSList();
    expect(list.length).to.equal(12);
    expect(list).to.not.include(tailAddr);

    // Can re-add back up to 15, then 16th reverts MaxBCSReached again
    await core.connect(advisor).setBCSMember(members[0].address, true);
    await core.connect(advisor).setBCSMember(members[6].address, true);
    await core.connect(advisor).setBCSMember(tailAddr, true);
    expect((await core.getBCSList()).length).to.equal(15);
    await expect(core.connect(advisor).setBCSMember(extra.address, true)).to.be.revertedWithCustomError(
      core,
      "MaxBCSReached"
    );
  });

  it("Section B MIN_BCS_FOR_PROPOSAL = 3 blocks BOTH createSpendRequest and student createRefundRequest until 3 eligible BCS exist", async function () {
    const { core, advisor, bcs1, bcs2, bcs3, studentA, recipient } = await deployFixture();
    await core.connect(studentA).deposit({ value: ethers.parseEther("5") });

    // Only 2 eligible BCS
    await setupActiveBCS(core, advisor, [bcs1, bcs2]);

    await expect(
      core.connect(bcs1).createSpendRequest(recipient.address, ethers.parseEther("1"), "Under quorum")
    )
      .to.be.revertedWithCustomError(core, "NotEnoughBCS")
      .withArgs(2n, 3n);

    await expect(core.connect(studentA).createRefundRequest(ethers.parseEther("1"), "Student refund under quorum"))
      .to.be.revertedWithCustomError(core, "NotEnoughBCS")
      .withArgs(2n, 3n);

    // Add 3rd BCS (not yet past 3-day activation -> bcsList.length == 3, eligible == 2!)
    await core.connect(advisor).setBCSMember(bcs3.address, true);
    expect(await core.activeBCSCount()).to.equal(3n);

    await expect(
      core.connect(bcs1).createSpendRequest(recipient.address, ethers.parseEther("1"), "3rd still pending")
    )
      .to.be.revertedWithCustomError(core, "NotEnoughBCS")
      .withArgs(2n, 3n);

    await expect(core.connect(studentA).createRefundRequest(ethers.parseEther("1"), "3rd still pending"))
      .to.be.revertedWithCustomError(core, "NotEnoughBCS")
      .withArgs(2n, 3n);

    // Advance 3 days -> 3 eligible -> both succeed with voterBase = 3
    await time.increase(THREE_DAYS);
    await core.connect(bcs1).createSpendRequest(recipient.address, ethers.parseEther("1"), "Now allowed");
    await core.connect(studentA).createRefundRequest(ethers.parseEther("1"), "Now allowed");
    expect((await core.spendRequests(1)).voterBase).to.equal(3n);
    expect((await core.refundRequests(1)).voterBase).to.equal(3n);
  });

  it("Section B snapshot voterBase stays immutable on mid-vote add/remove, and fallback executeRefundRequest works even if all BCS removed", async function () {
    const { core, advisor, bcs1, bcs2, bcs3, bcs4, bcs5, studentA, recipient } = await deployFixture();
    await setupActiveBCS(core, advisor, [bcs1, bcs2, bcs3]);
    await core.connect(studentA).deposit({ value: ethers.parseEther("10") });

    // Proposal 1 (Spend) & Proposal 1 (Refund) created with voterBase = 3
    await core.connect(bcs1).createSpendRequest(recipient.address, ethers.parseEther("2"), "Snapshot test");
    await core.connect(bcs1).voteSpendRequest(1, true); // 1/3 -> Pending

    // 1. Add bcs4, bcs5 -> voterBase stays 3; even after removal of bcs2 & bcs3 -> 1/3 still fails ThresholdNotMet(1, 3)
    await core.connect(advisor).setBCSMember(bcs4.address, true);
    await core.connect(advisor).setBCSMember(bcs5.address, true);
    await time.increase(THREE_DAYS);

    expect((await core.spendRequests(1)).voterBase).to.equal(3n);
    await core.connect(advisor).setBCSMember(bcs2.address, false);
    await core.connect(advisor).setBCSMember(bcs3.address, false);

    // Removed bcs2 cannot vote
    await expect(core.connect(bcs2).voteSpendRequest(1, true)).to.be.revertedWithCustomError(
      core,
      "NotActiveBCS"
    );

    // Threshold denominator MUST remain 3 (not dynamically changed when BCS removed!)
    await expect(core.connect(bcs1).executeSpendRequest(1))
      .to.be.revertedWithCustomError(core, "ThresholdNotMet")
      .withArgs(1n, 3n);

    // 2. Fallback executeRefundRequest succeeds even after ALL BCS removed once 2/3 reached Ready
    await setupActiveBCS(core, advisor, [bcs2, bcs3]); // bcs1, bcs2, bcs3 active again (and bcs4, bcs5) -> 5 active
    const Toggle = await ethers.getContractFactory("MockToggleReceiver");
    const studentMock = await Toggle.deploy(true);
    await studentMock.waitForDeployment();
    const coreAddr = await core.getAddress();
    await core.connect(advisor).setStudents([await studentMock.getAddress()], true);

    await studentMock.depositTo(coreAddr, { value: ethers.parseEther("3") }); // net 2.97
    await studentMock.requestRefundFrom(coreAddr, ethers.parseEther("2"), "Fallback after removal");

    expect((await core.refundRequests(1)).voterBase).to.equal(5n);
    await core.connect(bcs1).voteRefundRequest(1, true);
    await core.connect(bcs2).voteRefundRequest(1, true);
    await expect(core.connect(bcs3).voteRefundRequest(1, true)).to.emit(core, "RefundExecutionFailed"); // 3/5 = 60% -> Ready

    // Advisor removes all 5 BCS
    for (const m of [bcs1, bcs2, bcs3, bcs4, bcs5]) {
      await core.connect(advisor).setBCSMember(m.address, false);
    }
    expect(await core.activeBCSCount()).to.equal(0n);

    // Student still recovers ETH via executeRefundRequest using preserved voterBase = 5
    await studentMock.setRejectETH(false);
    await expect(() => studentMock.executeRefundOn(coreAddr, 1)).to.changeEtherBalance(
      studentMock,
      ethers.parseEther("2")
    );
  });

  it("Section B (Fraud): Advisor injects 3 phantom BCS wallets mid-vote -> blocked before 3 days (NotActiveBCS) and after 3 days (VoterNotEligibleAtCreation)", async function () {
    const { core, advisor, bcs1, bcs2, bcs3, signers, studentA, recipient } = await deployFixture();
    await setupActiveBCS(core, advisor, [bcs1, bcs2, bcs3]);
    await core.connect(studentA).deposit({ value: ethers.parseEther("10") });

    // Create spend & refund proposals with 3 legitimate BCS
    await core.connect(bcs1).createSpendRequest(recipient.address, ethers.parseEther("4"), "Spend before phantom");
    await core.connect(studentA).createRefundRequest(ethers.parseEther("2"), "Refund before phantom");

    // Advisor immediately adds 3 phantom wallets right after creation
    const [phantom1, phantom2, phantom3] = signers.slice(10, 13);
    await core.connect(advisor).setStudents([phantom1.address, phantom2.address, phantom3.address], true);
    await core.connect(advisor).setBCSMember(phantom1.address, true);
    await core.connect(advisor).setBCSMember(phantom2.address, true);
    await core.connect(advisor).setBCSMember(phantom3.address, true);

    // Before 3 days: blocked by NotActiveBCS
    await expect(core.connect(phantom1).voteSpendRequest(1, true)).to.be.revertedWithCustomError(
      core,
      "NotActiveBCS"
    );

    // Advance 3 days (still well inside 7-day voting period): phantoms become active BCS globally,
    // BUT were NOT eligible at proposal.createdAt -> VoterNotEligibleAtCreation!
    await time.increase(THREE_DAYS);

    for (const ph of [phantom1, phantom2, phantom3]) {
      await expect(core.connect(ph).voteSpendRequest(1, true))
        .to.be.revertedWithCustomError(core, "VoterNotEligibleAtCreation")
        .withArgs(1n, ph.address);

      await expect(core.connect(ph).voteRefundRequest(1, true))
        .to.be.revertedWithCustomError(core, "VoterNotEligibleAtCreation")
        .withArgs(1n, ph.address);
    }

    expect((await core.spendRequests(1)).yesVotes).to.equal(0n);
    expect((await core.refundRequests(1)).yesVotes).to.equal(0n);
    expect((await core.spendRequests(1)).voterBase).to.equal(3n);
  });

  it("Section C: conflict of interest blocks applicant/BCS-recipient voting, subtracts 1 from voterBase only if eligible, enforces yesVotes >= 2", async function () {
    const { core, advisor, bcs1, bcs2, bcs3, bcs4, outsider, studentA } = await deployFixture();
    await setupActiveBCS(core, advisor, [bcs1, bcs2, bcs3]);
    await core.connect(bcs1).deposit({ value: ethers.parseEther("5") });
    await core.connect(studentA).deposit({ value: ethers.parseEther("10") });

    // 1 & 4 (Fraud): BCS1 requests refund -> voterBase = 2; BCS1 self-vote reverts ConflictOfInterest; needs 2 remaining votes
    await core.connect(bcs1).createRefundRequest(ethers.parseEther("2"), "BCS1 self refund");
    expect((await core.refundRequests(1)).voterBase).to.equal(2n);

    await expect(core.connect(bcs1).voteRefundRequest(1, true)).to.be.revertedWithCustomError(
      core,
      "ConflictOfInterest"
    );
    await core.connect(bcs2).voteRefundRequest(1, true); // 1/2 = 50% -> Pending
    expect((await core.refundRequests(1)).status).to.equal(0n); // Pending

    await core.connect(bcs3).voteRefundRequest(1, true); // 2/2 = 100% -> Executed (yesVotes == 2)
    const ref1 = await core.refundRequests(1);
    expect(ref1.status).to.equal(2n); // Executed
    expect(ref1.yesVotes).to.equal(2n);

    // 2: SpendRequest with eligible BCS recipient (bcs3) -> voterBase = 2; bcs3 blocked with ConflictOfInterest
    await core.connect(bcs1).createSpendRequest(bcs3.address, ethers.parseEther("1"), "Reimburse bcs3");
    expect((await core.spendRequests(1)).voterBase).to.equal(2n);

    await expect(core.connect(bcs3).voteSpendRequest(1, true)).to.be.revertedWithCustomError(
      core,
      "ConflictOfInterest"
    );
    await core.connect(bcs1).voteSpendRequest(1, true); // 1/2 -> Pending
    expect((await core.spendRequests(1)).status).to.equal(0n);

    await core.connect(bcs2).voteSpendRequest(1, true); // 2/2 -> Executed (yesVotes == 2)
    const req1 = await core.spendRequests(1);
    expect(req1.status).to.equal(2n);
    expect(req1.yesVotes).to.equal(2n);

    // 3: SpendRequest with non-BCS recipient (outsider) -> voterBase = 3; ALL BCS (including creator bcs1) can vote
    await core.connect(bcs1).createSpendRequest(outsider.address, ethers.parseEther("1"), "External vendor");
    expect((await core.spendRequests(2)).voterBase).to.equal(3n);
    await core.connect(bcs1).voteSpendRequest(2, true);
    await core.connect(bcs2).voteSpendRequest(2, true);
    const req2 = await core.spendRequests(2);
    expect(req2.status).to.equal(2n);
    expect(req2.yesVotes).to.equal(2n);

    // Edge case: bcs4 added (pending < 3 days) is SpendRequest recipient -> voterBase stays 3 (NOT 2!),
    // and after 3 days bcs4 STILL reverts ConflictOfInterest if trying to vote
    await core.connect(advisor).setBCSMember(bcs4.address, true);
    await core.connect(bcs1).createSpendRequest(bcs4.address, ethers.parseEther("1"), "Pending BCS recipient");
    expect((await core.spendRequests(3)).voterBase).to.equal(3n);

    await time.increase(THREE_DAYS);
    await expect(core.connect(bcs4).voteSpendRequest(3, true)).to.be.revertedWithCustomError(
      core,
      "ConflictOfInterest"
    );
    await core.connect(bcs1).voteSpendRequest(3, true);
    await core.connect(bcs2).voteSpendRequest(3, true);
    expect((await core.spendRequests(3)).yesVotes).to.be.greaterThanOrEqual(2n);
  });

  it("Issue 2: Majority No-votes rejects proposal, releases reserved fund immediately, prevents double-release, and enforces open spend proposal limit (MAX_OPEN_SPEND_PER_CREATOR = 3)", async function () {
    const { core, advisor, bcs1, bcs2, bcs3, studentA, recipient } = await deployFixture();
    await setupActiveBCS(core, advisor, [bcs1, bcs2, bcs3]);
    await core.connect(studentA).deposit({ value: ethers.parseEther("10") }); // 9.9 ETH net class fund

    expect(await core.MAX_OPEN_SPEND_PER_CREATOR()).to.equal(3n);
    expect(await core.openSpendRequestCount(bcs1.address)).to.equal(0n);

    // 1. (c) Gian lận: 1 BCS tạo 4 đề xuất chi mở đồng thời -> đề xuất thứ 4 bị revert với TooManyOpenRequests
    await core.connect(bcs1).createSpendRequest(recipient.address, ethers.parseEther("1"), "Spend 1");
    await core.connect(bcs1).createSpendRequest(recipient.address, ethers.parseEther("1"), "Spend 2");
    await core.connect(bcs1).createSpendRequest(recipient.address, ethers.parseEther("1"), "Spend 3");
    expect(await core.openSpendRequestCount(bcs1.address)).to.equal(3n);

    await expect(
      core.connect(bcs1).createSpendRequest(recipient.address, ethers.parseEther("1"), "Spend 4 - Exceeds limit")
    ).to.be.revertedWithCustomError(core, "TooManyOpenRequests");

    // 2. (a) BCS bỏ phiếu chống chiếm đa số:
    // Với Spend 1 (voterBase = 3): cần 51% (ít nhất 2 phiếu thuận).
    // Nếu bcs1 vote No, bcs2 vote No -> max possible Yes = 1 < 2 -> Chuyển sang Rejected ngay lập tức!
    const reservedBefore = await core.reservedSpendAmount();
    expect(reservedBefore).to.equal(ethers.parseEther("3"));

    await core.connect(bcs1).voteSpendRequest(1, false); // 1 No, maxYes = 2 -> still Pending
    expect((await core.spendRequests(1)).status).to.equal(0n); // Pending

    await expect(core.connect(bcs2).voteSpendRequest(1, false)) // 2 No, maxYes = 1 < 2 -> REJECTED!
      .to.emit(core, "SpendRequestRejected")
      .withArgs(1n);

    const req1 = await core.spendRequests(1);
    expect(req1.status).to.equal(3n); // RequestStatus.Rejected (0=Pending, 1=Ready, 2=Executed, 3=Rejected, 4=Expired, 5=Cancelled)
    expect(await core.reservedSpendAmount()).to.equal(reservedBefore - ethers.parseEther("1"));
    expect(await core.openSpendRequestCount(bcs1.address)).to.equal(2n); // Giảm biến đếm open spend!

    // (b) Sau đó gọi tiếp không thể nhả tiền lần hai:
    // bcs3 thử vote -> revert InvalidRequestStatus
    await expect(core.connect(bcs3).voteSpendRequest(1, false))
      .to.be.revertedWithCustomError(core, "InvalidRequestStatus")
      .withArgs(1n);

    // executeSpendRequest -> revert InvalidRequestStatus
    await expect(core.connect(bcs2).executeSpendRequest(1))
      .to.be.revertedWithCustomError(core, "InvalidRequestStatus")
      .withArgs(1n);

    // expireSpendRequest -> revert InvalidRequestStatus
    await time.increase(7 * 24 * 60 * 60 + 10);
    await expect(core.expireSpendRequest(1))
      .to.be.revertedWithCustomError(core, "InvalidRequestStatus")
      .withArgs(1n);

    // Số tiền reserved vẫn giữ nguyên (không bị trừ lần hai)
    expect(await core.reservedSpendAmount()).to.equal(ethers.parseEther("2"));

    // Vì count đã giảm về 2, bcs1 giờ có thể tạo thêm đề xuất mới thành công
    await core.connect(bcs1).createSpendRequest(recipient.address, ethers.parseEther("1"), "Spend 4 after reject");
    expect(await core.openSpendRequestCount(bcs1.address)).to.equal(3n);

    // 3. Kiểm tra tương tự đối với RefundRequest:
    // Sinh viên A xin hoàn 2 ETH -> reservedRefund = 2 ETH, pendingStudentRefund = 2 ETH
    await core.connect(studentA).createRefundRequest(ethers.parseEther("2"), "Refund request");
    expect(await core.reservedRefundAmount()).to.equal(ethers.parseEther("2"));
    expect(await core.pendingStudentRefundAmount(studentA.address)).to.equal(ethers.parseEther("2"));

    // 2 No votes trên voterBase 3 -> Rejected
    await core.connect(bcs1).voteRefundRequest(1, false);
    await expect(core.connect(bcs2).voteRefundRequest(1, false))
      .to.emit(core, "RefundRequestRejected")
      .withArgs(1n);

    const ref1 = await core.refundRequests(1);
    expect(ref1.status).to.equal(3n); // RequestStatus.Rejected
    expect(await core.reservedRefundAmount()).to.equal(0n);
    expect(await core.pendingStudentRefundAmount(studentA.address)).to.equal(0n);

    // Gọi expire / execute trên Refund đã Rejected đều bị revert InvalidRefundStatus
    await expect(core.executeRefundRequest(1))
      .to.be.revertedWithCustomError(core, "InvalidRefundStatus")
      .withArgs(1n);
    await expect(core.expireRefundRequest(1))
      .to.be.revertedWithCustomError(core, "InvalidRefundStatus")
      .withArgs(1n);
  });
});
