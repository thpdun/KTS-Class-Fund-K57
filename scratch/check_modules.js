const path = require('path');
const npxNodeModules = 'C:\\Users\\Thao\\AppData\\Local\\npm-cache\\_npx\\fcea0c4d773c1d63\\node_modules';

try {
  const vmModule = require(path.join(npxNodeModules, '@ethereumjs/vm'));
  const utilModule = require(path.join(npxNodeModules, '@ethereumjs/util'));
  console.log('VM keys:', Object.keys(vmModule));
  console.log('Util keys:', Object.keys(utilModule).slice(0, 15));
} catch (e) {
  console.error('Error:', e);
}
