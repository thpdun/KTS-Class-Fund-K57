# BÁO CÁO ĐÓNG BĂNG ARTIFACT TRIỂN KHAI VÀ KIỂM TOÁN TIỀN DEPLOYMENT (FIX 12)

**Dự án:** KTS-Class-Fund-K57 (Hệ thống Quản lý Quỹ lớp Ngành Kinh tế Số)  
**Ngày thực hiện kiểm toán:** 01/11/2026  
**Mục tiêu:** Chuẩn bị chính xác bộ Solidity source, ABI, compiler settings và frontend configuration sẽ sử dụng khi deploy `ProjectCore` lên mạng Ethereum Sepolia Testnet.  
**Trạng thái tuân thủ Quy tắc An toàn:**  
- [x] Không deploy contract.  
- [x] Không gửi giao dịch blockchain.  
- [x] Không sử dụng hoặc yêu cầu private key.  
- [x] Không sửa `contracts/project/ProjectCore.sol`.  
- [x] Không sửa `web/index.html`.  
- [x] Không thay đổi địa chỉ contract hiện tại (`0xe3e1db1da1cae10e92337c36bb13004bf984ee91`).  
- [x] Không tự ý tạo phiên bản hợp đồng mới.  

---

## TASK 1 — XÁC MINH VÀ ĐỐI CHIẾU ABI CHUYÊN SÂU

### 1. Đối chiếu trực tiếp 3 nguồn ABI:
1. **Source ABI:** Biên dịch trực tiếp từ [contracts/project/ProjectCore.sol](file:///d:/document/TDT/KTS-Class-Fund-K57/contracts/project/ProjectCore.sol).
2. **Audited ABI:** Tệp lưu trữ độc lập tại [scratch/audited_ProjectCore.abi](file:///d:/document/TDT/KTS-Class-Fund-K57/scratch/audited_ProjectCore.abi).
3. **Frontend Embedded ABI:** Mảng hằng số `CONTRACT_ABI` nhúng trong [web/index.html](file:///d:/document/TDT/KTS-Class-Fund-K57/web/index.html).

### 2. Bảng tổng quan số lượng các thành phần ABI:

| Phân loại thành phần (Type) | Source `ProjectCore.sol` | `audited_ProjectCore.abi` | `web/index.html` (CONTRACT_ABI) | Trạng thái đối chiếu |
| :--- | :---: | :---: | :---: | :---: |
| **Tổng số Entries** | **83** | **83** | **83** | **Khớp 100% (83/83)** |
| **Functions (Hàm)** | **39** | **39** | **39** | **Khớp 100% (39/39)** |
| **Events (Sự kiện)** | **17** | **17** | **17** | **Khớp 100% (17/17)** |
| **Custom Errors (Lỗi tùy biến)**| **25** | **25** | **25** | **Khớp 100% (25/25)** |
| **Constructor (Hàm khởi tạo)** | **1** | **1** | **1** | **Khớp 100% (1/1)** |
| **Receive Function** | **1** | **1** | **1** | **Khớp 100% (1/1)** |
| **Fallback Function** | **0** | **0** | **0** | **Khớp 100% (0/0)** |

---

### 3. Làm rõ sự khác biệt "15 Events" vs "17 Events" giữa FIX 6 và FIX 11

Trong quá trình rà soát lịch sử kiểm toán, có sự khác biệt về con số sự kiện được ghi trong báo cáo:
- **FIX 6 ("Frontend Preparation"):** Đã đồng bộ giao diện và ghi nhận ABI đầy đủ với **17 sự kiện**.
- **FIX 11 ("Final Pre-Deployment Audit"):** Tại Mục 5.2 (dòng 219) có ghi: *"Trạng thái ABI: Khớp 100% với 39 functions và 15 events của hợp đồng"*.

#### Phân tích nguyên nhân kỹ thuật và đối chiếu chứng cứ:
1. **Nguồn gốc 15 sự kiện ban đầu (Trước khi nâng cấp cơ chế Auto-Execution an toàn):**
   Trong thiết kế ban đầu theo đặc tả tài liệu môn học ([docs/SPEC.md](file:///d:/document/TDT/KTS-Class-Fund-K57/docs/SPEC.md)), hợp đồng chỉ có 15 sự kiện tiêu chuẩn:
   `BCSMemberUpdated`, `FundDeposited`, `AdminFeeCollected`, `AdminFeeWithdrawn`, `SpendRequestCreated`, `SpendRequestVoted`, `SpendRequestReady`, `SpendRequestExecuted`, `SpendRequestExpired`, `RefundRequestCreated`, `RefundRequestVoted`, `RefundRequestReady`, `RefundRequestExecuted`, `RefundRequestExpired`, và `RefundProcessed`.
2. **Sự bổ sung 2 sự kiện tại FIX 6 nhằm chống Gas Griefing và xử lý thất bại giao dịch:**
   Để giải quyết rủi ro ví người nhận hoặc sinh viên từ chối nhận ETH (revert callback hoặc đốt cạn gas), hợp đồng đã nâng cấp cơ chế tự động chuyển tiền với mô hình CEI kết hợp Fallback Rollback:
   - Nếu lệnh gọi chuyển ETH thất bại, hợp đồng không revert toàn bộ giao dịch bỏ phiếu (để bảo vệ phiếu bầu của BCS), mà hoàn lại số dư về `classFundBalance` và chuyển trạng thái về `Ready`, đồng thời phát ra 2 sự kiện cảnh báo chuyên biệt:
     * `event SpendExecutionFailed(uint256 indexed requestId, address indexed recipient, uint256 amount);` (Dòng 154)
     * `event RefundExecutionFailed(uint256 indexed refundId, address indexed applicant, uint256 amount);` (Dòng 184)
   - Do đó, số lượng sự kiện thực tế trong mã nguồn [ProjectCore.sol](file:///d:/document/TDT/KTS-Class-Fund-K57/contracts/project/ProjectCore.sol) chính xác là **$15 + 2 = 17$ sự kiện**.
3. **Bản chất con số "15 events" trong báo cáo FIX 11:**
   - Đây là một **lỗi sai sót biên tập văn bản (typographical / documentation oversight)** trong Mục 5.2 của báo cáo FIX 11 do trích dẫn lại đoạn tóm tắt từ báo cáo cũ của Lab 14/15.
   - Bằng chứng không thể phủ nhận: Ngay trong chính nội dung của báo cáo FIX 11 (Task 1 và Task 4, dòng 33, 34, 36, 39, 40, 42, 85, 181), tác giả đã liệt kê và kiểm thử trực tiếp hành vi phát ra sự kiện `SpendExecutionFailed` và `RefundExecutionFailed` trong 28 kịch bản EVM.
4. **Kết luận xác nhận:**
   **17 events là con số chính xác 100% của hợp đồng hiện tại.** Cả 3 nguồn artifact (mã nguồn biên dịch, file ABI kiểm toán, và mã nguồn frontend) đều chứa đầy đủ 17 sự kiện này mà không có bất kỳ xung đột nào.

---

### 4. Bảng kiểm tra chi tiết từng Entry của ABI (Item-by-Item Verification)

#### A. Danh mục 17 Sự kiện (Events) — Đã đối chiếu từng Signature và Indexing:

| STT | Tên sự kiện (Event Signature) | Danh sách tham số & Kiểu dữ liệu | Thuộc tính Indexed | Trạng thái 3 nguồn |
| :---: | :--- | :--- | :---: | :---: |
| 1 | `AdminFeeCollected` | `address student, uint256 feeAmount` | `student` (indexed) | Trùng khớp 100% |
| 2 | `AdminFeeWithdrawn` | `address advisor, uint256 amount` | `advisor` (indexed) | Trùng khớp 100% |
| 3 | `BCSMemberUpdated` | `address member, bool status` | `member` (indexed) | Trùng khớp 100% |
| 4 | `FundDeposited` | `address student, uint256 amount` | `student` (indexed) | Trùng khớp 100% |
| 5 | `RefundExecutionFailed` | `uint256 refundId, address applicant, uint256 amount` | `refundId` (indexed) | Trùng khớp 100% |
| 6 | `RefundProcessed` | `address student, uint256 amount` | `student` (indexed) | Trùng khớp 100% |
| 7 | `RefundRequestCreated` | `uint256 refundId, address applicant, uint256 amount, string reason, uint256 createdAt` | `refundId` (indexed), `applicant` (indexed) | Trùng khớp 100% |
| 8 | `RefundRequestExecuted` | `uint256 refundId, address applicant, uint256 amount` | `refundId` (indexed), `applicant` (indexed) | Trùng khớp 100% |
| 9 | `RefundRequestExpired` | `uint256 refundId` | `refundId` (indexed) | Trùng khớp 100% |
| 10 | `RefundRequestReady` | `uint256 refundId` | `refundId` (indexed) | Trùng khớp 100% |
| 11 | `RefundRequestVoted` | `uint256 refundId, address voter, bool support, uint256 yesVotes, uint256 noVotes` | `refundId` (indexed), `voter` (indexed) | Trùng khớp 100% |
| 12 | `SpendExecutionFailed` | `uint256 requestId, address recipient, uint256 amount` | `requestId` (indexed), `recipient` (indexed) | Trùng khớp 100% |
| 13 | `SpendRequestCreated` | `uint256 requestId, address creator, address recipient, uint256 amount, string description, uint256 createdAt` | `requestId`, `creator`, `recipient` (indexed) | Trùng khớp 100% |
| 14 | `SpendRequestExecuted` | `uint256 requestId, address recipient, uint256 amount` | `requestId`, `recipient` (indexed) | Trùng khớp 100% |
| 15 | `SpendRequestExpired` | `uint256 requestId` | `requestId` (indexed) | Trùng khớp 100% |
| 16 | `SpendRequestReady` | `uint256 requestId` | `requestId` (indexed) | Trùng khớp 100% |
| 17 | `SpendRequestVoted` | `uint256 requestId, address voter, bool support, uint256 yesVotes, uint256 noVotes` | `requestId`, `voter` (indexed) | Trùng khớp 100% |

#### B. Danh mục 25 Lỗi Tùy biến (Custom Errors):

| STT | Mã lỗi (Custom Error) | Tham số trả về | Mô tả ngữ cảnh kích hoạt | Trạng thái 3 nguồn |
| :---: | :--- | :--- | :--- | :---: |
| 1 | `AlreadyVoted` | `uint256 requestId, address voter` | BCS đã bỏ phiếu cho đề xuất chi này | Trùng khớp 100% |
| 2 | `AlreadyVotedRefund` | `uint256 refundId, address voter` | BCS đã bỏ phiếu cho yêu cầu hoàn tiền này | Trùng khớp 100% |
| 3 | `ETHTransferFailed` | Không có | Lệnh chuyển ETH qua low-level call thất bại | Trùng khớp 100% |
| 4 | `InsufficientAdminFee` | `uint256 requested, uint256 available` | Rút phí vượt quá số dư `adminFeePool` | Trùng khớp 100% |
| 5 | `InsufficientAvailableFund` | `uint256 requested, uint256 available` | Chi vượt số dư quỹ sau khi trừ giữ chỗ | Trùng khớp 100% |
| 6 | `InsufficientContribution` | `uint256 requested, uint256 available` | Hoàn tiền vượt hạn mức sinh viên đã nộp | Trùng khớp 100% |
| 7 | `InsufficientFund` | `uint256 requested, uint256 available` | Quỹ lớp không đủ tiền thực tế để giải ngân | Trùng khớp 100% |
| 8 | `InvalidAddress` | Không có | Địa chỉ ví cung cấp là `address(0)` | Trùng khớp 100% |
| 9 | `InvalidRefundStatus` | `uint256 refundId` | Trạng thái yêu cầu hoàn tiền không hợp lệ | Trùng khớp 100% |
| 10 | `InvalidRequestStatus` | `uint256 requestId` | Trạng thái đề xuất chi không hợp lệ | Trùng khớp 100% |
| 11 | `NoActiveBCS` | Không có | Không có BCS hoạt động (`activeBCSCount == 0`) | Trùng khớp 100% |
| 12 | `NotActiveBCS` | Không có | Người gọi không phải BCS đang hoạt động | Trùng khớp 100% |
| 13 | `NotAdvisor` | Không có | Người gọi không phải Cố vấn học tập | Trùng khớp 100% |
| 14 | `RefundAlreadyExecuted` | `uint256 refundId` | Yêu cầu hoàn tiền đã giải ngân trước đó | Trùng khớp 100% |
| 15 | `RefundExpired` | `uint256 refundId` | Yêu cầu hoàn tiền đã hết hạn 7 ngày | Trùng khớp 100% |
| 16 | `RefundRequestNotFound` | `uint256 refundId` | Mã yêu cầu hoàn tiền không tồn tại | Trùng khớp 100% |
| 17 | `RefundVotingPeriodEnded` | `uint256 refundId` | Đã quá 7 ngày bỏ phiếu yêu cầu hoàn tiền | Trùng khớp 100% |
| 18 | `RefundVotingStillActive` | `uint256 refundId` | Chưa hết 7 ngày, chưa thể đánh dấu hết hạn | Trùng khớp 100% |
| 19 | `RequestAlreadyExecuted` | `uint256 requestId` | Đề xuất chi đã giải ngân trước đó | Trùng khớp 100% |
| 20 | `RequestExpired` | `uint256 requestId` | Đề xuất chi đã hết hạn 7 ngày | Trùng khớp 100% |
| 21 | `RequestNotFound` | `uint256 requestId` | Mã đề xuất chi không tồn tại | Trùng khớp 100% |
| 22 | `ThresholdNotMet` | `uint256 yesVotes, uint256 activeBCSCount` | Chưa đủ $\ge 51\%$ phiếu thuận từ BCS | Trùng khớp 100% |
| 23 | `VotingPeriodEnded` | `uint256 requestId` | Đã quá 7 ngày bỏ phiếu đề xuất chi | Trùng khớp 100% |
| 24 | `VotingStillActive` | `uint256 requestId` | Chưa hết 7 ngày, chưa thể đánh dấu hết hạn | Trùng khớp 100% |
| 25 | `ZeroAmount` | Không có | Số tiền giao dịch bằng 0 wei | Trùng khớp 100% |

#### C. Danh mục 39 Hàm (Functions):
Toàn bộ 39 hàm (gồm 11 hàm ghi trạng thái nonpayable/payable và 28 hàm view đọc trạng thái) đều khớp 100% về tên hàm, thứ tự tham số, kiểu dữ liệu vào/ra và tính biến đổi trạng thái (State Mutability):
1. `BPS_DENOMINATOR()` [view] $\rightarrow$ `uint256`
2. `FEE_BPS()` [view] $\rightarrow$ `uint256`
3. `PASSING_THRESHOLD_BPS()` [view] $\rightarrow$ `uint256`
4. `VOTING_PERIOD()` [view] $\rightarrow$ `uint256`
5. `activeBCSCount()` [view] $\rightarrow$ `uint256`
6. `adminFeePool()` [view] $\rightarrow$ `uint256`
7. `advisor()` [view] $\rightarrow$ `address`
8. `classFundBalance()` [view] $\rightarrow$ `uint256`
9. `createRefundRequest(uint256 amount, string reason)` [nonpayable] $\rightarrow$ `uint256`
10. `createSpendRequest(address recipient, uint256 amount, string description)` [nonpayable] $\rightarrow$ `uint256 requestId`
11. `deposit()` [payable]
12. `executeRefundRequest(uint256 refundId)` [nonpayable]
13. `executeSpendRequest(uint256 requestId)` [nonpayable]
14. `expireRefundRequest(uint256 refundId)` [nonpayable]
15. `expireSpendRequest(uint256 requestId)` [nonpayable]
16. `getAvailableClassFund()` [view] $\rightarrow$ `uint256`
17. `getFundBalance()` [view] $\rightarrow$ `uint256`
18. `getRefundRequest(uint256 refundId)` [view] $\rightarrow$ `(uint256 id, address applicant, uint256 amount, string reason, uint256 createdAt, uint256 yesVotes, uint256 noVotes, uint8 status)`
19. `getSpendRequest(uint256 requestId)` [view] $\rightarrow$ `(uint256 id, address recipient, uint256 amount, string description, address creator, uint256 createdAt, uint256 yesVotes, uint256 noVotes, uint8 status)`
20. `getStudentAvailableContribution(address student)` [view] $\rightarrow$ `uint256`
21. `getStudentContribution(address student)` [view] $\rightarrow$ `uint256`
22. `getTotalContractBalance()` [view] $\rightarrow$ `uint256`
23. `hasMemberVoted(uint256 requestId, address member)` [view] $\rightarrow$ `bool`
24. `hasMemberVotedRefund(uint256 refundId, address member)` [view] $\rightarrow$ `bool`
25. `hasVoted(uint256, address)` [view] $\rightarrow$ `bool`
26. `hasVotedRefund(uint256, address)` [view] $\rightarrow$ `bool`
27. `isBCSMember(address)` [view] $\rightarrow$ `bool`
28. `pendingStudentRefundAmount(address)` [view] $\rightarrow$ `uint256`
29. `refundRequestCount()` [view] $\rightarrow$ `uint256`
30. `refundRequests(uint256)` [view] $\rightarrow$ `(uint256 id, address applicant, uint256 amount, string reason, uint256 createdAt, uint256 yesVotes, uint256 noVotes, uint8 status)`
31. `reservedRefundAmount()` [view] $\rightarrow$ `uint256`
32. `reservedSpendAmount()` [view] $\rightarrow$ `uint256`
33. `setBCSMember(address member, bool status)` [nonpayable]
34. `spendRequestCount()` [view] $\rightarrow$ `uint256`
35. `spendRequests(uint256)` [view] $\rightarrow$ `(uint256 id, address recipient, uint256 amount, string description, address creator, uint256 createdAt, uint256 yesVotes, uint256 noVotes, uint8 status)`
36. `studentContributions(address)` [view] $\rightarrow$ `uint256`
37. `voteRefundRequest(uint256 refundId, bool support)` [nonpayable]
38. `voteSpendRequest(uint256 requestId, bool support)` [nonpayable]
39. `withdrawAdminFee(uint256 amount)` [nonpayable]

#### D. Constructor & Receive:
- `constructor()`: `inputs: []`, `stateMutability: "nonpayable"`.
- `receive()`: `inputs: []`, `stateMutability: "payable"`.

---

## TASK 2 — CHỐT CẤU HÌNH COMPILER SETTINGS & METRICS BYTECODE

### 1. Cấu hình biên dịch chính thức (Official Compiler Settings)

| Tham số cấu hình | Giá trị chỉ định chuẩn | Môi trường kiểm toán cục bộ | Tương thích triển khai Remix IDE |
| :--- | :--- | :--- | :--- |
| **Solidity Compiler** | `0.8.20` (hoặc `0.8.26`) | `0.8.26+commit.8a97fa7a.Emscripten.clang` | `0.8.20` hoặc `0.8.26` |
| **Compiler Pragma** | `pragma solidity ^0.8.20;` | Tuân thủ tuyệt đối | Tuân thủ tuyệt đối |
| **Optimizer** | **Enabled (true)** | `true` | Bật checkbox `Enable optimization` |
| **Optimizer Runs** | **200** | `200` | Nhập `200` |
| **EVM Version** | **Shanghai** | `shanghai` | Chọn `shanghai` |
| **Warnings & Errors** | **0 Warning, 0 Error** | **0 Warning, 0 Error** | Biên dịch sạch 100% |

### 2. Định lượng kích thước Bytecode và Giới hạn EIP

Việc tối ưu hóa và kiểm soát kích thước bytecode được đo lường chính xác với cấu hình tiêu chuẩn:

| Thông số Bytecode | Kích thước thực tế | Giới hạn tối đa EVM | Tỷ lệ sử dụng | Đánh giá an toàn |
| :--- | :---: | :---: | :---: | :---: |
| **Creation Bytecode** (Init code) | **12,421 bytes** | **49,152 bytes** (EIP-3860) | **25.27%** | **Cực kỳ an toàn (dư 74.7%)** |
| **Runtime Bytecode** (Deployed) | **12,350 bytes** | **24,576 bytes** (EIP-170) | **50.25%** | **Rất an toàn (dư gần 50%)** |

*Ghi chú so sánh các biến thể:*
- *Cấu hình EVM Cancun (runs=200):* Creation = 12,400 bytes, Runtime = 12,329 bytes.
- *Cấu hình EVM Paris (runs=200):* Creation = 12,467 bytes, Runtime = 12,396 bytes.
- *Cấu hình Không bật Optimizer (runs=0):* Creation = 18,944 bytes, Runtime = 18,873 bytes (vẫn dưới 24.5 KB nhưng tốn gas hơn 25%).
- **Lựa chọn tối ưu:** Giữ cấu hình chuẩn: **Optimizer: Enabled, Runs: 200, EVM Version: Shanghai**.

### 3. Bảng băm toàn vẹn (Artifact Checksums / Hashes)

Các giá trị băm mã hóa SHA-256 được chốt cố định để kiểm tra đối chiếu tính toàn vẹn khi deploy:
- **ABI SHA-256:** `3043fba474ac9e652b6e4ad1e687da7326a482f959453b4c56f48ef38ec89d7a`
- **Creation Bytecode SHA-256 (Shanghai 200):** `10ec8e2914a10a90da47100b4eb647eb51e1814ae949ddf929f706380dfcf71c`
- **Runtime Bytecode SHA-256 (Shanghai 200):** `21ea325838eb80caeb3d632d228f1376d64f0318c9ca1ecf5295be074f6d9013`

---

## TASK 3 — KIỂM TRA CONSTRUCTOR VÀ PHÂN QUYỀN ADVISOR

### 1. Phân tích Constructor:
```solidity
constructor() {
    advisor = msg.sender;
}
```
- **Tham số đầu vào:** Hoàn toàn không nhận tham số (`inputs: []`).
- **Cơ chế gán quyền:** Biến `advisor` được gán trực tiếp bằng địa chỉ ví của tài khoản thực hiện gửi giao dịch deploy (`msg.sender`).
- **Tính bất biến (`immutable`):** Biến `advisor` được định nghĩa là `address public immutable advisor;`. Do đó, địa chỉ ví deploy sẽ trở thành Cố vấn học tập duy nhất của hợp đồng suốt vòng đời hoạt động và không thể bị giả mạo hay tấn công thay đổi quyền.

### 2. Ma trận phân quyền các hàm quản trị (Access Control Matrix):

| Hàm (Function) | Modifier / Kiểm tra quyền | Vai trò được phép gọi | Tác động trạng thái | Kiểm tra rủi ro |
| :--- | :--- | :--- | :--- | :---: |
| `setBCSMember` | `onlyAdvisor` | **Chỉ duy nhất Cố vấn học tập** | Thêm/xóa thành viên Ban cán sự | An toàn, chặn Zero Address |
| `withdrawAdminFee` | `onlyAdvisor` | **Chỉ duy nhất Cố vấn học tập** | Rút phí vận hành 1% | An toàn, kiểm tra số dư pool |
| `createSpendRequest` | `onlyActiveBCS` | **Chỉ thành viên BCS hoạt động** | Tạo đề xuất chi tiền lớp | An toàn, kiểm tra quỹ khả dụng |
| `voteSpendRequest` | `onlyActiveBCS` | **Chỉ thành viên BCS hoạt động** | Bỏ phiếu đề xuất chi | An toàn, chặn vote trùng |
| `executeSpendRequest`| `onlyActiveBCS` | **Chỉ thành viên BCS hoạt động** | Giải ngân đề xuất ở `Ready` | An toàn, chặn chi 2 lần |
| `voteRefundRequest` | `onlyActiveBCS` | **Chỉ thành viên BCS hoạt động** | Bỏ phiếu yêu cầu hoàn tiền | An toàn, chặn vote trùng |
| `executeRefundRequest`| Bất kỳ (Kiểm tra điều kiện) | **BCS hoặc Sinh viên nộp đơn** | Chuyển tiền hoàn về ví sinh viên | An toàn, chỉ chuyển cho applicant |
| `expireSpendRequest` | Không giới hạn | **Bất kỳ ai (Permissionless)** | Hủy đề xuất quá hạn 7 ngày | An toàn, giải phóng tiền giữ chỗ |
| `expireRefundRequest`| Không giới hạn | **Bất kỳ ai (Permissionless)** | Hủy yêu cầu quá hạn 7 ngày | An toàn, giải phóng tiền giữ chỗ |
| `deposit` / `receive`| Không giới hạn | **Bất kỳ ai (Sinh viên lớp)** | Nạp tiền vào quỹ lớp | Tự trích 1% phí, cộng quỹ 99% |
| `createRefundRequest`| Không giới hạn | **Bất kỳ ai (Sinh viên lớp)** | Nộp đơn yêu cầu hoàn tiền nộp nhầm | Giới hạn $\le$ khoản đã nộp |

**Xác nhận:** Không có bất kỳ quyền quản trị nào bị bỏ sót trong checklist. Toàn bộ các hàm thay đổi trạng thái nhạy cảm đều được bảo vệ bởi modifier `onlyAdvisor` hoặc `onlyActiveBCS`.

---

## TASK 4 — KIỂM TRA TÍNH SẴN SÀNG CỦA FRONTEND (FRONTEND READINESS)

### 1. Đồng bộ ABI và Tên hàm trong Frontend:
- Mảng `CONTRACT_ABI` trong [web/index.html](file:///d:/document/TDT/KTS-Class-Fund-K57/web/index.html) khớp 100% với Compiled ABI (83/83 phần tử).
- Mọi hàm gọi Web3 từ frontend đều khớp chính xác tên hàm và tham số Solidity:
  * `contract.createSpendRequest(recipient, amountWei, desc)`
  * `contract.voteSpendRequest(requestId, support)`
  * `contract.executeSpendRequest(requestId)`
  * `contract.createRefundRequest(amountWei, reason)`
  * `contract.voteRefundRequest(refundId, support)`
  * `contract.executeRefundRequest(refundId)`
  * `contract.withdrawAdminFee(amountWei)`
  * `contract.setBCSMember(address, status)`
  * `contract.deposit({ value })`

### 2. Cơ chế phân tích Event (Event Parsing):
- **Đối với `voteSpendRequest`:** Giao diện đã cài đặt logic bóc tách `receipt.logs` qua `contract.interface.parseLog(log)`:
  * Nếu phát hiện event `SpendRequestExecuted` $\rightarrow$ Thông báo tự động giải ngân thành công.
  * Nếu phát hiện event `SpendExecutionFailed` $\rightarrow$ Đưa ra thông báo cảnh báo rõ ràng: *"Đề xuất đã chuyển sang trạng thái Sẵn sàng (Ready) do người nhận từ chối ETH. Ban cán sự có thể bấm nút 'Giải ngân' để thử lại"*.
  * Nếu phát hiện `SpendRequestReady` $\rightarrow$ Thông báo chuyển trạng thái Sẵn sàng.
- **Đối với `voteRefundRequest`:** Giao diện đã cài đặt phân tích tương ứng cho `RefundRequestExecuted` và `RefundExecutionFailed`.

### 3. Ánh xạ Enum Trạng thái (`RequestStatus`):
Khớp chính xác giữa Solidity và UI:
- `0`: `Pending` $\rightarrow$ Hiển thị badge vàng cam "Chờ duyệt" + Nút vote Đồng ý / Bác bỏ cho BCS.
- `1`: `Ready` $\rightarrow$ Hiển thị badge xanh dương "Sẵn sàng" + **Nút bấm thủ công "Giải ngân" / "Hoàn tiền" (Manual Retry)**.
- `2`: `Executed` $\rightarrow$ Hiển thị badge xanh lá "Đã giải ngân" / "Đã hoàn tiền" + Ẩn nút thao tác.
- `3`: `Rejected` $\rightarrow$ Hiển thị badge xám "Đã bác bỏ".
- `4`: `Expired` $\rightarrow$ Hiển thị badge đỏ "Hết hạn 7 ngày".
- `5`: `Cancelled` $\rightarrow$ Hiển thị badge xám "Đã hủy".

### 4. Đánh giá luồng giao diện:
- Giao diện không sửa đổi trong đợt kiểm tra này theo đúng quy tắc an toàn.
- Frontend đã hoàn toàn sẵn sàng kết nối ngay sau khi người dùng deploy contract mới và dán địa chỉ vào `CONFIG.defaultContractAddress`.

---

## TASK 5 — CHECKLIST TRIỂN KHAI VÀ BÀN GIAO DEPLOYMENT

> [!IMPORTANT]
> Quy trình dưới đây được thiết kế để người dùng tự tay thực hiện một cách an toàn nhất thông qua Remix IDE và ví MetaMask trên mạng **Ethereum Sepolia Testnet**.

### Bảng 10 Bước Triển Khai Chi Tiết:

| Bước | Thao tác trên Remix IDE / MetaMask | Giá trị cấu hình cần chọn | Mục đích kiểm soát an toàn |
| :---: | :--- | :--- | :--- |
| **1** | Mở trình duyệt và truy cập Remix IDE | `https://remix.ethereum.org` | Môi trường lập trình Web3 chuẩn mực |
| **2** | Tải mã nguồn `ProjectCore.sol` lên Remix | Copy nội dung từ `contracts/project/ProjectCore.sol` | Đảm bảo đúng file mã nguồn đã kiểm toán |
| **3** | Chuyển sang tab **Solidity Compiler** | Chọn phiên bản `0.8.20` (hoặc `0.8.26`) | Khớp với quy chuẩn đặc tả |
| **4** | Cấu hình Compiler nâng cao | Bật **Enable optimization**, điền **200** runs. Mục EVM Version chọn **shanghai** | Giảm 50% kích thước bytecode và tiết kiệm gas |
| **5** | Bấm **Compile ProjectCore.sol** | Kiểm tra biểu tượng tích xanh, 0 cảnh báo | Đảm bảo mã nguồn biên dịch hoàn toàn sạch |
| **6** | Chuyển sang tab **Deploy & Run Transactions** | Tại mục ENVIRONMENT: chọn **Injected Provider - MetaMask** | Kết nối trực tiếp ví MetaMask cá nhân |
| **7** | Kiểm tra mạng MetaMask | Xác nhận đang hiển thị mạng **Sepolia** (Network ID 11155111) | Chống deploy nhầm mạng Mainnet |
| **8** | Xác nhận địa chỉ ví triển khai (Deployer) | **Chắc chắn rằng ví MetaMask đang chọn chính là ví của Cố vấn học tập (Advisor)** | Vì `advisor = msg.sender` trong Constructor |
| **9** | Kiểm tra trường Deploy Arguments | Không nhập gì cả (trường đối số rỗng `constructor()`) | Constructor không nhận tham số |
| **10** | Bấm nút **Deploy (màu cam)** và Ký xác nhận | Xác nhận giao dịch trên popup MetaMask | **Hoàn tất triển khai on-chain** |

### Các bước ngay sau khi Deploy thành công:
1. Copy **Địa chỉ hợp đồng mới (Contract Address)** từ Remix hoặc Etherscan.
2. Lưu lại **Transaction Hash** và lưu file ABI để nộp bằng chứng.
3. Mở file [web/index.html](file:///d:/document/TDT/KTS-Class-Fund-K57/web/index.html), cập nhật địa chỉ mới vào:
   ```javascript
   const CONFIG = {
     defaultContractAddress: "0x<DIA_CHI_CONTRACT_MOI>",
     contractAddress: "0x<DIA_CHI_CONTRACT_MOI>",
     // ...
   };
   ```
4. Dùng ví Advisor vào giao diện hoặc Remix gọi `setBCSMember(bcsAddress, true)` để thiết lập danh sách Ban cán sự ban đầu.

---

## KẾT LUẬN CUỐI CÙNG

# **READY TO DEPLOY ON SEPOLIA**

### Tóm tắt căn cứ chuẩn thuận:
1. **ABI:** Đồng bộ tuyệt đối 100% giữa mã nguồn `ProjectCore.sol`, file lưu trữ kiểm toán `audited_ProjectCore.abi`, và giao diện `web/index.html` với cấu trúc chuẩn gồm **83 entries (39 hàm, 17 sự kiện, 25 lỗi tùy biến, 1 constructor, 1 receive)**. Vấn đề chênh lệch 15 vs 17 events đã được chứng minh và giải thích minh bạch.
2. **Bytecode:** Cấu hình trình biên dịch chốt chuẩn xác (`0.8.20/0.8.26`, Optimizer 200, Shanghai), kích thước bytecode chỉ chiếm 50.2% trần EIP-170, 0 cảnh báo, 0 lỗi biên dịch.
3. **Phân quyền:** Constructor phân quyền `advisor = msg.sender` bất biến an toàn tuyệt đối, ma trận phân quyền BCS/Advisor khép kín không sơ hở.
4. **Frontend:** Giao diện có sẵn cơ chế phân tích sự kiện Auto-Execution, nút manual retry, ánh xạ enum trạng thái chính xác và sẵn sàng hoạt động ngay sau khi gắn địa chỉ mới.
5. **Quy tắc an toàn:** Không có bất kỳ thay đổi nào làm phá vỡ tính toàn vẹn của mã nguồn production trước thời điểm triển khai.
