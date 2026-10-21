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
- **Ban cán sự lớp (BCS):** Đề xuất các khoản chi tiêu phục vụ hoạt động tập thể lớp, tham gia biểu quyết dân chủ ($\ge 51\%$) và thực thi giải ngân.
- **Sinh viên trong lớp:** Nộp ETH vào quỹ chung, theo dõi số dư minh bạch theo thời gian thực.

---

## 2. Hiện trạng mã nguồn và Phân định tính năng (Cập nhật sau Lab 13)

Để phản ánh chính xác tình trạng kỹ thuật sau **Lab 13 (Hoàn thiện phân quyền, biểu quyết $\ge 51\%$ và hardening an ninh)**, các tính năng được phân định rõ ràng giữa thực tế mã nguồn và lộ trình phát triển:

### 2.1. Tính năng ĐÃ TRIỂN KHAI trong mã nguồn hiện tại (`contracts/project/ProjectCore.sol`):
- [x] **R1 — Phân quyền Quản trị CVHT & Quản lý Ban cán sự (BCS):**
  - Modifier `onlyAdvisor`: Chỉ địa chỉ ví Cố vấn học tập mới có quyền thay đổi nhân sự BCS.
  - Hàm `setBCSMember(address member, bool status)`: Thêm mới, kích hoạt hoặc vô hiệu hóa thành viên BCS.
  - Cập nhật số lượng BCS hoạt động linh hoạt (`activeBCSCount`) làm mẫu số động cho biểu quyết.
  - Từ chối địa chỉ zero (`InvalidAddress()`) và chặn người ngoài can thiệp (`NotAdvisor()`).
  - Phát sự kiện `BCSMemberUpdated(member, status)`.
- [x] **R2 — Nạp quỹ linh hoạt & Phân bổ 99% / 1% theo Basis Points:**
  - Nạp qua 2 kênh: hàm `deposit()` (DApp) và hàm `receive()` (chuyển ETH trực tiếp).
  - Trích tự động **1%** (100 basis points) vào Quỹ dịch vụ vận hành (`adminFeePool`): `(amount * FEE_BPS) / BPS_DENOMINATOR`.
  - Phân bổ **99%** số tiền còn lại vào Quỹ lớp chính (`classFundBalance`): `amount - adminFee` (bảo toàn 100% wei lẻ do làm tròn số nguyên).
  - Chặn giao dịch nạp 0 ETH bằng lỗi tùy biến `ZeroAmount()`.
  - Ghi nhận đầy đủ lịch sử đóng góp gốc `studentContributions[student]`.
  - Phát sự kiện `FundDeposited` và `AdminFeeCollected`.
- [x] **R11 — Rút phí dịch vụ vận hành (CVHT):**
  - Hàm `withdrawAdminFee(uint256 amount)`: Dành riêng cho CVHT để bù đắp chi phí Gas.
  - Áp dụng nghiêm ngặt nguyên tắc Checks-Effects-Interactions (CEI): trừ `adminFeePool` trước khi chuyển ETH bằng low-level `.call`.
  - Chặn rút 0 ETH (`ZeroAmount()`) và chặn rút vượt quá số dư phí (`InsufficientAdminFee()`).
  - Tuyệt đối không xâm lấn hoặc ảnh hưởng đến Quỹ lớp chính (`classFundBalance`).
  - Phát sự kiện `AdminFeeWithdrawn(advisor, amount)`.
- [x] **R3 — Tạo đề xuất chi tiêu & Giữ chỗ số dư (BCS):**
  - Cấu trúc dữ liệu `SpendRequest` lưu trữ đầy đủ: người nhận, số tiền, mô tả, người tạo, thời điểm tạo, số phiếu thuận/chống, trạng thái.
  - Hàm `createSpendRequest(recipient, amount, description)`: Chỉ BCS đang hoạt động mới được gọi (`onlyActiveBCS`).
  - Kiểm tra số dư khả dụng thực tế qua `getAvailableClassFund()` và giữ chỗ an toàn qua biến `reservedSpendAmount` để chống chi vượt quỹ.
  - Phát sự kiện `SpendRequestCreated`.
- [x] **R4 & R5 — Biểu quyết dân chủ $\ge 51\%$, chống bỏ phiếu kép, thời hạn 7 ngày:**
  - Hàm `voteSpendRequest(requestId, support)`: Dành riêng cho thành viên BCS đang hoạt động.
  - Chống bỏ phiếu trùng (`AlreadyVoted(requestId, voter)`).
  - Tự động chuyển sang trạng thái `Ready` khi tỷ lệ phiếu thuận đạt $\ge 51\%$ (5,100 basis points) trên tổng số BCS hoạt động hiện hành.
  - Kiểm tra thời hạn 7 ngày (`VOTING_PERIOD = 7 days`): Chặn bỏ phiếu sau 7 ngày (`VotingPeriodEnded`).
  - Hàm `expireSpendRequest(requestId)`: Bất kỳ ai cũng có thể gọi sau 7 ngày để đánh dấu `Expired` nếu chưa đạt 51%, giải phóng số tiền giữ chỗ.
  - Phát sự kiện `SpendRequestVoted`, `SpendRequestReady`, `SpendRequestExpired`.
- [x] **R6 — Thực thi giải ngân an toàn tuân thủ CEI:**
  - Hàm `executeSpendRequest(requestId)`: Thành viên BCS gọi thực thi khi đề xuất đạt $\ge 51\%$.
  - Cập nhật trạng thái `Executed`, trừ `classFundBalance` và `reservedSpendAmount` TRƯỚC KHI chuyển ETH bằng `.call` (Checks-Effects-Interactions).
  - Chống thực thi lặp lại (`RequestAlreadyExecuted`).
  - Xử lý chuyển ETH thất bại đúng cách: nếu người nhận từ chối ETH hoặc độc hại, toàn bộ giao dịch revert (`ETHTransferFailed`), bảo toàn 100% kế toán.
  - Chống hoàn toàn Reentrancy: Trạng thái `Executed` được lưu trước khi gọi ngoài, triệt tiêu khả năng re-enter.
  - Phát sự kiện `SpendRequestExecuted(requestId, recipient, amount)`.
- [x] **Hàm tra cứu minh bạch (View / Getters):**
  - `getFundBalance()`: Số dư Quỹ lớp chính.
  - `getAvailableClassFund()`: Số dư khả dụng thực tế để tạo đề xuất chi mới.
  - `getTotalContractBalance()`: Tổng số dư ETH thực tế hiện có trong hợp đồng (`address(this).balance`).
  - `getStudentContribution(address student)`: Tổng đóng góp của sinh viên.
  - `getSpendRequest(requestId)`: Thông tin chi tiết đề xuất chi.
  - `hasMemberVoted(requestId, member)`: Kiểm tra trạng thái đã bỏ phiếu của thành viên BCS.

> [!NOTE]  
> **Lưu ý quan trọng về môi trường kiểm chứng:** Hợp đồng `ProjectCore.sol` tính đến hết Lab 13 **CHƯA ĐƯỢC TRIỂN KHAI (DEPLOY) LÊN MẠNG SEPOLIA TESTNET**. Mọi kết quả hoạt động hiện tại được kiểm chứng trên môi trường giả lập Python cục bộ (`test/test_economic_rules.py`), trình biên dịch `solc 0.8.37`, và máy ảo Remix VM (`test/ProjectCore_test.sol`). Việc triển khai on-chain lên Sepolia Testnet là mục tiêu chính thức của **Lab 15**.

### 2.2. Tính năng CHƯA TRIỂN KHAI (Kế hoạch các Lab tiếp theo):
- [ ] **Chức năng hoàn tiền an toàn cho sinh viên nộp nhầm (R7 tinh giản):** Kế hoạch thực hiện tại **Lab 14**.
- [ ] **Triển khai DApp Frontend kết nối MetaMask trên Sepolia Testnet:** Kế hoạch thực hiện tại **Lab 15**.
- [ ] **Các tính năng mở rộng v0.2 (Sau môn học):** Tải file ảnh minh chứng lên IPFS, hỗ trợ ERC-20 token (USDT/USDC).

---

## 3. Hướng dẫn kiểm tra và Chạy thử nghiệm thực tế

Dự án cung cấp tài liệu hướng dẫn cụ thể và tách biệt cho từng phương thức kiểm thử dựa trên các tệp thực tế hiện có trong repository:

### 3.1. Phương thức 1: Chạy kiểm thử tự động bằng Python

Tệp kiểm thử: `test/test_economic_rules.py`  
Mục đích: Kiểm tra tự động 100% logic kinh tế R1, R2, R11, R3, R4, R5, R6, cơ chế trích phí 1%, giữ chỗ quỹ chi tiêu, biểu quyết dân chủ $\ge 51\%$, chống bỏ phiếu kép, chống double-spending và mô phỏng gian lận.

- **Điều kiện môi trường cần có:**
  - Máy tính đã cài đặt **Python 3.10+** (đã kiểm tra tương thích trên Python 3.10, 3.11, 3.12, 3.13).
  - Sử dụng toàn bộ thư viện chuẩn của Python (`unittest`, `sys`, `typing`). **Không yêu cầu cài đặt thêm bất kỳ thư viện ngoài nào (không cần `pip install`)**.
- **Lệnh thực thi trong Terminal / PowerShell:**
  ```powershell
  python test/test_economic_rules.py
  ```
- **Kết quả thực tế quan sát được (15/15 ca ĐẠT):**
  ```text
  Ran 15 tests in 0.001s

  OK

  [Ca 1 - Nạp 1 ETH thành công]: Quỹ chính 0.99 ETH, Quỹ phí 0.01 ETH, bảo toàn số dư.
  [Ca 2 - Chặn nạp 0 ETH]: Revert ZeroAmount() thành công.
  [Ca 3 - Kênh nạp trực tiếp receive()]: Phân bổ 99%/1% chuẩn xác.
  [Ca 4 - Phép chia số nguyên & bảo toàn wei]: 99 wei (phí 0), 101 wei (phí 1).
  [Ca 5 - Kiểm tra chống gian lận & giá trị biên]: 100% giá trị biên bảo toàn số dư.
  [Ca 6 - Negative Test: Kênh receive() nạp 0 ETH]: Revert ZeroAmount().
  [Ca 7 - Đánh giá an toàn CEI luồng nạp]: Bất biến số dư được bảo toàn.
  [Ca 8 - R1: Phân quyền CVHT & BCS]: Chỉ CVHT được thêm/xóa BCS, chặn outsider thành công.
  [Ca 9 - R11: Rút phí vận hành]: CVHT rút phí thành công, Quỹ lớp 9.9 ETH được bảo toàn 100%.
  [Ca 10 - R3: Tạo đề xuất chi]: BCS tạo hợp lệ, giữ chỗ 2 ETH, chặn người ngoài và chi vượt ngân sách.
  [Ca 11 - R4/R5: Biểu quyết]: 1/3 (Pending), chặn double-voting, 2/3 >= 51% (Ready), chặn quá hạn 7 ngày.
  [Ca 12 - R6: Giải ngân & Bất biến kế toán]: Giải ngân thành công, chặn double-spending, bảo toàn bất biến.
  [Ca 13 - R11: Rollback khi chuyển phí thất bại]: adminFeePool được bảo toàn nguyên vẹn.
  [Ca 14 - R3: Giữ chỗ đa đề xuất]: Ngăn chặn thành công việc nhiều đề xuất chi vượt ngân sách.
  [Ca 15 - R5/R9: Đánh dấu Expired giải phóng tiền giữ chỗ]: 4 ETH giữ chỗ được giải phóng về quỹ khả dụng.
  ```

### 3.2. Phương thức 2: Chạy kiểm thử đơn vị Solidity bằng Remix VM

Tệp kiểm thử: `test/ProjectCore_test.sol` (kèm `test/VulnerableBank_test.sol` cho thực nghiệm Reentrancy Lab 13)  
Bản chất tệp: Đây là các **Solidity Test Contract** chuyên dụng được viết riêng cho plugin **Solidity Unit Testing** của Remix IDE. Tệp chứa hàm `beforeEach()` tự động khởi tạo môi trường trước mỗi ca kiểm thử và bộ **27 hàm kiểm thử** thuộc 7 nhóm (Nhóm A đến Nhóm G) trên `ProjectCoreTest`.

- **Hướng dẫn từng bước thực hiện trên Remix IDE:**
  1. Mở trình duyệt web và truy cập: [https://remix.ethereum.org](https://remix.ethereum.org).
  2. Tại bảng điều khiển File Explorer của Remix, tải lên các tệp theo đúng cấu trúc:
     - `contracts/project/ProjectCore.sol`
     - `test/ProjectCore_test.sol`
     - `contracts/training/VulnerableBank.sol`
     - `test/VulnerableBank_test.sol`
  3. Mở tab **Solidity Compiler** (icon thứ 3 ở thanh bên trái):
     - Chọn compiler: `0.8.20` hoặc cao hơn.
     - Nhấn **Compile ProjectCore.sol**. Xác nhận xuất hiện dấu tích xanh.
  4. Mở plugin **Solidity Unit Testing**:
     - Chọn tệp `test/ProjectCore_test.sol`.
     - Nhấn nút màu xanh **Run** để thực thi 27 hàm kiểm thử trên **Remix VM (Cancun / Shanghai)**.
  5. **Danh mục 27 hàm kiểm thử được thiết kế trong `ProjectCore_test.sol`:**
     - **Nhóm A — R2: Nạp tiền & Phân bổ 99%/1% (4 hàm):**
       - `testGroupA1_Deposit1ETH_Split99_1`: Nạp 1 ETH phân bổ chuẩn 0.99 ETH và 0.01 ETH.
       - `testGroupA2_DirectReceive`: Kênh nạp trực tiếp qua `receive()` hoạt động chuẩn.
       - `testGroupA3_ZeroAmountReverts`: Nạp 0 ETH vào `deposit()` và `receive()` bị revert `ZeroAmount()`.
       - `testGroupA4_IntegerMathEdgeCases`: Bảo toàn số dư cho khoản nạp 99 wei và 101 wei.
     - **Nhóm B — R1: Phân quyền CVHT & Quản trị BCS (4 hàm):**
       - `testGroupB1_AdvisorAddAndRemoveBCS`: CVHT thêm và xóa BCS, cập nhật `activeBCSCount`.
       - `testGroupB2_NonAdvisorCannotSetBCS`: Người ngoài cố thay đổi BCS bị revert `NotAdvisor()`.
       - `testGroupB3_ZeroAddressBCSReverts`: Thêm địa chỉ zero bị revert `InvalidAddress()`.
       - `testGroupB4_DisabledBCSCannotAct`: BCS vô hiệu hóa không thể tạo đề xuất (`NotActiveBCS()`).
     - **Nhóm C — R11: Rút phí vận hành (5 hàm):**
       - `testGroupC1_AdvisorWithdrawValidFee`: CVHT rút phí hợp lệ, Quỹ lớp 9.9 ETH không đổi.
       - `testGroupC2_NonAdvisorCannotWithdrawFee`: Người ngoài cố rút phí bị revert `NotAdvisor()`.
       - `testGroupC3_CannotWithdrawExceedingFeePool`: Rút vượt số dư phí bị revert `InsufficientAdminFee()`.
       - `testGroupC4_CannotWithdrawZeroFee`: Rút 0 ETH bị revert `ZeroAmount()`.
       - `testGroupC5_RejectingAdvisorWithdrawFeeRevertsAndRollsBack`: Ví nhận phí từ chối ETH thì revert và rollback `adminFeePool`.
     - **Nhóm D — R3: Tạo đề xuất chi tiêu & Giữ chỗ (4 hàm):**
       - `testGroupD1_ActiveBCSCreateSpendRequest`: BCS tạo đề xuất hợp lệ, giữ chỗ số dư `reservedSpendAmount`.
       - `testGroupD2_NonBCSCannotCreateRequest`: Người ngoài cố tạo đề xuất bị revert `NotActiveBCS()`.
       - `testGroupD3_ZeroRecipientOrAmountOrExceedingFundReverts`: Chặn recipient zero, amount 0, amount vượt quỹ.
       - `testGroupD4_MultipleRequestsCannotExceedAvailableFund`: Nhiều đề xuất không thể giữ chỗ vượt quá số dư khả dụng.
     - **Nhóm E — R4/R5: Biểu quyết & Ngưỡng 51% (4 hàm):**
       - `testGroupE1_VoteYesAndNo_AndDoubleVotingReverts`: Bỏ phiếu YES/NO, chặn double-voting, đạt 51% tự động Ready.
       - `testGroupE2_NonBCSCannotVote`: Người ngoài cố bỏ phiếu bị revert `NotActiveBCS()`.
       - `testGroupE3_DynamicBCSDenominator`: Mẫu số biểu quyết cập nhật động khi xóa thành viên ngừng hoạt động.
       - `testGroupE4_ExpireBeforeVotingPeriodReverts`: Gọi expire khi trong thời hạn 7 ngày bị revert `VotingStillActive()`.
     - **Nhóm F — R6: Giải ngân & An ninh chuyển tiền CEI (5 hàm):**
       - `testGroupF1_ExecuteSuccessfulWhenThresholdMet`: Giải ngân thành công khi đạt 51%.
       - `testGroupF2_CannotExecuteWithoutThreshold`: Chưa đạt 51% không thể giải ngân.
       - `testGroupF3_DoubleExecutionReverts`: Chống thực thi kép (`RequestAlreadyExecuted()`).
       - `testGroupF4_ExecuteRevertsIfRecipientRefusesETH`: Người nhận từ chối ETH thì revert bảo toàn toàn bộ trạng thái.
       - `testGroupF5_ReentrancyDuringExecuteIsBlockedByCEI`: Chống Reentrancy khi giải ngân nhờ CEI, kiểm chứng với attacker có quyền BCS.
     - **Nhóm G — Bất biến kế toán (1 hàm):**
       - `testGroupG1_AccountingConservationAndIsolation`: Bảo toàn số dư tổng thể và cách ly 2 quỹ.

> [!NOTE]
> **Trạng thái thực tế:** Bộ 27 hàm kiểm thử Solidity trên đã được biên dịch thành công 100% bằng `npx solc 0.8.37`. Do không dùng framework dòng lệnh nặng như Hardhat/Foundry, kết quả thực thi các hàm kiểm thử này được ghi nhận trực quan khi sinh viên nhấn nút **Run** trong giao diện Remix IDE.

### 3.3. Phương thức 3: Kiểm tra biên dịch cục bộ bằng trình biên dịch Solc

- **Lệnh thực thi trong PowerShell / Terminal:**
  ```powershell
  npx solc --bin contracts/project/ProjectCore.sol test/ProjectCore_test.sol
  ```
- **Kết quả thực tế:** Trình biên dịch `solc 0.8.37` hoàn thành với mã thoát `0` (Exit code: 0), xác nhận không có bất kỳ lỗi cú pháp nào trong hợp đồng chính `ProjectCore.sol` và tệp kiểm thử `ProjectCore_test.sol`.

---

## 4. Bảng tổng hợp đối chiếu kết quả kiểm thử (Expected vs Observed)

| Ca kiểm thử | Quy tắc / Kịch bản | Dữ liệu đầu vào | Kết quả mong đợi (Expected) | Kết quả thực tế quan sát được (Observed) | Trạng thái |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Ca 1** | R2: Nạp 1 ETH | `1 ether` | Quỹ lớp tăng 0.99 ETH; `adminFeePool` tăng 0.01 ETH; đóng góp 1 ETH. | Khớp 100%: Quỹ chính: 0.99 ETH, Phí: 0.01 ETH, Đóng góp: 1.0 ETH. | **ĐẠT (PASS)** |
| **Ca 2** | R2: Nạp 0 ETH | `0 ether` | Revert `ZeroAmount()`, không lưu vết số dư rác. | Revert đúng mã lỗi `ZeroAmount()`, trạng thái giữ nguyên hoàn toàn. | **ĐẠT (PASS)** |
| **Ca 3** | R2: Nạp qua `receive()` | `0.5 ether` | Phân bổ 99% ($0.495$ ETH) và 1% ($0.005$ ETH). | Khớp 100%: Phân bổ đúng 0.495 ETH và 0.005 ETH. | **ĐẠT (PASS)** |
| **Ca 4** | R2: Số nguyên biên | 99 wei & 101 wei | 99 wei: Phí 0 wei, Quỹ 99 wei; 101 wei: Phí 1 wei, Quỹ 100 wei. | Khớp 100%: Tổng số dư bảo toàn tuyệt đối, không tràn số. | **ĐẠT (PASS)** |
| **Ca 5** | R2: Chống gian lận | 0 wei & 8 giá trị biên | Chặn gửi 0 ETH; bảo toàn 100% wei trên mọi giá trị biên. | Bị chặn bởi `ZeroAmount()`; 8 giá trị biên đều bảo toàn 100% wei. | **ĐẠT (PASS)** |
| **Ca 6** | R2: Negative test `receive()` | `0 ether` | Revert `ZeroAmount()`. | Revert đúng `ZeroAmount()`. | **ĐẠT (PASS)** |
| **Ca 7** | R2: An toàn CEI luồng nạp | 2 ETH | Không có external call hướng ngoại, Reentrancy bất khả thi. | Trạng thái cập nhật trước; Reentrancy bất khả thi. | **ĐẠT (PASS)** |
| **Ca 8** | R1: Quản trị BCS | Thêm 2 BCS, xóa 1 BCS | Chỉ CVHT sửa được; chặn địa chỉ zero; chặn outsider. | Khớp 100%: `activeBCSCount` cập nhật đúng; outsider bị chặn. | **ĐẠT (PASS)** |
| **Ca 9** | R11: Rút phí vận hành | Rút 0.04 ETH từ pool 0.1 ETH | Rút phí thành công; Quỹ lớp 9.9 ETH không đổi; chặn outsider. | Khớp 100%: `adminFeePool` giảm còn 0.06 ETH; quỹ chính giữ nguyên 9.9 ETH. | **ĐẠT (PASS)** |
| **Ca 10** | R3: Tạo đề xuất chi | Đề xuất 2 ETH | Giữ chỗ 2 ETH (`reservedSpendAmount`), giảm quỹ khả dụng. | Khớp 100%: Giữ chỗ 2 ETH, khả dụng còn 7.9 ETH, chặn chi vượt quỹ. | **ĐẠT (PASS)** |
| **Ca 11** | R4/R5: Biểu quyết $\ge 51\%$ | 3 BCS bỏ phiếu | Chặn double vote; 2/3 phiếu thuận $\ge 51\%$ tự động sang Ready. | Khớp 100%: Chặn double-voting; tự động chuyển sang Ready khi đủ 51%. | **ĐẠT (PASS)** |
| **Ca 12** | R6: Giải ngân & Bất biến | Giải ngân 3 ETH khi đủ 51% | Tiền chuyển thành công; chặn double execution; bảo toàn kế toán. | Khớp 100%: Quỹ chính giảm đúng 3 ETH; chặn double-spending. | **ĐẠT (PASS)** |
| **Ca 13** | R11: Rollback rút phí | Ví nhận từ chối ETH | Revert `ETHTransferFailed()`, `adminFeePool` rollback nguyên vẹn. | Khớp 100%: `adminFeePool` giữ nguyên 0.1 ETH sau revert. | **ĐẠT (PASS)** |
| **Ca 14** | R3: Giữ chỗ đa đề xuất | 6 ETH + 5 ETH (vượt 9.9 ETH) | Đề xuất thứ 2 bị revert `InsufficientAvailableFund()`. | Khớp 100%: Không thể giữ chỗ vượt quỹ khả dụng. | **ĐẠT (PASS)** |
| **Ca 15** | R5/R9: Expire sau 7 ngày | Đề xuất quá hạn 7 ngày | Chuyển `Expired`, giải phóng số tiền giữ chỗ về quỹ khả dụng. | Khớp 100%: `reservedSpendAmount` về 0, quỹ khả dụng phục hồi 100%. | **ĐẠT (PASS)** |
| **Kiểm thử Sepolia** | On-chain public testnet | Sepolia ETH | Triển khai và tương tác on-chain qua MetaMask. | **CHƯA KIỂM THỬ** (Kế hoạch thực hiện tại Lab 15). | *Kế hoạch Lab 15* |
