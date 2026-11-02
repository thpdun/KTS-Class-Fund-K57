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
const ContractAdvisorArtifact = loadContract('scratch_GasGriefingAttackerContracts', 'ContractAdvisor');

async function testFlow5Behaviors() {
  console.log('--- TEST FLOW 5: withdrawAdminFee VỚI CONTRACT ADVISOR ---');
  const behaviors = [
    { name: '1. Accept ETH', id: 0 },
    { name: '2. Revert', id: 1 },
    { name: '3. Burn Gas', id: 2 },
    { name: '4. Infinite Loop (OOG)', id: 3 },
    { name: '5. Reentrancy Attempt', id: 4 }
  ];

  for (const b of behaviors) {
    const vm = await createVM({ activatePrecompiles: true });
    vm.evm.allowUnlimitedInitCodeSize = true;
    vm.evm.allowUnlimitedContractSize = true;

    const ADVISOR_EOA = '0x1000000000000000000000000000000000000001';
    const STUDENT = '0x3000000000000000000000000000000000000001';
    await vm.stateManager.putAccount(createAddressFromString(ADVISOR_EOA), createAccount({ balance: 1000n * 10n**18n }));
    await vm.stateManager.putAccount(createAddressFromString(STUDENT), createAccount({ balance: 1000n * 10n**18n }));

    // Deploy ContractAdvisor first
    const advDeploy = await vm.evm.runCall({
      caller: createAddressFromString(ADVISOR_EOA),
      data: hexToBytes(ContractAdvisorArtifact.bin + ContractAdvisorArtifact.iface.encodeDeploy(['0x0000000000000000000000000000000000000000']).slice(2)),
      gasLimit: 10000000n
    });
    const advContractAddr = bytesToHex(advDeploy.createdAddress.bytes);

    // Give balance to ContractAdvisor WITHOUT replacing account code!
    const acct = await vm.stateManager.getAccount(createAddressFromString(advContractAddr));
    acct.balance = 1000n * 10n**18n;
    await vm.stateManager.putAccount(createAddressFromString(advContractAddr), acct);

    // Deploy ProjectCore from ContractAdvisor address so ContractAdvisor is advisor
    const coreDeploy = await vm.evm.runCall({
      caller: createAddressFromString(advContractAddr),
      data: hexToBytes(ProjectCoreArtifact.bin),
      gasLimit: 10000000n
    });
    const coreAddr = bytesToHex(coreDeploy.createdAddress.bytes);

    // Deposit 10 ETH into core -> 0.1 ETH into adminFeePool
    await vm.evm.runCall({
      caller: createAddressFromString(STUDENT),
      to: createAddressFromString(coreAddr),
      data: hexToBytes(ProjectCoreArtifact.iface.encodeFunctionData('deposit', [])),
      value: ethers.parseEther('10'),
      gasLimit: 10000000n
    });

    // Set behavior
    await vm.evm.runCall({
      caller: createAddressFromString(ADVISOR_EOA),
      to: createAddressFromString(advContractAddr),
      data: hexToBytes(ContractAdvisorArtifact.iface.encodeFunctionData('setBehavior', [b.id])),
      gasLimit: 10000000n
    });

    // Call withdrawAdminFee(0.05 ether) from ContractAdvisor
    const wRes = await vm.evm.runCall({
      caller: createAddressFromString(advContractAddr),
      to: createAddressFromString(coreAddr),
      data: hexToBytes(ProjectCoreArtifact.iface.encodeFunctionData('withdrawAdminFee', [ethers.parseEther('0.05')])),
      gasLimit: 600000n
    });

    // Check pool after
    const poolRes = await vm.evm.runCall({
      caller: createAddressFromString(ADVISOR_EOA),
      to: createAddressFromString(coreAddr),
      data: hexToBytes(ProjectCoreArtifact.iface.encodeFunctionData('adminFeePool', [])),
      gasLimit: 10000000n
    });
    const poolAfter = ProjectCoreArtifact.iface.decodeFunctionResult('adminFeePool', poolRes.execResult.returnValue)[0];

    const isSuccess = !wRes.execResult.exceptionError;
    console.log(`[${b.name}] Tx Success = ${isSuccess}, GasUsed = ${wRes.execResult.executionGasUsed}, Error = ${wRes.execResult.exceptionError?.error || 'None'}`);
    console.log(`  -> adminFeePool: 0.1 ETH -> ${ethers.formatEther(poolAfter)} ETH (Bảo toàn = ${!isSuccess ? poolAfter === ethers.parseEther('0.1') : poolAfter === ethers.parseEther('0.05')})\n`);
  }
}

testFlow5Behaviors().catch(console.error);
