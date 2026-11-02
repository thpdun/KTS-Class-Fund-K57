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
const InfiniteLoopArtifact = loadContract('scratch_GasGriefingAttackerContracts', 'InfiniteLoopAttacker');

const ADVISOR = '0x1000000000000000000000000000000000000001';
const BCS1 = '0x2000000000000000000000000000000000000001';
const BCS2 = '0x2000000000000000000000000000000000000002';
const STUDENT1 = '0x3000000000000000000000000000000000000001';

async function initEVM() {
  const vm = await createVM({ activatePrecompiles: true });
  vm.evm.allowUnlimitedInitCodeSize = true;
  vm.evm.allowUnlimitedContractSize = true;

  const addresses = [ADVISOR, BCS1, BCS2, STUDENT1];
  for (const a of addresses) {
    await vm.stateManager.putAccount(createAddressFromString(a), createAccount({ balance: 10000n * 10n**18n }));
  }
  return vm;
}

async function scanPreciseBoundary() {
  console.log('========================================================================================');
  console.log('TASK 2 — PRECISE BOUNDARY GAS SCAN (Step: 2,500 gas from 300,000 to 335,000 gas)');
  console.log('========================================================================================\n');

  const testLimits = [
    300000, 302500, 305000, 307500, 310000, 312500, 315000, 317500,
    320000, 322500, 325000, 327500, 330000, 335000, 340000, 350000
  ];

  const results = [];

  for (const gl of testLimits) {
    const vm = await initEVM();

    // Deploy ProjectCore
    const coreDeploy = await vm.evm.runCall({
      caller: createAddressFromString(ADVISOR),
      data: hexToBytes(ProjectCoreArtifact.bin),
      gasLimit: 10000000n
    });
    const coreAddr = bytesToHex(coreDeploy.createdAddress.bytes);

    // Deploy InfiniteLoopAttacker
    const loopDeploy = await vm.evm.runCall({
      caller: createAddressFromString(STUDENT1),
      data: hexToBytes(InfiniteLoopArtifact.bin),
      gasLimit: 10000000n
    });
    const loopAddr = bytesToHex(loopDeploy.createdAddress.bytes);

    // Set BCS
    await vm.evm.runCall({
      caller: createAddressFromString(ADVISOR),
      to: createAddressFromString(coreAddr),
      data: hexToBytes(ProjectCoreArtifact.iface.encodeFunctionData('setBCSMember', [BCS1, true])),
      gasLimit: 10000000n
    });
    await vm.evm.runCall({
      caller: createAddressFromString(ADVISOR),
      to: createAddressFromString(coreAddr),
      data: hexToBytes(ProjectCoreArtifact.iface.encodeFunctionData('setBCSMember', [BCS2, true])),
      gasLimit: 10000000n
    });

    // Deposit 10 ETH
    await vm.evm.runCall({
      caller: createAddressFromString(STUDENT1),
      to: createAddressFromString(coreAddr),
      data: hexToBytes(ProjectCoreArtifact.iface.encodeFunctionData('deposit', [])),
      value: ethers.parseEther('10'),
      gasLimit: 10000000n
    });

    // Create Spend Request
    await vm.evm.runCall({
      caller: createAddressFromString(BCS1),
      to: createAddressFromString(coreAddr),
      data: hexToBytes(ProjectCoreArtifact.iface.encodeFunctionData('createSpendRequest', [loopAddr, ethers.parseEther('1'), 'Gas Griefing Scan'])),
      gasLimit: 10000000n
    });

    // BCS1 vote Yes
    await vm.evm.runCall({
      caller: createAddressFromString(BCS1),
      to: createAddressFromString(coreAddr),
      data: hexToBytes(ProjectCoreArtifact.iface.encodeFunctionData('voteSpendRequest', [1, true])),
      gasLimit: 10000000n
    });

    // BCS2 vote Yes with exact gasLimit
    const voteRes = await vm.evm.runCall({
      caller: createAddressFromString(BCS2),
      to: createAddressFromString(coreAddr),
      data: hexToBytes(ProjectCoreArtifact.iface.encodeFunctionData('voteSpendRequest', [1, true])),
      gasLimit: BigInt(gl)
    });

    // Check request status
    const reqRes = await vm.evm.runCall({
      caller: createAddressFromString(ADVISOR),
      to: createAddressFromString(coreAddr),
      data: hexToBytes(ProjectCoreArtifact.iface.encodeFunctionData('getSpendRequest', [1])),
      gasLimit: 10000000n
    });
    const reqDecoded = ProjectCoreArtifact.iface.decodeFunctionResult('getSpendRequest', reqRes.execResult.returnValue);

    const isSuccess = !voteRes.execResult.exceptionError;
    const gasUsed = voteRes.execResult.executionGasUsed.toString();
    const statusNames = ['Pending', 'Ready', 'Executed', 'Rejected', 'Expired', 'Cancelled'];
    const finalStatus = statusNames[Number(reqDecoded[8])];

    const est1_64 = Math.floor(gl / 64);

    results.push({
      gasLimit: gl,
      txSuccess: isSuccess,
      gasUsed: gasUsed,
      error: voteRes.execResult.exceptionError ? voteRes.execResult.exceptionError.error : 'None',
      finalStatus: finalStatus,
      est1_64: est1_64
    });
  }

  console.table(results);
}

scanPreciseBoundary().catch(console.error);
