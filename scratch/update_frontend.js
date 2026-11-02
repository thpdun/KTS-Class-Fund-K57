const fs = require('fs');

// First restore clean backup
fs.copyFileSync('web/index.html.bak_fix6', 'web/index.html');
console.log('Restored from backup.');

let content = fs.readFileSync('web/index.html', 'utf8');
const eol = '\r\n';
const auditedAbiStr = fs.readFileSync('scratch/audited_ProjectCore.abi', 'utf8').trim();

// 1. Sidebar link title
const oldSidebarPattern = /<a href="https:\/\/sepolia\.etherscan\.io\/address\/0xe3e1db1da1cae10e92337c36bb13004bf984ee91" target="_blank"\r?\n\s*style="color: #38bdf8; font-family: monospace; font-size: 0\.72rem;">0xe3e1\.\.\.ee91 ↗<\/a>/;
const newSidebarText = '<a href="https://sepolia.etherscan.io/address/0xe3e1db1da1cae10e92337c36bb13004bf984ee91" target="_blank"' + eol +
  '          style="color: #38bdf8; font-family: monospace; font-size: 0.72rem;" title="Hợp đồng Sepolia hiện tại (bản cũ, chưa có auto-execution)">0xe3e1...ee91 (cũ) ↗</a>';

if (oldSidebarPattern.test(content)) {
  content = content.replace(oldSidebarPattern, newSidebarText);
  console.log('Sidebar link updated.');
} else {
  console.error('Error: oldSidebarPattern did not match!');
  process.exit(1);
}

// 2. CONFIG comment
const oldConfigPattern = /defaultContractAddress: "0xe3e1db1da1cae10e92337c36bb13004bf984ee91",\r?\n\s*contractAddress: "0xe3e1db1da1cae10e92337c36bb13004bf984ee91"/;
const newConfigText = '// Ghi chú: Địa chỉ dưới đây là hợp đồng cũ đang chạy trên Sepolia (chưa có cơ chế auto-execution).' + eol +
  '      // Khi triển khai hợp đồng mới với tính năng auto-execution, cần cập nhật địa chỉ đã xác minh vào đây.' + eol +
  '      defaultContractAddress: "0xe3e1db1da1cae10e92337c36bb13004bf984ee91",' + eol +
  '      contractAddress: "0xe3e1db1da1cae10e92337c36bb13004bf984ee91"';

if (oldConfigPattern.test(content)) {
  content = content.replace(oldConfigPattern, newConfigText);
  console.log('CONFIG comment updated.');
} else {
  console.error('Error: oldConfigPattern did not match!');
  process.exit(1);
}

// 3. CONTRACT_ABI
const abiRegex = /const CONTRACT_ABI = \[[\s\S]*?\];/;
const newAbiDecl = 'const CONTRACT_ABI = ' + auditedAbiStr + ';';
if (abiRegex.test(content)) {
  content = content.replace(abiRegex, newAbiDecl);
  console.log('CONTRACT_ABI updated.');
} else {
  console.error('Error: abiRegex did not match!');
  process.exit(1);
}

// 4. voteRefund
const oldVoteRefundPattern = /async function voteRefund\(refundId, support\) \{[\s\S]*?async function executeRefund/;
const newVoteRefundCode = `async function voteRefund(refundId, support) {
      if (!signer) {
        alert("Bạn chưa kết nối ví MetaMask!");
        return;
      }
      if (!(await ensureCorrectNetwork())) return;
      if (!isBcsMember && window.currentVerifiedRole !== "bcs") {
        alert("Từ chối quyền: Chỉ thành viên Ban cán sự (BCS) đang hoạt động mới có quyền biểu quyết đơn hoàn tiền!");
        return;
      }
      if (!contract) {
        promptContractConfig("biểu quyết duyệt hoàn tiền");
        return;
      }

      try {
        logToTerminal(\`[Biểu quyết hoàn tiền] Đang bỏ phiếu \${support ? 'ĐỒNG Ý' : 'KHÔNG ĐỒNG Ý'} cho Yêu cầu #\${refundId}...\`);
        const tx = await contract.voteRefundRequest(refundId, support);
        const receipt = await tx.wait();

        // Bóc tách event từ receipt để phát hiện trạng thái auto-execution
        let autoExecSuccess = false;
        let autoExecFailed = false;
        let isReady = false;

        if (receipt && receipt.logs) {
          for (const log of receipt.logs) {
            try {
              const parsed = contract.interface.parseLog(log);
              if (parsed) {
                if (parsed.name === "RefundRequestExecuted") autoExecSuccess = true;
                if (parsed.name === "RefundExecutionFailed") autoExecFailed = true;
                if (parsed.name === "RefundRequestReady") isReady = true;
              }
            } catch (_) {}
          }
        }

        if (autoExecSuccess) {
          logToTerminal(\`[Thành công] Đã biểu quyết đạt ngưỡng và TỰ ĐỘNG HOÀN TIỀN thành công cho Yêu cầu #\${refundId}! Mã tx: \${tx.hash}\`);
          alert(\`Biểu quyết thành công! Yêu cầu hoàn tiền #\${refundId} đã đạt ngưỡng và được tự động hoàn tiền về ví sinh viên.\`);
        } else if (autoExecFailed) {
          logToTerminal(\`[Cảnh báo] Phiếu biểu quyết đã được ghi nhận và yêu cầu #\${refundId} đã thông qua. Tuy nhiên tự động chuyển ETH thất bại (ví nhận từ chối ETH hoặc lỗi gas). Yêu cầu chuyển sang trạng thái Sẵn sàng (Ready). Sinh viên hoặc Ban cán sự có thể bấm nút 'Hoàn tiền' / 'Nhận tiền hoàn' thủ công để thử lại.\`);
          alert(\`Đã ghi nhận phiếu biểu quyết! Yêu cầu hoàn tiền #\${refundId} đã thông qua nhưng chuyển ETH tự động thất bại (ví người nhận từ chối ETH). Đề xuất đã chuyển sang trạng thái 'Sẵn sàng'. Ban cán sự hoặc sinh viên có thể bấm nút 'Hoàn tiền' để thử lại.\`);
        } else if (isReady) {
          logToTerminal(\`[Thông báo] Biểu quyết thành công! Yêu cầu hoàn tiền #\${refundId} đã đạt ngưỡng và chuyển sang trạng thái Sẵn sàng (Ready).\`);
          alert(\`Biểu quyết thành công! Yêu cầu hoàn tiền #\${refundId} đã đạt ngưỡng và ở trạng thái Sẵn sàng hoàn tiền.\`);
        } else {
          logToTerminal(\`[Thành công] Đã ghi nhận phiếu biểu quyết cho Yêu cầu hoàn tiền #\${refundId}!\`);
        }

        await refreshContractData();
      } catch (err) {
        logToTerminal(\`[Lỗi bỏ phiếu hoàn tiền] \${err.shortMessage || err.message}\`);
        alert("Bỏ phiếu thất bại: " + (err.shortMessage || err.message));
      }
    }

    // Thực hiện hoàn tiền về ví sinh viên
    async function executeRefund`.replace(/\n/g, eol);

if (oldVoteRefundPattern.test(content)) {
  content = content.replace(oldVoteRefundPattern, newVoteRefundCode);
  console.log('voteRefund function updated.');
} else {
  console.error('Error: oldVoteRefundPattern did not match!');
  process.exit(1);
}

// 5. voteSpend
const oldVoteSpendPattern = /async function voteSpend\(requestId, support\) \{[\s\S]*?async function executeSpend/;
const newVoteSpendCode = `async function voteSpend(requestId, support) {
      if (!signer) {
        alert("Bạn chưa kết nối ví MetaMask!");
        return;
      }
      if (!(await ensureCorrectNetwork())) return;
      if (!isBcsMember && window.currentVerifiedRole !== "bcs") {
        alert("Từ chối quyền: Chỉ thành viên Ban cán sự (BCS) đang hoạt động mới có quyền bỏ phiếu đề xuất chi!");
        return;
      }
      if (!contract) {
        promptContractConfig("bỏ phiếu đề nghị chi");
        return;
      }

      try {
        logToTerminal(\`[Biểu quyết chi] Đang bỏ phiếu \${support ? 'ĐỒNG Ý' : 'KHÔNG ĐỒNG Ý'} cho Đề xuất #\${requestId}...\`);
        const tx = await contract.voteSpendRequest(requestId, support);
        const receipt = await tx.wait();

        // Bóc tách event từ receipt để phát hiện trạng thái auto-execution
        let autoExecSuccess = false;
        let autoExecFailed = false;
        let isReady = false;

        if (receipt && receipt.logs) {
          for (const log of receipt.logs) {
            try {
              const parsed = contract.interface.parseLog(log);
              if (parsed) {
                if (parsed.name === "SpendRequestExecuted") autoExecSuccess = true;
                if (parsed.name === "SpendExecutionFailed") autoExecFailed = true;
                if (parsed.name === "SpendRequestReady") isReady = true;
              }
            } catch (_) {}
          }
        }

        if (autoExecSuccess) {
          logToTerminal(\`[Thành công] Đã biểu quyết đạt ngưỡng và TỰ ĐỘNG GIẢI NGÂN thành công cho Đề xuất #\${requestId}! Mã tx: \${tx.hash}\`);
          alert(\`Biểu quyết thành công! Đề xuất #\${requestId} đã đạt ngưỡng và được tự động giải ngân thành công.\`);
        } else if (autoExecFailed) {
          logToTerminal(\`[Cảnh báo] Phiếu biểu quyết đã được ghi nhận và đề xuất #\${requestId} đã thông qua. Tuy nhiên tự động chuyển ETH thất bại (người nhận từ chối ETH hoặc lỗi gas). Đề xuất chuyển sang trạng thái Sẵn sàng (Ready). Ban cán sự có thể bấm nút 'Giải ngân' thủ công để thử lại.\`);
          alert(\`Đã ghi nhận phiếu biểu quyết! Đề xuất #\${requestId} đã đủ điều kiện nhưng tự động chuyển ETH thất bại (người nhận từ chối ETH). Đề xuất hiện ở trạng thái 'Sẵn sàng'. Ban cán sự có thể bấm nút 'Giải ngân' để thử lại.\`);
        } else if (isReady) {
          logToTerminal(\`[Thông báo] Biểu quyết thành công! Đề xuất #\${requestId} đã đạt ngưỡng và chuyển sang trạng thái Sẵn sàng (Ready).\`);
          alert(\`Biểu quyết thành công! Đề xuất #\${requestId} đã đạt ngưỡng và ở trạng thái Sẵn sàng giải ngân.\`);
        } else {
          logToTerminal(\`[Thành công] Đã ghi nhận phiếu biểu quyết cho Đề xuất #\${requestId}!\`);
        }

        await refreshContractData();
      } catch (err) {
        logToTerminal(\`[Lỗi bỏ phiếu chi] \${err.shortMessage || err.message}\`);
        alert("Bỏ phiếu thất bại: " + (err.shortMessage || err.message));
      }
    }

    // Thực hiện giải ngân đề xuất chi
    async function executeSpend`.replace(/\n/g, eol);

if (oldVoteSpendPattern.test(content)) {
  content = content.replace(oldVoteSpendPattern, newVoteSpendCode);
  console.log('voteSpend function updated.');
} else {
  console.error('Error: oldVoteSpendPattern did not match!');
  process.exit(1);
}

fs.writeFileSync('web/index.html', content, 'utf8');
console.log('Successfully written updated web/index.html!');
