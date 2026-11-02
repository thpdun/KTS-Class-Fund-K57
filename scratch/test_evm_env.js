const path = require('path');
const npxNodeModules = 'C:\\Users\\Thao\\AppData\\Local\\npm-cache\\_npx\\fcea0c4d773c1d63\\node_modules';

try {
  const { createVM } = require(path.join(npxNodeModules, '@ethereumjs/vm'));
  const { ethers } = require(path.join(npxNodeModules, 'ethers'));
  console.log('Successfully required @ethereumjs/vm and ethers!');
} catch (e) {
  console.error('Error requiring modules:', e.message);
}
