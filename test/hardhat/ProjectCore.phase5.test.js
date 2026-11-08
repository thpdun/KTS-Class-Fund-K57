const fs = require("fs");
const path = require("path");
const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time, setNextBlockBaseFeePerGas } = require("@nomicfoundation/hardhat-network-helpers");

describe("Phase 5 (Section F - Operating Fee, Automatic Gas Refund & Pool Transfer)", function () {
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

  it("Phase 5 Bytecode Size check stays well within 24,576-byte EIP-170 limit", async function () {
    const artifactPath = path.join(
      __dirname,
      "../../artifacts/contracts/project/ProjectCore.sol/ProjectCore.json"
    );
    const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
    const deployedBytes = (artifact.deployedBytecode.length - 2) / 2;
    const initBytes = (artifact.bytecode.length - 2) / 2;
    const pct = ((deployedBytes / MAX_CONTRACT_BYTES) * 100).toFixed(2);
    console.log(
      `    [Phase 5 Bytecode] deployed=${deployedBytes} / ${MAX_CONTRACT_BYTES} bytes (${pct}%), initcode=${initBytes} bytes`
    );
    expect(deployedBytes).to.be.lessThanOrEqual(MAX_CONTRACT_BYTES);
  });

  it("Section F1: moveFeeToClassFund - Advisor permission, validation (0 ETH, exceeding pool) and balance conservation", async function () {
    const { core, advisor, bcs1, student1, stranger } = await deployFixture();

    // Nạp 10 ETH: classFundBalance = 9.9 ETH, adminFeePool = 0.1 ETH
    await core.connect(student1).deposit({ value: ethers.parseEther("10") });
    expect(await core.adminFeePool()).to.equal(ethers.parseEther("0.1"));
    expect(await core.classFundBalance()).to.equal(ethers.parseEther("9.9"));
    expect(await core.getTotalContractBalance()).to.equal(ethers.parseEther("10"));

    // 1. Phân quyền: Người ngoài và BCS gọi -> Revert NotAdvisor
    await expect(
      core.connect(stranger).moveFeeToClassFund(ethers.parseEther("0.01"))
    ).to.be.revertedWithCustomError(core, "NotAdvisor");

    await expect(
      core.connect(bcs1).moveFeeToClassFund(ethers.parseEther("0.01"))
    ).to.be.revertedWithCustomError(core, "NotAdvisor");

    // 2. Chặn chuyển 0 ETH -> Revert ZeroAmount
    await expect(
      core.connect(advisor).moveFeeToClassFund(0n)
    ).to.be.revertedWithCustomError(core, "ZeroAmount");

    // 3. Chặn chuyển vượt quá adminFeePool -> Revert InsufficientAdminFee
    await expect(
      core.connect(advisor).moveFeeToClassFund(ethers.parseEther("0.2"))
    )
      .to.be.revertedWithCustomError(core, "InsufficientAdminFee")
      .withArgs(ethers.parseEther("0.2"), ethers.parseEther("0.1"));

    // 4. Chuyển hợp lệ 0.04 ETH -> Phí giảm còn 0.06 ETH, quỹ lớp tăng lên 9.94 ETH
    await expect(core.connect(advisor).moveFeeToClassFund(ethers.parseEther("0.04")))
      .to.emit(core, "FeeMovedToClassFund")
      .withArgs(advisor.address, ethers.parseEther("0.04"));

    expect(await core.adminFeePool()).to.equal(ethers.parseEther("0.06"));
    expect(await core.classFundBalance()).to.equal(ethers.parseEther("9.94"));

    // Bất biến kế toán: Tổng số dư hợp đồng không đổi (10 ETH)
    expect(await core.getTotalContractBalance()).to.equal(ethers.parseEther("10"));
    expect(await core.getTotalContractBalance()).to.equal(
      (await core.classFundBalance()) + (await core.adminFeePool())
    );
  });

  it("Section F2: Automatic gas refund on governance action - emits GasRefunded, refunds ETH, caps gas price at basefee + 2 gwei", async function () {
    const { core, advisor, bcs1, student1 } = await deployFixture();

    // Nạp 10 ETH để có 0.1 ETH trong adminFeePool
    await core.connect(student1).deposit({ value: ethers.parseEther("10") });
    const initialPool = await core.adminFeePool();
    expect(initialPool).to.equal(ethers.parseEther("0.1"));

    // Thiết lập basefee = 1 gwei, gasPrice = 5 gwei (vượt trần basefee + 2 gwei = 3 gwei)
    const baseFee = ethers.parseUnits("1", "gwei");
    const customGasPrice = ethers.parseUnits("5", "gwei");
    await setNextBlockBaseFeePerGas(baseFee);

    const now = await time.latest();
    const deadline = now + SEVEN_DAYS;

    // BCS1 tạo đợt thu (governanceAction) với gasPrice = 5 gwei
    const tx = await core
      .connect(bcs1)
      .createCollection(ethers.parseEther("1.0"), deadline, "Dot thu hoc ky 1", {
        gasPrice: customGasPrice,
      });
    const receipt = await tx.wait();

    // Tìm event GasRefunded
    const refundEvent = receipt.logs
      .map((l) => {
        try {
          return core.interface.parseLog(l);
        } catch {
          return null;
        }
      })
      .find((e) => e && e.name === "GasRefunded");

    expect(refundEvent).to.not.be.null;
    const [caller, units, effectivePrice, paid, shortfall] = refundEvent.args;

    expect(caller).to.equal(bcs1.address);
    // Gas price bị chặn ở baseFee + 2 gwei = 3 gwei thay vì 5 gwei
    expect(effectivePrice).to.equal(ethers.parseUnits("3", "gwei"));
    expect(units).to.be.greaterThan(30000n);
    expect(units).to.be.lessThanOrEqual(500000n);
    expect(paid).to.equal(units * effectivePrice);
    expect(shortfall).to.equal(0n);

    // adminFeePool giảm đúng bằng paid
    const updatedPool = await core.adminFeePool();
    expect(updatedPool).to.equal(initialPool - paid);

    // Bất biến kế toán: Tổng số dư bằng quỹ lớp + quỹ phí
    expect(await core.getTotalContractBalance()).to.equal(
      (await core.classFundBalance()) + (await core.adminFeePool())
    );
  });

  it("Section F3: Exhausted pool - governance actions still execute cleanly when pool is zero, recording shortfall", async function () {
    const { core, advisor, bcs1 } = await deployFixture();

    // Pool hiện tại = 0 (chưa có deposit nào)
    expect(await core.adminFeePool()).to.equal(0n);

    const now = await time.latest();
    const deadline = now + SEVEN_DAYS;

    // BCS1 tạo đợt thu khi pool rỗng
    const tx = await core
      .connect(bcs1)
      .createCollection(ethers.parseEther("0.5"), deadline, "Dot thu khi quy phi rong");
    const receipt = await tx.wait();

    // Đợt thu vẫn được tạo thành công
    expect(await core.collectionCount()).to.equal(1n);
    expect(await core.activeCollectionId()).to.equal(1n);

    // Event GasRefunded ghi nhận paid = 0 và shortfall = refundOwed
    const refundEvent = receipt.logs
      .map((l) => {
        try {
          return core.interface.parseLog(l);
        } catch {
          return null;
        }
      })
      .find((e) => e && e.name === "GasRefunded");

    expect(refundEvent).to.not.be.null;
    const [, units, effectivePrice, paid, shortfall] = refundEvent.args;
    expect(paid).to.equal(0n);
    expect(shortfall).to.equal(units * effectivePrice);
    expect(await core.adminFeePool()).to.equal(0n);
  });

  it("Section F4 (Fallback): Gas refund to rejecting recipient emits GasRefundFailed, restores pool balance, and does NOT revert main action", async function () {
    const { core, advisor, student1 } = await deployFixture();

    // Nạp 10 ETH -> pool = 0.1 ETH
    await core.connect(student1).deposit({ value: ethers.parseEther("10") });

    // Deploy mock actor đóng vai trò BCS nhưng từ chối nhận ETH
    const MockFactory = await ethers.getContractFactory("MockGasRefundActor", advisor);
    const rejectingActor = await MockFactory.deploy(await core.getAddress());
    await rejectingActor.waitForDeployment();
    const rejectingAddr = await rejectingActor.getAddress();

    // Cấp quyền student và BCS cho rejectingActor
    await core.connect(advisor).setStudents([rejectingAddr], true);
    await core.connect(advisor).setBCSMember(rejectingAddr, true);
    await time.increase(THREE_DAYS + 10);

    // Bật chế độ từ chối ETH
    await rejectingActor.setRejectGasRefund(true);

    const poolBeforeAction = await core.adminFeePool();
    expect(poolBeforeAction).to.be.greaterThan(0n);

    const now = await time.latest();
    const deadline = now + SEVEN_DAYS;

    // Rejecting actor tạo collection (governanceAction)
    const tx = await rejectingActor.callCreateCollection(
      ethers.parseEther("1.0"),
      deadline,
      "Collection tu mock tu choi gas"
    );
    const receipt = await tx.wait();

    // 1. Hành động chính vẫn THÀNH CÔNG (collection được tạo)
    expect(await core.collectionCount()).to.equal(1n);
    expect(await core.activeCollectionId()).to.equal(1n);

    // 2. Event GasRefundFailed được phát
    const failedEvent = receipt.logs
      .map((l) => {
        try {
          return core.interface.parseLog(l);
        } catch {
          return null;
        }
      })
      .find((e) => e && e.name === "GasRefundFailed");

    expect(failedEvent).to.not.be.null;
    expect(failedEvent.args[0]).to.equal(rejectingAddr);
    expect(failedEvent.args[1]).to.be.greaterThan(0n);

    // 3. Quỹ phí adminFeePool được hoàn trả nguyên vẹn (không bị thất thoát)
    expect(await core.adminFeePool()).to.equal(poolBeforeAction);
  });

  it("Section F5 (Fraud & Security): Reentrancy attack attempt during gas refund callback is blocked by _reentrancyLocked", async function () {
    const { core, advisor, bcs1, student1 } = await deployFixture();

    // Nạp 10 ETH -> pool = 0.1 ETH
    await core.connect(student1).deposit({ value: ethers.parseEther("10") });

    // Deploy mock actor và cấu hình cố ý tái nhập khi nhận hoàn gas
    const MockFactory = await ethers.getContractFactory("MockGasRefundActor", advisor);
    const reentrantActor = await MockFactory.deploy(await core.getAddress());
    await reentrantActor.waitForDeployment();
    const reentrantAddr = await reentrantActor.getAddress();

    // Cấp quyền student và BCS cho reentrantActor
    await core.connect(advisor).setStudents([reentrantAddr], true);
    await core.connect(advisor).setBCSMember(reentrantAddr, true);
    await time.increase(THREE_DAYS + 10);

    // Tạo collection 1 trước
    const now = await time.latest();
    await core.connect(bcs1).createCollection(ethers.parseEther("1"), now + SEVEN_DAYS, "Pre collection");

    // Bật chế độ cố ý gọi lại closeCollection(1, "Reentrant close") trong receive()
    await reentrantActor.setAttemptReentrancy(true);

    // Reentrant actor gọi closeCollection -> khi hoàn gas, fallback gọi lại closeCollection
    const tx = await reentrantActor.callCloseCollection(1n, "Normal close");
    await tx.wait();

    // Kiểm tra kết quả: Tấn công reentrancy bị chặn
    expect(await reentrantActor.reentrancyBlocked()).to.equal(true);

    // Selector lỗi trả về phải là ReentrancyGuardReentrantCall() (0x3ee5aeb5)
    const expectedSelector = ethers.id("ReentrancyGuardReentrantCall()").slice(0, 10);
    expect(await reentrantActor.reentrancyRevertSelector()).to.equal(expectedSelector);
  });
});
