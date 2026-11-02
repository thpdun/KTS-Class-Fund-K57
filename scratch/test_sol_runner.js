const fs = require('fs');
const path = require('path');
const npxNodeModules = 'C:\\Users\\Thao\\AppData\\Local\\npm-cache\\_npx\\fcea0c4d773c1d63\\node_modules';

const { createVM } = require(path.join(npxNodeModules, '@ethereumjs/vm'));
const { createAddressFromString, createAccount, bytesToHex, hexToBytes } = require(path.join(npxNodeModules, '@ethereumjs/util'));
const { ethers } = require(path.join(npxNodeModules, 'ethers'));

async function main() {
  const vm = await createVM({
    activatePrecompiles: true,
  });

  // BẬT CỜ CHO PHÉP UNLIMITED INITCODE & CONTRACT SIZE CHO TEST RUNNER (NHƯ REMIX VM)
  vm.evm.allowUnlimitedInitCodeSize = true;
  vm.evm.allowUnlimitedContractSize = true;

  const runnerAddr = createAddressFromString('0x1000000000000000000000000000000000000001');
  const account = createAccount({ balance: 10000n * 10n**18n }); // 10,000 ETH
  await vm.stateManager.putAccount(runnerAddr, account);

  // Load bytecode of ProjectCoreTest
  const binPath = path.join(__dirname, 'solc_out', 'test_ProjectCore_test_sol_ProjectCoreTest.bin');
  const abiPath = path.join(__dirname, 'solc_out', 'test_ProjectCore_test_sol_ProjectCoreTest.abi');
  const bytecode = '0x' + fs.readFileSync(binPath, 'utf8').trim();
  const abi = JSON.parse(fs.readFileSync(abiPath, 'utf8'));

  const iface = new ethers.Interface(abi);

  console.log('Deploying ProjectCoreTest contract to EVM with allowUnlimitedInitCodeSize=true...');
  const deployResult = await vm.evm.runCall({
    caller: runnerAddr,
    data: hexToBytes(bytecode),
    gasLimit: 300_000_000n,
    value: 100n * 10n**18n, // 100 ETH cho initialBalance
  });

  if (deployResult.execResult.exceptionError) {
    console.error('Deploy error:', deployResult.execResult.exceptionError);
    return;
  }

  const testContractAddr = deployResult.createdAddress;
  console.log('SUCCESS! ProjectCoreTest deployed at:', testContractAddr.toString());

  // Cấp thêm 500 ETH cho test contract trên EVM
  const testAcc = await vm.stateManager.getAccount(testContractAddr);
  testAcc.balance = 500n * 10n**18n;
  await vm.stateManager.putAccount(testContractAddr, testAcc);
  console.log('Test contract balance:', ethers.formatEther(testAcc.balance), 'ETH');

  // Gọi beforeEach()
  console.log('Calling beforeEach()...');
  const beforeEachData = iface.encodeFunctionData('beforeEach');
  const beforeEachRes = await vm.evm.runCall({
    caller: runnerAddr,
    to: testContractAddr,
    data: hexToBytes(beforeEachData),
    gasLimit: 100_000_000n,
  });

  if (beforeEachRes.execResult.exceptionError) {
    console.error('beforeEach error:', beforeEachRes.execResult.exceptionError);
    return;
  }
  console.log('beforeEach succeeded! Gas used:', beforeEachRes.execResult.executionGasUsed.toString());

  // Thử chạy một loạt các hàm test thực tế của ProjectCore_test.sol!
  const testFunctions = [
    'testGroupA1_Deposit1ETH_Split99_1',
    'testGroupA2_DirectReceive',
    'testGroupA3_ZeroAmountReverts',
    'testGroupA4_IntegerMathEdgeCases',
    'testGroupB1_AdvisorAddAndRemoveBCS',
    'testGroupB2_NonAdvisorCannotSetBCS',
  ];

  for (const fnName of testFunctions) {
    // Reset state bằng beforeEach trước mỗi test
    await vm.evm.runCall({
      caller: runnerAddr,
      to: testContractAddr,
      data: hexToBytes(iface.encodeFunctionData('beforeEach')),
      gasLimit: 100_000_000n,
    });

    const callData = iface.encodeFunctionData(fnName);
    const res = await vm.evm.runCall({
      caller: runnerAddr,
      to: testContractAddr,
      data: hexToBytes(callData),
      gasLimit: 100_000_000n,
      value: 10n * 10n**18n,
    });

    if (res.execResult.exceptionError) {
      console.log(`[FAIL] ${fnName}:`, res.execResult.exceptionError.error);
    } else {
      console.log(`[PASS] ${fnName} (Gas: ${res.execResult.executionGasUsed.toString()})`);
    }
  }
}

main().catch(console.error);
