const path = require('path');
const npxNodeModules = 'C:\\Users\\Thao\\AppData\\Local\\npm-cache\\_npx\\fcea0c4d773c1d63\\node_modules';
const utilModule = require(path.join(npxNodeModules, '@ethereumjs/util'));

for (const k of Object.keys(utilModule)) {
  if (k.toLowerCase().includes('address') || k.toLowerCase().includes('account')) {
    console.log(k, typeof utilModule[k]);
  }
}
