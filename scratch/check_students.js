const { ethers } = require('ethers');
const fs = require('fs');

async function test() {
  const provider = new ethers.JsonRpcProvider('https://ethereum-sepolia-rpc.publicnode.com');
  const target = '0x1F066cB83F41857DcC5D230C74963b12F1E8f58C';
  const abi = [
    'function studentTotalDeposited(address) view returns (uint256)',
    'function studentContributions(address) view returns (uint256)',
    'function paidInCollection(uint256, address) view returns (uint256)',
    'function classFundBalance() view returns (uint256)'
  ];
  const c = new ethers.Contract(target, abi, provider);
  const roster = JSON.parse(fs.readFileSync('backend/class_roster.json', 'utf8'));
  console.log('Total fund balance:', ethers.formatEther(await c.classFundBalance()), 'ETH');
  for (const s of roster) {
    const total = await c.studentTotalDeposited(s.wallet);
    const cont = await c.studentContributions(s.wallet);
    const colPaid = await c.paidInCollection(1, s.wallet);
    console.log(`${s.name} (${s.wallet.slice(0, 10)}...): totalDeposited=${ethers.formatEther(total)} ETH, cont=${ethers.formatEther(cont)} ETH, col#1Paid=${ethers.formatEther(colPaid)} ETH`);
  }
}

test().catch(console.error);
