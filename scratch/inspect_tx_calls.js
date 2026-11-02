const fs = require('fs');

const content = fs.readFileSync('web/index.html', 'utf8');
const lines = content.split('\n');

const targets = ['voteSpendRequest', 'voteRefundRequest', 'executeSpendRequest', 'executeRefundRequest', 'withdrawAdminFee', 'estimateGas', 'gasLimit'];

console.log('--- SEARCHING IN WEB/INDEX.HTML ---');
lines.forEach((line, idx) => {
  targets.forEach(t => {
    if (line.includes(t)) {
      console.log(`L${idx + 1} [${t}]: ${line.trim()}`);
    }
  });
});
