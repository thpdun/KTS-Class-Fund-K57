const path = require('path');
const npxNodeModules = 'C:\\Users\\Thao\\AppData\\Local\\npm-cache\\_npx\\fcea0c4d773c1d63\\node_modules';
const { Common, Hardfork, Mainnet } = require(path.join(npxNodeModules, '@ethereumjs/common'));

console.log('Hardforks:', Object.keys(Hardfork));

// Check if we can instantiate Common with Paris / Merge
const commonParis = new Common({ chain: Mainnet, hardfork: Hardfork.Paris });
console.log('Paris maxInitCodeSize:', commonParis.param('gasConfig', 'maxInitCodeSize'));
console.log('Shanghai maxInitCodeSize:', new Common({ chain: Mainnet, hardfork: Hardfork.Shanghai }).param('gasConfig', 'maxInitCodeSize'));
