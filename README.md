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

## 2. Hiện trạng mã nguồn và Phân định tính năng (Cập nhật sau Lab 14)

Để phản ánh chính xác tình trạng kỹ thuật sau **Lab 14 (Hoàn tiền an toàn R7 tinh giản, kiểm thử tích hợp chu trình 5 bước và tối ưu Gas)**, các tính năng được phân định rõ ràng giữa thực tế mã nguồn và lộ trình phát triển:

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
- [x] **R7 — Quy trình Hoàn tiền có Biểu quyết Ban Cán sự (Governance-Controlled Refund):**
  - **Khắc phục triệt để lỗ hổng rút tiền trực tiếp:** Loại bỏ hoàn toàn mọi cơ chế cho phép sinh viên tự gọi rút tiền mà không có sự biểu quyết và phê chuẩn từ Ban cán sự.
  - **Quy trình 3 bước kiểm soát nghiêm ngặt tương tự đề xuất chi tiêu:**
    1. **Bước 1 — Tạo yêu cầu hoàn tiền:** Hàm `createRefundRequest(uint256 amount, string memory reason)` cho phép sinh viên tạo yêu cầu nhận lại khoản tiền đã nộp nhầm.
       - Kiểm tra `amount > 0` (`ZeroAmount()`).
       - Kiểm tra `amount <= getStudentAvailableContribution(msg.sender)` (`InsufficientContribution`): Chỉ được yêu cầu trong hạn mức đóng góp khả dụng của chính mình sau khi trừ đi các yêu cầu hoàn tiền đang chờ duyệt (`pendingStudentRefundAmount`). Người lạ hoặc người chưa nộp tiền bị chặn (`available = 0`).
       - Kiểm tra `amount <= getAvailableClassFund()` (`InsufficientAvailableFund`): Không được yêu cầu vượt quá số dư quỹ khả dụng sau khi trừ cả khoản giữ chỗ chi tiêu lẫn hoàn tiền (`reservedSpendAmount + reservedRefundAmount`).
       - Áp dụng cơ chế **giữ chỗ kép** (Dual-layer Reservation): Đồng thời tăng `reservedRefundAmount += amount` (khóa quỹ lớp) và `pendingStudentRefundAmount[msg.sender] += amount` (khóa hạn mức đóng góp của sinh viên). Chặn tạo nhiều yêu cầu đồng thời vượt tổng hạn mức.
       - Không tự động chuyển ETH ra khỏi hợp đồng tại bước tạo yêu cầu.
       - Phát sự kiện `RefundRequestCreated(requestId, applicant, amount, reason)`.
    2. **Bước 2 — Ban cán sự biểu quyết:** Hàm `voteRefundRequest(uint256 requestId, bool support)` dành riêng cho thành viên BCS đang hoạt động (`onlyActiveBCS`).
       - Mỗi thành viên BCS chỉ được bỏ phiếu một lần duy nhất cho mỗi yêu cầu (`AlreadyVotedRefund(requestId, voter)`).
       - Thời hạn biểu quyết 7 ngày (`VOTING_PERIOD = 7 days`). Chặn bỏ phiếu sau 7 ngày (`RefundVotingPeriodEnded`).
       - Tự động chuyển sang trạng thái Sẵn sàng thực thi (`Ready`) khi đạt tỷ lệ đồng ý $\ge 51\%$ (5,100 basis points) trên tổng số BCS hoạt động hiện hành.
       - Dọn dẹp quá hạn: Hàm `expireRefundRequest(uint256 requestId)` cho phép bất kỳ ai giải phóng số tiền giữ chỗ kép về quỹ khả dụng nếu sau 7 ngày không đạt đủ 51% phiếu thuận.
       - Phát sự kiện `RefundRequestVoted`, `RefundRequestReady`, `RefundRequestExpired`.
    3. **Bước 3 — Thực thi hoàn tiền:** Hàm `executeRefundRequest(uint256 requestId)` giải ngân cho sinh viên.
       - Chỉ yêu cầu ở trạng thái `Ready` mới được thực thi (`InvalidRefundStatus`).
       - Xác minh lại hạn mức đóng góp và số dư quỹ lớp trước khi giải ngân.
       - Tuân thủ nghiêm ngặt nguyên tắc Checks-Effects-Interactions (CEI): Cập nhật `req.status = Executed`, trừ `studentContributions[applicant]`, trừ `classFundBalance`, giải phóng `reservedRefundAmount` và `pendingStudentRefundAmount[applicant]` TRƯỚC KHI chuyển ETH.
       - Chuyển ETH trực tiếp về chính địa chỉ của người yêu cầu (`req.applicant`) qua `.call{value: req.amount}("")`. Không ai có thể đổi địa chỉ nhận tiền.
       - Xử lý chuyển ETH thất bại: Revert `ETHTransferFailed()` và rollback 100% kế toán.
       - Chống Reentrancy và chống thực thi kép (`RefundAlreadyExecuted`).
       - Phát sự kiện `RefundRequestExecuted(requestId, applicant, amount)`.
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
> **Lưu ý quan trọng về môi trường kiểm chứng:** Hợp đồng `ProjectCore.sol` tính đến hết Lab 14 **CHƯA ĐƯỢC TRIỂN KHAI (DEPLOY) LÊN MẠNG SEPOLIA TESTNET**. Mọi kết quả hoạt động hiện tại được kiểm chứng trên môi trường giả lập Python cục bộ (`test/test_economic_rules.py`), trình biên dịch `solc 0.8.37`, và máy ảo Remix VM (`test/ProjectCore_test.sol` & `test/ProjectCore_integration_test.sol`). Việc triển khai on-chain lên Sepolia Testnet là mục tiêu chính thức của **Lab 15**.

### 2.2. Tính năng CHƯA TRIỂN KHAI (Kế hoạch các Lab tiếp theo):
- [ ] **Triển khai DApp Frontend kết nối MetaMask trên Sepolia Testnet:** Kế hoạch thực hiện tại **Lab 15**.
- [ ] **Các tính năng mở rộng v0.2 (Sau môn học):** Tải file ảnh minh chứng lên IPFS, hỗ trợ ERC-20 token (USDT/USDC).

---

## 3. Hướng dẫn kiểm tra và Chạy thử nghiệm thực tế

Dự án cung cấp tài liệu hướng dẫn cụ thể và tách biệt cho từng phương thức kiểm thử dựa trên các tệp thực tế hiện có trong repository:

### 3.1. Phương thức 1: Chạy kiểm thử tự động bằng Python

Tệp kiểm thử: `test/test_economic_rules.py`  
Mục đích: Kiểm tra tự động 100% logic kinh tế R1, R2, R11, R3, R4, R5, R6, R7 (hoàn tiền), toàn bộ chu trình 5 bước dòng tiền (Nạp → Biểu quyết → Chi → Hoàn tiền → Rút tiền), cơ chế trích phí 1%, giữ chỗ quỹ chi tiêu, biểu quyết dân chủ $\ge 51\%$, chống bỏ phiếu kép, chống double-spending và mô phỏng gian lận.

- **Điều kiện môi trường cần có:**
  - Máy tính đã cài đặt **Python 3.10+** (đã kiểm tra tương thích trên Python 3.10, 3.11, 3.12, 3.13).
  - Sử dụng toàn bộ thư viện chuẩn của Python (`unittest`, `sys`, `typing`). **Không yêu cầu cài đặt thêm bất kỳ thư viện ngoài nào (không cần `pip install`)**.
- **Lệnh thực thi trong Terminal / PowerShell:**
  ```powershell
  python test/test_economic_rules.py
  ```
- **Kết quả thực tế quan sát được (24/24 ca ĐẠT):**
  ```text
  Ran 24 tests in 0.007s

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
  [Ca 16 - R7: Hoàn tiền có biểu quyết]: Tạo yêu cầu -> BCS duyệt 2/3 -> Thực thi 4 ETH thành công, bảo toàn phí 0.1 ETH.
  [Ca 17 - R7 Negative: Hoàn tiền 0 wei]: Revert ZeroAmount() thành công.
  [Ca 18 - R7 Negative: Hoàn vượt đóng góp]: Revert InsufficientContribution() thành công.
  [Ca 19 - R7 Negative: Người ngoài xin hoàn tiền]: Chặn người chưa đóng góp thành công.
  [Ca 20 - R7 Negative: Hoàn vượt quỹ khả dụng]: Chặn hoàn tiền xâm lấn ngân sách đề xuất chi thành công.
  [Ca 21 - R7 Negative: Chặn yêu cầu kép vượt hạn mức]: Chặn tạo nhiều yêu cầu hoàn tiền vượt đóng góp thành công.
  [Ca 22 - R7 Biểu quyết]: Chặn người ngoài vote, chặn vote kép, xử lý hết hạn 7 ngày chuẩn xác.
  [Ca 23 - R7 Thực thi]: Chặn thực thi khi chưa đạt 51%, chặn thực thi kép thành công.
  [Ca 24 - Integration Test: Chu trình 5 bước có biểu quyết BCS]: Hoàn thành xuất sắc 100% chu trình (Nạp -> Biểu quyết chi -> Chi -> Yêu cầu hoàn -> BCS duyệt -> Hoàn -> Rút phí), bảo toàn tuyệt đối số dư.
  ```

### 3.2. Phương thức 2: Chạy kiểm thử đơn vị & tích hợp Solidity bằng Remix VM

Dự án cung cấp 2 bộ kiểm thử Solidity chuyên biệt được viết cho plugin **Solidity Unit Testing** của Remix IDE:
1. **Unit Test Suite:** `test/ProjectCore_test.sol` (27 hàm kiểm thử phân bổ qua 7 nhóm A đến G, kiểm thử chi tiết từng chức năng độc lập).
2. **Integration Test Suite:** `test/ProjectCore_integration_test.sol` (19 hàm kiểm thử, kiểm thử toàn bộ chu trình 5 bước dòng tiền: **Nạp → Biểu quyết → Chi → Hoàn tiền → Rút tiền**, các điều kiện biên & gian lận, và đo lường Gas tiêu thụ thực tế).
3. **Thực nghiệm Reentrancy (Lab 13):** `contracts/training/VulnerableBank.sol` và `test/VulnerableBank_test.sol`.

- **Hướng dẫn từng bước thực hiện trên Remix IDE:**
  1. Mở trình duyệt web và truy cập: [https://remix.ethereum.org](https://remix.ethereum.org).
  2. Tại bảng điều khiển File Explorer của Remix, tải lên các tệp theo đúng cấu trúc:
     - `contracts/project/ProjectCore.sol`
     - `test/ProjectCore_test.sol`
     - `test/ProjectCore_integration_test.sol`
     - `contracts/training/VulnerableBank.sol`
     - `test/VulnerableBank_test.sol`
  3. Mở tab **Solidity Compiler** (icon thứ 3 ở thanh bên trái):
     - Chọn compiler: `0.8.20` hoặc cao hơn (khuyên dùng `0.8.20` hoặc `0.8.37`).
     - Nhấn **Compile ProjectCore.sol**. Xác nhận xuất hiện dấu tích xanh.
  4. Mở plugin **Solidity Unit Testing**:
     - Chọn tệp `test/ProjectCore_test.sol` hoặc `test/ProjectCore_integration_test.sol`.
     - Nhấn nút màu xanh **Run** để thực thi bộ kiểm thử trên **Remix VM (Cancun / Shanghai)**.
  5. **Danh mục 27 hàm kiểm thử trong `test/ProjectCore_test.sol`:**
     - **Nhóm A — R2: Nạp tiền & Phân bổ 99%/1% (4 hàm):** `testGroupA1_Deposit1ETH_Split99_1`, `testGroupA2_DirectReceive`, `testGroupA3_ZeroAmountReverts`, `testGroupA4_IntegerMathEdgeCases`.
     - **Nhóm B — R1: Phân quyền CVHT & Quản trị BCS (4 hàm):** `testGroupB1_AdvisorAddAndRemoveBCS`, `testGroupB2_NonAdvisorCannotSetBCS`, `testGroupB3_ZeroAddressBCSReverts`, `testGroupB4_DisabledBCSCannotAct`.
     - **Nhóm C — R11: Rút phí vận hành (5 hàm):** `testGroupC1_AdvisorWithdrawValidFee`, `testGroupC2_NonAdvisorCannotWithdrawFee`, `testGroupC3_CannotWithdrawExceedingFeePool`, `testGroupC4_CannotWithdrawZeroFee`, `testGroupC5_RejectingAdvisorWithdrawFeeRevertsAndRollsBack`.
     - **Nhóm D — R3: Tạo đề xuất chi tiêu & Giữ chỗ (4 hàm):** `testGroupD1_ActiveBCSCreateSpendRequest`, `testGroupD2_NonBCSCannotCreateRequest`, `testGroupD3_ZeroRecipientOrAmountOrExceedingFundReverts`, `testGroupD4_MultipleRequestsCannotExceedAvailableFund`.
     - **Nhóm E — R4/R5: Biểu quyết & Ngưỡng 51% (4 hàm):** `testGroupE1_VoteYesAndNo_AndDoubleVotingReverts`, `testGroupE2_NonBCSCannotVote`, `testGroupE3_DynamicBCSDenominator`, `testGroupE4_ExpireBeforeVotingPeriodReverts`.
     - **Nhóm F — R6: Giải ngân & An ninh chuyển tiền CEI (5 hàm):** `testGroupF1_ExecuteSuccessfulWhenThresholdMet`, `testGroupF2_CannotExecuteWithoutThreshold`, `testGroupF3_DoubleExecutionReverts`, `testGroupF4_ExecuteRevertsIfRecipientRefusesETH`, `testGroupF5_ReentrancyDuringExecuteIsBlockedByCEI`.
     - **Nhóm G — Bất biến kế toán (1 hàm):** `testGroupG1_AccountingConservationAndIsolation`.
   6. **Danh mục 19 hàm kiểm thử trong `test/ProjectCore_integration_test.sol` (Lab 14 nâng cấp):**
      - **Chu trình dòng tiền khép kín 5 bước có biểu quyết BCS (1 hàm):**
        - `testIntegration_FullFiveStepLifecycle`: Khảo sát toàn bộ chu trình Nạp (15 ETH) → Biểu quyết chi (đạt 2/3) → Chi giải ngân (4 ETH) → Sinh viên tạo yêu cầu hoàn tiền (3 ETH) → BCS biểu quyết thông qua (2/3) → Thực thi hoàn tiền → Rút phí vận hành (0.1 ETH). Kiểm tra đối soát mọi biến trạng thái kế toán và `address(this).balance` sau từng bước.
      - **Nhóm A — Kiểm thử biên & Gian lận Tạo yêu cầu hoàn tiền (8 hàm):**
        - `testRefund_ZeroAmountReverts`: Chặn yêu cầu hoàn 0 wei (`ZeroAmount()`).
        - `testRefund_ExceedingContributionReverts`: Chặn yêu cầu hoàn vượt mức đóng góp của chính mình (`InsufficientContribution`).
        - `testRefund_NonContributorCannotRefund`: Người lạ/chưa nộp cố tạo yêu cầu hoàn tiền bị chặn (`InsufficientContribution`).
        - `testRefund_ExactMaximumBoundary`: Yêu cầu hoàn tiền chính xác bằng mức đóng góp tối đa đưa hạn mức khả dụng về 0.
        - `testRefund_DoubleRefundExceedingTotalReverts`: Chặn tạo nhiều yêu cầu hoàn tiền đồng thời vượt tổng hạn mức đóng góp.
        - `testRefund_ExceedingAvailableFundDueToReservedSpendReverts`: Chặn yêu cầu hoàn tiền xâm lấn quỹ đang giữ chỗ chi tiêu.
        - `testRefund_RejectingRecipientRollsBack`: Địa chỉ sinh viên từ chối ETH khi thực thi thì revert `ETHTransferFailed()` và rollback 100% kế toán.
        - `testRefund_ReentrancyBlockedByCEI`: Attacker gọi reentrancy trong lúc thực thi hoàn tiền bị triệt tiêu ngay bởi CEI.
      - **Nhóm B & C — Kiểm thử biên Biểu quyết & Thực thi (5 hàm):**
        - `testSpend_CannotExecuteWithoutThreshold`: Đề xuất chi chưa đủ 51% không thể giải ngân.
        - `testSpend_CannotExecuteTwice`: Chặn giải ngân 2 lần cho cùng một đề xuất chi (`RequestAlreadyExecuted`).
        - `testVoting_DoubleVotingReverts`: Chặn BCS bỏ phiếu lặp lại cho đề xuất chi (`AlreadyVoted`).
        - `testRefund_VotingAndExecutionRules`: Kiểm tra biểu quyết hoàn tiền: người ngoài không được vote, chặn vote trùng, chưa đạt 51% không được thực thi.
        - `testRefund_CannotExecuteTwice`: Chặn thực thi hoàn tiền hai lần cho cùng một yêu cầu (`RefundAlreadyExecuted`).
      - **Nhóm D — Kiểm thử nạp & Bảo toàn số dư (2 hàm):**
        - `testDeposit_MultipleDepositsFromSameAccountAccumulate`: Nộp nhiều lần từ cùng 1 tài khoản tích lũy chính xác cả đóng góp lẫn quỹ lớp.
        - `testAccounting_NoWeiLossAcrossAllOperations`: Kiểm tra bất biến số dư tổng thể, không thất thoát 1 wei nào.
      - **Đo lường Gas tiêu thụ (1 hàm):**
        - `testGas_MeasureAllFunctions`: Đo lường chi phí Gas thực tế cho cả 8 thao tác cốt lõi gồm tạo yêu cầu hoàn tiền, biểu quyết hoàn tiền và thực thi hoàn tiền.
> [!NOTE]
> **Trạng thái thực tế:** Cả 2 bộ kiểm thử Solidity (`ProjectCore_test.sol` gồm 27 hàm và `ProjectCore_integration_test.sol` gồm 19 hàm) đã được biên dịch thành công 100% bằng `npx solc 0.8.37`. Do không dùng framework dòng lệnh nặng như Hardhat/Foundry, kết quả thực thi các hàm kiểm thử này được ghi nhận trực quan khi sinh viên nhấn nút **Run** trong giao diện Remix IDE.

### 3.3. Phương thức 3: Kiểm tra biên dịch cục bộ bằng trình biên dịch Solc

- **Lệnh thực thi trong PowerShell / Terminal:**
  ```powershell
  npx solc --bin contracts/project/ProjectCore.sol test/ProjectCore_test.sol test/ProjectCore_integration_test.sol
  ```
- **Kết quả thực tế:** Trình biên dịch `solc 0.8.37` hoàn thành với mã thoát `0` (Exit code: 0), xác nhận không có bất kỳ lỗi cú pháp nào trong hợp đồng chính `ProjectCore.sol`, tệp kiểm thử đơn vị `ProjectCore_test.sol`, và tệp kiểm thử tích hợp `ProjectCore_integration_test.sol`.

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
| **Ca 16** | R7: Hoàn tiền có biểu quyết | Nộp 10 ETH, tạo yêu cầu 4 ETH, BCS duyệt 2/3, thực thi | Yêu cầu tạo thành công, BCS duyệt chuyển Ready, thực thi hoàn 4 ETH về ví. | Khớp 100%: Đóng góp giảm đúng 4 ETH, quỹ chính giảm đúng 4 ETH, phí giữ nguyên. | **ĐẠT (PASS)** |
| **Ca 17** | R7 Negative: Hoàn 0 wei | Yêu cầu hoàn 0 ETH | Revert `ZeroAmount()`, không biến đổi trạng thái. | Revert đúng mã lỗi `ZeroAmount()`. | **ĐẠT (PASS)** |
| **Ca 18** | R7 Negative: Hoàn vượt đóng góp | Nộp 10 ETH, xin hoàn 12 ETH | Revert `InsufficientContribution(12 ETH, 10 ETH)`. | Revert đúng `InsufficientContribution`, bảo vệ tài sản của quỹ. | **ĐẠT (PASS)** |
| **Ca 19** | R7 Negative: Người ngoài xin hoàn | Người ngoài nộp 0 ETH xin hoàn 1 ETH | Revert `InsufficientContribution(1 ETH, 0 ETH)`. | Revert đúng `InsufficientContribution`, chặn kẻ gian bòn rút quỹ. | **ĐẠT (PASS)** |
| **Ca 20** | R7 Negative: Hoàn vượt quỹ khả dụng | Đề xuất chi giữ chỗ 6 ETH, xin hoàn 5 ETH (khả dụng 3.9 ETH) | Revert `InsufficientAvailableFund()`, bảo vệ ngân sách chi tiêu đã duyệt. | Khớp 100%: Ngân sách giữ chỗ của đề xuất chi không bị xâm lấn. | **ĐẠT (PASS)** |
| **Ca 21** | R7 Negative: Yêu cầu kép vượt mức | Nộp 10 ETH, tạo yêu cầu 1 (6 ETH) rồi tạo yêu cầu 2 (5 ETH) | Yêu cầu 1 thành công (hạn mức còn 4 ETH); Yêu cầu 2 revert `InsufficientContribution`. | Chặn thành công yêu cầu kép; ngăn dùng trùng hạn mức đang chờ duyệt. | **ĐẠT (PASS)** |
| **Ca 22** | R7: Biểu quyết hoàn tiền | Outsider vote, vote trùng, quá hạn 7 ngày | Outsider bị revert; vote trùng revert; quá hạn 7 ngày revert và expire giải phóng giữ chỗ. | Khớp 100%: Kiểm soát biểu quyết chặt chẽ, dọn dẹp quá hạn giải phóng tiền. | **ĐẠT (PASS)** |
| **Ca 23** | R7: Thực thi hoàn tiền | Thực thi khi chưa đủ 51%, thực thi 2 lần | Chưa đủ 51% revert `InvalidRefundStatus`; thực thi 2 lần revert `RefundAlreadyExecuted`. | Khớp 100%: Chỉ thực thi khi được BCS thông qua, chặn thực thi kép tuyệt đối. | **ĐẠT (PASS)** |
| **Ca 24** | Integration: Chu trình 5 bước có biểu quyết BCS | Nạp (15 ETH) → Biểu quyết chi → Chi (4 ETH) → Yêu cầu hoàn (3 ETH) → BCS duyệt → Hoàn → Rút phí (0.1 ETH) | Hoàn thành toàn vẹn cả chu trình có biểu quyết BCS; bảo toàn 100% Wei không thất thoát. | Khớp 100%: Toàn bộ chu trình dòng tiền vận hành thông suốt qua biểu quyết BCS. | **ĐẠT (PASS)** |
| **Kiểm thử Sepolia** | On-chain public testnet | Sepolia ETH | Triển khai và tương tác on-chain qua MetaMask. | **CHƯA KIỂM THỬ** (Kế hoạch thực hiện tại Lab 15). | *Kế hoạch Lab 15* |
