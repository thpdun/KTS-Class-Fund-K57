const { ethers } = require('ethers');

async function test() {
  const provider = new ethers.JsonRpcProvider('https://ethereum-sepolia-rpc.publicnode.com');
  const target = '0x1F066cB83F41857DcC5D230C74963b12F1E8f58C';
  const abi = [
    'event GasRefunded(address indexed recipient, uint256 gasUnits, uint256 gasPrice, uint256 amountPaid, uint256 shortfall)',
    'event GasRefundFailed(address indexed recipient, uint256 amountFailed)',
    'function adminFeePool() view returns (uint256)',
    'function classFundBalance() view returns (uint256)'
  ];
  const contract = new ethers.Contract(target, abi, provider);

  const pool = await contract.adminFeePool();
  console.log('Current adminFeePool:', pool.toString(), 'wei =', ethers.formatEther(pool), 'ETH');

  const currentBlock = await provider.getBlockNumber();
  console.log('Current block:', currentBlock);
  const startBlock = Math.max(0, currentBlock - 20000);

  const refundedFilter = contract.filters.GasRefunded();
  const failedFilter = contract.filters.GasRefundFailed();

  const refundedLogs = await contract.queryFilter(refundedFilter, startBlock, currentBlock);
  console.log('GasRefunded logs count:', refundedLogs.length);
  for (let i = 0; i < refundedLogs.length; i++) {
    const l = refundedLogs[i];
    console.log(`Refunded [${i}]: recipient=${l.args[0]}, gasUnits=${l.args[1]}, gasPrice=${l.args[2]}, amountPaid=${ethers.formatEther(l.args[3])} ETH, shortfall=${ethers.formatEther(l.args[4])} ETH, tx=${l.transactionHash}`);
  }

  const failedLogs = await contract.queryFilter(failedFilter, startBlock, currentBlock);
  console.log('GasRefundFailed logs count:', failedLogs.length);
  for (let i = 0; i < failedLogs.length; i++) {
    const l = failedLogs[i];
    console.log(`Failed [${i}]: recipient=${l.args[0]}, amountFailed=${ethers.formatEther(l.args[1])} ETH, tx=${l.transactionHash}`);
  }

  // Also check old contract 0x90948699FF04bC9cF159a39e200F09885439503D
  const oldTarget = '0x90948699FF04bC9cF159a39e200F09885439503D';
  const oldContract = new ethers.Contract(oldTarget, abi, provider);
  const oldPool = await oldContract.adminFeePool();
  console.log('\n--- Old Contract 0x9094... ---');
  console.log('Old contract adminFeePool:', oldPool.toString(), 'wei =', ethers.formatEther(oldPool), 'ETH');
  const oldRefundedLogs = await oldContract.queryFilter(refundedFilter, startBlock, currentBlock);
  console.log('Old contract GasRefunded logs count:', oldRefundedLogs.length);
  for (let i = 0; i < oldRefundedLogs.length; i++) {
    const l = oldRefundedLogs[i];
    console.log(`Old Refunded [${i}]: recipient=${l.args[0]}, amountPaid=${ethers.formatEther(l.args[3])} ETH, tx=${l.transactionHash}`);
  }
}

test().catch(console.error);

