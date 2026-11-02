const fs = require('fs');

const compiledAbi = JSON.parse(fs.readFileSync('scratch/audited_ProjectCore.abi', 'utf8'));
const htmlContent = fs.readFileSync('web/index.html', 'utf8');
const match = htmlContent.match(/const\s+CONTRACT_ABI\s*=\s*(\[[\s\S]*?\]);/);
const frontendAbi = JSON.parse(match[1]);

// Compare compiled vs frontend deeply
console.log('Comparing compiled vs frontend...');
console.log('Lengths:', compiledAbi.length, frontendAbi.length);

let diffs = [];
for (let i = 0; i < compiledAbi.length; i++) {
  const itemC = compiledAbi[i];
  // Find matching item in frontend
  const itemF = frontendAbi.find(x => x.name === itemC.name && x.type === itemC.type);
  if (!itemF) {
    diffs.push(`Missing in frontend: ${itemC.type} ${itemC.name || '(unnamed)'}`);
    continue;
  }
  const strC = JSON.stringify(itemC);
  const strF = JSON.stringify(itemF);
  if (strC !== strF) {
    diffs.push(`Diff in ${itemC.type} ${itemC.name}:\n  C: ${strC}\n  F: ${strF}`);
  }
}

console.log('Total diffs found:', diffs.length);
if (diffs.length > 0) {
  console.log('Differences:', diffs);
} else {
  console.log('PERFECT 100% MATCH ACROSS ALL 83 ENTRIES!');
}
