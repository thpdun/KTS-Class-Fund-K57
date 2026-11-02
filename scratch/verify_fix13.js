const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

function sha256(data) {
  return crypto.createHash('sha256').update(typeof data === 'string' ? data : JSON.stringify(data)).digest('hex');
}

const solc20Path = 'C:\\Users\\Thao\\AppData\\Local\\npm-cache\\_npx\\dcf17ee7dc4f21b7\\node_modules\\solc';
const solc26Path = 'C:\\Users\\Thao\\AppData\\Local\\npm-cache\\_npx\\fcea0c4d773c1d63\\node_modules\\solc';

const solc20 = require(solc20Path);
const solc26 = require(solc26Path);

console.log('=== FIX 13 COMPILER VERIFICATION ===\n');
console.log('Solc 0.8.20 Version:', solc20.version());
console.log('Solc 0.8.26 Version (FIX 12 used):', solc26.version());

const sourcePath = path.resolve('contracts/project/ProjectCore.sol');
const sourceCode = fs.readFileSync(sourcePath, 'utf8');

function compile(solcInstance, evm = 'shanghai', runs = 200) {
  const input = {
    language: 'Solidity',
    sources: {
      'ProjectCore.sol': { content: sourceCode }
    },
    settings: {
      optimizer: { enabled: true, runs: runs },
      evmVersion: evm,
      outputSelection: {
        '*': {
          '*': ['abi', 'evm.bytecode', 'evm.deployedBytecode', 'metadata']
        }
      }
    }
  };
  const res = JSON.parse(solcInstance.compile(JSON.stringify(input)));
  const errs = res.errors ? res.errors.filter(e => e.severity === 'error') : [];
  const warns = res.errors ? res.errors.filter(e => e.severity === 'warning') : [];
  if (errs.length > 0) throw new Error('Compile error: ' + JSON.stringify(errs));
  const contract = res.contracts['ProjectCore.sol']['ProjectCore'];
  return {
    compilerVersion: solcInstance.version(),
    creationBytecode: contract.evm.bytecode.object,
    creationSize: contract.evm.bytecode.object.length / 2,
    runtimeBytecode: contract.evm.deployedBytecode.object,
    runtimeSize: contract.evm.deployedBytecode.object.length / 2,
    abi: contract.abi,
    warnings: warns
  };
}

console.log('\n--- 1. BIÊN DỊCH BẰNG SOLC 0.8.20 (Cấu hình chuẩn FIX 13: runs=200, EVM=shanghai) ---');
const res20 = compile(solc20, 'shanghai', 200);

console.log('Compiler 0.8.20 Warnings:', res20.warnings.length);
console.log('Creation Bytecode Size (0.8.20):', res20.creationSize, 'bytes');
console.log('Runtime Bytecode Size (0.8.20):', res20.runtimeSize, 'bytes');
console.log('Creation Bytecode Hash (0.8.20 SHA-256):', sha256(res20.creationBytecode));
console.log('Runtime Bytecode Hash (0.8.20 SHA-256):', sha256(res20.runtimeBytecode));
console.log('ABI Hash (0.8.20 SHA-256):', sha256(JSON.stringify(res20.abi)));

console.log('\n--- 2. BIÊN DỊCH BẰNG SOLC 0.8.26 (Để so sánh chính xác với FIX 12) ---');
const res26 = compile(solc26, 'shanghai', 200);
console.log('Creation Bytecode Size (0.8.26):', res26.creationSize, 'bytes');
console.log('Runtime Bytecode Size (0.8.26):', res26.runtimeSize, 'bytes');
console.log('Creation Bytecode Hash (0.8.26 SHA-256):', sha256(res26.creationBytecode));
console.log('Runtime Bytecode Hash (0.8.26 SHA-256):', sha256(res26.runtimeBytecode));
console.log('ABI Hash (0.8.26 SHA-256):', sha256(JSON.stringify(res26.abi)));

console.log('\n--- 3. ĐỐI CHIẾU VỚI CÁC ARTIFACT HIỆN TẠI ---');
const auditedAbi = JSON.parse(fs.readFileSync('scratch/audited_ProjectCore.abi', 'utf8'));

const htmlContent = fs.readFileSync('web/index.html', 'utf8');
const matchAbi = htmlContent.match(/const\s+CONTRACT_ABI\s*=\s*(\[[\s\S]*?\]);/);
const frontendAbi = JSON.parse(matchAbi[1]);

// FIX 12 values recorded:
const fix12AbiHash = '3043fba474ac9e652b6e4ad1e687da7326a482f959453b4c56f48ef38ec89d7a';
const fix12RuntimeHash = '21ea325838eb80caeb3d632d228f1376d64f0318c9ca1ecf5295be074f6d9013';
const fix12CreationHash = '10ec8e2914a10a90da47100b4eb647eb51e1814ae949ddf929f706380dfcf71c';

// So sánh cấu trúc ABI giữa 0.8.20 và 0.8.26
const abi20Str = JSON.stringify(res20.abi);
const abi26Str = JSON.stringify(res26.abi);
const auditedAbiStr = JSON.stringify(auditedAbi);
const frontendAbiStr = JSON.stringify(frontendAbi);

console.log('ABI 0.8.20 identical to ABI 0.8.26?:', abi20Str === abi26Str);
console.log('ABI 0.8.20 identical to audited_ProjectCore.abi?:', abi20Str === auditedAbiStr);
console.log('ABI 0.8.20 identical to web/index.html CONTRACT_ABI?:', abi20Str === frontendAbiStr);

// Kiểm tra chi tiết entry
function countEntries(abi) {
  return {
    functions: abi.filter(x => x.type === 'function').length,
    events: abi.filter(x => x.type === 'event').length,
    errors: abi.filter(x => x.type === 'error').length,
    constructor: abi.filter(x => x.type === 'constructor').length,
    receive: abi.filter(x => x.type === 'receive').length,
    fallback: abi.filter(x => x.type === 'fallback').length,
    total: abi.length
  };
}

const counts20 = countEntries(res20.abi);
console.log('\nThống kê số lượng ABI 0.8.20:', counts20);

// Kiểm tra giới hạn EIP
const eip3860Max = 49152;
const eip170Max = 24576;

console.log(`\nKiểm tra giới hạn EIP cho 0.8.20:`);
console.log(`  - Creation Bytecode: ${res20.creationSize} / ${eip3860Max} bytes (${(res20.creationSize / eip3860Max * 100).toFixed(2)}%) -> ${res20.creationSize <= eip3860Max ? 'PASS' : 'FAIL'}`);
console.log(`  - Runtime Bytecode: ${res20.runtimeSize} / ${eip170Max} bytes (${(res20.runtimeSize / eip170Max * 100).toFixed(2)}%) -> ${res20.runtimeSize <= eip170Max ? 'PASS' : 'FAIL'}`);

// Lưu kết quả vào scratch/fix13_results.json
fs.writeFileSync('scratch/fix13_results.json', JSON.stringify({
  solc20: {
    version: solc20.version(),
    creationSize: res20.creationSize,
    runtimeSize: res20.runtimeSize,
    creationHash: sha256(res20.creationBytecode),
    runtimeHash: sha256(res20.runtimeBytecode),
    abiHash: sha256(JSON.stringify(res20.abi)),
    counts: counts20
  },
  solc26: {
    version: solc26.version(),
    creationSize: res26.creationSize,
    runtimeSize: res26.runtimeSize,
    creationHash: sha256(res26.creationBytecode),
    runtimeHash: sha256(res26.runtimeBytecode),
    abiHash: sha256(JSON.stringify(res26.abi))
  },
  fix12Recorded: {
    abiHash: fix12AbiHash,
    creationHash: fix12CreationHash,
    runtimeHash: fix12RuntimeHash
  },
  comparisons: {
    abiIdenticalToFix12: sha256(JSON.stringify(res20.abi)) === fix12AbiHash,
    abiIdenticalToAudited: abi20Str === auditedAbiStr,
    abiIdenticalToFrontend: abi20Str === frontendAbiStr,
    runtimeBytecodeIdenticalToFix12: sha256(res20.runtimeBytecode) === fix12RuntimeHash
  }
}, null, 2));

console.log('\nĐã lưu toàn bộ kết quả vào scratch/fix13_results.json');
