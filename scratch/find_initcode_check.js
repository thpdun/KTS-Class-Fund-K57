const fs = require('fs');
const path = require('path');
const npxNodeModules = 'C:\\Users\\Thao\\AppData\\Local\\npm-cache\\_npx\\fcea0c4d773c1d63\\node_modules';

function searchDir(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      searchDir(full);
    } else if (entry.name.endsWith('.js')) {
      const content = fs.readFileSync(full, 'utf8');
      if (content.includes('initcode exceeds max initcode size')) {
        console.log('Found in:', full);
        const lines = content.split('\n');
        for (let i = 0; i < lines.length; i++) {
          if (lines[i].includes('initcode exceeds max initcode size')) {
            console.log(lines.slice(Math.max(0, i - 10), i + 10).join('\n'));
          }
        }
      }
    }
  }
}

searchDir(path.join(npxNodeModules, '@ethereumjs', 'evm'));
