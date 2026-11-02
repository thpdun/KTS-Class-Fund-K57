const path = require('path');
const npxNodeModules = 'C:\\Users\\Thao\\AppData\\Local\\npm-cache\\_npx\\fcea0c4d773c1d63\\node_modules';
const { Common, Hardfork, Mainnet } = require(path.join(npxNodeModules, '@ethereumjs/common'));

// How does Common store params?
const common = new Common({ chain: Mainnet, hardfork: Hardfork.Cancun });
console.log('common.paramNames:', common.param);
// Let us inspect the internal _params or methods of common
console.log('common methods:', Object.getOwnPropertyNames(Object.getPrototypeOf(common)));
console.log('custom hardfork / eip options');
