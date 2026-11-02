const paths = [
  'C:\\Users\\Thao\\AppData\\Local\\npm-cache\\_npx\\5418e66fe108ee42\\node_modules\\solc',
  'C:\\Users\\Thao\\AppData\\Local\\npm-cache\\_npx\\cd7d3ad854976e28\\node_modules\\solc',
  'C:\\Users\\Thao\\AppData\\Local\\npm-cache\\_npx\\dc2ab74206152663\\node_modules\\solc',
  'C:\\Users\\Thao\\AppData\\Local\\npm-cache\\_npx\\dcf17ee7dc4f21b7\\node_modules\\solc',
  'C:\\Users\\Thao\\AppData\\Local\\npm-cache\\_npx\\fcea0c4d773c1d63\\node_modules\\solc'
];

for (const p of paths) {
  try {
    const solc = require(p);
    console.log(p, '=>', solc.version());
  } catch (e) {
    console.log(p, '=> ERROR:', e.message);
  }
}
