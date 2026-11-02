const fs = require('fs');
const path = require('path');

const html = fs.readFileSync('web/index.html', 'utf8');

console.log('HTML size:', html.length, 'characters');

// 1. Tìm các chuỗi 0x địa chỉ Ethereum
const ethAddrRegex = /0x[a-fA-F0-9]{40}/g;
const addresses = [...new Set(html.match(ethAddrRegex) || [])];
console.log('\n--- CÁC ĐỊA CHỈ VÍ / CONTRACT TÌM THẤY TRONG HTML ---');
console.log(addresses);

// 2. Kiểm tra địa chỉ cụ thể 0xe3e1db1da1cae10e92337c36bb13004bf984ee91
const targetAddr = '0xe3e1db1da1cae10e92337c36bb13004bf984ee91';
console.log(`\nCó chứa target address (${targetAddr}) không?`, html.toLowerCase().includes(targetAddr.toLowerCase()));

// 3. Tìm các biến contractAddress hoặc tương tự
const contractVars = html.match(/(?:contractAddress|CONTRACT_ADDRESS|CORE_ADDRESS|coreAddress|contract_address|ADDRESS)\s*[:=]\s*["'`]([^"'`]+)["'`]/gi);
console.log('\n--- CÁC BIẾN ADDRESS GÁN TRONG JS ---');
console.log(contractVars);

// 4. Tìm các script tags
const scriptMatches = [...html.matchAll(/<script[\s\S]*?>([\s\S]*?)<\/script>/gi)];
console.log(`\nTổng số thẻ <script>: ${scriptMatches.length}`);

// 5. Tìm ABI được định nghĩa
const abiMatches = html.match(/(?:const|let|var)\s+([a-zA-Z0-9_]*ABI[a-zA-Z0-9_]*)\s*=\s*(\[[\s\S]*?\]);/gi);
if (abiMatches) {
  console.log(`\n--- TÌM THẤY ${abiMatches.length} KHAI BÁO ABI ---`);
  for (const m of abiMatches) {
    console.log(m.slice(0, 200) + '...');
  }
} else {
  console.log('\nKhông thấy regex ABI chuẩn, tìm các mảng JSON có type function...');
  const jsonMatches = html.match(/\[\s*\{\s*["']type["']\s*:\s*["']function["'][\s\S]*?\]/gi);
  console.log('Found json function arrays:', jsonMatches ? jsonMatches.length : 0);
}

// 6. Tìm các lệnh gọi hàm contract
const fnNames = [
  'createSpendRequest', 'voteSpendRequest', 'executeSpendRequest', 'expireSpendRequest', 'cancelSpendRequest',
  'createRefundRequest', 'voteRefundRequest', 'executeRefundRequest', 'expireRefundRequest', 'cancelRefundRequest',
  'deposit', 'withdrawAdminFee', 'setBCSMember', 'isBCSMember', 'activeBCSCount', 'classFundBalance', 'adminFeePool',
  'reservedSpendAmount', 'reservedRefundAmount', 'getAvailableClassFund', 'getFundBalance'
];

console.log('\n--- CÁC HÀM CONTRACT ĐƯỢC GỌI TRONG FRONTEND ---');
for (const fn of fnNames) {
  const count = (html.match(new RegExp(`\\b${fn}\\b`, 'g')) || []).length;
  console.log(`  - ${fn}: xuất hiện ${count} lần`);
}

// 7. Tìm các event được lắng nghe trong frontend
const eventNames = [
  'SpendRequestCreated', 'SpendRequestVoted', 'SpendRequestExecuted', 'SpendRequestReady', 'SpendExecutionFailed',
  'RefundRequested', 'RefundRequestVoted', 'RefundRequestExecuted', 'RefundRequestReady', 'RefundExecutionFailed', 'RefundProcessed',
  'FundDeposited', 'AdminFeeCollected', 'AdminFeeWithdrawn', 'BCSMemberUpdated'
];

console.log('\n--- CÁC SỰ KIỆN ĐƯỢC TÌM THẤY TRONG FRONTEND ---');
for (const ev of eventNames) {
  const count = (html.match(new RegExp(`\\b${ev}\\b`, 'g')) || []).length;
  console.log(`  - ${ev}: xuất hiện ${count} lần`);
}
