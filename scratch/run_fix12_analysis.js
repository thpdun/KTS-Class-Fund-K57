const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// Load solc
const npxNodeModules = 'C:\\Users\\Thao\\AppData\\Local\\npm-cache\\_npx\\fcea0c4d773c1d63\\node_modules';
const solc = require(path.join(npxNodeModules, 'solc'));

function sha256(data) {
  return crypto.createHash('sha256').update(typeof data === 'string' ? data : JSON.stringify(data)).digest('hex');
}

console.log('================================================================');
console.log('FIX 12 — TOÀN BỘ KIỂM TOÁN VÀ ĐÓNG BĂNG DỮ LIỆU DEPLOYMENT');
console.log('================================================================\n');

// 1. BIÊN DỊCH VỚI NHIỀU CẤU HÌNH ĐỂ ĐỐI CHIẾU
const sourcePath = path.resolve('contracts/project/ProjectCore.sol');
const sourceCode = fs.readFileSync(sourcePath, 'utf8');

function compile(optEnabled, runs, evm) {
  const input = {
    language: 'Solidity',
    sources: {
      'ProjectCore.sol': { content: sourceCode }
    },
    settings: {
      optimizer: { enabled: optEnabled, runs: runs },
      evmVersion: evm,
      outputSelection: {
        '*': {
          '*': ['abi', 'evm.bytecode', 'evm.deployedBytecode', 'metadata']
        }
      }
    }
  };
  const res = JSON.parse(solc.compile(JSON.stringify(input)));
  const errs = res.errors ? res.errors.filter(e => e.severity === 'error') : [];
  const warns = res.errors ? res.errors.filter(e => e.severity === 'warning') : [];
  if (errs.length > 0) throw new Error('Compile error: ' + JSON.stringify(errs));
  const contract = res.contracts['ProjectCore.sol']['ProjectCore'];
  return {
    creationBytecode: contract.evm.bytecode.object,
    creationSize: contract.evm.bytecode.object.length / 2,
    runtimeBytecode: contract.evm.deployedBytecode.object,
    runtimeSize: contract.evm.deployedBytecode.object.length / 2,
    abi: contract.abi,
    metadata: contract.metadata,
    warnings: warns
  };
}

// Cấu hình chuẩn Task 2: 0.8.20, optimizer true, runs 200, shanghai
const standardConfig = compile(true, 200, 'shanghai');
const cancunConfig = compile(true, 200, 'cancun');
const parisConfig = compile(true, 200, 'paris');
const noOptConfig = compile(false, 200, 'shanghai');

console.log('TASK 2 — CÔNG BỐ COMPILER SETTINGS & BYTECODE METRICS:');
console.log('----------------------------------------------------');
console.log('Solidity Compiler Version:', solc.version());
console.log('Standard Config (Optimizer=true, runs=200, EVM=shanghai):');
console.log('  - Creation Bytecode Size:', standardConfig.creationSize, 'bytes (EIP-3860 limit: 49,152 bytes)');
console.log('  - Runtime Bytecode Size:', standardConfig.runtimeSize, 'bytes (EIP-170 limit: 24,576 bytes)');
console.log('  - Warnings count:', standardConfig.warnings.length);
console.log('  - Creation Bytecode SHA-256:', sha256(standardConfig.creationBytecode));
console.log('  - Runtime Bytecode SHA-256:', sha256(standardConfig.runtimeBytecode));
console.log('  - ABI SHA-256:', sha256(JSON.stringify(standardConfig.abi)));

console.log('\nSo sánh kích thước theo EVM Version:');
console.log(`  - Shanghai (runs=200): Runtime = ${standardConfig.runtimeSize} bytes, Creation = ${standardConfig.creationSize} bytes`);
console.log(`  - Cancun (runs=200):   Runtime = ${cancunConfig.runtimeSize} bytes, Creation = ${cancunConfig.creationSize} bytes`);
console.log(`  - Paris (runs=200):    Runtime = ${parisConfig.runtimeSize} bytes, Creation = ${parisConfig.creationSize} bytes`);
console.log(`  - Shanghai (no opt):   Runtime = ${noOptConfig.runtimeSize} bytes, Creation = ${noOptConfig.creationSize} bytes`);

// 2. SO SÁNH 3 NGUỒN ABI
console.log('\nTASK 1 — SO SÁNH TRỰC TIẾP 3 BỘ ABI:');
console.log('------------------------------------');

const compiledAbi = standardConfig.abi;
const auditedAbi = JSON.parse(fs.readFileSync('scratch/audited_ProjectCore.abi', 'utf8'));

const htmlContent = fs.readFileSync('web/index.html', 'utf8');
const matchAbi = htmlContent.match(/const\s+CONTRACT_ABI\s*=\s*(\[[\s\S]*?\]);/);
if (!matchAbi) {
  console.error('Lỗi: Không tìm thấy CONTRACT_ABI trong web/index.html');
  process.exit(1);
}
const frontendAbi = JSON.parse(matchAbi[1]);

function summarizeAbi(abi) {
  const fns = abi.filter(x => x.type === 'function');
  const events = abi.filter(x => x.type === 'event');
  const errors = abi.filter(x => x.type === 'error');
  const ctor = abi.filter(x => x.type === 'constructor');
  const rcv = abi.filter(x => x.type === 'receive');
  const fb = abi.filter(x => x.type === 'fallback');
  return { fns, events, errors, ctor, rcv, fb, total: abi.length };
}

const sCompiled = summarizeAbi(compiledAbi);
const sAudited = summarizeAbi(auditedAbi);
const sFrontend = summarizeAbi(frontendAbi);

console.log('BẢNG TỔNG QUAN SỐ LƯỢNG ENTRY:');
console.log('| Mục | Compiled ABI (Source) | audited_ProjectCore.abi | web/index.html ABI |');
console.log('|---|---|---|---|');
console.log(`| Tổng số entries | ${sCompiled.total} | ${sAudited.total} | ${sFrontend.total} |`);
console.log(`| Functions | ${sCompiled.fns.length} | ${sAudited.fns.length} | ${sFrontend.fns.length} |`);
console.log(`| Events | ${sCompiled.events.length} | ${sAudited.events.length} | ${sFrontend.events.length} |`);
console.log(`| Custom Errors | ${sCompiled.errors.length} | ${sAudited.errors.length} | ${sFrontend.errors.length} |`);
console.log(`| Constructor | ${sCompiled.ctor.length} | ${sAudited.ctor.length} | ${sFrontend.ctor.length} |`);
console.log(`| Receive | ${sCompiled.rcv.length} | ${sAudited.rcv.length} | ${sFrontend.rcv.length} |`);
console.log(`| Fallback | ${sCompiled.fb.length} | ${sAudited.fb.length} | ${sFrontend.fb.length} |`);

// So sánh từng entry Functions
function formatFn(f) {
  const inputs = (f.inputs || []).map(i => `${i.type} ${i.name}`).join(', ');
  const outputs = (f.outputs || []).map(o => `${o.type} ${o.name}`).join(', ');
  return `${f.name}(${inputs})${outputs ? ` returns (${outputs})` : ''} [${f.stateMutability}]`;
}

function formatEvent(e) {
  const inputs = (e.inputs || []).map(i => `${i.type}${i.indexed ? ' indexed' : ''} ${i.name}`).join(', ');
  return `${e.name}(${inputs})`;
}

function formatError(err) {
  const inputs = (err.inputs || []).map(i => `${i.type} ${i.name}`).join(', ');
  return `${err.name}(${inputs})`;
}

const compFnSignatures = sCompiled.fns.map(formatFn).sort();
const auditFnSignatures = sAudited.fns.map(formatFn).sort();
const frontFnSignatures = sFrontend.fns.map(formatFn).sort();

const compEventSignatures = sCompiled.events.map(formatEvent).sort();
const auditEventSignatures = sAudited.events.map(formatEvent).sort();
const frontEventSignatures = sFrontend.events.map(formatEvent).sort();

const compErrorSignatures = sCompiled.errors.map(formatError).sort();
const auditErrorSignatures = sAudited.errors.map(formatError).sort();
const frontErrorSignatures = sFrontend.errors.map(formatError).sort();

console.log('\n--- KIỂM TRA ĐỘ KHỚP TỪNG PHẦN TỬ ---');

console.log('1. Khớp Functions (Compiled vs Audited):', JSON.stringify(compFnSignatures) === JSON.stringify(auditFnSignatures));
console.log('2. Khớp Functions (Compiled vs Frontend):', JSON.stringify(compFnSignatures) === JSON.stringify(frontFnSignatures));

console.log('3. Khớp Events (Compiled vs Audited):', JSON.stringify(compEventSignatures) === JSON.stringify(auditEventSignatures));
console.log('4. Khớp Events (Compiled vs Frontend):', JSON.stringify(compEventSignatures) === JSON.stringify(frontEventSignatures));

console.log('5. Khớp Errors (Compiled vs Audited):', JSON.stringify(compErrorSignatures) === JSON.stringify(auditErrorSignatures));
console.log('6. Khớp Errors (Compiled vs Frontend):', JSON.stringify(compErrorSignatures) === JSON.stringify(frontErrorSignatures));

console.log('\nDANH SÁCH TẤT CẢ 17 EVENTS TRONG COMPILED ABI:');
sCompiled.events.forEach((e, idx) => {
  console.log(`  ${idx + 1}. ${formatEvent(e)}`);
});

console.log('\nDANH SÁCH TẤT CẢ 26 ERRORS TRONG COMPILED ABI:');
sCompiled.errors.forEach((e, idx) => {
  console.log(`  ${idx + 1}. ${formatError(e)}`);
});

console.log('\nDANH SÁCH 39 FUNCTIONS TRONG COMPILED ABI:');
sCompiled.fns.forEach((f, idx) => {
  console.log(`  ${idx + 1}. ${formatFn(f)}`);
});

// TASK 3: KIỂM TRA CONSTRUCTOR VÀ ADVISOR
console.log('\nTASK 3 — KIỂM TRA CONSTRUCTOR & ADVISOR:');
console.log('----------------------------------------');
console.log('Constructor ABI:', JSON.stringify(sCompiled.ctor));
const ctorCodeMatch = sourceCode.match(/constructor\s*\((.*?)\)\s*\{([\s\S]*?)\}/);
if (ctorCodeMatch) {
  console.log('Constructor Source Parameters:', ctorCodeMatch[1].trim() === '' ? 'None (inputs: [])' : ctorCodeMatch[1]);
  console.log('Constructor Source Body:\n', ctorCodeMatch[2].trim());
}

// TASK 4: KIỂM TRA FRONTEND READINESS
console.log('\nTASK 4 — KIỂM TRA FRONTEND READINESS:');
console.log('------------------------------------');
// Kiểm tra tên hàm gọi trong frontend
const fnCallsInFrontend = [
  'createSpendRequest', 'voteSpendRequest', 'executeSpendRequest',
  'createRefundRequest', 'voteRefundRequest', 'executeRefundRequest',
  'withdrawAdminFee', 'setBCSMember', 'deposit',
  'studentContributions', 'classFundBalance', 'adminFeePool',
  'reservedSpendAmount', 'reservedRefundAmount', 'activeBCSCount',
  'spendRequests', 'refundRequests', 'isBCSMember', 'hasVoted', 'hasVotedRefund',
  'advisor', 'getAvailableClassFund', 'getAvailableSpendBudget',
  'FEE_BPS', 'BPS_DENOMINATOR', 'PASSING_THRESHOLD_BPS', 'VOTING_PERIOD',
  'spendRequestCount', 'refundRequestCount'
];

fnCallsInFrontend.forEach(fn => {
  const inCompiled = sCompiled.fns.some(f => f.name === fn) || fn === 'deposit'; // deposit có thể là receive hoặc custom
  const inSource = sourceCode.includes(fn);
  console.log(`  - Function/Field '${fn}': In Compiled ABI = ${inCompiled}, In Source = ${inSource}`);
});

// Kiểm tra event listeners/parsers trong frontend
console.log('\nKiểm tra event parsers trong frontend (voteSpend & voteRefund):');
const spendFailParser = htmlContent.includes('SpendExecutionFailed');
const refundFailParser = htmlContent.includes('RefundExecutionFailed');
const spendExecParser = htmlContent.includes('SpendRequestExecuted');
const refundExecParser = htmlContent.includes('RefundRequestExecuted');
console.log('  - Parse SpendExecutionFailed:', spendFailParser);
console.log('  - Parse RefundExecutionFailed:', refundFailParser);
console.log('  - Parse SpendRequestExecuted:', spendExecParser);
console.log('  - Parse RefundRequestExecuted:', refundExecParser);

// Kiểm tra các nút manual retry
const retrySpendBtn = htmlContent.includes('executeSpend') || htmlContent.includes('btn-execute-spend');
const retryRefundBtn = htmlContent.includes('executeRefund') || htmlContent.includes('btn-execute-refund');
console.log('  - Nút manual retry Spend Request:', retrySpendBtn);
console.log('  - Nút manual retry Refund Request:', retryRefundBtn);

// Ghi kết quả tổng hợp ra file tạm để xuất báo cáo
fs.writeFileSync('scratch/fix12_summary.json', JSON.stringify({
  compilerVersion: solc.version(),
  standardConfig: {
    creationSize: standardConfig.creationSize,
    runtimeSize: standardConfig.runtimeSize,
    creationSha256: sha256(standardConfig.creationBytecode),
    runtimeSha256: sha256(standardConfig.runtimeBytecode),
    abiSha256: sha256(JSON.stringify(standardConfig.abi))
  },
  abiStats: {
    compiled: { total: sCompiled.total, fns: sCompiled.fns.length, events: sCompiled.events.length, errors: sCompiled.errors.length },
    audited: { total: sAudited.total, fns: sAudited.fns.length, events: sAudited.events.length, errors: sAudited.errors.length },
    frontend: { total: sFrontend.total, fns: sFrontend.fns.length, events: sFrontend.events.length, errors: sFrontend.errors.length }
  },
  eventsList: compEventSignatures,
  errorsList: compErrorSignatures,
  fnsList: compFnSignatures
}, null, 2));

console.log('\nĐã lưu kết quả tóm tắt vào scratch/fix12_summary.json.');
