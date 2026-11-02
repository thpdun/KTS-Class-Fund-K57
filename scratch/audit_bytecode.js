const fs = require('fs');
const path = require('path');
const solc = require('C:\\Users\\Thao\\AppData\\Local\\npm-cache\\_npx\\fcea0c4d773c1d63\\node_modules\\solc');

function compileContract(optimize = false, runs = 200, evmVersion = 'cancun') {
  const sourcePath = path.resolve('contracts/project/ProjectCore.sol');
  const sourceCode = fs.readFileSync(sourcePath, 'utf8');

  const input = {
    language: 'Solidity',
    sources: {
      'ProjectCore.sol': {
        content: sourceCode,
      },
    },
    settings: {
      optimizer: {
        enabled: optimize,
        runs: runs,
      },
      evmVersion: evmVersion,
      outputSelection: {
        '*': {
          '*': ['abi', 'evm.bytecode', 'evm.deployedBytecode'],
        },
      },
    },
  };

  const output = JSON.parse(solc.compile(JSON.stringify(input)));

  if (output.errors) {
    const fatal = output.errors.filter(e => e.severity === 'error');
    if (fatal.length > 0) {
      console.error('Compilation errors:', fatal);
      throw new Error('Compilation failed');
    }
  }

  const contract = output.contracts['ProjectCore.sol']['ProjectCore'];
  const creationBytecode = contract.evm.bytecode.object;
  const runtimeBytecode = contract.evm.deployedBytecode.object;

  const creationSize = creationBytecode.length / 2;
  const runtimeSize = runtimeBytecode.length / 2;

  return {
    compilerVersion: solc.version(),
    optimize,
    runs,
    evmVersion,
    creationSize,
    runtimeSize,
    creationBytecode,
    runtimeBytecode,
    abi: contract.abi,
  };
}

console.log('=== KẾT QUẢ PHÂN TÍCH BYTECODE PROJECTCORE ===\n');

// 1. Without optimizer (Cancun)
const noOpt = compileContract(false, 200, 'cancun');
console.log('1. Cấu hình KHÔNG OPTIMIZER (Cancun):');
console.log(`   - Compiler version: ${noOpt.compilerVersion}`);
console.log(`   - Creation bytecode size: ${noOpt.creationSize} bytes (Giới hạn EIP-3860 Shanghai: 49,152 bytes) -> ${noOpt.creationSize <= 49152 ? 'ĐẠT' : 'VƯỢT'}`);
console.log(`   - Runtime / Deployed bytecode size: ${noOpt.runtimeSize} bytes (Giới hạn EIP-170 Spurious Dragon: 24,576 bytes) -> ${noOpt.runtimeSize <= 24576 ? 'ĐẠT' : 'VƯỢT'}`);

// 2. With optimizer (runs = 200, Cancun)
const withOpt = compileContract(true, 200, 'cancun');
console.log('\n2. Cấu hình CÓ OPTIMIZER (runs = 200, Cancun):');
console.log(`   - Compiler version: ${withOpt.compilerVersion}`);
console.log(`   - Creation bytecode size: ${withOpt.creationSize} bytes -> ${withOpt.creationSize <= 49152 ? 'ĐẠT' : 'VƯỢT'}`);
console.log(`   - Runtime / Deployed bytecode size: ${withOpt.runtimeSize} bytes -> ${withOpt.runtimeSize <= 24576 ? 'ĐẠT' : 'VƯỢT'}`);

// 3. With optimizer (runs = 200, Shanghai)
const shanghaiOpt = compileContract(true, 200, 'shanghai');
console.log('\n3. Cấu hình CÓ OPTIMIZER (runs = 200, Shanghai):');
console.log(`   - Creation bytecode size: ${shanghaiOpt.creationSize} bytes -> ${shanghaiOpt.creationSize <= 49152 ? 'ĐẠT' : 'VƯỢT'}`);
console.log(`   - Runtime / Deployed bytecode size: ${shanghaiOpt.runtimeSize} bytes -> ${shanghaiOpt.runtimeSize <= 24576 ? 'ĐẠT' : 'VƯỢT'}`);

// Save audited ABI and bytecode to scratch for verification
fs.writeFileSync('scratch/audited_ProjectCore.abi', JSON.stringify(withOpt.abi, null, 2));
fs.writeFileSync('scratch/audited_ProjectCore.bin', withOpt.creationBytecode);
fs.writeFileSync('scratch/audited_ProjectCore_runtime.bin', withOpt.runtimeBytecode);
