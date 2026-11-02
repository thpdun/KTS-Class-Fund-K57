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

async function debugFlow5() {
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
  const advAddr = bytesToHex(advDeploy.createdAddress.bytes);
  await vm.stateManager.putAccount(createAddressFromString(advAddr), createAccount({ balance: 1000n * 10n**18n }));
  console.log('ContractAdvisor deployed at:', advAddr);

  // Deploy ProjectCore from ContractAdvisor address
  const coreDeploy = await vm.evm.runCall({
    caller: createAddressFromString(advAddr),
    data: hexToBytes(ProjectCoreArtifact.bin),
    gasLimit: 10000000n
  });
  const coreAddr = bytesToHex(coreDeploy.createdAddress.bytes);
  console.log('ProjectCore deployed at:', coreAddr);

  // Check core.advisor()
  const advCall = await vm.evm.runCall({
    caller: createAddressFromString(ADVISOR_EOA),
    to: createAddressFromString(coreAddr),
    data: hexToBytes(ProjectCoreArtifact.iface.encodeFunctionData('advisor', [])),
    gasLimit: 10000000n
  });
  console.log('core.advisor():', ProjectCoreArtifact.iface.decodeFunctionResult('advisor', advCall.execResult.returnValue)[0]);

  // Deposit 10 ETH
  await vm.evm.runCall({
    caller: createAddressFromString(STUDENT),
    to: createAddressFromString(coreAddr),
    data: hexToBytes(ProjectCoreArtifact.iface.encodeFunctionData('deposit', [])),
    value: ethers.parseEther('10'),
    gasLimit: 10000000n
  });

  // Set behavior to 1 (Revert)
  const setRes = await vm.evm.runCall({
    caller: createAddressFromString(ADVISOR_EOA),
    to: createAddressFromString(advAddr),
    data: hexToBytes(ContractAdvisorArtifact.iface.encodeFunctionData('setBehavior', [1])),
    gasLimit: 10000000n
  });
  console.log('setBehavior(1) success:', !setRes.execResult.exceptionError);

  // Check behavior
  const bRes = await vm.evm.runCall({
    caller: createAddressFromString(ADVISOR_EOA),
    to: createAddressFromString(advAddr),
    data: hexToBytes(ContractAdvisorArtifact.iface.encodeFunctionData('currentBehavior', [])),
    gasLimit: 10000000n
  });
  console.log('currentBehavior:', ContractAdvisorArtifact.iface.decodeFunctionResult('currentBehavior', bRes.execResult.returnValue)[0]);

  // Now ContractAdvisor calls withdrawAdminFee
  const wRes = await vm.evm.runCall({
    caller: createAddressFromString(advAddr),
    to: createAddressFromString(coreAddr),
    data: hexToBytes(ProjectCoreArtifact.iface.encodeFunctionData('withdrawAdminFee', [ethers.parseEther('0.05')])),
    gasLimit: 10000000n
  });

  console.log('withdrawAdminFee result:');
  console.log('  exceptionError:', wRes.execResult.exceptionError);
  console.log('  returnValue:', bytesToHex(wRes.execResult.returnValue));
}

debugFlow5().catch(console.error);
