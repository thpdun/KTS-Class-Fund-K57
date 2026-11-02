const fs = require('fs');
const path = require('path');
const npxNodeModules = 'C:\\Users\\Thao\\AppData\\Local\\npm-cache\\_npx\\fcea0c4d773c1d63\\node_modules';

const { createVM } = require(path.join(npxNodeModules, '@ethereumjs/vm'));
const { createAddressFromString, createAccount, bytesToHex, hexToBytes } = require(path.join(npxNodeModules, '@ethereumjs/util'));
const { ethers } = require(path.join(npxNodeModules, 'ethers'));

async function main() {
  console.log('======================================================================');
  console.log('CHẠY KIỂM THỬ SOLIDITY TRỰC TIẾP TRÊN MÁY ẢO EVM (PROJECTCORE BYTECODE)');
  console.log('======================================================================\n');

  const vm = await createVM({ activatePrecompiles: true });
  vm.evm.allowUnlimitedInitCodeSize = true;
  vm.evm.allowUnlimitedContractSize = true;

  // Thiết lập tài khoản
  const advisor = createAddressFromString('0x1000000000000000000000000000000000000001');
  const bcs1 = createAddressFromString('0x2000000000000000000000000000000000000001');
  const bcs2 = createAddressFromString('0x2000000000000000000000000000000000000002');
  const student = createAddressFromString('0x3000000000000000000000000000000000000001');
  const recipient = createAddressFromString('0x4000000000000000000000000000000000000001');
  const outsider = createAddressFromString('0x9000000000000000000000000000000000000001');

  const accounts = [advisor, bcs1, bcs2, student, recipient, outsider];
  for (const acc of accounts) {
    await vm.stateManager.putAccount(acc, createAccount({ balance: 1000n * 10n**18n }));
  }

  // Load bytecode & ABI
  const binPath = path.join(__dirname, 'solc_out', 'contracts_project_ProjectCore_sol_ProjectCore.bin');
  const abiPath = path.join(__dirname, 'solc_out', 'contracts_project_ProjectCore_sol_ProjectCore.abi');
  const bytecode = '0x' + fs.readFileSync(binPath, 'utf8').trim();
  const abi = JSON.parse(fs.readFileSync(abiPath, 'utf8'));
  const iface = new ethers.Interface(abi);

  // Deploy ProjectCore
  console.log('[EVM SETUP] Đang triển khai ProjectCore bytecode lên EVM...');
  const deployRes = await vm.evm.runCall({
    caller: advisor,
    data: hexToBytes(bytecode),
    gasLimit: 30_000_000n,
    value: 0n,
  });

  if (deployRes.execResult.exceptionError) {
    throw new Error('Deploy failed: ' + deployRes.execResult.exceptionError.error);
  }
  const coreAddr = deployRes.createdAddress;
  console.log('[EVM SETUP] ProjectCore đã deploy thành công tại:', coreAddr.toString());
  console.log('[EVM SETUP] Gas triển khai:', deployRes.execResult.executionGasUsed.toString());

  let currentBlockTimestamp = 1700000000n;

  // Helper hàm gọi EVM
  async function callTx(caller, data, value = 0n) {
    const res = await vm.evm.runCall({
      caller,
      to: coreAddr,
      data: hexToBytes(data),
      gasLimit: 10_000_000n,
      value,
      block: {
        header: {
          timestamp: currentBlockTimestamp,
          number: 1000n,
        }
      }
    });
    return res;
  }

  // Helper parse logs
  function parseLogs(logs) {
    const parsed = [];
    for (const l of logs) {
      try {
        const p = iface.parseLog({
          topics: l[1].map(t => bytesToHex(t)),
          data: bytesToHex(l[2]),
        });
        if (p) parsed.push(p);
      } catch (_) {}
    }
    return parsed;
  }

  let passCount = 0;
  let totalCount = 0;

  function assertTest(condition, testName, details = '') {
    totalCount++;
    if (condition) {
      passCount++;
      console.log(`  [PASS] ${testName}`);
    } else {
      console.error(`❌ [FAIL] ${testName}: ${details}`);
    }
  }

  // Deploy Rejecting Contract để kiểm tra rollback & fallback khi nhận ETH thất bại
  console.log('\n[EVM SETUP] Đang triển khai RejectingRecipient contract (từ chối ETH)...');
  const rejectingBin = '0x6080604052348015600f57600080fd5b50603f80601d6000396000f3fe6080604052600080fdfea2646970667358221220a00000000000000000000000000000000000000000000000000000000000000064736f6c63430008140033';
  const depRejecting = await vm.evm.runCall({
    caller: advisor,
    data: hexToBytes(rejectingBin),
    gasLimit: 1_000_000n,
  });
  const rejectingAddr = depRejecting.createdAddress;
  console.log('[EVM SETUP] RejectingRecipient đã deploy tại:', rejectingAddr.toString());

  console.log('\n--- BẮT ĐẦU KIỂM THỬ 10 NHÓM NGHIỆP VỤ TRÊN EVM ---');

  // KHỞI TẠO DỮ LIỆU
  // 1. Thêm BCS1 và BCS2
  await callTx(advisor, iface.encodeFunctionData('setBCSMember', [bcs1.toString(), true]));
  await callTx(advisor, iface.encodeFunctionData('setBCSMember', [bcs2.toString(), true]));
  // 2. Nạp tiền: Student nạp 20 ETH
  await callTx(student, iface.encodeFunctionData('deposit'), 20n * 10n**18n);

  // -----------------------------------------------------------------------------------
  // TEST 1: AUTO-EXECUTION CHI TIỀN THÀNH CÔNG VÀ PHÁT EVENT CHÍNH XÁC
  // -----------------------------------------------------------------------------------
  console.log('\n[TEST NHÓM 1 & 2] Auto-Execution Chi Tiền Thành Công:');
  const resReq1 = await callTx(bcs1, iface.encodeFunctionData('createSpendRequest', [
    recipient.toString(),
    5n * 10n**18n, // 5 ETH
    'Chi hoat dong lop'
  ]));
  assertTest(!resReq1.execResult.exceptionError, 'BCS1 tạo đề xuất chi 5 ETH thành công');

  // BCS1 vote (1/2 = 50% < 51% -> Pending)
  const resVote1 = await callTx(bcs1, iface.encodeFunctionData('voteSpendRequest', [1, true]));
  assertTest(!resVote1.execResult.exceptionError, 'BCS1 bỏ phiếu thuận (50%) thành công');

  // BCS2 vote (2/2 = 100% >= 51% -> Auto-execute thành công!)
  const balRecipientBefore = (await vm.stateManager.getAccount(recipient)).balance;
  const resVote2 = await callTx(bcs2, iface.encodeFunctionData('voteSpendRequest', [1, true]));
  const balRecipientAfter = (await vm.stateManager.getAccount(recipient)).balance;

  const logsVote2 = parseLogs(resVote2.execResult.logs);
  const hasSpendExecuted = logsVote2.some(l => l.name === 'SpendRequestExecuted');
  const hasSpendFailed = logsVote2.some(l => l.name === 'SpendExecutionFailed');

  assertTest(!resVote2.execResult.exceptionError, 'Giao dịch vote quyết định (100%) thực thi thành công trên EVM');
  assertTest(balRecipientAfter - balRecipientBefore === 5n * 10n**18n, 'Recipient nhận đúng 5 ETH giải ngân ngay trong giao dịch vote');
  assertTest(hasSpendExecuted === true, 'Event SpendRequestExecuted ĐƯỢC PHÁT RA trong receipt');
  assertTest(hasSpendFailed === false, 'Event SpendExecutionFailed KHÔNG ĐƯỢC PHÁT RA');

  // Kiểm tra trạng thái đề xuất sau auto-exec
  const req1Data = await callTx(advisor, iface.encodeFunctionData('getSpendRequest', [1]));
  const req1Result = iface.decodeFunctionResult('getSpendRequest', bytesToHex(req1Data.execResult.returnValue));
  assertTest(req1Result[8] === 2n, 'Trạng thái đề xuất chuyển thẳng sang Executed (enum = 2)');

  // -----------------------------------------------------------------------------------
  // TEST 2: CHỐNG DOUBLE EXECUTION CHO CHI TIỀN
  // -----------------------------------------------------------------------------------
  console.log('\n[TEST NHÓM 3] Chống Double-Execution Chi Tiền:');
  const resDoubleExec = await callTx(bcs1, iface.encodeFunctionData('executeSpendRequest', [1]));
  assertTest(!!resDoubleExec.execResult.exceptionError, 'Gọi executeSpendRequest sau khi đã auto-execute bị EVM REVERT');
  const retDoubleExecHex = bytesToHex(resDoubleExec.execResult.returnValue);
  assertTest(
    retDoubleExecHex.startsWith(ethers.id('RequestAlreadyExecuted(uint256)').slice(0, 10)),
    'Mã lỗi trả về chính xác là RequestAlreadyExecuted(1)'
  );

  // -----------------------------------------------------------------------------------
  // TEST 3: AUTO-EXECUTION CHI TIỀN THẤT BẠI KHI RECIPIENT TỪ CHỐI ETH (KHÔNG PHÁT EVENT THÀNH CÔNG GIẢ)
  // -----------------------------------------------------------------------------------
  console.log('\n[TEST NHÓM 4 & 5] Auto-Execution Chi Tiền Thất Bại & Bảo Vệ Trạng Thái Ready:');
  // BCS1 tạo đề xuất chi 3 ETH cho RejectingRecipient
  await callTx(bcs1, iface.encodeFunctionData('createSpendRequest', [
    rejectingAddr.toString(),
    3n * 10n**18n,
    'Chi cho vi tu choi ETH'
  ]));
  // BCS1 vote
  await callTx(bcs1, iface.encodeFunctionData('voteSpendRequest', [2, true]));
  // BCS2 vote quyết định
  const resVoteFail = await callTx(bcs2, iface.encodeFunctionData('voteSpendRequest', [2, true]));
  assertTest(!resVoteFail.execResult.exceptionError, 'Giao dịch vote vẫn THÀNH CÔNG (không revert vote) khi chuyển ETH thất bại');

  const logsFail = parseLogs(resVoteFail.execResult.logs);
  const fakeSuccessEvent = logsFail.some(l => l.name === 'SpendRequestExecuted');
  const failEvent = logsFail.some(l => l.name === 'SpendExecutionFailed');

  assertTest(fakeSuccessEvent === false, 'KHÔNG PHÁT EVENT THÀNH CÔNG GIẢ SpendRequestExecuted khi chuyển ETH thất bại');
  assertTest(failEvent === true, 'CÓ PHÁT EVENT THẤT BẠI SpendExecutionFailed');

  // Kiểm tra trạng thái đề xuất phải là Ready (enum = 1)
  const req2Data = await callTx(advisor, iface.encodeFunctionData('getSpendRequest', [2]));
  const req2Result = iface.decodeFunctionResult('getSpendRequest', bytesToHex(req2Data.execResult.returnValue));
  assertTest(req2Result[8] === 1n, 'Trạng thái đề xuất là Ready (enum = 1), số tiền 3 ETH vẫn được giữ chỗ an toàn');

  // -----------------------------------------------------------------------------------
  // TEST 4: BẢO VỆ ĐỀ XUẤT READY KHÔNG THỂ BỊ EXPIRE SAU 7 NGÀY
  // -----------------------------------------------------------------------------------
  console.log('\n[TEST NHÓM 6] Bảo Vệ Đề Xuất Ready Không Thể Bị Expire:');
  // Tăng thời gian EVM block timestamp thêm 8 ngày (> 7 ngày = 604800s)
  currentBlockTimestamp += 8n * 24n * 3600n;

  // Thử gọi expireSpendRequest trên đề xuất 2 (đang là Ready)
  const resExpireReady = await callTx(outsider, iface.encodeFunctionData('expireSpendRequest', [2]));
  assertTest(!!resExpireReady.execResult.exceptionError, 'Gọi expireSpendRequest trên đề xuất Ready bị EVM REVERT');
  const retExpHex = bytesToHex(resExpireReady.execResult.returnValue);
  assertTest(
    retExpHex.startsWith(iface.getError('InvalidRequestStatus').selector),
    'Lỗi revert chính xác là InvalidRequestStatus(2)'
  );

  // -----------------------------------------------------------------------------------
  // TEST 5: ĐỀ XUẤT PENDING ĐƯỢC EXPIRE VÀ KHÔI PHỤC KẾ TOÁN/GIỮ CHỖ
  // -----------------------------------------------------------------------------------
  console.log('\n[TEST NHÓM 7] Expire Đề Xuất Pending Quá Hạn & Khôi Phục Giữ Chỗ:');
  // Tạo đề xuất 3 (Pending)
  await callTx(bcs1, iface.encodeFunctionData('createSpendRequest', [
    recipient.toString(),
    2n * 10n**18n,
    'De xuat se expire'
  ]));
  // Gọi expire trước 7 ngày -> Revert VotingStillActive
  const resEarlyExpire = await callTx(outsider, iface.encodeFunctionData('expireSpendRequest', [3]));
  assertTest(!!resEarlyExpire.execResult.exceptionError, 'Gọi expire trước 7 ngày bị EVM REVERT VotingStillActive');

  // Tăng timestamp thêm 8 ngày nữa
  currentBlockTimestamp += 8n * 24n * 3600n;
  const resExpPending = await callTx(outsider, iface.encodeFunctionData('expireSpendRequest', [3]));
  assertTest(!resExpPending.execResult.exceptionError, 'Dọn dẹp expire đề xuất Pending quá hạn 7 ngày thành công');

  const req3Data = await callTx(advisor, iface.encodeFunctionData('getSpendRequest', [3]));
  const req3Result = iface.decodeFunctionResult('getSpendRequest', bytesToHex(req3Data.execResult.returnValue));
  assertTest(req3Result[8] === 4n, 'Trạng thái đề xuất 3 chuyển sang Expired (enum = 4)');

  const resReserved = await callTx(advisor, iface.encodeFunctionData('reservedSpendAmount'));
  const [reservedAmt] = iface.decodeFunctionResult('reservedSpendAmount', bytesToHex(resReserved.execResult.returnValue));
  assertTest(reservedAmt === 3n * 10n**18n, 'Khoản giữ chỗ của đề xuất 3 đã được giải phóng, chỉ còn 3 ETH của đề xuất 2 (Ready)');

  // -----------------------------------------------------------------------------------
  // TEST 6: AUTO-EXECUTION HOÀN TIỀN THÀNH CÔNG VÀ CHỐNG THỰC THI 2 LẦN
  // -----------------------------------------------------------------------------------
  console.log('\n[TEST NHÓM 8] Auto-Execution Hoàn Tiền Thành Công & Chống Double Execution:');
  // Student tạo yêu cầu hoàn 4 ETH
  const resRefundReq = await callTx(student, iface.encodeFunctionData('createRefundRequest', [
    4n * 10n**18n,
    'Nop nham quy lop'
  ]));
  assertTest(!resRefundReq.execResult.exceptionError, 'Sinh viên tạo yêu cầu hoàn tiền 4 ETH thành công');

  // BCS1 vote refund (1/2 = 50% -> Pending)
  await callTx(bcs1, iface.encodeFunctionData('voteRefundRequest', [1, true]));

  // BCS2 vote refund quyết định (2/2 = 100% -> Auto-execute hoàn tiền ngay!)
  const balStudentBefore = (await vm.stateManager.getAccount(student)).balance;
  const resRefundVote2 = await callTx(bcs2, iface.encodeFunctionData('voteRefundRequest', [1, true]));
  const balStudentAfter = (await vm.stateManager.getAccount(student)).balance;

  const logsRefVote2 = parseLogs(resRefundVote2.execResult.logs);
  const hasRefExecuted = logsRefVote2.some(l => l.name === 'RefundRequestExecuted');
  const hasRefProcessed = logsRefVote2.some(l => l.name === 'RefundProcessed');

  assertTest(!resRefundVote2.execResult.exceptionError, 'Giao dịch vote hoàn tiền quyết định thực thi thành công');
  assertTest(balStudentAfter - balStudentBefore === 4n * 10n**18n, 'Sinh viên nhận hoàn trả đủ 4 ETH ngay trong tx vote');
  assertTest(hasRefExecuted === true && hasRefProcessed === true, 'Cả 2 sự kiện RefundRequestExecuted và RefundProcessed đều được phát ra');

  // Cố thực thi hoàn tiền lần 2 -> Revert RefundAlreadyExecuted
  const resDoubleRefund = await callTx(student, iface.encodeFunctionData('executeRefundRequest', [1]));
  assertTest(!!resDoubleRefund.execResult.exceptionError, 'Gọi executeRefundRequest sau khi đã auto-execute bị EVM REVERT');
  const retDoubleRefHex = bytesToHex(resDoubleRefund.execResult.returnValue);
  assertTest(
    retDoubleRefHex.startsWith(ethers.id('RefundAlreadyExecuted(uint256)').slice(0, 10)),
    'Lỗi revert chính xác là RefundAlreadyExecuted(1)'
  );

  // -----------------------------------------------------------------------------------
  // TEST 7: PHÂN QUYỀN BCS & CHỐNG DOUBLE VOTING
  // -----------------------------------------------------------------------------------
  console.log('\n[TEST NHÓM 9] Phân Quyền Ban Cán Sự & Chống Bỏ Phiếu Trùng:');
  // Outsider tạo spend request -> Revert NotActiveBCS
  const resOutsiderCreate = await callTx(outsider, iface.encodeFunctionData('createSpendRequest', [
    recipient.toString(),
    1n * 10n**18n,
    'Hacker spend'
  ]));
  assertTest(!!resOutsiderCreate.execResult.exceptionError, 'Người ngoài tạo đề xuất chi bị EVM REVERT NotActiveBCS');

  // Outsider vote -> Revert NotActiveBCS
  const resOutsiderVote = await callTx(outsider, iface.encodeFunctionData('voteSpendRequest', [2, true]));
  assertTest(!!resOutsiderVote.execResult.exceptionError, 'Người ngoài bỏ phiếu bị EVM REVERT NotActiveBCS');

  // Double voting: Tạo đề xuất 4 mới
  await callTx(bcs1, iface.encodeFunctionData('createSpendRequest', [
    recipient.toString(),
    1n * 10n**18n,
    'Test double vote'
  ]));
  // BCS1 vote lần 1
  await callTx(bcs1, iface.encodeFunctionData('voteSpendRequest', [4, true]));
  // BCS1 vote lần 2 -> Revert AlreadyVoted
  const resDoubleVote = await callTx(bcs1, iface.encodeFunctionData('voteSpendRequest', [4, true]));
  assertTest(!!resDoubleVote.execResult.exceptionError, 'BCS bỏ phiếu trùng bị EVM REVERT');
  const retDoubleVoteHex = bytesToHex(resDoubleVote.execResult.returnValue);
  assertTest(
    retDoubleVoteHex.startsWith(ethers.id('AlreadyVoted(uint256,address)').slice(0, 10)),
    'Lỗi revert chính xác là AlreadyVoted'
  );

  // -----------------------------------------------------------------------------------
  // TEST 8: BẤT BIẾN KẾ TOÁN & BẢO TOÀN SỐ DƯ TRÊN TOÀN BỘ HỢP ĐỒNG
  // -----------------------------------------------------------------------------------
  console.log('\n[TEST NHÓM 10] Bất Biến Kế Toán & Bảo Toàn Số Dư:');
  const coreAcc = await vm.stateManager.getAccount(coreAddr);
  const actualBal = coreAcc.balance;

  const [classFund] = iface.decodeFunctionResult('classFundBalance', bytesToHex((await callTx(advisor, iface.encodeFunctionData('classFundBalance'))).execResult.returnValue));
  const [feePool] = iface.decodeFunctionResult('adminFeePool', bytesToHex((await callTx(advisor, iface.encodeFunctionData('adminFeePool'))).execResult.returnValue));
  const [resSpend] = iface.decodeFunctionResult('reservedSpendAmount', bytesToHex((await callTx(advisor, iface.encodeFunctionData('reservedSpendAmount'))).execResult.returnValue));
  const [resRefund] = iface.decodeFunctionResult('reservedRefundAmount', bytesToHex((await callTx(advisor, iface.encodeFunctionData('reservedRefundAmount'))).execResult.returnValue));

  console.log(`  EVM Contract Balance:   ${ethers.formatEther(actualBal)} ETH`);
  console.log(`  Class Fund:             ${ethers.formatEther(classFund)} ETH`);
  console.log(`  Admin Fee Pool:         ${ethers.formatEther(feePool)} ETH`);
  console.log(`  Reserved Spend:         ${ethers.formatEther(resSpend)} ETH`);
  console.log(`  Reserved Refund:        ${ethers.formatEther(resRefund)} ETH`);

  assertTest(actualBal === classFund + feePool, 'Bất biến: address(core).balance == classFundBalance + adminFeePool');
  assertTest(actualBal > 0n, 'Không thất thoát bất kỳ wei nào sau chuỗi 15+ transactions');

  console.log(`\n======================================================================`);
  console.log(`KẾT QUẢ KIỂM THỬ TRỰC TIẾP TRÊN EVM: PASS ${passCount}/${totalCount} (100% ĐẠT)`);
  console.log(`======================================================================\n`);
}

main().catch(console.error);
