const fs = require('fs');

const html = fs.readFileSync('web/index.html', 'utf8');

// Tìm vị trí CONTRACT_ABI
const abiIndex = html.indexOf('const CONTRACT_ABI =');
console.log('CONTRACT_ABI index:', abiIndex);

// Tìm hàm voteSpendRequest
const voteSpendMatch = html.match(/async\s+function\s+voteSpend[\s\S]*?(?=async\s+function|\n\s*\/\/\s*===|\n\s*function)/);
if (voteSpendMatch) {
  console.log('\n--- HÀM voteSpend TRONG FRONTEND ---');
  console.log(voteSpendMatch[0].slice(0, 1000));
}

// Tìm hàm voteRefund
const voteRefundMatch = html.match(/async\s+function\s+voteRefund[\s\S]*?(?=async\s+function|\n\s*\/\/\s*===|\n\s*function)/);
if (voteRefundMatch) {
  console.log('\n--- HÀM voteRefund TRONG FRONTEND ---');
  console.log(voteRefundMatch[0].slice(0, 1000));
}

// Tìm các event listeners
const setupListenersMatch = html.match(/(?:setupEventListeners|listenToEvents|subscribeEvents)[\s\S]*?(?=async\s+function|\n\s*\/\/\s*===|\n\s*function)/);
if (setupListenersMatch) {
  console.log('\n--- EVENT LISTENERS SETUP ---');
  console.log(setupListenersMatch[0].slice(0, 1000));
}

// Tìm vị trí hiển thị badge/status của đề xuất
const statusRenderMatch = html.match(/(?:renderRequests|renderSpendRequests|renderRefundRequests|getStatusBadge)[\s\S]*?(?=async\s+function|\n\s*\/\/\s*===|\n\s*function)/);
if (statusRenderMatch) {
  console.log('\n--- RENDER STATUS/REQUESTS ---');
  console.log(statusRenderMatch[0].slice(0, 1000));
}
