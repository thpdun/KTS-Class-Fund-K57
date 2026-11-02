const fs = require('fs');
const path = require('path');
const npxNodeModules = 'C:\\Users\\Thao\\AppData\\Local\\npm-cache\\_npx\\fcea0c4d773c1d63\\node_modules';

const { createVM } = require(path.join(npxNodeModules, '@ethereumjs/vm'));
const { Common, Hardfork, Mainnet } = require(path.join(npxNodeModules, '@ethereumjs/common'));
const { createAddressFromString, createAccount, hexToBytes } = require(path.join(npxNodeModules, '@ethereumjs/util'));

async function testHardfork(hf) {
  try {
    const common = new Common({ chain: Mainnet, hardfork: hf });
    const vm = await createVM({ common });
    const runnerAddr = createAddressFromString('0x1000000000000000000000000000000000000001');
    await vm.stateManager.putAccount(runnerAddr, createAccount({ balance: 1000n * 10n**18n }));

    const binPath = path.join(__dirname, 'solc_out', 'test_ProjectCore_test_sol_ProjectCoreTest.bin');
    const bytecode = '0x' + fs.readFileSync(binPath, 'utf8').trim();

    const deployResult = await vm.evm.runCall({
      caller: runnerAddr,
      data: hexToBytes(bytecode),
      gasLimit: 100_000_000n,
      value: 100n * 10n**18n,
    });

    if (deployResult.execResult.exceptionError) {
      console.log(`Hardfork ${hf}: Deploy failed:`, deployResult.execResult.exceptionError.error);
    } else {
      console.log(`Hardfork ${hf}: Deploy SUCCESS! Address:`, deployResult.createdAddress.toString());
    }
  } catch (e) {
    console.log(`Hardfork ${hf} error:`, e.message);
  }
}

async function main() {
  await testHardfork(Hardfork.Paris);
  await testHardfork(Hardfork.London);
}

main();
