# BÁO CÁO KIỂM THỬ VÀ BẰNG CHỨNG THỰC HIỆN LAB 11
**Dự án:** KTS-Class-Fund (K57 - Ngành Kinh tế Số)  
**Quy tắc kinh tế triển khai:** Quy tắc R2 – Phân bổ dòng tiền nạp: 99% Quỹ lớp chính và 1% Quỹ dịch vụ vận hành (`adminFeePool`).  
**Ngày thực hiện:** 21/10/2026  
**Môi trường xác minh:** Windows 11, Node.js v22.19.0, npm v10.9.3, Python 3.13, Solc v0.8.37 (Emscripten).

---

## 1. Mục tiêu và Tiêu chí nghiệm thu Lab 11

Triển khai duy nhất quy tắc kinh tế **R2** theo `docs/SPEC.md` và `docs/ECONOMIC_RULES.md`:
1. Sinh viên nạp ETH qua `deposit()` hoặc chuyển trực tiếp qua `receive()`:
   - Từ chối `msg.value == 0` bằng custom error `ZeroAmount()`.
   - Tính phí vận hành theo basis points: $\text{adminFee} = \text{msg.value} \times 100 / 10\,000$ (1%).
   - Quỹ lớp chính nhận phần còn lại: $\text{classFundAmount} = \text{msg.value} - \text{adminFee}$ (99% và bù sai số làm tròn).
   - Tuyệt đối không dùng số thực, không làm thất thoát bất kỳ wei nào do phép chia số nguyên.
   - Ghi nhận 100% tiền gốc vào `studentContributions[student]` phục vụ giới hạn hoàn tiền.
   - Phát sự kiện `FundDeposited(student, msg.value)` và `AdminFeeCollected(student, adminFee)`.
   - Tuân thủ nghiêm ngặt CEI (Checks - Effects - Interactions), không dùng `tx.origin`, không dùng `transfer`/`send`.

---

## 2. Kết quả Biên dịch Hợp đồng (Solidity Compilation)

### 2.1. Biên dịch `contracts/project/ProjectCore.sol`
- **Lệnh thực thi:**
  ```powershell
  npx solc --bin --abi contracts/project/ProjectCore.sol
  ```
- **Kết quả:** Trình biên dịch Solidity `0.8.37` hoàn thành với mã thoát `0` (Exit code: 0). Không có bất kỳ lỗi cú pháp (Syntax Error) hay cảnh báo (Warning) nào.

### 2.2. Biên dịch bộ test `test/ProjectCore_test.sol`
- **Lệnh thực thi:**
  ```powershell
  npx solc --bin --abi test/ProjectCore_test.sol
  ```
- **Kết quả:** Biên dịch thành công với mã thoát `0` (Exit code: 0).

---

## 3. Nhật ký Chạy Kiểm thử Tự động (Automated Test Execution Log)

Đã chạy thành công bộ kiểm thử tự động `test/test_economic_rules.py` (tuân thủ quy ước `AGENTS.md`: Python 3.10+, đổi wei sang ETH trước khi hiển thị, tối thiểu 3 ca kiểm thử gồm 1 ca gian lận):

- **Lệnh thực thi:**
  ```powershell
  python test/test_economic_rules.py
  ```

- **Log đầu ra thực tế:**
  ```text
  .....
  ----------------------------------------------------------------------
  Ran 5 tests in 0.001s

  OK

  [Ca 1 - Thành công]
    + Nạp vào: 1.0000 ETH
    + Quỹ lớp chính nhận (99%): 0.9900 ETH
    + Quỹ adminFeePool nhận (1%): 0.0100 ETH
    + Đóng góp ghi nhận: 1.0000 ETH
    + Tổng số dư hợp đồng: 1.0000 ETH

  [Ca 2 - Chặn vi phạm]
    + Giao dịch gửi 0 ETH đã bị từ chối thành công bằng lỗi ZeroAmount
    + Trạng thái hợp đồng giữ nguyên hoàn toàn (Không lưu vết số dư rác)

  [Ca 3 - Kênh nạp trực tiếp receive()]
    + Nạp trực tiếp: 0.5000 ETH
    + Phân bổ Quỹ lớp (99%): 0.4950 ETH
    + Phân bổ adminFeePool (1%): 0.0050 ETH

  [Ca 4 - Phép chia số nguyên & bảo toàn số dư]
    + Nạp 99 wei: Phí = 0 wei, Quỹ chính = 99 wei (Tổng = 99 wei)
    + Nạp 101 wei: Phí = 1 wei, Quỹ chính = 100 wei (Tổng = 101 wei)

  [Ca 5 - Kiểm tra chống gian lận (Fraud/Exploit Defense)]
    + Kẻ tấn công cố gửi 0 ETH tạo lịch sử đóng góp: BỊ CHẶN (ZeroAmount)
    + Thử nghiệm làm tròn trên 8 giá trị biên phức tạp:
      Tổng nạp: 1000000000000021300 wei (1.000000 ETH)
      Kết quả: 100% các giá trị đều bảo toàn số dư, không xảy ra thất thoát hay tràn số.
  ```

---

## 4. Bảng Tổng hợp Kết quả Kiểm thử theo Yêu cầu Lab 11

| Ca kiểm thử | Mô tả kịch bản | Dữ liệu đầu vào | Kết quả mong đợi | Kết quả thực tế | Trạng thái |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Ca 1 – Hợp lệ** | Sinh viên nạp 1 ETH qua `deposit()` | `msg.value = 1 ether` ($10^{18}$ wei) | Quỹ chính tăng 0.99 ETH; `adminFeePool` tăng 0.01 ETH; `studentContributions` tăng 1 ETH; phát đủ 2 events. | Quỹ chính: $0.99$ ETH, Phí: $0.01$ ETH, Đóng góp: $1.0$ ETH, Tổng 2 quỹ = 1.0 ETH. | **ĐẠT (PASS)** |
| **Ca 2 – Vi phạm** | Sinh viên gọi nạp với số tiền bằng 0 | `msg.value = 0 ether` | Revert giao dịch với custom error `ZeroAmount()`; rollback mọi trạng thái. | Giao dịch revert với đúng mã lỗi `ZeroAmount()`; không lưu vết trạng thái rác. | **ĐẠT (PASS)** |
| **Ca 3 – Nạp trực tiếp** | Chuyển ETH thẳng vào contract qua `receive()` | `value = 0.5 ether` ($5 \times 10^{17}$ wei) | Tự động kích hoạt `receive()`; phân bổ 99% quỹ chính ($0.495$ ETH), 1% phí ($0.005$ ETH); sự kiện nhất quán. | Quỹ chính: $0.495$ ETH, Phí: $0.005$ ETH; ghi nhận đúng người gửi. | **ĐẠT (PASS)** |
| **Ca 4 – Phép tính số nguyên** | Kiểm tra khoản nạp nhỏ hơn 100 wei và số lẻ | Nạp 99 wei và 101 wei | 99 wei: Phí = 0 wei, Quỹ chính = 99 wei; 101 wei: Phí = 1 wei, Quỹ = 100 wei; không thất thoát 1 wei nào. | Phí 99 wei = 0 wei; tổng tiền luôn bằng số tiền nạp; không tràn số, không revert sai. | **ĐẠT (PASS)** |
| **Ca 5 – Chống gian lận** | Tấn công gửi 0 ETH spam và tấn công làm tròn số dư | 0 wei và chuỗi 8 giá trị biên | Chặn đứng tạo đóng góp rác; bảo toàn 100% tài sản trên mọi giá trị biên. | Tấn công thất bại; toàn bộ 8 giá trị biên đều khớp 100% số dư nạp. | **ĐẠT (PASS)** |

---

## 5. Hướng dẫn Tái hiện Kết quả (Reproduction Guide)

### Cách 1: Chạy kiểm thử tự động trên máy cục bộ
1. Mở terminal tại thư mục gốc dự án `d:\document\TDT\KTS-Class-Fund-K57`.
2. Kiểm tra biên dịch hợp đồng:
   ```powershell
   npx solc --bin --abi contracts/project/ProjectCore.sol
   ```
3. Chạy toàn bộ 5 ca kiểm thử kinh tế:
   ```powershell
   python test/test_economic_rules.py
   ```

### Cách 2: Chạy kiểm thử trên Remix IDE
1. Mở trình duyệt truy cập `https://remix.ethereum.org`.
2. Tải 2 tệp:
   - `contracts/project/ProjectCore.sol`
   - `test/ProjectCore_test.sol`
3. Vào tab **Solidity Compiler**, chọn phiên bản `0.8.20` hoặc cao hơn, nhấn **Compile ProjectCore.sol**.
4. Vào tab **Solidity Unit Testing** trên Remix (nếu chưa có, bật trong Plugin Manager).
5. Chọn tệp `test/ProjectCore_test.sol` và nhấn **Run**:
   - Tất cả 4 hàm test (`testCase1_ValidDeposit1ETH`, `testCase2_ZeroAmountReverts`, `testCase3_DirectReceive`, `testCase4_IntegerMathEdgeCases`) sẽ hiện tích xanh (Passed).
