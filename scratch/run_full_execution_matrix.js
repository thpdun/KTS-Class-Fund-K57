const fs = require('fs');
const path = require('path');
const npxNodeModules = 'C:\\Users\\Thao\\AppData\\Local\\npm-cache\\_npx\\fcea0c4d773c1d63\\node_modules';

const { createVM } = require(path.join(npxNodeModules, '@ethereumjs/vm'));
const { createAddressFromString, createAccount, bytesToHex, hexToBytes } = require(path.join(npxNodeModules, '@ethereumjs/util'));
const { ethers } = require(path.join(npxNodeModules, 'ethers'));

const solcOut = path.join(__dirname, 'solc_out');

function loadContract(prefix, name) {
  const bin = '0x' + fs.readFileSync(path.join(solcOut, `${prefix}_sol_${name}.bin`), 'utf8').trim();
  const abi = JSON.parse(fs.readFileSync(path.join(solcOut, `${prefix}_sol_${name}.abi`), 'utf8'));
  return { bin, abi, iface: new ethers.Interface(abi) };
}

const ProjectCoreArtifact = loadContract('contracts_project_ProjectCore', 'ProjectCore');
const AlwaysRevertArtifact = loadContract('scratch_GasGriefingAttackerContracts', 'AlwaysRevertingRecipient');
const EmptyFallbackArtifact = loadContract('scratch_GasGriefingAttackerContracts', 'EmptyFallbackRecipient');
const GasBurningConsumerArtifact = loadContract('scratch_GasGriefingAttackerContracts', 'GasBurningConsumer');
const InfiniteLoopArtifact = loadContract('scratch_GasGriefingAttackerContracts', 'InfiniteLoopAttacker');
const ReentrancyAttackerArtifact = loadContract('scratch_GasGriefingAttackerContracts', 'ComprehensiveReentrancyAttacker');
const GasBurnRefundArtifact = loadContract('scratch_GasGriefingAttackerContracts', 'GasBurningRefundStudent');
const AlwaysRevertRefundArtifact = loadContract('scratch_GasGriefingAttackerContracts', 'AlwaysRevertingRefundStudent');
const InfiniteLoopRefundArtifact = loadContract('scratch_GasGriefingAttackerContracts', 'InfiniteLoopRefundStudent');
const EmptyFallbackRefundArtifact = loadContract('scratch_GasGriefingAttackerContracts', 'EmptyFallbackRefundStudent');
const ContractAdvisorArtifact = loadContract('scratch_GasGriefingAttackerContracts', 'ContractAdvisor');

// Addresses
const ADVISOR = '0x1000000000000000000000000000000000000001';
const BCS1 = '0x2000000000000000000000000000000000000001';
const BCS2 = '0x2000000000000000000000000000000000000002';
const BCS3 = '0x2000000000000000000000000000000000000003';
const STUDENT1 = '0x3000000000000000000000000000000000000001';
const EOA_RECIPIENT = '0x4000000000000000000000000000000000000001';

async function initEVM() {
  const vm = await createVM({ activatePrecompiles: true });
  vm.evm.allowUnlimitedInitCodeSize = true;
  vm.evm.allowUnlimitedContractSize = true;

  const addresses = [ADVISOR, BCS1, BCS2, BCS3, STUDENT1, EOA_RECIPIENT];
  for (const a of addresses) {
    await vm.stateManager.putAccount(createAddressFromString(a), createAccount({ balance: 10000n * 10n**18n }));
  }
  return vm;
}

async function deployContract(vm, sender, artifact, constructorArgs = [], value = 0n) {
  const deployData = artifact.iface.encodeDeploy(constructorArgs);
  const txData = artifact.bin + deployData.slice(2);
  const result = await vm.evm.runCall({
    caller: createAddressFromString(sender),
    data: hexToBytes(txData),
    gasLimit: 10000000n,
    value: value
  });
  if (result.execResult.exceptionError) {
    throw new Error(`Deploy failed: ${result.execResult.exceptionError.error}`);
  }
  return bytesToHex(result.createdAddress.bytes);
}

async function sendTx(vm, sender, target, iface, fnName, args = [], value = 0n, gasLimit = 5000000n) {
  const data = iface.encodeFunctionData(fnName, args);
  const result = await vm.evm.runCall({
    caller: createAddressFromString(sender),
    to: createAddressFromString(target),
    data: hexToBytes(data),
    value: value,
    gasLimit: BigInt(gasLimit)
  });

  const logs = (result.execResult.logs || []).map(l => {
    const address = bytesToHex(l[0]);
    const topics = l[1].map(t => bytesToHex(t));
    const dataHex = bytesToHex(l[2]);
    let parsed = null;
    try {
      parsed = iface.parseLog({ topics, data: dataHex });
    } catch (_) {}
    return { address, topics, data: dataHex, parsed };
  });

  return {
    gasUsed: result.execResult.executionGasUsed,
    gasLimit: BigInt(gasLimit),
    success: !result.execResult.exceptionError,
    error: result.execResult.exceptionError ? result.execResult.exceptionError.error : null,
    returnValue: result.execResult.returnValue ? bytesToHex(result.execResult.returnValue) : '0x',
    logs
  };
}

async function callView(vm, target, iface, fnName, args = []) {
  const data = iface.encodeFunctionData(fnName, args);
  const result = await vm.evm.runCall({
    caller: createAddressFromString(ADVISOR),
    to: createAddressFromString(target),
    data: hexToBytes(data),
    gasLimit: 5000000n
  });
  if (result.execResult.exceptionError) {
    throw new Error(`View call ${fnName} failed: ${result.execResult.exceptionError.error}`);
  }
  const decoded = iface.decodeFunctionResult(fnName, result.execResult.returnValue);
  return decoded.length === 1 ? decoded[0] : decoded;
}

async function setupStandardFund(vm, customAdvisor = ADVISOR) {
  // We deploy with customAdvisor as msg.sender so customAdvisor becomes advisor
  const coreAddr = await deployContract(vm, customAdvisor, ProjectCoreArtifact);

  await sendTx(vm, customAdvisor, coreAddr, ProjectCoreArtifact.iface, 'setBCSMember', [BCS1, true]);
  await sendTx(vm, customAdvisor, coreAddr, ProjectCoreArtifact.iface, 'setBCSMember', [BCS2, true]);
  await sendTx(vm, customAdvisor, coreAddr, ProjectCoreArtifact.iface, 'setBCSMember', [BCS3, true]);

  // Deposit 10 ETH from STUDENT1 -> 9.9 ETH classFund, 0.1 ETH adminFeePool
  await sendTx(vm, STUDENT1, coreAddr, ProjectCoreArtifact.iface, 'deposit', [], ethers.parseEther('10'));
  return coreAddr;
}

async function runFullMatrix() {
  console.log('========================================================================================');
  console.log('AUTO-EXECUTION FIX 10: GAS & EXECUTION PATH FINAL VERIFICATION');
  console.log('========================================================================================\n');

  const matrixResults = [];

  // ==========================================================================
  // PHẦN 1: 5 LUỒNG THỰC THI CHUYỂN ETH VỚI CÁC LOẠI RECIPIENT
  // ==========================================================================

  // --- LUỒNG 1: voteSpendRequest kích hoạt auto-execution ---
  console.log('--- LUỒNG 1: voteSpendRequest kích hoạt auto-execution ---');
  const spendActors = [
    { name: '1. EOA Chuẩn', artifact: null, isEOA: true },
    { name: '2. Luôn Revert', artifact: AlwaysRevertArtifact },
    { name: '3. Thiếu Receive/Fallback', artifact: EmptyFallbackArtifact },
    { name: '4. Đốt Gas nhận ETH (Consumer)', artifact: GasBurningConsumerArtifact },
    { name: '5. Đốt Gas vô hạn (InfiniteLoop)', artifact: InfiniteLoopArtifact },
    { name: '6. Thử Reentrancy (Callback)', artifact: ReentrancyAttackerArtifact }
  ];

  for (const actor of spendActors) {
    const vm = await initEVM();
    const core = await setupStandardFund(vm);
    let recipientAddr = EOA_RECIPIENT;
    if (!actor.isEOA) {
      recipientAddr = await deployContract(vm, STUDENT1, actor.artifact, actor.artifact === ReentrancyAttackerArtifact ? [core] : []);
      if (actor.artifact === ReentrancyAttackerArtifact) {
        await sendTx(vm, STUDENT1, recipientAddr, actor.artifact.iface, 'setTargets', [1, 1]);
        await sendTx(vm, STUDENT1, core, ProjectCoreArtifact.iface, 'createRefundRequest', [ethers.parseEther('0.1'), 'dummy']);
      }
    }

    await sendTx(vm, BCS1, core, ProjectCoreArtifact.iface, 'createSpendRequest', [recipientAddr, ethers.parseEther('1'), 'Chi tiêu test']);
    await sendTx(vm, BCS1, core, ProjectCoreArtifact.iface, 'voteSpendRequest', [1, true]);

    const fundBefore = await callView(vm, core, ProjectCoreArtifact.iface, 'classFundBalance');
    const resBefore = await callView(vm, core, ProjectCoreArtifact.iface, 'reservedSpendAmount');

    // Vote thứ 2 kích hoạt auto-execution (gasLimit 600,000)
    const voteTx = await sendTx(vm, BCS2, core, ProjectCoreArtifact.iface, 'voteSpendRequest', [1, true], 0n, 600000);

    const fundAfter = await callView(vm, core, ProjectCoreArtifact.iface, 'classFundBalance');
    const resAfter = await callView(vm, core, ProjectCoreArtifact.iface, 'reservedSpendAmount');
    const reqAfter = await callView(vm, core, ProjectCoreArtifact.iface, 'getSpendRequest', [1]);
    const eventNames = voteTx.logs.map(l => l.parsed ? l.parsed.name : 'Unknown');

    const statusNames = ['Pending', 'Ready', 'Executed', 'Rejected', 'Expired', 'Cancelled'];

    matrixResults.push({
      flow: '1. voteSpendRequest (Auto)',
      actor: actor.name,
      gasLimit: '600,000',
      gasUsed: voteTx.gasUsed.toString(),
      txStatus: voteTx.success ? 'SUCCESS' : `REVERT (${voteTx.error})`,
      events: eventNames.join(', ') || 'None',
      statusBeforeAfter: `Pending (0) -> ${statusNames[Number(reqAfter[8])]} (${reqAfter[8]})`,
      balanceBeforeAfter: `${ethers.formatEther(fundBefore)} -> ${ethers.formatEther(fundAfter)} ETH`,
      resBeforeAfter: `${ethers.formatEther(resBefore)} -> ${ethers.formatEther(resAfter)} ETH`
    });
  }

  // --- LUỒNG 2: voteRefundRequest kích hoạt auto-execution ---
  console.log('--- LUỒNG 2: voteRefundRequest kích hoạt auto-execution ---');
  const refundActors = [
    { name: '1. EOA Chuẩn', isEOA: true },
    { name: '2. Luôn Revert', artifact: AlwaysRevertRefundArtifact },
    { name: '3. Thiếu Receive/Fallback', artifact: EmptyFallbackRefundArtifact },
    { name: '4. Đốt Gas nhận ETH', artifact: GasBurnRefundArtifact },
    { name: '5. Đốt Gas vô hạn (InfiniteLoop)', artifact: InfiniteLoopRefundArtifact }
  ];

  for (const actor of refundActors) {
    const vm = await initEVM();
    const core = await setupStandardFund(vm);
    let studentAddr = STUDENT1;

    if (!actor.isEOA) {
      studentAddr = await deployContract(vm, STUDENT1, actor.artifact, [core]);
      // Deposit 2 ETH from student contract
      await sendTx(vm, STUDENT1, studentAddr, actor.artifact.iface, 'deposit', [ethers.parseEther('2')], ethers.parseEther('2'));
      // Create refund from student contract
      await sendTx(vm, STUDENT1, studentAddr, actor.artifact.iface, 'createRefund', [ethers.parseEther('1.5'), 'Test refund']);
    } else {
      // EOA student nạp thêm và tạo refund
      await sendTx(vm, STUDENT1, core, ProjectCoreArtifact.iface, 'createRefundRequest', [ethers.parseEther('1'), 'EOA refund test']);
    }

    await sendTx(vm, BCS1, core, ProjectCoreArtifact.iface, 'voteRefundRequest', [1, true]);

    const fundBefore = await callView(vm, core, ProjectCoreArtifact.iface, 'classFundBalance');
    const resRefundBefore = await callView(vm, core, ProjectCoreArtifact.iface, 'reservedRefundAmount');

    const voteTx = await sendTx(vm, BCS2, core, ProjectCoreArtifact.iface, 'voteRefundRequest', [1, true], 0n, 600000);

    const fundAfter = await callView(vm, core, ProjectCoreArtifact.iface, 'classFundBalance');
    const resRefundAfter = await callView(vm, core, ProjectCoreArtifact.iface, 'reservedRefundAmount');
    const refAfter = await callView(vm, core, ProjectCoreArtifact.iface, 'getRefundRequest', [1]);
    const eventNames = voteTx.logs.map(l => l.parsed ? l.parsed.name : 'Unknown');

    const statusNames = ['Pending', 'Ready', 'Executed', 'Rejected', 'Expired', 'Cancelled'];

    matrixResults.push({
      flow: '2. voteRefundRequest (Auto)',
      actor: actor.name,
      gasLimit: '600,000',
      gasUsed: voteTx.gasUsed.toString(),
      txStatus: voteTx.success ? 'SUCCESS' : `REVERT (${voteTx.error})`,
      events: eventNames.join(', ') || 'None',
      statusBeforeAfter: `Pending (0) -> ${statusNames[Number(refAfter[7])]} (${refAfter[7]})`,
      balanceBeforeAfter: `${ethers.formatEther(fundBefore)} -> ${ethers.formatEther(fundAfter)} ETH`,
      resBeforeAfter: `${ethers.formatEther(resRefundBefore)} -> ${ethers.formatEther(resRefundAfter)} ETH`
    });
  }

  // --- LUỒNG 3: executeSpendRequest (Manual Retry sau khi đã Ready) ---
  console.log('--- LUỒNG 3: executeSpendRequest (Manual Retry) ---');
  for (const actor of spendActors) {
    const vm = await initEVM();
    const core = await setupStandardFund(vm);
    let recipientAddr = EOA_RECIPIENT;
    if (!actor.isEOA) {
      recipientAddr = await deployContract(vm, STUDENT1, actor.artifact, actor.artifact === ReentrancyAttackerArtifact ? [core] : []);
      if (actor.artifact === ReentrancyAttackerArtifact) {
        await sendTx(vm, STUDENT1, recipientAddr, actor.artifact.iface, 'setTargets', [1, 1]);
        await sendTx(vm, STUDENT1, core, ProjectCoreArtifact.iface, 'createRefundRequest', [ethers.parseEther('0.1'), 'dummy']);
      }
    }

    await sendTx(vm, BCS1, core, ProjectCoreArtifact.iface, 'createSpendRequest', [recipientAddr, ethers.parseEther('1'), 'Chi tiêu test']);
    await sendTx(vm, BCS1, core, ProjectCoreArtifact.iface, 'voteSpendRequest', [1, true]);
    // Vote 2 với recipient AlwaysRevert hoặc gasLimit vừa đủ để chắc chắn request vào Ready
    // Nếu actor là AlwaysRevert hoặc EmptyFallback thì auto-execution sẽ đưa vào Ready!
    // Với EOA hoặc Consumer, auto-execution sẽ Executed luôn, do đó để đưa vào Ready ta có thể dùng AlwaysRevert ban đầu rồi đổi/hoặc tạo đề xuất đã Ready.
    // Trong ProjectCore, nếu vote thông qua nhưng auto-exec thất bại, nó ở Ready.
    // Hãy test trường hợp request ĐANG Ở READY:
    await sendTx(vm, BCS2, core, ProjectCoreArtifact.iface, 'voteSpendRequest', [1, true], 0n, 600000);

    // Kiểm tra trạng thái hiện tại
    let reqCurrent = await callView(vm, core, ProjectCoreArtifact.iface, 'getSpendRequest', [1]);

    // Nếu đã Executed (như trường hợp EOA hoặc Consumer), tạo đề xuất #2 với recipient AlwaysRevert trước để vào Ready, rồi kiểm tra execute
    // Hoặc kiểm tra trực tiếp hành vi executeSpendRequest trên request hiện tại:
    const fundBefore = await callView(vm, core, ProjectCoreArtifact.iface, 'classFundBalance');
    const resBefore = await callView(vm, core, ProjectCoreArtifact.iface, 'reservedSpendAmount');

    const execTx = await sendTx(vm, BCS3, core, ProjectCoreArtifact.iface, 'executeSpendRequest', [1], 0n, 600000);

    const fundAfter = await callView(vm, core, ProjectCoreArtifact.iface, 'classFundBalance');
    const resAfter = await callView(vm, core, ProjectCoreArtifact.iface, 'reservedSpendAmount');
    reqCurrent = await callView(vm, core, ProjectCoreArtifact.iface, 'getSpendRequest', [1]);
    const eventNames = execTx.logs.map(l => l.parsed ? l.parsed.name : 'Unknown');
    const statusNames = ['Pending', 'Ready', 'Executed', 'Rejected', 'Expired', 'Cancelled'];

    matrixResults.push({
      flow: '3. executeSpendRequest (Manual)',
      actor: actor.name,
      gasLimit: '600,000',
      gasUsed: execTx.gasUsed.toString(),
      txStatus: execTx.success ? 'SUCCESS' : `REVERT (${execTx.error})`,
      events: eventNames.join(', ') || 'None',
      statusBeforeAfter: `Status sau execute: ${statusNames[Number(reqCurrent[8])]} (${reqCurrent[8]})`,
      balanceBeforeAfter: `${ethers.formatEther(fundBefore)} -> ${ethers.formatEther(fundAfter)} ETH`,
      resBeforeAfter: `${ethers.formatEther(resBefore)} -> ${ethers.formatEther(resAfter)} ETH`
    });
  }

  // --- LUỒNG 4: executeRefundRequest (Manual Retry sau khi đã Ready) ---
  console.log('--- LUỒNG 4: executeRefundRequest (Manual Retry) ---');
  for (const actor of refundActors) {
    const vm = await initEVM();
    const core = await setupStandardFund(vm);
    let studentAddr = STUDENT1;

    if (!actor.isEOA) {
      studentAddr = await deployContract(vm, STUDENT1, actor.artifact, [core]);
      await sendTx(vm, STUDENT1, studentAddr, actor.artifact.iface, 'deposit', [ethers.parseEther('2')], ethers.parseEther('2'));
      await sendTx(vm, STUDENT1, studentAddr, actor.artifact.iface, 'createRefund', [ethers.parseEther('1.5'), 'Test refund']);
    } else {
      await sendTx(vm, STUDENT1, core, ProjectCoreArtifact.iface, 'createRefundRequest', [ethers.parseEther('1'), 'EOA refund test']);
    }

    await sendTx(vm, BCS1, core, ProjectCoreArtifact.iface, 'voteRefundRequest', [1, true]);
    await sendTx(vm, BCS2, core, ProjectCoreArtifact.iface, 'voteRefundRequest', [1, true], 0n, 600000);

    const fundBefore = await callView(vm, core, ProjectCoreArtifact.iface, 'classFundBalance');
    const resBefore = await callView(vm, core, ProjectCoreArtifact.iface, 'reservedRefundAmount');

    // BCS gọi executeRefundRequest(1)
    const execTx = await sendTx(vm, BCS1, core, ProjectCoreArtifact.iface, 'executeRefundRequest', [1], 0n, 600000);

    const fundAfter = await callView(vm, core, ProjectCoreArtifact.iface, 'classFundBalance');
    const resAfter = await callView(vm, core, ProjectCoreArtifact.iface, 'reservedRefundAmount');
    const refCurrent = await callView(vm, core, ProjectCoreArtifact.iface, 'getRefundRequest', [1]);
    const eventNames = execTx.logs.map(l => l.parsed ? l.parsed.name : 'Unknown');
    const statusNames = ['Pending', 'Ready', 'Executed', 'Rejected', 'Expired', 'Cancelled'];

    matrixResults.push({
      flow: '4. executeRefundRequest (Manual)',
      actor: actor.name,
      gasLimit: '600,000',
      gasUsed: execTx.gasUsed.toString(),
      txStatus: execTx.success ? 'SUCCESS' : `REVERT (${execTx.error})`,
      events: eventNames.join(', ') || 'None',
      statusBeforeAfter: `Status sau execute: ${statusNames[Number(refCurrent[7])]} (${refCurrent[7]})`,
      balanceBeforeAfter: `${ethers.formatEther(fundBefore)} -> ${ethers.formatEther(fundAfter)} ETH`,
      resBeforeAfter: `${ethers.formatEther(resBefore)} -> ${ethers.formatEther(resAfter)} ETH`
    });
  }

  // --- LUỒNG 5: withdrawAdminFee ---
  console.log('--- LUỒNG 5: withdrawAdminFee ---');
  const advisorBehaviors = [
    { name: '1. Advisor là EOA Chuẩn', isEOA: true },
    { name: '2. Contract Advisor: Chấp nhận ETH', behavior: 0 },
    { name: '3. Contract Advisor: Revert', behavior: 1 },
    { name: '4. Contract Advisor: Đốt Gas nhận ETH', behavior: 2 },
    { name: '5. Contract Advisor: Vòng lặp vô hạn', behavior: 3 },
    { name: '6. Contract Advisor: Thử Reentrancy', behavior: 4 }
  ];

  for (const adv of advisorBehaviors) {
    const vm = await initEVM();
    let advisorAddr = ADVISOR;
    let contractAdvisor = null;

    if (!adv.isEOA) {
      contractAdvisor = await deployContract(vm, ADVISOR, ContractAdvisorArtifact, ['0x0000000000000000000000000000000000000000']);
      const acct = await vm.stateManager.getAccount(createAddressFromString(contractAdvisor));
      acct.balance = 1000n * 10n**18n;
      await vm.stateManager.putAccount(createAddressFromString(contractAdvisor), acct);
      advisorAddr = contractAdvisor;
    }

    const core = await setupStandardFund(vm, advisorAddr);

    if (contractAdvisor) {
      await sendTx(vm, ADVISOR, contractAdvisor, ContractAdvisorArtifact.iface, 'setBehavior', [adv.behavior]);
    }

    const poolBefore = await callView(vm, core, ProjectCoreArtifact.iface, 'adminFeePool');
    const withdrawAmount = ethers.parseEther('0.05'); // Rút 0.05 / 0.1 ETH trong pool

    let withdrawTx;
    if (adv.isEOA) {
      withdrawTx = await sendTx(vm, ADVISOR, core, ProjectCoreArtifact.iface, 'withdrawAdminFee', [withdrawAmount], 0n, 600000);
    } else {
      // ContractAdvisor calls withdraw
      // ContractAdvisor needs target to be core. Let's make sure it calls core
      // Let's do raw call: caller=advisorAddr, to=core, fn=withdrawAdminFee
      withdrawTx = await sendTx(vm, advisorAddr, core, ProjectCoreArtifact.iface, 'withdrawAdminFee', [withdrawAmount], 0n, 600000);
    }

    const poolAfter = await callView(vm, core, ProjectCoreArtifact.iface, 'adminFeePool');
    const eventNames = withdrawTx.logs.map(l => l.parsed ? l.parsed.name : 'Unknown');

    matrixResults.push({
      flow: '5. withdrawAdminFee',
      actor: adv.name,
      gasLimit: '600,000',
      gasUsed: withdrawTx.gasUsed.toString(),
      txStatus: withdrawTx.success ? 'SUCCESS' : `REVERT (${withdrawTx.error})`,
      events: eventNames.join(', ') || 'None',
      statusBeforeAfter: `Pool: ${ethers.formatEther(poolBefore)} -> ${ethers.formatEther(poolAfter)} ETH`,
      balanceBeforeAfter: `Fee Pool ${withdrawTx.success ? 'đã rút 0.05 ETH' : 'bảo toàn 100%'}`,
      resBeforeAfter: 'N/A (AdminFee không ảnh hưởng classFund)'
    });
  }

  console.log('========================================================================================');
  console.log('BẢNG TỔNG HỢP MATRIX 5 LUỒNG THỰC THI CHUYỂN ETH');
  console.log('========================================================================================');
  console.table(matrixResults);

  // ==========================================================================
  // PHẦN 2: TÌM NGƯỠNG GAS GIỚI HẠN (FINE-GRAINED GAS BOUNDARY SCAN)
  // ==========================================================================
  console.log('\n========================================================================================');
  console.log('PHẦN 2: DÒ TÌM NGƯỠNG GAS GIỚI HẠN (BOUNDARY GAS SCAN)');
  console.log('========================================================================================\n');

  // 1. Ngưỡng thấp nhất để auto-execution thành công tới EOA chuẩn
  console.log('--- Scan: Ngưỡng gas thấp nhất cho voteSpendRequest (Auto-exec thành công tới EOA) ---');
  let minGasAutoExecEOA = null;
  const eoaGasLimits = [80000, 90000, 100000, 110000, 120000, 130000, 150000];
  for (const gl of eoaGasLimits) {
    const vm = await initEVM();
    const core = await setupStandardFund(vm);
    await sendTx(vm, BCS1, core, ProjectCoreArtifact.iface, 'createSpendRequest', [EOA_RECIPIENT, ethers.parseEther('1'), 'test']);
    await sendTx(vm, BCS1, core, ProjectCoreArtifact.iface, 'voteSpendRequest', [1, true]);
    const tx = await sendTx(vm, BCS2, core, ProjectCoreArtifact.iface, 'voteSpendRequest', [1, true], 0n, gl);
    console.log(`GasLimit ${gl}: Success=${tx.success}, GasUsed=${tx.gasUsed}, Error=${tx.error}`);
    if (tx.success && !minGasAutoExecEOA) minGasAutoExecEOA = { gl, used: tx.gasUsed };
  }

  // 2. Ngưỡng thấp nhất để rollback thành công khi recipient AlwaysRevert
  console.log('\n--- Scan: Ngưỡng gas thấp nhất cho voteSpendRequest rollback (AlwaysRevert) ---');
  let minGasRollbackRevert = null;
  const revertGasLimits = [70000, 80000, 90000, 100000, 110000, 120000];
  for (const gl of revertGasLimits) {
    const vm = await initEVM();
    const core = await setupStandardFund(vm);
    const badRec = await deployContract(vm, STUDENT1, AlwaysRevertArtifact);
    await sendTx(vm, BCS1, core, ProjectCoreArtifact.iface, 'createSpendRequest', [badRec, ethers.parseEther('1'), 'test']);
    await sendTx(vm, BCS1, core, ProjectCoreArtifact.iface, 'voteSpendRequest', [1, true]);
    const tx = await sendTx(vm, BCS2, core, ProjectCoreArtifact.iface, 'voteSpendRequest', [1, true], 0n, gl);
    console.log(`GasLimit ${gl}: Success=${tx.success}, GasUsed=${tx.gasUsed}, Error=${tx.error}`);
    if (tx.success && !minGasRollbackRevert) minGasRollbackRevert = { gl, used: tx.gasUsed };
  }

  // 3. Dò điểm gãy (Tipping Point) khi recipient là InfiniteLoopAttacker (Đốt cạn 63/64 gas)
  console.log('\n--- Scan: Điểm gãy Out-of-Gas vs Rollback thành công (InfiniteLoopAttacker) ---');
  const boundaryScanLimits = [300000, 325000, 350000, 375000, 400000, 425000, 450000, 475000, 500000];
  const boundaryResults = [];

  for (const gl of boundaryScanLimits) {
    const vm = await initEVM();
    const core = await setupStandardFund(vm);
    const loopRec = await deployContract(vm, STUDENT1, InfiniteLoopArtifact);
    await sendTx(vm, BCS1, core, ProjectCoreArtifact.iface, 'createSpendRequest', [loopRec, ethers.parseEther('1'), 'test']);
    await sendTx(vm, BCS1, core, ProjectCoreArtifact.iface, 'voteSpendRequest', [1, true]);
    const tx = await sendTx(vm, BCS2, core, ProjectCoreArtifact.iface, 'voteSpendRequest', [1, true], 0n, gl);

    const req = await callView(vm, core, ProjectCoreArtifact.iface, 'getSpendRequest', [1]);
    const statusNames = ['Pending', 'Ready', 'Executed', 'Rejected', 'Expired', 'Cancelled'];

    boundaryResults.push({
      gasLimit: gl,
      success: tx.success,
      gasUsed: tx.gasUsed.toString(),
      error: tx.error || 'None',
      finalStatus: statusNames[Number(req[8])],
      remaining1_64Est: Math.floor(gl / 64)
    });
  }

  console.table(boundaryResults);
}

runFullMatrix().catch(err => {
  console.error('LỖI THỰC THI MATRIX:', err);
  process.exit(1);
});
