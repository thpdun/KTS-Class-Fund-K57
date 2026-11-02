const fs = require('fs');

const html = fs.readFileSync('web/index.html', 'utf8');
const compiledAbi = JSON.parse(fs.readFileSync('scratch/audited_ProjectCore.abi', 'utf8'));

const startIdx = html.indexOf('const CONTRACT_ABI =');
const endIdx = html.indexOf(';', startIdx);

console.log('startIdx:', startIdx);
console.log('endIdx:', endIdx);
console.log('Length of declaration:', endIdx - startIdx);

// Lấy 2 event mới
const spendFailedEvent = compiledAbi.find(x => x.name === 'SpendExecutionFailed');
const refundFailedEvent = compiledAbi.find(x => x.name === 'RefundExecutionFailed');

console.log('SpendExecutionFailed:', JSON.stringify(spendFailedEvent));
console.log('RefundExecutionFailed:', JSON.stringify(refundFailedEvent));
