const fs = require('fs');
const path = require('path');
const npxNodeModules = 'C:\\Users\\Thao\\AppData\\Local\\npm-cache\\_npx\\fcea0c4d773c1d63\\node_modules';

const { createVM } = require(path.join(npxNodeModules, '@ethereumjs/vm'));
const { createAddressFromString, createAccount, bytesToHex, hexToBytes } = require(path.join(npxNodeModules, '@ethereumjs/util'));
const { ethers } = require(path.join(npxNodeModules, 'ethers'));

async function main() {
  const vm = await createVM({ activatePrecompiles: true });
  vm.evm.allowUnlimitedInitCodeSize = true;
  vm.evm.allowUnlimitedContractSize = true;

  const runnerAddr = createAddressFromString('0x1000000000000000000000000000000000000001');
  await vm.stateManager.putAccount(runnerAddr, createAccount({ balance: 10000n * 10n**18n }));

  const binPath = path.join(__dirname, 'solc_out', 'test_ProjectCore_test_sol_ProjectCoreTest.bin');
  const bytecode = '0x' + fs.readFileSync(binPath, 'utf8').trim();

  // Try with value = 0 first, because in Solidity constructor is non-payable unless marked payable!
  console.log('Trying deploy with value = 0...');
  const res1 = await vm.evm.runCall({
    caller: runnerAddr,
    data: hexToBytes(bytecode),
    gasLimit: 300_000_000n,
    value: 0n,
  });

  if (res1.execResult.exceptionError) {
    console.log('Value=0 error:', res1.execResult.exceptionError.error);
    const retHex = bytesToHex(res1.execResult.returnValue);
    console.log('Return value hex:', retHex);
  } else {
    console.log('Value=0 SUCCESS! Address:', res1.createdAddress.toString());
  }
}

main().catch(console.error);
