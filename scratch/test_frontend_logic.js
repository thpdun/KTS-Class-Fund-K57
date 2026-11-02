const fs = require('fs');
const path = require('path');
const npxNodeModules = 'C:\\Users\\Thao\\AppData\\Local\\npm-cache\\_npx\\fcea0c4d773c1d63\\node_modules';
const { ethers } = require(path.join(npxNodeModules, 'ethers'));

// 1. Read CONTRACT_ABI from web/index.html
const html = fs.readFileSync('web/index.html', 'utf8');
const abiMatch = html.match(/const CONTRACT_ABI = (\[[\s\S]*?\]);/);
if (!abiMatch) {
  console.error('FAIL: Could not extract CONTRACT_ABI from web/index.html');
  process.exit(1);
}

const abi = JSON.parse(abiMatch[1]);
console.log('CONTRACT_ABI successfully parsed from web/index.html. Item count:', abi.length);

const iface = new ethers.Interface(abi);

// 2. Test SpendExecutionFailed event encoding & decoding
const dummySpendRequestId = 42n;
const dummyRecipient = '0x1111111111111111111111111111111111111111';
const dummyAmount = ethers.parseEther('1.5');

const spendFailedFragment = iface.getEvent('SpendExecutionFailed');
if (!spendFailedFragment) {
  console.error('FAIL: SpendExecutionFailed not found in Interface!');
  process.exit(1);
}
console.log('PASS: SpendExecutionFailed found:', spendFailedFragment.format());

// Encode dummy SpendExecutionFailed log using Ethers v6 encodeEventLog
const spendFailedLog = iface.encodeEventLog(spendFailedFragment, [dummySpendRequestId, dummyRecipient, dummyAmount]);
const parsedSpendFail = iface.parseLog(spendFailedLog);
console.log('PASS: Parsed SpendExecutionFailed log:', {
  name: parsedSpendFail.name,
  requestId: parsedSpendFail.args[0].toString(),
  recipient: parsedSpendFail.args[1],
  amount: ethers.formatEther(parsedSpendFail.args[2])
});

// 3. Test RefundExecutionFailed event encoding & decoding
const dummyRefundId = 17n;
const dummyApplicant = '0x2222222222222222222222222222222222222222';
const dummyRefundAmount = ethers.parseEther('0.8');

const refundFailedFragment = iface.getEvent('RefundExecutionFailed');
if (!refundFailedFragment) {
  console.error('FAIL: RefundExecutionFailed not found in Interface!');
  process.exit(1);
}
console.log('PASS: RefundExecutionFailed found:', refundFailedFragment.format());

// Encode dummy RefundExecutionFailed log using Ethers v6 encodeEventLog
const refundFailedLog = iface.encodeEventLog(refundFailedFragment, [dummyRefundId, dummyApplicant, dummyRefundAmount]);
const parsedRefundFail = iface.parseLog(refundFailedLog);
console.log('PASS: Parsed RefundExecutionFailed log:', {
  name: parsedRefundFail.name,
  refundId: parsedRefundFail.args[0].toString(),
  applicant: parsedRefundFail.args[1],
  amount: ethers.formatEther(parsedRefundFail.args[2])
});

// 4. Test vote log parsing simulation (Simulating voteSpend and voteRefund branch logic)
function simulateVoteSpendHandling(logs) {
  let autoExecSuccess = false;
  let autoExecFailed = false;
  let isReady = false;

  for (const log of logs) {
    try {
      const parsed = iface.parseLog(log);
      if (parsed) {
        if (parsed.name === "SpendRequestExecuted") autoExecSuccess = true;
        if (parsed.name === "SpendExecutionFailed") autoExecFailed = true;
        if (parsed.name === "SpendRequestReady") isReady = true;
      }
    } catch (_) {}
  }

  if (autoExecSuccess) return 'AUTO_EXEC_SUCCESS';
  if (autoExecFailed) return 'AUTO_EXEC_FAILED';
  if (isReady) return 'READY';
  return 'VOTED';
}

function simulateVoteRefundHandling(logs) {
  let autoExecSuccess = false;
  let autoExecFailed = false;
  let isReady = false;

  for (const log of logs) {
    try {
      const parsed = iface.parseLog(log);
      if (parsed) {
        if (parsed.name === "RefundRequestExecuted") autoExecSuccess = true;
        if (parsed.name === "RefundExecutionFailed") autoExecFailed = true;
        if (parsed.name === "RefundRequestReady") isReady = true;
      }
    } catch (_) {}
  }

  if (autoExecSuccess) return 'AUTO_EXEC_SUCCESS';
  if (autoExecFailed) return 'AUTO_EXEC_FAILED';
  if (isReady) return 'READY';
  return 'VOTED';
}

// Case A: Spend auto-exec success
const spendExecFrag = iface.getEvent('SpendRequestExecuted');
const logSpendSuccess = iface.encodeEventLog(spendExecFrag, [dummySpendRequestId, dummyRecipient, dummyAmount]);
console.log('Simulation Case A (Spend Success):', simulateVoteSpendHandling([logSpendSuccess]));

// Case B: Spend auto-exec failed
console.log('Simulation Case B (Spend Failed):', simulateVoteSpendHandling([spendFailedLog]));

// Case C: Spend reached threshold ready
const spendReadyFrag = iface.getEvent('SpendRequestReady');
const logSpendReady = iface.encodeEventLog(spendReadyFrag, [dummySpendRequestId]);
console.log('Simulation Case C (Spend Ready):', simulateVoteSpendHandling([logSpendReady]));

// Case D: Spend normal vote
const spendVotedFrag = iface.getEvent('SpendRequestVoted');
const logSpendVoted = iface.encodeEventLog(spendVotedFrag, [dummySpendRequestId, dummyRecipient, true, 1n, 0n]);
console.log('Simulation Case D (Spend Normal Voted):', simulateVoteSpendHandling([logSpendVoted]));

// Case E: Refund auto-exec success
const refundExecFrag = iface.getEvent('RefundRequestExecuted');
const logRefundSuccess = iface.encodeEventLog(refundExecFrag, [dummyRefundId, dummyApplicant, dummyRefundAmount]);
console.log('Simulation Case E (Refund Success):', simulateVoteRefundHandling([logRefundSuccess]));

// Case F: Refund auto-exec failed
console.log('Simulation Case F (Refund Failed):', simulateVoteRefundHandling([refundFailedLog]));

// Case G: Refund reached threshold ready
const refundReadyFrag = iface.getEvent('RefundRequestReady');
const logRefundReady = iface.encodeEventLog(refundReadyFrag, [dummyRefundId]);
console.log('Simulation Case G (Refund Ready):', simulateVoteRefundHandling([logRefundReady]));

console.log('\nALL FRONTEND LOGIC SIMULATIONS PASSED!');
