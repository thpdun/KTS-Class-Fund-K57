const path = require('path');
const npxNodeModules = 'C:\\Users\\Thao\\AppData\\Local\\npm-cache\\_npx\\fcea0c4d773c1d63\\node_modules';
const { createVM } = require(path.join(npxNodeModules, '@ethereumjs/vm'));
const { Address, Account, bytesToHex, hexToBytes } = require(path.join(npxNodeModules, '@ethereumjs/util'));

async function main() {
  const vm = await createVM({
    activatePrecompiles: true,
  });

  const address = Address.fromString('0x1111111111111111111111111111111111111111');
  const account = new Account(0n, 1000n * 10n**18n); // 1000 ETH
  await vm.stateManager.putAccount(address, account);

  const acc = await vm.stateManager.getAccount(address);
  console.log('Account balance:', acc.balance.toString());
}

main().catch(console.error);
