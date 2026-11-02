const fs = require('fs');

const html = fs.readFileSync('web/index.html', 'utf8');

const contractOnMatches = [...html.matchAll(/contract\.on\s*\(\s*["']([^"']+)["']/g)];
console.log('Contract.on events:', contractOnMatches.map(m => m[1]));

// Tìm xem có event listener nào khác không
const onMatches = [...html.matchAll(/\.on\s*\(\s*["']([^"']+)["']/g)];
console.log('Tất cả .on calls:', onMatches.map(m => m[1]));
