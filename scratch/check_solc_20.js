const path = require('path');
const npxNodeModules = 'C:\\Users\\Thao\\AppData\\Local\\npm-cache\\_npx\\fcea0c4d773c1d63\\node_modules';
const solc = require(path.join(npxNodeModules, 'solc'));

solc.loadRemoteVersion('v0.8.20+commit.a1b79de6', (err, solc20) => {
  if (err) {
    console.log('Error loading 0.8.20:', err.message);
  } else {
    console.log('Successfully loaded solc 0.8.20:', solc20.version());
  }
});
