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

  const deployerStr = '0x1000000000000000000000000000000000000001';
  const deployerAddr = createAddressFromString(deployerStr);
  const account = createAccount({ balance: 1000n * 10n**18n }); // 1000 ETH
  await vm.stateManager.putAccount(deployerAddr, account);

  // Load bytecode of ProjectCore
  const binPath = path.join(__dirname, 'solc_out', 'contracts_project_ProjectCore_sol_ProjectCore.bin');
  const abiPath = path.join(__dirname, 'solc_out', 'contracts_project_ProjectCore_sol_ProjectCore.abi');
  const bytecode = '0x' + fs.readFileSync(binPath, 'utf8').trim();
  const abi = JSON.parse(fs.readFileSync(abiPath, 'utf8'));

  const iface = new ethers.Interface(abi);

  // Deploy ProjectCore
  const deployResult = await vm.evm.runCall({
    caller: deployerAddr,
    data: hexToBytes(bytecode),
    gasLimit: 30_000_000n,
    value: 0n,
  });

  if (deployResult.execResult.exceptionError) {
    throw new Error('Deploy failed: ' + deployResult.execResult.exceptionError.error);
  }

  const contractAddr = deployResult.createdAddress;
  console.log('ProjectCore deployed at:', contractAddr.toString());

  // Test deposit 10 ETH
  const depositData = iface.encodeFunctionData('deposit');
  const depositResult = await vm.evm.runCall({
    caller: deployerAddr,
    to: contractAddr,
    data: hexToBytes(depositData),
    gasLimit: 1_000_000n,
    value: 10n * 10n**18n, // 10 ETH
  });

  console.log('Deposit exception:', depositResult.execResult.exceptionError);
  console.log('Deposit gas used:', depositResult.execResult.executionGasUsed.toString());
  console.log('Deposit logs count:', depositResult.execResult.logs.length);

  // Call getFundBalance
  const getFundData = iface.encodeFunctionData('getFundBalance');
  const getFundResult = await vm.evm.runCall({
    caller: deployerAddr,
    to: contractAddr,
    data: hexToBytes(getFundData),
    gasLimit: 1_000_000n,
  });

  const [fundBal] = iface.decodeFunctionResult('getFundBalance', bytesToHex(getFundResult.execResult.returnValue));
  console.log('Fund balance on EVM:', ethers.formatEther(fundBal), 'ETH (Expected 9.9 ETH)');
}

main().catch(console.error);
