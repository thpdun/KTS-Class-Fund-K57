const fs = require('fs');

const html = fs.readFileSync('web/index.html', 'utf8');
const compiledAbi = JSON.parse(fs.readFileSync('scratch/audited_ProjectCore.abi', 'utf8'));

// Trích xuất CONTRACT_ABI từ html
const match = html.match(/const\s+CONTRACT_ABI\s*=\s*(\[[\s\S]*?\]);/);
if (!match) {
  console.error('Không tìm thấy CONTRACT_ABI');
  process.exit(1);
}

const frontendAbi = JSON.parse(match[1]);

console.log('=== SO SÁNH ABI FRONTEND VỚI ABI BIÊN DỊCH PROJECTCORE.SOL ===\n');

// So sánh Functions
const compFns = compiledAbi.filter(x => x.type === 'function').map(x => x.name);
const frontFns = frontendAbi.filter(x => x.type === 'function').map(x => x.name);

console.log(`Số hàm trong Compiled ABI: ${compFns.length}`);
console.log(`Số hàm trong Frontend ABI: ${frontFns.length}`);

const missingFnsInFront = compFns.filter(f => !frontFns.includes(f));
const extraFnsInFront = frontFns.filter(f => !compFns.includes(f));
console.log('Hàm có trong Contract nhưng THIẾU trong Frontend:', missingFnsInFront);
console.log('Hàm có trong Frontend nhưng THIẾU trong Contract:', extraFnsInFront);

// So sánh Events
const compEvents = compiledAbi.filter(x => x.type === 'event').map(x => x.name);
const frontEvents = frontendAbi.filter(x => x.type === 'event').map(x => x.name);

console.log(`\nSố Event trong Compiled ABI: ${compEvents.length}`);
console.log(`Số Event trong Frontend ABI: ${frontEvents.length}`);

const missingEventsInFront = compEvents.filter(e => !frontEvents.includes(e));
const extraEventsInFront = frontEvents.filter(e => !compEvents.includes(e));
console.log('Event có trong Contract nhưng THIẾU trong Frontend:', missingEventsInFront);
console.log('Event có trong Frontend nhưng THIẾU trong Contract:', extraEventsInFront);

// So sánh Errors
const compErrors = compiledAbi.filter(x => x.type === 'error').map(x => x.name);
const frontErrors = frontendAbi.filter(x => x.type === 'error').map(x => x.name);

console.log(`\nSố Custom Error trong Compiled ABI: ${compErrors.length}`);
console.log(`Số Custom Error trong Frontend ABI: ${frontErrors.length}`);

const missingErrorsInFront = compErrors.filter(e => !frontErrors.includes(e));
console.log('Custom Error có trong Contract nhưng THIẾU trong Frontend:', missingErrorsInFront);
