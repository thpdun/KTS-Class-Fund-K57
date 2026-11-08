const fs = require("fs");
const path = require("path");
const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

describe("Phase 4 (Section E - On-chain Fund Collections & Per-Collection Deposits)", function () {
  const MAX_CONTRACT_BYTES = 24576;
  const THREE_DAYS = 3 * 24 * 60 * 60;
  const SEVEN_DAYS = 7 * 24 * 60 * 60;

  async function deployFixture() {
    const signers = await ethers.getSigners();
    const [advisor, bcs1, bcs2, bcs3, student1, student2, stranger] = signers;
    const Factory = await ethers.getContractFactory("ProjectCore", advisor);
    const core = await Factory.deploy();
    await core.waitForDeployment();

    // Setup 5 enrolled students
    await core.connect(advisor).setStudents(
      [bcs1.address, bcs2.address, bcs3.address, student1.address, student2.address],
      true
    );

    // Setup 3 active BCS members with 3-day activation delay
    await core.connect(advisor).setBCSMember(bcs1.address, true);
    await core.connect(advisor).setBCSMember(bcs2.address, true);
    await core.connect(advisor).setBCSMember(bcs3.address, true);
    await time.increase(THREE_DAYS + 10);

    return { core, advisor, bcs1, bcs2, bcs3, student1, student2, stranger, signers };
  }

  it("Phase 4 Bytecode Size check stays well within 24,576-byte EIP-170 limit", async function () {
    const artifactPath = path.join(
      __dirname,
      "../../artifacts/contracts/project/ProjectCore.sol/ProjectCore.json"
    );
    const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
    const deployedBytes = (artifact.deployedBytecode.length - 2) / 2;
    const initBytes = (artifact.bytecode.length - 2) / 2;
    const pct = ((deployedBytes / MAX_CONTRACT_BYTES) * 100).toFixed(2);
    console.log(
      `    [Phase 4 Bytecode] deployed=${deployedBytes} / ${MAX_CONTRACT_BYTES} bytes (${pct}%), initcode=${initBytes} bytes`
    );
    expect(deployedBytes).to.be.lessThanOrEqual(MAX_CONTRACT_BYTES);
  });

  it("Section E1: createCollection validates parameters and restricts caller to active BCS only", async function () {
    const { core, advisor, bcs1, student1, stranger } = await deployFixture();

    const now = await time.latest();
    const deadline = now + SEVEN_DAYS;

    // 1. Permission checks: stranger, student, and advisor are rejected
    await expect(
      core.connect(stranger).createCollection(ethers.parseEther("1.0"), deadline, "Quy hoc ky 1")
    ).to.be.revertedWithCustomError(core, "NotActiveBCS");

    await expect(
      core.connect(student1).createCollection(ethers.parseEther("1.0"), deadline, "Quy hoc ky 1")
    ).to.be.revertedWithCustomError(core, "NotActiveBCS");

    await expect(
      core.connect(advisor).createCollection(ethers.parseEther("1.0"), deadline, "Quy hoc ky 1")
    ).to.be.revertedWithCustomError(core, "NotActiveBCS");

    // 2. Target 0 reverts ZeroAmount
    await expect(
      core.connect(bcs1).createCollection(0, deadline, "Target zero")
    ).to.be.revertedWithCustomError(core, "ZeroAmount");

    // 3. Past or current deadline reverts InvalidDeadline
    await expect(
      core.connect(bcs1).createCollection(ethers.parseEther("1.0"), now, "Past deadline")
    ).to.be.revertedWithCustomError(core, "InvalidDeadline");

    // 4. Empty purpose reverts EmptyPurpose
    await expect(
      core.connect(bcs1).createCollection(ethers.parseEther("1.0"), deadline, "")
    ).to.be.revertedWithCustomError(core, "EmptyPurpose");

    // 5. Purpose exceeding 256 bytes reverts PurposeTooLong
    const longPurpose = "A".repeat(257);
    await expect(
      core.connect(bcs1).createCollection(ethers.parseEther("1.0"), deadline, longPurpose)
    ).to.be.revertedWithCustomError(core, "PurposeTooLong");

    // 6. Valid creation succeeds and records expectedPayers = enrolledCount (5)
    await expect(
      core.connect(bcs1).createCollection(ethers.parseEther("1.0"), deadline, "Quy hoc ky 1 - 2026")
    )
      .to.emit(core, "CollectionCreated")
      .withArgs(1n, ethers.parseEther("1.0"), deadline, "Quy hoc ky 1 - 2026", bcs1.address, 5n);

    expect(await core.collectionCount()).to.equal(1n);
    expect(await core.activeCollectionId()).to.equal(1n);
    expect(await core.getActiveCollectionId()).to.equal(1n);

    const col = await core.getCollection(1);
    expect(col.id).to.equal(1n);
    expect(col.targetWei).to.equal(ethers.parseEther("1.0"));
    expect(col.deadline).to.equal(BigInt(deadline));
    expect(col.purpose).to.equal("Quy hoc ky 1 - 2026");
    expect(col.creator).to.equal(bcs1.address);
    expect(col.closed).to.be.false;
    expect(col.expectedPayers).to.equal(5n);
    expect(col.paidCount).to.equal(0n);
  });

  it("Section E2: Only 1 collection can be open at a time; closeCollection closes and allows next collection", async function () {
    const { core, advisor, bcs1, bcs2, student1 } = await deployFixture();

    const now = await time.latest();
    const deadline = now + SEVEN_DAYS;

    await core.connect(bcs1).createCollection(ethers.parseEther("1.0"), deadline, "Dot thu 1");

    // Trying to create Collection 2 while Collection 1 is still open reverts CollectionStillOpen
    await expect(
      core.connect(bcs2).createCollection(ethers.parseEther("2.0"), deadline + 1000, "Dot thu 2")
    ).to.be.revertedWithCustomError(core, "CollectionStillOpen")
      .withArgs(1n);

    // Non-BCS closing collection reverts NotActiveBCS
    await expect(
      core.connect(advisor).closeCollection(1, "Advisor close")
    ).to.be.revertedWithCustomError(core, "NotActiveBCS");
    await expect(
      core.connect(student1).closeCollection(1, "Student close")
    ).to.be.revertedWithCustomError(core, "NotActiveBCS");

    // Closing non-existent collection reverts CollectionNotFound
    await expect(
      core.connect(bcs1).closeCollection(99, "Not found")
    ).to.be.revertedWithCustomError(core, "CollectionNotFound");

    // Valid close by BCS emits CollectionClosed
    await expect(core.connect(bcs2).closeCollection(1, "Dong dot thu 1"))
      .to.emit(core, "CollectionClosed");

    expect(await core.activeCollectionId()).to.equal(0n);
    expect(await core.getActiveCollectionId()).to.equal(0n);

    const col1 = await core.getCollection(1);
    expect(col1.closed).to.be.true;
    expect(col1.closedAt).to.be.greaterThan(0n);

    // Closing already closed collection reverts CollectionAlreadyClosed
    await expect(
      core.connect(bcs1).closeCollection(1, "Dong lan 2")
    ).to.be.revertedWithCustomError(core, "CollectionAlreadyClosed");

    // Now BCS can open Collection 2
    await expect(
      core.connect(bcs1).createCollection(ethers.parseEther("2.0"), deadline + 2000, "Dot thu 2")
    ).to.emit(core, "CollectionCreated").withArgs(2n, ethers.parseEther("2.0"), deadline + 2000, "Dot thu 2", bcs1.address, 5n);

    expect(await core.activeCollectionId()).to.equal(2n);
  });

  it("Issue 1: createCollection auto-closes unclosed expired collection when past deadline, reverts while still within deadline", async function () {
    const { core, bcs1, bcs2 } = await deployFixture();

    const now = await time.latest();
    const deadline1 = now + 1000;

    await core.connect(bcs1).createCollection(ethers.parseEther("1.0"), deadline1, "Dot thu sap het han");
    expect(await core.activeCollectionId()).to.equal(1n);

    // 1. Khi còn trong hạn (block.timestamp <= deadline): vẫn revert CollectionStillOpen
    await expect(
      core.connect(bcs2).createCollection(ethers.parseEther("2.0"), deadline1 + 5000, "Dot thu moi bi chan")
    ).to.be.revertedWithCustomError(core, "CollectionStillOpen").withArgs(1n);

    // 2. Tăng thời gian vượt qua deadline1 (block.timestamp > deadline1)
    await time.increaseTo(deadline1 + 10);

    // 3. Gọi createCollection mới: tự động đóng đợt 1 với lý do "Hết hạn tự động", emit CollectionClosed và tạo đợt 2 thành công
    const newDeadline = (await time.latest()) + SEVEN_DAYS;
    const tx = await core.connect(bcs2).createCollection(ethers.parseEther("2.0"), newDeadline, "Dot thu 2 sau khi dot 1 het han");
    await expect(tx)
      .to.emit(core, "CollectionClosed")
      .withArgs(1n, "Hết hạn tự động", bcs2.address, await time.latest());
    await expect(tx)
      .to.emit(core, "CollectionCreated")
      .withArgs(2n, ethers.parseEther("2.0"), newDeadline, "Dot thu 2 sau khi dot 1 het han", bcs2.address, 5n);

    // Kiểm tra trạng thái đợt cũ đã được đóng
    const col1 = await core.getCollection(1);
    expect(col1.closed).to.be.true;
    expect(col1.closedAt).to.be.greaterThan(0n);

    // Đợt mới hiện đang active
    expect(await core.activeCollectionId()).to.equal(2n);
    expect(await core.getActiveCollectionId()).to.equal(2n);
  });

  it("Section E3: depositToCollection enforces whitelist, fee split, and thresholds for 'Đã nộp'", async function () {
    const { core, bcs1, student1, student2, stranger } = await deployFixture();

    const now = await time.latest();
    const deadline = now + SEVEN_DAYS;
    await core.connect(bcs1).createCollection(ethers.parseEther("1.0"), deadline, "Dot thu hoc ky");

    // 1. Non-enrolled stranger reverts NotEnrolledStudent
    await expect(
      core.connect(stranger).depositToCollection(1, { value: ethers.parseEther("1.0") })
    ).to.be.revertedWithCustomError(core, "NotEnrolledStudent")
      .withArgs(stranger.address);

    // 2. Zero amount reverts ZeroAmount
    await expect(
      core.connect(student1).depositToCollection(1, { value: 0 })
    ).to.be.revertedWithCustomError(core, "ZeroAmount");

    // 3. Partial deposit: student1 deposits 0.4 ETH
    expect(await core.hasPaidInCollection(1, student1.address)).to.be.false;
    expect((await core.getCollection(1)).paidCount).to.equal(0n);

    await expect(
      core.connect(student1).depositToCollection(1, { value: ethers.parseEther("0.4") })
    )
      .to.emit(core, "CollectionDeposited")
      .withArgs(1n, student1.address, ethers.parseEther("0.4"), ethers.parseEther("0.4"), 0n);

    expect(await core.paidInCollection(1, student1.address)).to.equal(ethers.parseEther("0.4"));
    expect(await core.hasPaidInCollection(1, student1.address)).to.be.false;
    expect((await core.getCollection(1)).paidCount).to.equal(0n);

    // Net accounting checked: 99% of 0.4 ETH = 0.396 ETH net, 1% = 0.004 ETH admin fee
    expect(await core.studentContributions(student1.address)).to.equal(ethers.parseEther("0.396"));
    expect(await core.adminFeePool()).to.equal(ethers.parseEther("0.004"));

    // 4. Second partial deposit: student1 deposits 0.6 ETH -> total 1.0 ETH (hits target)
    await expect(
      core.connect(student1).depositToCollection(1, { value: ethers.parseEther("0.6") })
    )
      .to.emit(core, "CollectionDeposited")
      .withArgs(1n, student1.address, ethers.parseEther("0.6"), ethers.parseEther("1.0"), 1n);

    expect(await core.paidInCollection(1, student1.address)).to.equal(ethers.parseEther("1.0"));
    expect(await core.hasPaidInCollection(1, student1.address)).to.be.true;
    expect((await core.getCollection(1)).paidCount).to.equal(1n);

    // 5. Overpayment: student1 deposits another 0.5 ETH -> paidCount remains 1
    await expect(
      core.connect(student1).depositToCollection(1, { value: ethers.parseEther("0.5") })
    )
      .to.emit(core, "CollectionDeposited")
      .withArgs(1n, student1.address, ethers.parseEther("0.5"), ethers.parseEther("1.5"), 1n);

    expect(await core.paidInCollection(1, student1.address)).to.equal(ethers.parseEther("1.5"));
    expect((await core.getCollection(1)).paidCount).to.equal(1n);

    // 6. Direct full payment by student2
    await core.connect(student2).depositToCollection(1, { value: ethers.parseEther("1.0") });
    expect(await core.hasPaidInCollection(1, student2.address)).to.be.true;
    expect((await core.getCollection(1)).paidCount).to.equal(2n);
  });

  it("Section E4: depositToCollection reverts on closed or expired collections", async function () {
    const { core, bcs1, student1 } = await deployFixture();

    const now = await time.latest();
    const deadline = now + SEVEN_DAYS;
    await core.connect(bcs1).createCollection(ethers.parseEther("1.0"), deadline, "Dot thu test time");

    // Fast forward past deadline
    await time.increase(SEVEN_DAYS + 10);

    // Deposit past deadline reverts CollectionExpired
    await expect(
      core.connect(student1).depositToCollection(1, { value: ethers.parseEther("1.0") })
    ).to.be.revertedWithCustomError(core, "CollectionExpired");

    // Close collection
    await core.connect(bcs1).closeCollection(1, "Dong dot thu da het han");

    // Deposit into closed collection reverts CollectionIsClosed
    await expect(
      core.connect(student1).depositToCollection(1, { value: ethers.parseEther("1.0") })
    ).to.be.revertedWithCustomError(core, "CollectionIsClosed")
      .withArgs(1n);
  });

  it("Section E5 (Fraud & Isolation): General deposits and cross-collection payments do not bleed over", async function () {
    const { core, bcs1, student1 } = await deployFixture();

    const now = await time.latest();
    const deadline1 = now + SEVEN_DAYS;
    await core.connect(bcs1).createCollection(ethers.parseEther("1.0"), deadline1, "Dot 1");

    // 1. student1 deposits 2 ETH into general fund via deposit()
    await core.connect(student1).deposit({ value: ethers.parseEther("2.0") });
    // General deposit does not mark collection 1 as paid
    expect(await core.hasPaidInCollection(1, student1.address)).to.be.false;
    expect(await core.paidInCollection(1, student1.address)).to.equal(0n);
    expect((await core.getCollection(1)).paidCount).to.equal(0n);

    // 2. student1 pays 1 ETH into Collection 1
    await core.connect(student1).depositToCollection(1, { value: ethers.parseEther("1.0") });
    expect(await core.hasPaidInCollection(1, student1.address)).to.be.true;

    // 3. Close Collection 1 and open Collection 2
    await core.connect(bcs1).closeCollection(1, "Xong dot 1");
    const deadline2 = (await time.latest()) + SEVEN_DAYS;
    await core.connect(bcs1).createCollection(ethers.parseEther("1.0"), deadline2, "Dot 2");

    // Student1 has NOT paid in Collection 2 despite having 2.97 ETH net in studentContributions!
    expect(await core.hasPaidInCollection(2, student1.address)).to.be.false;
    expect(await core.paidInCollection(2, student1.address)).to.equal(0n);
    expect((await core.getCollection(2)).paidCount).to.equal(0n);
  });
});

