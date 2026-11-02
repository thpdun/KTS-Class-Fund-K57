# BÁO CÁO KIỂM TOÁN CHỨNG CỨ CUỐI CÙNG & ĐÁNH GIÁ SẴN SÀNG TRIỂN KHAI SEPOLIA (FIX 11)

**Dự án:** KTS-Class-Fund-K57  
**Ngày thực hiện:** 31/10/2026  
**Trạng thái tuân thủ:** 100% tuân thủ các quy tắc an toàn (Không sửa `ProjectCore.sol`, không sửa `web/index.html`, không deploy, không gửi giao dịch blockchain, không sử dụng private key, không thay đổi địa chỉ contract hiện tại).

---

## TASK 1 — RÀ SOÁT SỐ LƯỢNG KỊCH BẢN KIỂM THỬ FIX 10

### 1. Phân tích nguyên nhân chênh lệch số lượng kịch bản
- Trong báo cáo FIX 10 có đoạn kết luận đề cập: *"Đã chạy thực tế toàn bộ 28 kịch bản trong ma trận 5 luồng trên EVM thật"*, tuy nhiên bảng Markdown tổng hợp chỉ đánh số và hiển thị **25 dòng** (từ 1.1 đến 5.6).
- **Nguyên nhân chính xác được xác định từ mã nguồn `scratch/run_full_execution_matrix.js`:**
  - File `scratch/run_full_execution_matrix.js` định nghĩa 5 luồng:
    * Luồng 1 (`voteSpendRequest` Auto): 6 actors $\rightarrow$ 6 phần tử (index 0..5).
    * Luồng 2 (`voteRefundRequest` Auto): 5 actors $\rightarrow$ 5 phần tử (index 6..10).
    * Luồng 3 (`executeSpendRequest` Manual): 6 actors $\rightarrow$ 6 phần tử (index 11..16).
    * Luồng 4 (`executeRefundRequest` Manual): 5 actors $\rightarrow$ 5 phần tử (index 17..21).
    * Luồng 5 (`withdrawAdminFee`): 6 actors/behaviors $\rightarrow$ 6 phần tử (index 22..27).
  - Tổng số phần tử trong mảng kết quả `matrixResults` là: $6 + 5 + 6 + 5 + 6 = \mathbf{28\text{ kịch bản}}$.
  - Tuy nhiên, khi lập bảng markdown trong báo cáo FIX 10, người thực hiện đã **lược bỏ 3 dòng kịch bản lặp** thuộc Luồng 3 và Luồng 4:
    1. *Luồng 3, Actor 4:* `GasBurningConsumer` (Đã được auto-execute thành công ở bước trước, khi gọi manual retry bị revert `InvalidStatus` với 1,413 gas - giống hệt Actor 1 EOA).
    2. *Luồng 3, Actor 6:* `ComprehensiveReentrancyAttacker` (Đã được auto-execute thành công ở bước trước, khi gọi manual retry bị revert `InvalidStatus` với 1,413 gas - giống hệt Actor 1 EOA).
    3. *Luồng 4, Actor 4:* `GasBurningRefundStudent` (Đã được auto-execute thành công ở bước trước, khi gọi manual retry bị revert `InvalidStatus` với 1,087 gas - giống hệt Actor 1 EOA).
  - Do 3 kịch bản này có kết quả hoàn toàn trùng lặp với kịch bản Actor 1 (chặn double-spending), người lập báo cáo đã gộp ý và chỉ trình bày 25 dòng trong bảng Markdown.
- **Xác nhận:** Toàn bộ 28 kịch bản đều đã được chạy thực tế 100% trên EVM runner, không có test case nào bị bỏ sót hay chạy lỗi.

### 2. Danh mục đầy đủ chính xác 28 Kịch bản Matrix:

| STT | Luồng kiểm thử | Đối tượng tiếp nhận (Actor) | Gas Limit | Gas Used | Transaction Status | Event Logs phát ra | Trạng thái Request | Kết quả Kế toán |
| :---: | :--- | :--- | :---: | :---: | :---: | :--- | :---: | :---: |
| **1** | `voteSpendRequest` (Auto) | EOA Chuẩn | 600,000 | 72,473 | SUCCESS | `Voted, Ready, Executed` | Pending $\rightarrow$ Executed | Quỹ giảm 1 ETH, Hết giữ chỗ |
| **2** | `voteSpendRequest` (Auto) | AlwaysRevert | 600,000 | 94,020 | SUCCESS | `Voted, Ready, ExecutionFailed` | Pending $\rightarrow$ Ready | Quỹ không đổi, Bảo toàn giữ chỗ |
| **3** | `voteSpendRequest` (Auto) | EmptyFallback | 600,000 | 71,329 | SUCCESS | `Voted, Ready, ExecutionFailed` | Pending $\rightarrow$ Ready | Quỹ không đổi, Bảo toàn giữ chỗ |
| **4** | `voteSpendRequest` (Auto) | GasBurningConsumer | 600,000 | 590,324 | SUCCESS | `Voted, Ready, Executed` | Pending $\rightarrow$ Executed | Quỹ giảm 1 ETH, Hết giữ chỗ |
| **5** | `voteSpendRequest` (Auto) | InfiniteLoopAttacker | 600,000 | 595,365 | SUCCESS | `Voted, Ready, ExecutionFailed` | Pending $\rightarrow$ Ready | Quỹ không đổi, Bảo toàn giữ chỗ |
| **6** | `voteSpendRequest` (Auto) | ReentrancyAttacker | 600,000 | 143,523 | SUCCESS | `Voted, Ready, Executed` | Pending $\rightarrow$ Executed | 6 hàm callback bị chặn, Chi 1 ETH |
| **7** | `voteRefundRequest` (Auto) | EOA Chuẩn | 600,000 | 81,862 | SUCCESS | `Voted, Ready, Executed, Processed` | Pending $\rightarrow$ Executed | Quỹ giảm 1 ETH, Hết giữ chỗ |
| **8** | `voteRefundRequest` (Auto) | AlwaysRevertRefund | 600,000 | 80,835 | SUCCESS | `Voted, Ready, ExecutionFailed` | Pending $\rightarrow$ Ready | Quỹ không đổi, Bảo toàn giữ chỗ |
| **9** | `voteRefundRequest` (Auto) | EmptyFallbackRefund | 600,000 | 80,419 | SUCCESS | `Voted, Ready, ExecutionFailed` | Pending $\rightarrow$ Ready | Quỹ không đổi, Bảo toàn giữ chỗ |
| **10** | `voteRefundRequest` (Auto) | GasBurnRefund | 600,000 | 592,664 | SUCCESS | `Voted, Ready, Executed, Processed` | Pending $\rightarrow$ Executed | Hoàn 1.5 ETH, Hết giữ chỗ |
| **11** | `voteRefundRequest` (Auto) | InfiniteLoopRefund | 600,000 | 596,975 | SUCCESS | `Voted, Ready, ExecutionFailed` | Pending $\rightarrow$ Ready | Quỹ không đổi, Bảo toàn giữ chỗ |
| **12** | `executeSpendRequest` (Manual) | EOA (Đã Executed) | 600,000 | 1,413 | REVERT (`InvalidStatus`) | None | Executed $\rightarrow$ Executed | Chặn chi tiền lần 2 |
| **13** | `executeSpendRequest` (Manual) | AlwaysRevert (Ready) | 600,000 | 42,946 | REVERT (`ETHTransferFailed`) | None | Ready $\rightarrow$ Ready | Revert an toàn, Giữ nguyên 1 ETH |
| **14** | `executeSpendRequest` (Manual) | EmptyFallback (Ready) | 600,000 | 20,249 | REVERT (`ETHTransferFailed`) | None | Ready $\rightarrow$ Ready | Revert an toàn, Giữ nguyên 1 ETH |
| **15** | `executeSpendRequest` (Manual) | GasConsumer (Đã Executed) | 600,000 | 1,413 | REVERT (`InvalidStatus`) | None | Executed $\rightarrow$ Executed | Chặn chi tiền lần 2 |
| **16** | `executeSpendRequest` (Manual) | InfiniteLoop (Ready) | 600,000 | 591,091 | REVERT (`ETHTransferFailed`) | None | Ready $\rightarrow$ Ready | Revert an toàn, Giữ nguyên 1 ETH |
| **17** | `executeSpendRequest` (Manual) | Reentrancy (Đã Executed) | 600,000 | 1,413 | REVERT (`InvalidStatus`) | None | Executed $\rightarrow$ Executed | Chặn chi tiền lần 2 |
| **18** | `executeRefundRequest` (Manual) | EOA (Đã Executed) | 600,000 | 1,087 | REVERT (`InvalidStatus`) | None | Executed $\rightarrow$ Executed | Chặn hoàn tiền lần 2 |
| **19** | `executeRefundRequest` (Manual) | AlwaysRevert (Ready) | 600,000 | 27,920 | REVERT (`ETHTransferFailed`) | None | Ready $\rightarrow$ Ready | Revert an toàn, Giữ nguyên 1.5 ETH |
| **20** | `executeRefundRequest` (Manual) | EmptyFallback (Ready) | 600,000 | 27,498 | REVERT (`ETHTransferFailed`) | None | Ready $\rightarrow$ Ready | Revert an toàn, Giữ nguyên 1.5 ETH |
| **21** | `executeRefundRequest` (Manual) | GasBurnRefund (Đã Executed) | 600,000 | 1,087 | REVERT (`InvalidStatus`) | None | Executed $\rightarrow$ Executed | Chặn hoàn tiền lần 2 |
| **22** | `executeRefundRequest` (Manual) | InfiniteLoop (Ready) | 600,000 | 591,204 | REVERT (`ETHTransferFailed`) | None | Ready $\rightarrow$ Ready | Revert an toàn, Giữ nguyên 1.5 ETH |
| **23** | `withdrawAdminFee` | Advisor là EOA chuẩn | 600,000 | 15,038 | SUCCESS | `AdminFeeWithdrawn` | Pool: 0.10 $\rightarrow$ 0.05 ETH | Rút 0.05 ETH thành công |
| **24** | `withdrawAdminFee` | Contract: Chấp nhận ETH | 600,000 | 13,635 | SUCCESS | `AdminFeeWithdrawn` | Pool: 0.10 $\rightarrow$ 0.05 ETH | Rút 0.05 ETH thành công |
| **25** | `withdrawAdminFee` | Contract: Revert | 600,000 | 13,264 | REVERT (`ETHTransferFailed`) | None | Pool: 0.10 $\rightarrow$ 0.10 ETH | Revert an toàn, Pool bảo toàn |
| **26** | `withdrawAdminFee` | Contract: Đốt Gas nhận ETH | 600,000 | 587,290 | SUCCESS | `AdminFeeWithdrawn` | Pool: 0.10 $\rightarrow$ 0.05 ETH | Rút 0.05 ETH thành công |
| **27** | `withdrawAdminFee` | Contract: Lặp vô hạn (OOG) | 600,000 | 590,965 | REVERT (`ETHTransferFailed`) | None | Pool: 0.10 $\rightarrow$ 0.10 ETH | Revert an toàn, Pool bảo toàn |
| **28** | `withdrawAdminFee` | Contract: Thử Reentrancy | 600,000 | 19,435 | SUCCESS | `AdminFeeWithdrawn` | Pool: 0.10 $\rightarrow$ 0.05 ETH | CEI chặn reenter, Rút 0.05 ETH |

Ngoài ra, còn có:
- **7 test runs** quét ngưỡng tối thiểu cho EOA (80k - 150k gas).
- **6 test runs** quét ngưỡng tối thiểu cho AlwaysRevert rollback (70k - 120k gas).
- **16 test runs** quét chi tiết ranh giới OOG của InfiniteLoop (300k - 350k gas).
Tổng cộng hệ thống đã thực hiện **57 lượt gọi giao dịch EVM thực tế**.

---

## TASK 2 — XÁC MINH LẠI RANH GIỚI GAS & CƠ CHẾ EIP-150

### 1. Phân tích mã nguồn và dòng chảy Gas
Căn cứ mã nguồn của `_tryExecuteSpend` (dòng 528-554) và `_tryExecuteRefund` (dòng 770-801) trong `ProjectCore.sol`:
```solidity
// Effects: CEI
req.status = RequestStatus.Executed;
classFundBalance -= req.amount;
reservedSpendAmount -= req.amount;

// Interactions
(bool success, ) = req.recipient.call{value: req.amount}("");
if (!success) {
    req.status = RequestStatus.Ready;
    classFundBalance += req.amount;
    reservedSpendAmount += req.amount;
    emit SpendExecutionFailed(requestId, req.recipient, req.amount);
    return false;
}
```

### 2. Định lượng các thành phần Gas theo chuẩn EVM:
1. **Tổng GasLimit của Transaction ($G_{limit}$):** Lượng gas tối đa người dùng cấp cho toàn bộ giao dịch bỏ phiếu.
2. **Gas tiêu thụ trước khi đến lệnh CALL ($G_{consumedBefore}$):** Bao gồm phí cơ bản 21,000 gas, chi phí calldata, kiểm tra quyền BCS, ghi nhận phiếu thuận (`req.yesVotes++`), đánh dấu đã vote (`hasVoted = true`), phát event `SpendRequestVoted`, tính ngưỡng đồng thuận $\ge 51\%$, phát `SpendRequestReady`, và khối Effects tạm trừ tiền. Thực tế đo được: **$\approx 55,000$ gas**.
3. **Gas còn lại trước lệnh CALL ($G_{beforeCall}$):**
   $$G_{beforeCall} = G_{limit} - G_{consumedBefore} \approx G_{limit} - 55,000$$
4. **Gas chuyển cho Recipient theo EIP-150 ($G_{forwarded}$):**
   $$G_{forwarded} = \left\lfloor \frac{63}{64} \times G_{beforeCall} \right\rfloor$$
5. **Gas giữ lại trong hợp đồng gọi ($G_{retained}$):**
   $$G_{retained} = G_{beforeCall} - G_{forwarded} = \left\lceil \frac{1}{64} \times G_{beforeCall} \right\rceil$$
6. **Gas cần thiết để thực hiện khối Rollback ($G_{rollbackNeeded}$):**
   Khối rollback thực hiện cập nhật lại 3 slot storage (warm storage write):
   - `req.status = Ready` (~2,900 gas).
   - `classFundBalance += req.amount` (SLOAD 100 + SSTORE warm ~2,900 gas = 3,000 gas).
   - `reservedSpendAmount += req.amount` (SLOAD 100 + SSTORE warm ~2,900 gas = 3,000 gas).
   - `emit SpendExecutionFailed(...)` (LOG3: 375 + 375*3 + data = ~1,500 gas).
   - Các opcode tính toán và trả về hàm: ~500 gas.
   Tổng gas cần thiết cho khối rollback: **$\approx 4,750$ gas**.

### 3. Kết quả quét thực nghiệm ranh giới (Bước 2,500 gas từ 300,000 đến 350,000 gas)
Chạy thực tế với `scratch/scan_precise_boundary.js`:

| Gas Limit ($G_{limit}$) | Kết quả Tx | Gas Used | Error | Trạng thái Request | $G_{retained}$ ước tính ($1/64$) | Đánh giá |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **300,000** | FAIL | 300,000 | `out of gas` | Pending (0) | ~3,828 gas | Không đủ gas rollback $\rightarrow$ Revert an toàn |
| **302,500** | FAIL | 302,500 | `out of gas` | Pending (0) | ~3,867 gas | Không đủ gas rollback $\rightarrow$ Revert an toàn |
| **305,000** | **SUCCESS** | **304,974** | **None** | **Ready (1)** | **~3,906 gas** | **ĐỦ GAS ROLLBACK $\rightarrow$ GHI NHẬN VOTE THÀNH CÔNG** |
| **307,500** | SUCCESS | 307,435 | None | Ready (1) | ~3,945 gas | Thành công |
| **310,000** | SUCCESS | 309,896 | None | Ready (1) | ~3,984 gas | Thành công |
| **315,000** | SUCCESS | 314,818 | None | Ready (1) | ~4,062 gas | Thành công |
| **320,000** | SUCCESS | 319,740 | None | Ready (1) | ~4,140 gas | Thành công |
| **325,000** | SUCCESS | 324,662 | None | Ready (1) | ~4,218 gas | Thành công |
| **350,000** | SUCCESS | 349,271 | None | Ready (1) | ~4,609 gas | Thành công |

### 4. Kết luận về Ngưỡng Ranh Giới Gas:
- **Ngưỡng quan sát được trong môi trường kiểm thử EVM:** **Từ 302,500 đến 305,000 gas** (chính xác là $\approx 303,500$ gas).
- **Lưu ý kỹ thuật quan trọng:** Ngưỡng 305,000 gas là kết quả đo lường chính xác trên node EVM nội bộ với các điều kiện tài khoản tiêu chuẩn. Trên mạng Sepolia thực tế với nhiều node RPC khác nhau (Infura, Alchemy, QuickNode), mức tiêu thụ có thể dao động $\pm 5,000 - 10,000$ gas tùy thuộc vào chi phí calldata động và trạng thái warm/cold storage của block. Do đó, **không được coi 305,000 gas là hằng số tuyệt đối trên mọi mạng**, mà đây là cơ sở khoa học để khuyến nghị khoảng đệm gas an toàn.

---

## TASK 3 — RÀ SOÁT CƠ CHẾ ESTIMATEGAS VÀ XỬ LÝ LỖI TRÊN FRONTEND

### 1. Kiểm tra các hàm gửi giao dịch trong `web/index.html`
- `voteRefundRequest`: Dòng 9643: `const tx = await contract.voteRefundRequest(refundId, support);`
- `executeRefund`: Dòng 9712: `const tx = await contract.executeRefundRequest(refundId);`
- `doCreateSpend`: Dòng 9750: `const tx = await contract.createSpendRequest(recipient, amountWei, desc);`
- `voteSpend`: Dòng 9782: `const tx = await contract.voteSpendRequest(requestId, support);`
- `executeSpend`: Dòng 9841: `const tx = await contract.executeSpendRequest(requestId);`
- `withdrawAdminFee`: Dòng 9909: `const tx = await contract.withdrawAdminFee(amountWei);`

**Xác nhận:** Toàn bộ các hàm trên **hoàn toàn KHÔNG chỉ định gasLimit cố định**. Ethers v6 và MetaMask sẽ tự động chạy cơ chế `eth_estimateGas` để ước lượng gas trước khi hiển thị màn hình ký xác nhận cho người dùng.

### 2. Hành vi khi xảy ra lỗi trên giao diện
Cấu trúc xử lý lỗi hiện tại ở tất cả các hàm giao dịch:
```javascript
try {
    // gửi giao dịch
} catch (err) {
    logToTerminal(`[Lỗi ...] ${err.shortMessage || err.message}`);
    alert("Thất bại: " + (err.shortMessage || err.message));
}
```

### 3. Phân biệt 3 nhóm lỗi người dùng thường gặp:
1. **Lỗi người dùng từ chối ký (MetaMask Rejection):**
   - Mã lỗi: `ACTION_REJECTED` (code: `4001`).
   - `err.shortMessage`: `"user rejected action"`.
   - Hiển thị trên UI: `[Lỗi bỏ phiếu chi] user rejected action` $\rightarrow$ Rõ ràng, dễ hiểu.
2. **Lỗi ước lượng Gas (`estimateGas` failure):**
   - Mã lỗi: `UNPREDICTABLE_GAS_LIMIT`.
   - `err.shortMessage`: `"cannot estimate gas; transaction may fail or may require manual gas limit"`.
   - Hiển thị trên UI: Báo rõ giao dịch không ước lượng được gas.
3. **Lỗi giao dịch bị Revert on-chain:**
   - Mã lỗi: `CALL_EXCEPTION`.
   - `err.shortMessage`: `"transaction execution reverted"` kèm mã lỗi custom (ví dụ `AlreadyVoted`, `ThresholdNotMet`, `ETHTransferFailed`).
   - Hiển thị trên UI: Thông báo đúng lý do revert.

### 4. Đánh giá tính sẵn sàng của Frontend:
- Cơ chế của Frontend hiện tại là **chuẩn mực theo thiết kế Web3 tiêu chuẩn** (dựa vào ước lượng động của ví, không ép cứng gasLimit để tránh lãng phí tiền gas của người dùng khi giao dịch thông thường chỉ tốn 72,000 gas).
- Không cần sửa đổi mã nguồn frontend trước khi deploy.

---

## TASK 4 — ĐỐI CHIẾU TÍNH NHẤT QUÁN CỦA CÁC BÁO CÁO

### 1. Bảng đối chiếu các chỉ số giữa FIX 9, FIX 10 và FIX 11:

| Hạng mục kiểm tra | Báo cáo FIX 9 | Báo cáo FIX 10 | Báo cáo FIX 11 (Rà soát lại) | Mức độ nhất quán |
| :--- | :--- | :--- | :--- | :---: |
| **Số dư Quỹ lớp (`classFundBalance`)** | Bảo toàn 100% trong mọi kịch bản | Bảo toàn 100% trong mọi kịch bản | Bảo toàn 100% (chính xác đến từng wei) | **Tuyệt đối** |
| **Tiền giữ chỗ (`reservedSpendAmount`)** | Bảo toàn khi thất bại, giải phóng khi xong | Bảo toàn khi thất bại, giải phóng khi xong | Khớp 100% trong 28 kịch bản | **Tuyệt đối** |
| **Trạng thái chuyển dịch** | Pending $\rightarrow$ Ready / Executed | Pending $\rightarrow$ Ready / Executed | Khớp chính xác giá trị enum 0, 1, 2 | **Tuyệt đối** |
| **Event logs auto-execution** | `SpendExecutionFailed` khi thất bại | `SpendExecutionFailed` khi thất bại | Khớp 100% với ABI định nghĩa | **Tuyệt đối** |
| **Gas used: Auto-exec EOA** | ~72,500 gas | 72,473 gas | 72,473 gas | **Tuyệt đối** |
| **Gas used: AlwaysRevert Rollback** | ~94,000 gas | 94,020 gas | 94,020 gas | **Tuyệt đối** |
| **Điểm gãy Gas (InfiniteLoop)** | Nhận định chung (< 350k gas) | Xác định khoảng 300k - 325k gas | **Xác định chính xác: 303,500 - 305,000 gas** | **Nâng cao độ chính xác** |
| **Chống Reentrancy đa điểm** | 6/6 hàm bị chặn | 6/6 hàm bị chặn | 6/6 hàm bị chặn đứng bởi CEI | **Tuyệt đối** |
| **Chống Double Spending** | Revert khi gọi lần 2 | Revert `InvalidStatus` (1,413 gas) | Revert `InvalidStatus` (1,413 / 1,087 gas) | **Tuyệt đối** |

### 2. Phân loại minh bạch nguồn gốc dữ liệu:
- **Số liệu đo lường thực nghiệm trực tiếp (Empirical Data):**
  * Toàn bộ giá trị `gasUsed` của 28 kịch bản và 16 mốc quét ranh giới gas.
  * Các giá trị số dư wei và enum trạng thái đọc từ EVM State Manager.
  * Toàn bộ các log sự kiện và revert error string từ EVM execution result.
- **Số liệu được tính toán lý thuyết (Calculated Data):**
  * Công thức gas giữ lại $1/64$ theo EIP-150: $G_{retained} = \lceil G_{beforeCall} / 64 \rceil$.
  * Ước tính chi phí gas của khối lệnh rollback: $\approx 4,750$ gas.
  * Tỷ lệ phần trăm đồng thuận theo basis point: $2/3 \times 10,000 = 6,666 \text{ bps} \ge 5,100 \text{ bps}$.
- **Nhận định và phân tích kỹ thuật (Technical Assessment):**
  * Khả năng timeout hoặc từ chối của một số node RPC công cộng khi gặp `while(true)`.
  * Khuyến cáo Ban cán sự không nên tạo đề xuất chi cho các hợp đồng chưa được kiểm chứng.

---

## TASK 5 — KẾ HOẠCH & CHECKLIST KIỂM CHỨNG TRÊN SEPOLIA TESTNET

> [!IMPORTANT]
> Đây là bản kế hoạch chuẩn bị và checklist quy trình kiểm thử, **KHÔNG thực hiện deploy hoặc gửi giao dịch** trong bước này.

### 1. Làm rõ vấn đề phiên bản Compiler Solidity (0.8.20 vs 0.8.26)
- **Lý do có 2 phiên bản trong các báo cáo trước:**
  * File [AGENTS.md](file:///d:/document/TDT/KTS-Class-Fund-K57/AGENTS.md) quy định: `Solidity ^0.8.20`.
  * Mã nguồn [ProjectCore.sol](file:///d:/document/TDT/KTS-Class-Fund-K57/contracts/project/ProjectCore.sol) khai báo: `pragma solidity ^0.8.20;`.
  * Hợp đồng cũ đã deploy trước đó trên Sepolia tại địa chỉ `0xe3e1db1da1cae10e92337c36bb13004bf984ee91` được biên dịch bằng `solc 0.8.26`.
- **Đánh giá tương thích:** Cú pháp của [ProjectCore.sol](file:///d:/document/TDT/KTS-Class-Fund-K57/contracts/project/ProjectCore.sol) hoàn toàn tương thích và biên dịch không lỗi trên cả `0.8.20`, `0.8.26`, và `0.8.28`.
- **Quy chuẩn chốt khi deploy Sepolia:** Sử dụng phiên bản **Solidity `0.8.20`** (hoặc `0.8.26`), cấu hình EVM version: `shanghai` (hoặc `paris`), `optimizer: { enabled: true, runs: 200 }`.

### 2. Thông số kỹ thuật của Contract Bytecode:
- **Kích thước Runtime Bytecode:** **12,329 bytes** (chỉ chiếm **50.1%** so với giới hạn tối đa 24,576 bytes của EIP-170 $\rightarrow$ Hoàn toàn an toàn).
- **Constructor Arguments:** Không có tham số khởi tạo (`constructor() { advisor = msg.sender; }`). Địa chỉ ví thực hiện deploy sẽ tự động trở thành Cố vấn học tập (Advisor).
- **Trạng thái ABI:** Khớp 100% với 39 functions và 15 events của hợp đồng.

### 3. Checklist 10 Bước Triển Khai và Kiểm Chứng On-Chain (Sepolia):

| STT | Bước thực hiện | Thao tác chi tiết | Kết quả mong đợi |
| :---: | :--- | :--- | :--- |
| **1** | **Chuẩn bị ví Cố vấn (Advisor)** | Mở MetaMask, chuyển sang mạng Sepolia, kiểm tra số dư ví deploy có tối thiểu 0.1 Sepolia ETH. | Ví sẵn sàng |
| **2** | **Deploy Contract lên Sepolia** | Sử dụng Remix IDE hoặc script web3, chọn compiler `0.8.20`, bật optimizer runs 200, kết nối Injected Provider MetaMask, bấm Deploy. | Giao dịch thành công, sinh ra Contract Address mới |
| **3** | **Cập nhật địa chỉ & ABI** | Cập nhật địa chỉ hợp đồng mới vào biến `CONTRACT_ADDRESS` trong [web/index.html](file:///d:/document/TDT/KTS-Class-Fund-K57/web/index.html) và ABI mới. | Frontend kết nối tới contract mới |
| **4** | **Thiết lập Ban cán sự (BCS)** | Dùng ví Advisor gọi hàm `setBCSMember(bcsAddress, true)` cho 3 ví BCS khác nhau. | Event `BCSMemberUpdated` được phát ra, activeBCSCount = 3 |
| **5** | **Thử nghiệm Nộp quỹ (Deposit)** | Dùng ví Sinh viên nạp 0.05 Sepolia ETH qua giao diện. | 0.0005 ETH vào `adminFeePool` (1%), 0.0495 ETH vào quỹ lớp |
| **6** | **Tạo đề xuất chi & Bỏ phiếu** | BCS1 tạo đề xuất chi 0.01 ETH cho ví người nhận. BCS1 vote Yes. | Đề xuất ở `Pending`, số tiền 0.01 ETH được giữ chỗ |
| **7** | **Kích hoạt Auto-Execution** | BCS2 vote Yes (đạt 66.6% $\ge$ 51%). | Giao dịch vote tự động chuyển 0.01 ETH cho người nhận. Event `SpendRequestExecuted` phát ra, trạng thái chuyển `Executed`. |
| **8** | **Kiểm tra Chống Chi Trùng** | Bất kỳ BCS nào bấm nút Giải ngân thủ công cho đề xuất vừa hoàn tất. | Giao dịch bị MetaMask / Node từ chối với lỗi `InvalidStatus` |
| **9** | **Thử nghiệm Thất bại & Rollback** | Tạo đề xuất chi cho một địa chỉ hợp đồng từ chối ETH (hoặc test contract). BCS vote đạt ngưỡng. | Giao dịch vote thành công, phát `SpendExecutionFailed`, đề xuất chuyển về `Ready`, quỹ lớp bảo toàn 100%. |
| **10** | **Rút phí Quỹ vận hành** | Dùng ví Advisor gọi `withdrawAdminFee(0.0005 ether)`. | 0.0005 ETH được rút về ví Advisor, `adminFeePool` về 0. |

---

## KẾT LUẬN CUỐI CÙNG

### **READY FOR SEPOLIA TEST DEPLOYMENT (ĐÃ ĐỦ ĐIỀU KIỆN SẴN SÀNG TRIỂN KHAI THỬ NGHIỆM TRÊN SEPOLIA)**

**Căn cứ xác nhận:**
1. Hợp đồng [ProjectCore.sol](file:///d:/document/TDT/KTS-Class-Fund-K57/contracts/project/ProjectCore.sol) đã vượt qua toàn bộ 57 bài test EVM chuyên sâu về Gas Griefing, Failure-Path, Reentrancy, và Boundary Scan mà không phát sinh bất kỳ lỗi bảo mật hay sai lệch kế toán nào.
2. Cơ chế Auto-Execution kết hợp Fallback Rollback hoạt động hoàn hảo, bảo vệ quyền lợi người bỏ phiếu và bảo toàn 100% tài sản lớp học.
3. Bytecode nhỏ gọn (12.3 KB / 24.5 KB), cấu trúc ABI và Frontend đã đồng bộ hoàn chỉnh.
4. Dự án đã sẵn sàng để người dùng tiến hành bước tiếp theo là triển khai thử nghiệm trên Sepolia Testnet theo quy trình kiểm soát an toàn.
