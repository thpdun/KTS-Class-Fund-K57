const fs = require("fs");
const path = require("path");
const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

describe("Phase 3 (Section D - On-chain Student List & Roster Hash Commitment)", function () {
  const MAX_CONTRACT_BYTES = 24576;
  const THREE_DAYS = 3 * 24 * 60 * 60;

  async function deployFixture() {
    const signers = await ethers.getSigners();
    const [advisor, bcs1, bcs2, bcs3, student1, student2, stranger, outsider] = signers;
    const Factory = await ethers.getContractFactory("ProjectCore", advisor);
    const core = await Factory.deploy();
    await core.waitForDeployment();
    return { core, advisor, bcs1, bcs2, bcs3, student1, student2, stranger, outsider, signers };
  }

  it("Phase 3 Bytecode Size check stays well within 24,576-byte EIP-170 limit", async function () {
    const artifactPath = path.join(
      __dirname,
      "../../artifacts/contracts/project/ProjectCore.sol/ProjectCore.json"
    );
    const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
    const deployedBytes = (artifact.deployedBytecode.length - 2) / 2;
    const initBytes = (artifact.bytecode.length - 2) / 2;
    const pct = ((deployedBytes / MAX_CONTRACT_BYTES) * 100).toFixed(2);
    console.log(
      `    [Phase 3 Bytecode] deployed=${deployedBytes} / ${MAX_CONTRACT_BYTES} bytes (${pct}%), initcode=${initBytes} bytes`
    );
    expect(deployedBytes).to.be.lessThanOrEqual(MAX_CONTRACT_BYTES);
  });

  it("Section D: setStudents enforces onlyAdvisor, batch cap <= 100, zero address check, and idempotency", async function () {
    const { core, advisor, student1, student2, outsider } = await deployFixture();

    expect(await core.MAX_BATCH()).to.equal(100n);
    expect(await core.enrolledCount()).to.equal(0n);

    // 1. Only advisor can call setStudents
    await expect(
      core.connect(outsider).setStudents([student1.address], true)
    ).to.be.revertedWithCustomError(core, "NotAdvisor");

    // 2. Batch size cap: 101 addresses reverts BatchTooLarge
    const batch101 = Array.from({ length: 101 }, () => ethers.Wallet.createRandom().address);
    await expect(
      core.connect(advisor).setStudents(batch101, true)
    ).to.be.revertedWithCustomError(core, "BatchTooLarge");

    // Exactly 100 addresses succeeds
    const batch100 = Array.from({ length: 100 }, () => ethers.Wallet.createRandom().address);
    await expect(core.connect(advisor).setStudents(batch100, true)).to.not.be.reverted;
    expect(await core.enrolledCount()).to.equal(100n);

    // 3. Zero address in batch reverts InvalidAddress
    await expect(
      core.connect(advisor).setStudents([ethers.ZeroAddress], true)
    ).to.be.revertedWithCustomError(core, "InvalidAddress");

    // 4. Advisor cannot be enrolled as student
    await expect(
      core.connect(advisor).setStudents([advisor.address], true)
    ).to.be.revertedWithCustomError(core, "AdvisorCannotBeStudent");

    // 5. Idempotency: duplicate addresses in batch do not inflate enrolledCount
    const prevCount = await core.enrolledCount();
    await expect(core.connect(advisor).setStudents([student1.address, student1.address], true))
      .to.emit(core, "StudentEnrollmentUpdated")
      .withArgs(student1.address, true);
    expect(await core.enrolledCount()).to.equal(prevCount + 1n);
    expect(await core.isStudent(student1.address)).to.equal(true);

    // Re-enrolling already enrolled student is no-op
    await core.connect(advisor).setStudents([student1.address], true);
    expect(await core.enrolledCount()).to.equal(prevCount + 1n);

    // Removing student decrements enrolledCount
    await expect(core.connect(advisor).setStudents([student1.address], false))
      .to.emit(core, "StudentEnrollmentUpdated")
      .withArgs(student1.address, false);
    expect(await core.enrolledCount()).to.equal(prevCount);
    expect(await core.isStudent(student1.address)).to.equal(false);
  });

  it("Section D: BCS membership requires prior student enrollment, and active BCS cannot be removed as student", async function () {
    const { core, advisor, bcs1 } = await deployFixture();

    // 1. Trying to add non-student as BCS reverts BCSMustBeEnrolledStudent
    expect(await core.isStudent(bcs1.address)).to.equal(false);
    await expect(
      core.connect(advisor).setBCSMember(bcs1.address, true)
    ).to.be.revertedWithCustomError(core, "BCSMustBeEnrolledStudent");

    // 2. Enroll as student first, then adding as BCS succeeds
    await core.connect(advisor).setStudents([bcs1.address], true);
    expect(await core.isStudent(bcs1.address)).to.equal(true);
    await core.connect(advisor).setBCSMember(bcs1.address, true);
    expect(await core.isBCSMember(bcs1.address)).to.equal(true);

    // 3. Trying to remove student while still active BCS reverts StudentIsBCS
    await expect(
      core.connect(advisor).setStudents([bcs1.address], false)
    ).to.be.revertedWithCustomError(core, "StudentIsBCS");

    // 4. Remove BCS first, then removing student succeeds
    await core.connect(advisor).setBCSMember(bcs1.address, false);
    await expect(core.connect(advisor).setStudents([bcs1.address], false)).to.not.be.reverted;
    expect(await core.isStudent(bcs1.address)).to.equal(false);
  });

  it("Section D: Whitelist deposit & receive - strangers and advisor are reverted with NotEnrolledStudent", async function () {
    const { core, advisor, student1, stranger } = await deployFixture();
    const oneEth = ethers.parseEther("1");

    // 1. Stranger deposit() reverts NotEnrolledStudent
    await expect(
      core.connect(stranger).deposit({ value: oneEth })
    ).to.be.revertedWithCustomError(core, "NotEnrolledStudent")
      .withArgs(stranger.address);

    // 2. Stranger direct receive() reverts NotEnrolledStudent
    await expect(
      stranger.sendTransaction({ to: await core.getAddress(), value: oneEth })
    ).to.be.revertedWithCustomError(core, "NotEnrolledStudent")
      .withArgs(stranger.address);

    // 3. Advisor deposit() and direct receive() revert NotEnrolledStudent
    await expect(
      core.connect(advisor).deposit({ value: oneEth })
    ).to.be.revertedWithCustomError(core, "NotEnrolledStudent")
      .withArgs(advisor.address);

    await expect(
      advisor.sendTransaction({ to: await core.getAddress(), value: oneEth })
    ).to.be.revertedWithCustomError(core, "NotEnrolledStudent")
      .withArgs(advisor.address);

    // 4. Enrolled student deposit() and direct receive() succeed
    await core.connect(advisor).setStudents([student1.address], true);
    await expect(core.connect(student1).deposit({ value: oneEth })).to.emit(core, "FundDeposited");
    await expect(
      student1.sendTransaction({ to: await core.getAddress(), value: oneEth })
    ).to.emit(core, "FundDeposited");
    expect(await core.studentTotalDeposited(student1.address)).to.equal(ethers.parseEther("2"));
  });

  it("Section D: Removed student can still create and execute refund requests if studentContributions > 0", async function () {
    const { core, advisor, bcs1, bcs2, bcs3, student1 } = await deployFixture();
    await core.connect(advisor).setStudents([bcs1.address, bcs2.address, bcs3.address, student1.address], true);
    for (const b of [bcs1, bcs2, bcs3]) {
      await core.connect(advisor).setBCSMember(b.address, true);
    }
    await time.increase(THREE_DAYS);

    // Student deposits 5 ETH (net 4.95 ETH)
    await core.connect(student1).deposit({ value: ethers.parseEther("5") });
    expect(await core.studentContributions(student1.address)).to.equal(ethers.parseEther("4.95"));

    // Advisor unenrolls student1 (e.g. dropped out of class)
    await core.connect(advisor).setStudents([student1.address], false);
    expect(await core.isStudent(student1.address)).to.equal(false);

    // Student1 cannot deposit anymore
    await expect(
      core.connect(student1).deposit({ value: ethers.parseEther("1") })
    ).to.be.revertedWithCustomError(core, "NotEnrolledStudent")
      .withArgs(student1.address);

    // BUT student1 CAN still create refund request for net contribution!
    const twoEth = ethers.parseEther("2");
    await expect(core.connect(student1).createRefundRequest(twoEth, "Rut quy sau thoi hoc"))
      .to.emit(core, "RefundRequestCreated");

    // BCS votes 2/3 >= 51% -> auto-executes payout to student1
    await core.connect(bcs1).voteRefundRequest(1, true);
    await expect(() => core.connect(bcs2).voteRefundRequest(1, true)).to.changeEtherBalance(
      student1,
      twoEth
    );

    const ref = await core.refundRequests(1);
    expect(ref.status).to.equal(2n); // Executed
    expect(await core.studentContributions(student1.address)).to.equal(ethers.parseEther("2.95"));
    expect(await core.studentTotalDeposited(student1.address)).to.equal(ethers.parseEther("5"));
  });

  it("Section D: commitRoster hash commitment is advisor-only and emits RosterCommitted", async function () {
    const { core, advisor, outsider } = await deployFixture();
    const sampleHash = ethers.keccak256(ethers.toUtf8Bytes("CANONICAL_ROSTER_V1"));

    expect(await core.rosterHash()).to.equal(ethers.ZeroHash);

    // Outsider cannot commit roster hash
    await expect(
      core.connect(outsider).commitRoster(sampleHash)
    ).to.be.revertedWithCustomError(core, "NotAdvisor");

    // Advisor commits roster hash
    await expect(core.connect(advisor).commitRoster(sampleHash))
      .to.emit(core, "RosterCommitted")
      .withArgs(sampleHash, advisor.address, (t) => t > 0);

    expect(await core.rosterHash()).to.equal(sampleHash);
  });

  it("Section D: getUnaccountedBalance detects forced ETH without corrupting accounting invariant", async function () {
    const { core, advisor, student1 } = await deployFixture();
    await core.connect(advisor).setStudents([student1.address], true);

    await core.connect(student1).deposit({ value: ethers.parseEther("10") });
    expect(await core.classFundBalance()).to.equal(ethers.parseEther("9.9"));
    expect(await core.adminFeePool()).to.equal(ethers.parseEther("0.1"));
    expect(await core.getUnaccountedBalance()).to.equal(0n);

    // Force 3 ETH into contract using Hardhat network helper
    const coreAddr = await core.getAddress();
    const forcedTotal = ethers.parseEther("13"); // 10 ETH recorded + 3 ETH forced
    await ethers.provider.send("hardhat_setBalance", [coreAddr, "0x" + forcedTotal.toString(16)]);

    // Contract balance is now 13 ETH, recorded pools sum to 10 ETH
    expect(await ethers.provider.getBalance(coreAddr)).to.equal(forcedTotal);
    expect(await core.classFundBalance()).to.equal(ethers.parseEther("9.9"));
    expect(await core.adminFeePool()).to.equal(ethers.parseEther("0.1"));
    expect(await core.getTotalContractBalance()).to.equal(forcedTotal);
    const recordedTotal = (await core.classFundBalance()) + (await core.adminFeePool());
    expect(recordedTotal).to.equal(ethers.parseEther("10"));

    // Invariant: balance >= recorded pools holds
    expect(await ethers.provider.getBalance(coreAddr)).to.be.greaterThan(recordedTotal);

    // getUnaccountedBalance returns exact 3 ETH difference
    expect(await core.getUnaccountedBalance()).to.equal(ethers.parseEther("3"));
  });
});
