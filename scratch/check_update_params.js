const path = require('path');
const npxNodeModules = 'C:\\Users\\Thao\\AppData\\Local\\npm-cache\\_npx\\fcea0c4d773c1d63\\node_modules';
const { Common, Hardfork, Mainnet } = require(path.join(npxNodeModules, '@ethereumjs/common'));

const common = new Common({ chain: Mainnet, hardfork: Hardfork.Cancun });
console.log('EIP 3860 active?', common.isActivatedEIP(3860));
console.log('maxInitCodeSize:', common.param('vm', 'maxInitCodeSize'));
console.log('maxCodeSize:', common.param('vm', 'maxCodeSize'));

// Can we updateParams?
common.updateParams({
  vm: {
    maxInitCodeSize: 1000000000n,
    maxCodeSize: 1000000000n,
  }
});
console.log('Updated maxInitCodeSize:', common.param('vm', 'maxInitCodeSize'));
console.log('Updated maxCodeSize:', common.param('vm', 'maxCodeSize'));
