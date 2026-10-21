# KTS-Class-Fund

Hệ thống Hợp đồng thông minh Quản lý Quỹ lớp Phi tập trung dành cho sinh viên ngành Kinh tế Số (Khoa Hệ thống Thông tin Kinh tế, Trường Đại học Kinh tế – Đại học Huế).

## Thành viên nhóm thực hiện
| Họ và tên | Mã sinh viên | Vai trò trong dự án |
| :--- | :--- | :--- |
| **Trần Hoàng Phương Dung** | 23K4300004 | Trưởng nhóm / Smart Contract Developer |
| **Võ Ngọc Tâm Phúc** | 23K4300015 | Thành viên kỹ thuật / QA & Tester |

---

## 1. Giới thiệu dự án

KTS-Class-Fund là giải pháp Smart Contract nhằm minh bạch hóa toàn diện dòng tiền thu chi của quỹ lớp. Hệ thống giải quyết các vấn đề tồn đọng của phương thức giữ quỹ truyền thống (tiền mặt hoặc tài khoản ngân hàng cá nhân), tự động trích quỹ dịch vụ vận hành để hỗ trợ chi phí Gas mạng lưới cho người quản trị, và lưu trữ lịch sử giao dịch bất biến trên blockchain.

### Phân quyền các vai trò người dùng (Theo `docs/SPEC.md`):
- **Cố vấn học tập (CVHT / Owner):** Quản lý nhân sự Ban cán sự (kích hoạt/hủy quyền) và có đặc quyền rút Quỹ dịch vụ vận hành (`adminFeePool`) để bù đắp chi phí Gas.
- **Ban cán sự lớp (BCS):** Đề xuất các khoản chi tiêu phục vụ hoạt động tập thể lớp.
- **Sinh viên trong lớp:** Nộp ETH vào quỹ chung, theo dõi số dư minh bạch theo thời gian thực.

---

## 2. Hiện trạng mã nguồn và Phân định tính năng (Cập nhật sau Lab 11 & Lab 12)

Để phản ánh chính xác tình trạng kỹ thuật tại cổng kiểm duyệt **Gate Review 1 (Lab 12)**, các tính năng được phân định rõ ràng giữa thực tế mã nguồn và lộ trình phát triển:

### 2.1. Tính năng ĐÃ TRIỂN KHAI trong mã nguồn hiện tại (`contracts/project/ProjectCore.sol`):
- [x] **Nạp quỹ linh hoạt:** Sinh viên có thể nạp ETH vào quỹ qua 2 kênh:
  - Hàm `deposit()`: Dành cho giao dịch từ giao diện DApp.
  - Hàm `receive()`: Tự động tiếp nhận khi sinh viên chuyển ETH trực tiếp từ ví cá nhân (MetaMask).
  - Cả hai kênh đều sử dụng chung hàm xử lý nội bộ `_processDeposit(sender, amount)` để bảo đảm tính nhất quán và áp dụng nguyên tắc Checks - Effects - Interactions (CEI).
- [x] **Quy tắc kinh tế R2 (Phân bổ 99% / 1% theo Basis Points):**
  - Trích tự động **1%** (100 basis points) vào Quỹ dịch vụ vận hành (`adminFeePool`) để hỗ trợ chi phí Gas cho Cố vấn học tập: `adminFee = (amount * FEE_BPS) / BPS_DENOMINATOR` với `FEE_BPS = 100`, `BPS_DENOMINATOR = 10_000`.
  - Phân bổ **99%** số tiền còn lại vào Quỹ lớp chính khả dụng (`classFundBalance`): `classFundAmount = amount - adminFee`.
- [x] **Bảo toàn số dư & Phép tính số nguyên:** Sử dụng hoàn toàn số nguyên không âm (`uint256`), không dùng số thực. Phần bù sai số làm tròn được cộng trọn vẹn vào Quỹ lớp chính để không làm thất thoát bất kỳ wei nào của sinh viên. Với các khoản nạp nhỏ hơn 100 wei, phí vận hành tính ra bằng 0 wei và quỹ lớp nhận đủ 100% giá trị nạp, giao dịch không bị revert vô cớ.
- [x] **Chặn giao dịch vi phạm (Nạp 0 ETH):** Kiểm tra `amount == 0` ngay bước Checks và từ chối giao dịch bằng lỗi tùy biến `ZeroAmount()`, tiết kiệm chi phí Gas hơn so với chuỗi ký tự lỗi dài và không lưu vết số dư rác.
- [x] **Theo dõi đóng góp gốc của từng sinh viên:** Ghi nhận đủ 100% số tiền gốc thực tế sinh viên nạp vào bảng ánh xạ `studentContributions[student]` làm căn cứ xác định hạn mức khi xét duyệt hoàn tiền.
- [x] **Lưu vết sự kiện Blockchain đầy đủ:** Phát sự kiện chuẩn on-chain:
  - `event FundDeposited(address indexed student, uint256 amount)`
  - `event AdminFeeCollected(address indexed student, uint256 feeAmount)`
- [x] **Hàm tra cứu minh bạch (View / Getters):**
  - `getFundBalance()`: Tra cứu số dư khả dụng của Quỹ lớp chính (99% từ tiền nạp).
  - `getTotalContractBalance()`: Tra cứu tổng số dư ETH thực tế hiện có trong hợp đồng (`address(this).balance`).
  - `getStudentContribution(address student)`: Tra cứu tổng số tiền đã đóng góp của một địa chỉ ví sinh viên cụ thể.

> [!NOTE]  
> **Lưu ý quan trọng về môi trường kiểm chứng:** Hợp đồng `ProjectCore.sol` tính đến hết Lab 12 **CHƯA ĐƯỢC TRIỂN KHAI (DEPLOY) LÊN MẠNG SEPOLIA TESTNET**. Mọi kết quả hoạt động hiện tại được kiểm chứng trên môi trường giả lập Python cục bộ (`test/test_economic_rules.py`), trình biên dịch `solc 0.8.37`, và máy ảo Remix VM (`test/ProjectCore_test.sol`). Việc triển khai on-chain lên Sepolia Testnet là mục tiêu chính thức của **Lab 15**.

### 2.2. Tính năng CHƯA TRIỂN KHAI (Chưa có trong mã nguồn hiện tại):
Đối chiếu trực tiếp với `contracts/project/ProjectCore.sol`, các chức năng sau **hoàn toàn chưa được cài đặt**:
- [ ] **Chưa có cơ chế biểu quyết thông qua đề xuất chi quỹ:** Chưa có cấu trúc dữ liệu `SpendRequest`, chưa có mapping ghi nhận biểu quyết `hasVoted`, chưa có hàm tính tỷ lệ đồng ý tối thiểu 51% của Ban cán sự (R4, R5).
- [ ] **Chưa có cơ chế thời hạn biểu quyết và giải ngân:** Chưa có logic kiểm tra thời hạn 7 ngày (`block.timestamp <= createdAt + 7 days`) hay cơ chế đánh dấu hết hạn (R5, R9).
- [ ] **Chưa có chức năng hoàn tiền:** Chưa có bất kỳ hàm yêu cầu hoàn tiền, phê duyệt hoàn tiền hay logic chuyển trả ETH hoàn lại cho sinh viên nộp nhầm (R7, R10).
- [ ] **Chưa có quản lý thành viên Ban cán sự & phân quyền đầy đủ:** Chưa có mapping danh sách thành viên BCS (`isBCSMember`), chưa có hàm thêm/xóa BCS (`setBCSMember`), chưa có modifier `onlyAdvisor` (R1) ngoài việc gán địa chỉ `advisor = msg.sender` trong `constructor`.
- [ ] **Chưa có hàm rút phí quản lý (`withdrawAdminFee` - R11):** Tiền phí vận hành 1% tích lũy trong `adminFeePool` tạm thời chưa thể rút ra ngoài ví Cố vấn học tập.

### 2.3. Lộ trình phát triển sản phẩm (Phân định rõ 3 giai đoạn):
1. **Giai đoạn hiện tại (Đã hoàn thành đến hết Lab 12):**
   - Triển khai và kiểm chứng 100% quy tắc kinh tế nạp quỹ R2 (`deposit`, `receive`, 99/1 basis points, custom error `ZeroAmount`, events, getters).
   - Kiểm thử tự động Python 5/5 ca ĐẠT, kiểm thử Remix VM 4/4 ca ĐẠT, biên dịch Solc không lỗi.
2. **Giai đoạn mục tiêu phiên bản v0.1 (Kế hoạch thực hiện Lab 13 – Lab 15):**
   - **Lab 13 (Phân quyền, Rút phí & Luồng Biểu quyết cốt lõi):**
     - Cài đặt modifier `onlyAdvisor`, hàm quản lý nhân sự BCS `setBCSMember(...)` (R1).
     - Cài đặt hàm rút phí vận hành `withdrawAdminFee(amount)` cho CVHT (R11).
     - Xây dựng quy trình tạo Đề xuất chi và **Biểu quyết dân chủ $\ge 51\%$** (R3, R4, R5, R6) trong thời hạn 7 ngày. **Biểu quyết là chức năng cốt lõi bắt buộc của dự án, được giữ nguyên vẹn trong v0.1.**
   - **Lab 14 (Hoàn tiền an toàn & Kiểm thử tích hợp toàn diện):**
     - Đánh giá và cài đặt luồng **Hoàn tiền an toàn (R7 tinh giản)** cho trường hợp sinh viên nộp nhầm với điều kiện an toàn kép: `refundAmount <= studentContributions[msg.sender]` và `refundAmount <= classFundBalance`.
     - Kiểm thử tích hợp liên hoàn toàn bộ chu trình sống của dòng tiền (Nạp $\rightarrow$ Biểu quyết $\rightarrow$ Chi $\rightarrow$ Hoàn $\rightarrow$ Rút phí), lập bảng đo lường Gas.
   - **Lab 15 (Kết nối DApp Frontend & Triển khai Sepolia):**
     - Kết nối giao diện người dùng `web/index.html` với hợp đồng qua MetaMask và Ethers.js.
     - Triển khai hợp đồng chính thức lên mạng thử nghiệm Ethereum Sepolia Testnet, thực hiện demo giao dịch thực tế.
3. **Giai đoạn mở rộng phiên bản v0.2 (Đề xuất hoãn sau khi hoàn thành môn học):**
   - Tích hợp tải file minh chứng và lưu trữ mã băm IPFS CID (`proofHash`) on-chain.
   - Cơ chế ủy quyền biểu quyết (Proxy Voting) hoặc phân bổ trọng số phiếu bầu.
   - Cơ chế tự động dọn dẹp hàng đợi quá hạn đa trạng thái phức tạp (v0.1 kiểm tra trực tiếp qua `block.timestamp`).
   - Hỗ trợ nạp quỹ bằng các loại token ERC-20 (USDT/USDC) để chống rủi ro biến động tỷ giá ETH và tích hợp cổng thanh toán tiền pháp định (Fiat).

---

## 3. Hướng dẫn kiểm tra và Chạy thử nghiệm thực tế

Dự án cung cấp tài liệu hướng dẫn cụ thể và tách biệt cho từng phương thức kiểm thử dựa trên các tệp thực tế hiện có trong repository:

### 3.1. Phương thức 1: Chạy kiểm thử tự động bằng Python

Tệp kiểm thử: `test/test_economic_rules.py`  
Mục đích: Kiểm tra tự động toàn bộ logic số học, quy tắc kinh tế R2, cơ chế trích phí 1%, kiểm tra số nguyên biên và mô phỏng chống gian lận.

- **Điều kiện môi trường cần có:**
  - Máy tính đã cài đặt **Python 3.10+** (đã kiểm tra tương thích trên Python 3.10, 3.11, 3.12, 3.13).
  - Sử dụng toàn bộ thư viện chuẩn của Python (`unittest`, `sys`, `typing`). **Không yêu cầu cài đặt thêm bất kỳ thư viện ngoài nào (không cần `pip install`)**.
- **Lệnh thực thi trong Terminal / PowerShell:**
  ```powershell
  python test/test_economic_rules.py
  ```
- **Kết quả thực tế quan sát được (Quan sát trực tiếp trên terminal):**
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

### 3.2. Phương thức 2: Chạy kiểm thử đơn vị Solidity bằng Remix VM

Tệp kiểm thử: `test/ProjectCore_test.sol`  
Bản chất tệp: Đây là một **Solidity Test Contract** chuyên dụng được viết riêng cho plugin **Solidity Unit Testing** của Remix IDE (chứ không phải hợp đồng cần deploy thủ công để thao tác bằng tay). Tệp chứa hàm `beforeEach()` tự động khởi tạo môi trường trước mỗi ca kiểm thử và 4 hàm test: `testCase1_ValidDeposit1ETH`, `testCase2_ZeroAmountReverts`, `testCase3_DirectReceive`, `testCase4_IntegerMathEdgeCases`.

- **Hướng dẫn từng bước thực hiện trên Remix IDE:**
  1. Mở trình duyệt web và truy cập: [https://remix.ethereum.org](https://remix.ethereum.org).
  2. Tại bảng điều khiển File Explorer của Remix, tải lên hoặc tạo mới 2 tệp theo đúng cấu trúc thư mục:
     - `contracts/project/ProjectCore.sol`
     - `test/ProjectCore_test.sol`
  3. Mở tab **Solidity Compiler** (icon thứ 3 ở thanh bên trái):
     - Chọn phiên bản Compiler tương thích: `0.8.20` hoặc cao hơn (khuyến nghị `0.8.20` đến `0.8.26`).
     - Chọn tệp `contracts/project/ProjectCore.sol` và nhấn **Compile ProjectCore.sol**. Xác nhận xuất hiện dấu tích xanh thông báo biên dịch không có lỗi.
  4. Kích hoạt plugin **Solidity Unit Testing**:
     - Nhấp vào biểu tượng **Plugin Manager** (icon hình phích cắm ở góc dưới cùng bên trái thanh công cụ).
     - Nhập từ khóa `Solidity unit testing` vào ô tìm kiếm.
     - Nhấn nút **Activate** để kích hoạt plugin. Một biểu tượng hình dấu tích kiểm tra sẽ xuất hiện trên thanh công cụ bên trái.
  5. Chạy bộ kiểm thử tự động:
     - Nhấp vào tab **Solidity Unit Testing** vừa kích hoạt.
     - Tại mục lựa chọn file test, chọn tệp `test/ProjectCore_test.sol`.
     - Nhấn nút màu xanh **Run** để bắt đầu thực thi kiểm thử trên môi trường giả lập **Remix VM (Cancun / Shanghai)**.
  6. **Đánh giá và nhận biết kết quả:**
     - **Kết quả thành công (ĐẠT):** Cả 4 hàm kiểm thử đều hiển thị biểu tượng tích xanh lá cây kèm chữ `Passed`:
       - `✓ testCase1_ValidDeposit1ETH` (Nạp 1 ETH phân bổ chuẩn 0.99 ETH và 0.01 ETH).
       - `✓ testCase2_ZeroAmountReverts` (Nạp 0 ETH bị revert đúng mã lỗi `ZeroAmount()`).
       - `✓ testCase3_DirectReceive` (Kênh nạp trực tiếp qua `receive()` hoạt động chuẩn).
       - `✓ testCase4_IntegerMathEdgeCases` (Bảo toàn số dư cho khoản nạp 99 wei và 101 wei).
     - **Cách nhận biết kiểm thử thất bại (LỖI):** Nếu có bất kỳ điều kiện `require` nào trong tệp test không được thỏa mãn hoặc hợp đồng không revert đúng lỗi `ZeroAmount()`, hàm kiểm thử tương ứng sẽ xuất hiện biểu tượng dấu chéo màu đỏ (`Failed`) kèm chuỗi thông báo lỗi chi tiết chỉ rõ dòng lệnh vi phạm.

### 3.3. Phương thức 3: Kiểm tra biên dịch cục bộ bằng trình biên dịch Solc

- **Lệnh thực thi trong PowerShell / Terminal:**
  ```powershell
  npx solc --bin --abi contracts/project/ProjectCore.sol
  ```
- **Kết quả thực tế:** Trình biên dịch `solc 0.8.37` hoàn thành với mã thoát `0` (Exit code: 0), không xuất hiện bất kỳ cảnh báo (warning) hay lỗi cú pháp (error) nào.

### 3.4. Bảng tổng hợp đối chiếu kết quả kiểm thử (Expected vs Observed)

| Ca kiểm thử | Kịch bản kiểm thử | Dữ liệu đầu vào | Kết quả mong đợi (Expected) | Kết quả thực tế quan sát được (Observed) | Trạng thái |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Ca 1 (Hợp lệ)** | Nạp 1 ETH qua `deposit()` | `1 ether` ($10^{18}$ wei) | Quỹ lớp tăng 0.99 ETH; `adminFeePool` tăng 0.01 ETH; đóng góp tăng 1 ETH; phát 2 events. | Khớp 100%: Quỹ chính: 0.99 ETH, Phí: 0.01 ETH, Đóng góp: 1.0 ETH, Tổng 2 quỹ = 1.0 ETH. | **ĐẠT (PASS)** |
| **Ca 2 (Chặn vi phạm)** | Gửi giao dịch nạp 0 ETH | `0 ether` | Giao dịch revert với lỗi `ZeroAmount()`, không lưu vết số dư rác. | Revert đúng mã lỗi `ZeroAmount()`, trạng thái giữ nguyên hoàn toàn. | **ĐẠT (PASS)** |
| **Ca 3 (Nạp trực tiếp)** | Chuyển ETH thẳng vào contract qua `receive()` | `0.5 ether` | Phân bổ 99% ($0.495$ ETH) vào Quỹ lớp và 1% ($0.005$ ETH) vào Quỹ phí; ghi nhận người gửi. | Khớp 100%: Phân bổ đúng 0.495 ETH và 0.005 ETH, đóng góp ghi nhận 0.5 ETH. | **ĐẠT (PASS)** |
| **Ca 4 (Số nguyên biên)** | Nạp khoản cực nhỏ (< 100 wei) và số lẻ | 99 wei và 101 wei | 99 wei: Phí 0 wei, Quỹ 99 wei; 101 wei: Phí 1 wei, Quỹ 100 wei; tổng bảo toàn 100%. | Khớp 100%: Phí 99 wei = 0 wei; tổng số dư bảo toàn tuyệt đối, không tràn số. | **ĐẠT (PASS)** |
| **Ca 5 (Chống gian lận)** | Gửi 0 ETH spam và tấn công làm tròn 8 giá trị biên | 0 wei và 8 giá trị biên | Chặn gửi 0 ETH; bảo toàn 100% tài sản trên mọi giá trị biên phức tạp. | Bị chặn bởi `ZeroAmount()`; 8 giá trị biên đều bảo toàn 100% wei, không thất thoát. | **ĐẠT (PASS)** |
| **Ca kiểm thử on-chain** | Tương tác giao dịch thực tế trên mạng công khai Sepolia | Sepolia ETH | Hợp đồng hoạt động trên mạng public testnet qua MetaMask. | **CHƯA KIỂM THỬ** (Hợp đồng chưa deploy lên Sepolia; kế hoạch thực hiện tại Lab 15). | *Kế hoạch Lab 15* |

# ECO2432 Web3 Starter

Kho khởi đầu dùng xuyên suốt 15 bài thực hành.

## Bắt đầu (thay cho bước "Fork kho" trong sổ tay)

Sổ tay ghi "Fork kho `hce-web3-starter`". Học kỳ này kho được phát dạng tệp nén, nên làm như sau:

1. Giải nén thư mục này vào máy, mở bằng Antigravity.
2. Đọc `AGENTS.md` trước khi yêu cầu công cụ AI sinh mã.
3. Sao chép `SPEC.md` và `AI_JOURNAL.md` cho từng bài.
4. Chỉ dùng ví thử nghiệm và mạng Sepolia; không dùng khóa ví có tiền thật.

Đưa lên GitHub (làm khi đã có tài khoản; cần trước khi nộp Lab 1):

```bash
git init -b main
git add .
git commit -m "chore: thiet lap moi truong lam viec"
git remote add origin https://github.com/<tai-khoan>/<ten-repo>.git   # repo tạo TRỐNG trên GitHub
git push -u origin main
```

Lab 8 (repo nhóm): một thành viên tạo repo trống mới, đưa nội dung thư mục này lên theo đúng các
lệnh trên, rồi mời các thành viên khác làm collaborator.

## Cấu trúc

- `contracts/training/`: hợp đồng mẫu dùng ở Lab 9, 10, 11 và 13
  (`TimeLockVault`, `VaultBuggy`, `ClassPoint`, `VulnerableBank`).
- `contracts/lab04/ClubTokens.sol`: ba token dùng cho Lab 4.
- `web/index.html`: giao diện mẫu dùng ở Lab 15.
- `prompt_templates.md`: mẫu câu lệnh có yêu cầu và tiêu chí kiểm chứng rõ ràng.

Các hợp đồng có chữ `Buggy`, `Vulnerable` hoặc cảnh báo trong mã đều chứa lỗi có chủ đích.

## Chạy hợp đồng

- Cách chính: mở Remix IDE (`https://remix.ethereum.org`), tạo tệp, dán mã. Remix tự tải thư viện
  `@openzeppelin/...`, không cần cài gì.
- Nếu Antigravity gạch đỏ dòng `import "@openzeppelin/..."`: đó là do máy chưa có thư viện, mã
  không sai. Muốn hết gạch đỏ thì cài Node.js rồi chạy `npm install` trong thư mục này (không bắt buộc).
