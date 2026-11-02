const https = require('https');
const fs = require('fs');

const targetAddr = '0xe3e1db1da1cae10e92337c36bb13004bf984ee91';
const rpcEndpoints = [
  'https://ethereum-sepolia-rpc.publicnode.com',
  'https://rpc.sepolia.org',
  'https://sepolia.gateway.tenderly.co',
  'https://1rpc.io/sepolia'
];

function rpcCall(endpoint, method, params) {
  return new Promise((resolve, reject) => {
    const url = new URL(endpoint);
    const body = JSON.stringify({
      jsonrpc: '2.0',
      id: 1,
      method: method,
      params: params,
    });

    const req = https.request({
      hostname: url.hostname,
      port: url.port || 443,
      path: url.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),
      },
      timeout: 8000,
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          resolve(json.result);
        } catch (e) {
          reject(e);
        }
      });
    });

    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy();
      reject(new Error('RPC Timeout'));
    });
    req.write(body);
    req.end();
  });
}

async function main() {
  console.log(`Đang truy vấn dữ liệu công khai trên Sepolia cho địa chỉ: ${targetAddr}...`);

  let code = null;
  let chainId = null;
  let successfulRpc = null;

  for (const rpc of rpcEndpoints) {
    try {
      console.log(`Thử kết nối RPC: ${rpc}`);
      chainId = await rpcCall(rpc, 'eth_chainId', []);
      code = await rpcCall(rpc, 'eth_getCode', [targetAddr, 'latest']);
      successfulRpc = rpc;
      break;
    } catch (err) {
      console.log(`  -> Lỗi kết nối RPC ${rpc}: ${err.message}`);
    }
  }

  if (!code || code === '0x' || code === '0x0') {
    console.log(`\nKết quả: Không tìm thấy contract bytecode tại ${targetAddr} hoặc RPC không phản hồi.`);
    if (code === '0x' || code === '0x0') {
      console.log('Địa chỉ này hiện là EOA hoặc chưa được deploy contract trên Sepolia.');
    }
    return;
  }

  console.log(`\nThành công kết nối qua ${successfulRpc}!`);
  console.log(`Chain ID: ${parseInt(chainId, 16)} (Sepolia = 11155111)`);
  console.log(`Runtime Bytecode Size on Sepolia: ${code.slice(2).length / 2} bytes`);

  // So sánh với local compiled runtime bytecode
  const localRuntime = fs.readFileSync('scratch/audited_ProjectCore_runtime.bin', 'utf8').trim();
  const onchainRuntime = code.slice(2);

  console.log(`Local compiled runtime size: ${localRuntime.length / 2} bytes`);

  if (onchainRuntime.toLowerCase() === localRuntime.toLowerCase()) {
    console.log('KẾT LUẬN: Runtime bytecode on-chain KHỚP HOÀN TOÀN với bản ProjectCore hiện tại!');
  } else {
    console.log('KẾT LUẬN: Runtime bytecode on-chain KHÁC với bản ProjectCore hiện tại.');
    console.log('-> Địa chỉ 0xe3e1db1da1cae10e92337c36bb13004bf984ee91 chứa phiên bản cũ (trước auto-execution).');
  }

  fs.writeFileSync('scratch/onchain_sepolia_code.bin', onchainRuntime);
}

main().catch(err => {
  console.log('Không thể kết nối internet hoặc RPC Sepolia:', err.message);
});
