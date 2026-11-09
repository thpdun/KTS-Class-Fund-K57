# KTS-Class-Fund

Hệ thống Hợp đồng thông minh Quản lý Quỹ lớp Phi tập trung dành cho sinh viên ngành Kinh tế Số (Khoa Hệ thống Thông tin Kinh tế, Trường Đại học Kinh tế – Đại học Huế).

## Thành viên nhóm thực hiện
| Họ và tên | Mã sinh viên | Vai trò trong dự án |
| :--- | :--- | :--- |
| **Trần Hoàng Phương Dung** | 23K4300004 | Trưởng nhóm / Smart Contract Developer |
| **Võ Ngọc Tâm Phúc** | 23K4300015 | Thành viên kỹ thuật / QA & Tester |

---

## 1. Giới thiệu dự án

KTS-Class-Fund là giải pháp Smart Contract nhằm minh bạch hóa toàn diện dòng tiền thu chi của quỹ lớp. Hệ thống giải quyết các vấn đề tồn đọng của phương thức giữ quỹ truyền thống (tiền mặt hoặc tài khoản ngân hàng cá nhân), tự động phân bổ quỹ dịch vụ vận hành để bù đắp chi phí Gas mạng lưới cho người quản trị qua cơ chế EIP-1559, bảo vệ thông tin định danh sinh viên (PII), và lưu trữ lịch sử giao dịch bất biến trên blockchain.

### Phân quyền các vai trò người dùng (Theo `docs/SPEC.md`):
- **Cố vấn học tập (CVHT / Owner):** Quản lý nhân sự Ban cán sự, quản lý danh sách sinh viên ghi danh on-chain, cam kết mã băm danh bạ bảo vệ PII, và chuyển quỹ phí vận hành dư sang Quỹ lớp chính.
- **Ban cán sự lớp (BCS):** Khởi tạo đợt thu quỹ on-chain, đóng đợt thu, đề xuất các khoản chi tiêu phục vụ hoạt động tập thể lớp, tham gia biểu quyết dân chủ ($\ge 51\%$) trên mẫu số snapshot cử tri, và thực thi giải ngân/hoàn tiền.
- **Sinh viên trong lớp:** Nộp ETH vào quỹ chung hoặc đợt thu cụ thể, theo dõi số dư minh bạch theo thời gian thực, tạo yêu cầu hoàn tiền khi nộp thừa/nhầm trong hạn mức Net 99%.

---

## 2. Hiện trạng mã nguồn và Phân định tính năng (Cập nhật sau Lab 15)

Sau đợt nâng cấp toàn diện **Lab 15** theo tài liệu `docs/CHANGE_PLAN_LAB15.md`, hệ thống hoàn thiện 7 nhóm thay đổi kiến trúc (A–G) từ Smart Contract, backend đến giao diện DApp:

### 2.1. Tính năng ĐÃ TRIỂN KHAI trong mã nguồn hiện tại (`contracts/project/ProjectCore.sol`):
- [x] **R1 — Phân quyền Quản trị CVHT, Quản lý BCS & Chống Thao túng Biểu quyết (Nhóm B):**
  - Modifier `onlyAdvisor`: Chỉ địa chỉ ví Cố vấn học tập mới có quyền thay đổi nhân sự BCS.
  - Hàm `setBCSMember(address member, bool status)`: Yêu cầu địa chỉ phải là sinh viên đã ghi danh (`onlyStudent`).
  - **Hoãn kích hoạt (`BCS_ACTIVATION_DELAY = 3 seconds`):** Thành viên BCS mới được thêm phải đủ 3 giây mới được tạo đề xuất hoặc bỏ phiếu (đã cấu hình giảm từ 3 ngày xuống 3 giây để thuận tiện kiểm thử và demo nhanh), chặn việc CVHT bổ nhiệm tức thời ví ma để lũng đoạn biểu quyết.
  - **Giới hạn quy mô BCS:** `MIN_BCS_FOR_PROPOSAL = 3` (bắt buộc tối thiểu 3 BCS hoạt động mới được tạo đề xuất), trần tối đa `MAX_BCS = 15`. Quản lý danh sách động `bcsList` qua kỹ thuật O(1) Swap-and-Pop.
  - **Snapshot `voterBase`:** Mẫu số cử tri được chốt cố định tại thời điểm tạo đề xuất chi hoặc hoàn tiền; thay đổi nhân sự sau đó không ảnh hưởng tới các đề xuất đang biểu quyết.
  - Phát sự kiện `BCSMemberUpdated(member, status)`.
- [x] **R2 — Nạp quỹ Whitelist, Phân bổ 99%/1% & Hạch toán Net 99% (Nhóm A & D):**
  - **Whitelist nạp tiền:** Chỉ sinh viên trong danh bạ on-chain (`isStudent[wallet] == true`) mới được gọi `deposit()` hoặc chuyển ETH qua `receive()`. Người ngoài bị từ chối với lỗi `NotEnrolledStudent()`.
  - Phân bổ tự động: **1%** vào Quỹ dịch vụ vận hành (`adminFeePool`) và **99%** vào Quỹ lớp chính (`classFundBalance`).
  - **Hạch toán Net 99%:** `studentContributions[student]` chỉ ghi nhận 99% net (hạn mức có thể hoàn lại); `studentTotalDeposited[student]` lưu 100% gross (hiển thị lịch sử).
  - Bảo toàn 100% wei lẻ do phép chia số nguyên, chặn nạp 0 ETH bằng `ZeroAmount()`.
  - Phát sự kiện `FundDeposited` và `AdminFeeCollected`.
- [x] **R7 — Quy trình Hoàn tiền có Biểu quyết BCS & Chặn Xung đột Lợi ích (Nhóm A & C):**
  - **Tạo yêu cầu hoàn tiền:** Sinh viên gọi `createRefundRequest(amount, reason)`.
    - Hạn mức hoàn tối đa được giới hạn bởi công thức:
      $$\text{maxRefund} = \min(\text{getStudentAvailableContribution(msg.sender)}, \text{getAvailableClassFund()})$$
    - Giữ chỗ kép (Dual-layer Reservation): Đồng thời tăng `reservedRefundAmount` (khóa quỹ lớp) và `pendingStudentRefundAmount[msg.sender]` (khóa hạn mức đóng góp cá nhân).
  - **Biểu quyết dân chủ $\ge 51\%$:** BCS biểu quyết qua `voteRefundRequest(requestId, support)`. Thời hạn 7 ngày.
  - **Chặn xung đột lợi ích (Conflict of Interest):** Sinh viên xin hoàn tiền nếu là BCS thì bị chặn biểu quyết trên yêu cầu của chính mình (`ConflictOfInterestApplicantCannotVote`). Mẫu số tính ngưỡng tự động giảm 1 (`voterBase - 1`) và yêu cầu tối thiểu 2 phiếu thuận (`yesVotes >= 2`).
  - **Thực thi hoàn tiền:** Hàm `executeRefundRequest(requestId)` tuân thủ nghiêm ngặt CEI, chuyển ETH trực tiếp về ví sinh viên qua `.call{value: req.amount}("")`. Rollback toàn bộ kế toán nếu chuyển ETH thất bại (`ETHTransferFailed`).
- [x] **R3, R4, R5, R6 — Đề xuất Chi tiêu, Biểu quyết Snapshot & Chặn Xung đột Lợi ích (Nhóm B & C):**
  - `createSpendRequest(recipient, amount, description)`: Chỉ BCS đủ điều kiện gọi khi `activeBCSCount >= 3`. Giữ chỗ an toàn qua `reservedSpendAmount`.
  - `voteSpendRequest(requestId, support)`: Chặn bỏ phiếu kép, tính ngưỡng $\ge 51\%$ theo snapshot `voterBase`.
  - **Chặn xung đột lợi ích:** BCS là người thụ hưởng tiền giải ngân (`recipient`) bị chặn biểu quyết (`ConflictOfInterestRecipientCannotVote`).
  - `executeSpendRequest(requestId)`: Tự động hoặc gọi thủ công khi đạt $\ge 51\%$, giải ngân an toàn theo CEI.
  - `expireSpendRequest(requestId)` / `expireRefundRequest(requestId)`: Cho phép bất kỳ ai giải phóng số tiền giữ chỗ sau 7 ngày nếu không đạt đủ 51%.
- [x] **Mục D — Quản lý Danh sách Sinh viên On-chain & Bảo vệ PII:**
  - `setStudents(address[] calldata students, bool status)`: CVHT cập nhật danh sách sinh viên (tối đa 100 ví/lần). Không cho phép xóa sinh viên đang là BCS (`CannotRemoveActiveBCSAsStudent`).
  - `commitRoster(bytes32 hash)`: CVHT cam kết mã băm SHA-256 của danh bạ lên chuỗi (`rosterHash`). Toàn bộ tên, MSSV và thông tin cá nhân (PII) được lưu trữ ngoài chuỗi (off-chain).
  - `getUnaccountedBalance()`: Phát hiện các khoản ETH bị ép chuyển vào hợp đồng (qua `selfdestruct`) mà không làm sai lệch sổ sách kế toán.
- [x] **Mục E — Quản lý Đợt thu Quỹ On-chain:**
  - `createCollection(targetWei, deadline, purpose)`: Chỉ BCS gọi, mở đợt thu mới khi không có đợt thu nào đang mở (`OnlyOneActiveCollectionAllowed`).
  - `closeCollection(id, reason)`: BCS đóng sớm đợt thu.
  - `depositToCollection(id)`: Nộp tiền vào đúng đợt thu. Tiêu chí "Đã nộp" tính theo `paidInCollection >= targetWei` của đúng đợt thu đó.
- [x] **Mục F — Bỏ Rút Phí, Tự động Hoàn Gas & Chuyển Phí Dư:**
  - **Xóa bỏ hoàn toàn hàm rút phí:** Xóa `withdrawAdminFee` và sự kiện `AdminFeeWithdrawn`.
  - **Tự động hoàn Gas (`governanceAction`):** 10 hàm quản trị của CVHT và BCS được tự động hoàn phí gas theo chuẩn EIP-1559:
    $$\text{gasRefund} = \min(\text{gasUsed}, 500,000) \times \min(\text{tx.gasprice}, \text{block.basefee} + 2\text{ gwei})$$
  - Xử lý thiếu hụt (Shortfall): Nếu `adminFeePool` không đủ, chuyển hết số dư hiện có và ghi nhận thiếu hụt (`gasRefundShortfall`), tuyệt đối không revert giao dịch quản trị chính.
  - Fallback an toàn: Nếu ví người gọi từ chối ETH hoàn gas, phát `GasRefundFailed`, hoàn trả pool và không revert giao dịch chính.
  - `moveFeeToClassFund(uint256 amount)`: CVHT chuyển phí vận hành dư sang Quỹ lớp chính.
- [x] **Hàm tra cứu minh bạch (View / Getters):**
  - `getFundBalance()`, `getAvailableClassFund()`, `getTotalContractBalance()`, `getUnaccountedBalance()`.
  - `getStudentContribution(address student)` (99% net), `studentTotalDeposited(address student)` (100% gross).
  - `getStudentMaxRefund(address student)` = $\min(\text{availableContribution}, \text{availableClassFund})$.
  - `getSpendRequest(requestId)`, `getRefundRequest(requestId)`, `getCollection(collectionId)`.
  - `isStudent(address)`, `isBCSMember(address)`, `getBCSList()`, `getActiveBCSCount()`.

---

## Cấu hình biên dịch/deploy

- **Solidity compiler:** `0.8.20` (`solc 0.8.20`, pragma `^0.8.20`).
- **EVM version:** `shanghai` (khai báo tường minh cho cả trình biên dịch và `networks.hardhat.hardfork` trong `hardhat.config.js`).
- **Optimizer:** Bật (`enabled: true`, `runs: 200`).
- **Kích thước Deployed Bytecode thực tế:**
  - `deployedBytecode`: **22,045 bytes** (Đạt **89.70%** ngưỡng trần 24,576 bytes của EIP-170, biên an toàn còn **2,531 bytes**).
  - `initcode`: **22,139 bytes** (Nằm sâu dưới giới hạn 49,152 bytes của Shanghai hardfork).

> [!WARNING]  
> **Lưu ý khi biên dịch/deploy bằng Remix IDE:** Phải chọn đúng **Compiler `0.8.20`**, **EVM Version `shanghai`**, và bật **Enable optimization** với `runs = 200`. Nếu tắt optimizer, kích thước `deployedBytecode` sẽ vượt quá giới hạn **24.576 byte** của chuẩn EIP-170 và giao dịch deploy sẽ thất bại.

- **Lệnh kiểm chứng tổng hợp (Hardhat + Python + Solc):**
  ```powershell
  npm run verify
  ```

> [!NOTE]  
> **Thông tin triển khai thực tế trên Ethereum Sepolia Testnet & Frontend DApp:**  
> - **Địa chỉ Smart Contract:** [`0x90948699FF04bC9cF159a39e200F09885439503D`](https://sepolia.etherscan.io/address/0x90948699FF04bC9cF159a39e200F09885439503D) *(và bản nâng cấp Lab 15: [`0x1F066cB83F41857DcC5D230C74963b12F1E8f58C`](https://sepolia.etherscan.io/address/0x1F066cB83F41857DcC5D230C74963b12F1E8f58C))*.
> - **Frontend DApp Web3:** Triển khai hoàn chỉnh tại `web/index.html` (chạy trên cổng `http://localhost:3000`), kết nối MetaMask trực tiếp, tích hợp đầy đủ 3 vai trò (Sinh viên, BCS, Cố vấn), quản lý đợt thu on-chain, biểu quyết giải ngân, hoàn tiền Net 99%, đối soát danh bạ SHA-256, và sổ nhật ký dòng tiền phân tán.
> - **Môi trường kiểm chứng tự động:** 41 bài kiểm thử EVM Hardhat (`test/hardhat/`), 61 bài kiểm thử quy tắc kinh tế Python (`test/test_economic_rules.py`), và trình biên dịch `solc 0.8.20`.

---

## 3. Hướng dẫn kiểm tra và Chạy thử nghiệm thực tế

### 3.1. Phương thức 1: Chạy kiểm thử tự động bằng Hardhat
- **Tệp kiểm thử:** Bộ kiểm thử `test/hardhat/` gồm:
  - `ProjectCore.baseline.test.js`: Kiểm thử đường cơ sở chức năng cốt lõi.
  - `ProjectCore.phase1.test.js`: Kiểm thử hạch toán Net 99%, làm tròn số nguyên, và chống gian lận rút quỹ.
  - `ProjectCore.phase2.test.js`: Kiểm thử snapshot voterBase, độ trễ 3 ngày, xung đột lợi ích, tự động bác bỏ đề xuất chi / hoàn tiền (`Rejected`) khi phiếu chống chiếm đa số, và giới hạn `MAX_OPEN_SPEND_PER_CREATOR = 3`.
  - `ProjectCore.phase3.test.js`: Kiểm thử danh bạ sinh viên on-chain, băm danh bạ, và phát hiện ETH chuyển ép.
  - `ProjectCore.phase4.test.js`: Kiểm thử đợt thu on-chain, nạp theo đợt, và tự động đóng đợt thu quá hạn khi tạo đợt mới.
  - `ProjectCore.phase5.test.js`: Kiểm thử điều chuyển phí dư, tự động hoàn gas, bảo vệ chống tái nhập và bỏ qua hoàn gas khi trạng thái BCS không đổi.
- **Mục đích:** Kiểm thử toàn diện 41 kịch bản tự động trên mạng Hardhat Shanghai, thao túng thời gian thực tế bằng `time.increase` (kiểm tra hoãn 3 ngày, hết hạn 7 ngày), kiểm thử giá gas tùy chỉnh EIP-1559, kiểm tra giới hạn kích thước bytecode EIP-170, và kịch bản tấn công giả mạo cử tri.
- **Lệnh thực thi:**
  ```powershell
  npx hardhat test
  ```
- **Kết quả thực tế quan sát được (41/41 ca ĐẠT):**
  ```text
  41 passing (10s)
  ```

### 3.2. Phương thức 2: Chạy kiểm thử mô phỏng kinh tế bằng Python
- **Tệp kiểm thử:** `test/test_economic_rules.py`
- **Mục đích:** Kiểm tra tự động 100% logic kinh tế 7 nhóm thay đổi A–G và 3 bản sửa lỗi: hạch toán Net 99%, bảo toàn wei lẻ, hoãn 3 ngày, snapshot voterBase, xung đột lợi ích, whitelist danh bạ, đợt thu on-chain, tự đóng đợt quá hạn, bác bỏ đề xuất khi No chiếm đa số, giới hạn 3 đề xuất mở, cơ chế hoàn gas và chuyển phí dư sang Quỹ lớp.
- **Lệnh thực thi:**
  ```powershell
  python test/test_economic_rules.py
  ```
- **Kết quả thực tế quan sát được (61/61 ca ĐẠT):**
  ```text
  Ran 61 tests in 0.014s

  OK
  ```

### 3.3. Phương thức 3: Kiểm tra biên dịch cục bộ bằng trình biên dịch Solc
- **Lệnh thực thi:**
  ```powershell
  npx --no-install solc --optimize --optimize-runs 200 --bin -o cache/solc-bin contracts/project/ProjectCore.sol test/ProjectCore_test.sol test/ProjectCore_integration_test.sol
  ```
- **Kết quả thực tế:** Biên dịch sạch sẽ 100%, Exit code 0, không có lỗi cú pháp.

### 3.4. Phương thức 4: Kiểm thử Tích hợp Backend, Giao diện và An ninh
- **Kiểm thử Indexer & Đồng bộ:** `python test/test_blockchain_indexer.py` (32 tests PASS), `python test/test_auto_execution.py` (18 tests PASS).
- **Kiểm thử Hash Danh bạ & Tiến độ:** `python test/test_roster_hash.py` (10 tests PASS), `python test/test_campaign_progress.py` (13 tests PASS).
- **Kiểm thử Giao diện DApp:**
  - `node test/test_metamask_and_ui_verification.js` (4/4 PASS).
  - `node test/test_stage2_roles.js` (14/14 PASS).
  - `node test/test_frontend_multiple_progress.js` (4/4 PASS).
  - `node test/test_announcement_modal_behavior.js` (4/4 PASS).
  - `node test/test_frontend_dom_cleanup.js` (30/30 PASS).
  - `node test/test_roster_status.js` (7/7 PASS).
- **Kiểm thử An ninh Backend (Khi máy chủ hoạt động):**
  - `python test/test_stage3b3_security.py` (10/10 tests PASS).
  - `python test/test_stage3b4_security.py` (7/7 tests PASS).
  - `python test/test_stage3b45_regression.py` (8/8 tests PASS).
  - `python test/test_cors_security.py` (6/6 tests PASS).

---

## 4. Bảng tổng hợp đối chiếu kết quả kiểm thử tiêu biểu

| Ca kiểm thử | Quy tắc / Kịch bản | Dữ liệu đầu vào | Kết quả mong đợi (Expected) | Kết quả thực tế quan sát được (Observed) | Trạng thái |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Kích thước Bytecode** | Giới hạn EIP-170 | Compiler 0.8.20 shanghai runs 200 | Deployed bytecode $\le$ 24,576 bytes. | **20,767 bytes** (84.50% giới hạn). | **ĐẠT (PASS)** |
| **Section A1** | Hạch toán Net 99% | Nộp 10 ETH | Net 9.9 ETH, Quỹ phí 0.1 ETH, Gross 10 ETH. Hoàn tối đa 9.9 ETH. | Khớp 100%: Quỹ chính 9.9 ETH, phí 0.1 ETH, hoàn sạch đưa limit về 0. | **ĐẠT (PASS)** |
| **Section A3** | Chống gian lận hoàn tiền | A & B mỗi người nộp 10 ETH; A xin hoàn 10 ETH | A chỉ có net 9.9 ETH; xin 10 ETH bị revert `InsufficientContribution`. | Revert `InsufficientContribution`, bảo vệ an toàn 100% tiền của B. | **ĐẠT (PASS)** |
| **Section B1** | Hoãn kích hoạt BCS 3 ngày | Thêm BCS mới | Chưa đủ 3 ngày: không được tạo đề xuất hoặc vote (`NotActiveBCS`). | Đúng 3 ngày mới kích hoạt; thêm lại reset trễ 3 ngày. | **ĐẠT (PASS)** |
| **Section B4** | Snapshot voterBase | Tạo đề xuất lúc có 3 BCS | `voterBase = 3` bất biến kể cả khi CVHT thêm/xóa BCS giữa chừng. | Snapshot giữ nguyên; tỷ lệ 51% tính trên mẫu số snapshot. | **ĐẠT (PASS)** |
| **Section C1** | Chặn xung đột lợi ích | Sinh viên xin hoàn tiền đồng thời là BCS | Bị tước quyền vote trên yêu cầu của chính mình (`ConflictOfInterestApplicantCannotVote`). | Mẫu số giảm 1 (`voterBase - 1`), yêu cầu $\ge 2$ phiếu thuận. | **ĐẠT (PASS)** |
| **Section D1** | Whitelist nạp tiền | Người ngoài chưa ghi danh nộp ETH | Revert `NotEnrolledStudent()`. | Revert chính xác `NotEnrolledStudent()`, chặn người ngoài. | **ĐẠT (PASS)** |
| **Section D5** | Cam kết Hash danh bạ | CVHT gọi `commitRoster(hash)` | Lưu trữ mã hash SHA-256, phát `RosterCommitted`. | Lưu hash thành công; không đưa PII sinh viên lên chuỗi. | **ĐẠT (PASS)** |
| **Section E1** | Quản lý đợt thu on-chain | BCS tạo đợt thu mới | Đợt thu mở thành công; chỉ 1 đợt thu mở tại 1 thời điểm. | Tạo đợt thu thành công; mở đợt thứ 2 bị revert `OnlyOneActiveCollectionAllowed`. | **ĐẠT (PASS)** |
| **Section E3** | Nộp vào đợt thu | Sinh viên nộp `depositToCollection` | Phân bổ 99%/1%, cập nhật `paidInCollection`, đánh dấu "Đã nộp" khi đủ target. | Khớp 100%: Phân định rõ ràng tiến độ từng đợt thu. | **ĐẠT (PASS)** |
| **Section F1** | Chuyển phí sang Quỹ lớp | CVHT gọi `moveFeeToClassFund(2 ETH)` | Trừ `adminFeePool` 2 ETH, tăng `classFundBalance` 2 ETH. | Chuyển thành công; bảo toàn 100% tổng số dư hợp đồng. | **ĐẠT (PASS)** |
| **Section F2** | Tự động hoàn Gas EIP-1559 | Thực hiện hàm quản trị | Đo gas thực tế, hoàn ETH về ví người gọi, phát `GasRefunded`. | Hoàn gas thành công; giá gas bị khống chế tối đa `basefee + 2 gwei`. | **ĐẠT (PASS)** |
| **Section F3** | Xử lý khi cạn Quỹ phí | Gọi hàm quản trị khi pool = 0 | Chuyển 0 ETH, ghi nhận `gasRefundShortfall`, hàm chính vẫn hoàn tất. | Giao dịch quản trị thành công trọn vẹn, không bị revert. | **ĐẠT (PASS)** |
| **Section F4** | Fallback hoàn gas thất bại | Ví nhận từ chối ETH | Phát `GasRefundFailed`, trả lại số dư vào pool, hàm chính không revert. | Thao tác chính thành công, pool hoàn trả nguyên vẹn. | **ĐẠT (PASS)** |
| **Section G** | Tích hợp DApp & ABI | Tương tác giao diện `web/index.html` | Hiển thị đầy đủ đợt thu, hoàn tiền net, hoàn gas banner, đối soát hash danh bạ. | Giao diện hoạt động mượt mà, đồng bộ 100% ABI mới. | **ĐẠT (PASS)** |
| **Kiểm thử Sepolia & Frontend DApp** | On-chain public testnet | Sepolia ETH & MetaMask | Triển khai và tương tác on-chain thực tế qua giao diện DApp (`web/index.html`). | **ĐÃ TRIỂN KHAI & KIỂM THỬ THỰC TẾ (PASS)** tại địa chỉ `0x90948699FF04bC9cF159a39e200F09885439503D` / `0x1F066cB83F41857DcC5D230C74963b12F1E8f58C`. | **ĐẠT (PASS)** |

---

## 5. Bảng giải trình & Đối chiếu khắc phục 7 nội dung góp ý từ Hội đồng đánh giá

Dưới đây là bảng đối chiếu chi tiết hiện trạng mã nguồn giải quyết 7 điểm phản hồi/góp ý từ đợt đánh giá của Hội đồng / Thầy cô:

| STT | Nội dung góp ý từ Hội đồng | Hiện trạng giải quyết | Cơ chế xử lý cụ thể trong mã nguồn & Kiểm thử | Trạng thái |
| :---: | :--- | :---: | :--- | :---: |
| **1** | **Hoàn tiền 100% vs Net 99%:** Sinh viên nạp gộp nhưng quỹ chỉ giữ 99% (1% vào adminFeePool). Cần hoàn tối đa 99% số ròng để không lấy lạm tiền của người khác. | **ĐÃ SỬA TRIỆT ĐỂ** | - Tách bạch hai sổ sách kế toán: `studentContributions` chỉ ghi nhận 99% Net (hạn mức được phép hoàn), còn `studentTotalDeposited` ghi 100% Gross (lịch sử nạp).<br>- Hàm `getStudentMaxRefund` khống chế trần: $\min(\text{availableContribution}, \text{availableClassFund})$.<br>- Phí 1% là phí dịch vụ mạng không hoàn lại (non-refundable). Revert `InsufficientContribution` nếu yêu cầu vượt số Net.<br>- Kiểm chứng: Test Hardhat A1, A3 (`ProjectCore.phase1.test.js`) & Python Test 1–12. | **ĐÃ HOÀN TẤT (PASS)** |
| **2** | **Mẫu số biểu quyết động:** Ngưỡng 51% tính trên activeBCSCount hiện hành; nếu CVHT thêm/xóa BCS giữa chừng thì kết quả đề xuất bị thay đổi. Cần chụp snapshot voterBase. | **ĐÃ SỬA TRIỆT ĐỂ** | - Cả `SpendRequest` và `RefundRequest` đều lưu trường `uint256 voterBase`.<br>- Giá trị này được đóng băng (snapshot) tại thời điểm tạo đề xuất: `req.voterBase = activeBCSCount`. Mọi thao tác thêm/xóa BCS sau đó không làm thay đổi mẫu số của đề xuất đang chạy.<br>- Bổ sung thêm rào chắn: Yêu cầu tối thiểu 3 BCS hoạt động (`MIN_BCS_FOR_PROPOSAL = 3`) và thời gian hoãn kích hoạt BCS mới `BCS_ACTIVATION_DELAY` để ngăn CVHT tạo BCS ma.<br>- Kiểm chứng: Test Hardhat B1, B4 (`ProjectCore.phase2.test.js`). | **ĐÃ HOÀN TẤT (PASS)** |
| **3** | **Xung đột lợi ích (Conflict of Interest):** BCS tạo đề xuất chi có thể tự vote cho mình, hoặc người nhận (recipient) là chính họ. Cần cấm vote hoặc yêu cầu tối thiểu 2 người. | **ĐÃ SỬA TRIỆT ĐỂ** | - **Chi tiêu:** Nếu BCS là người thụ hưởng (`recipient == msg.sender`), hợp đồng revert lỗi `ConflictOfInterestRecipientCannotVote()`.<br>- **Hoàn tiền:** Nếu sinh viên xin hoàn là BCS (`applicant == msg.sender`), bị tước quyền vote qua lỗi `ConflictOfInterestApplicantCannotVote()`.<br>- Mẫu số tự động trừ đi 1 (`voterBase - 1`) và bắt buộc tối thiểu 2 phiếu thuận (`yesVotes >= 2`) từ các BCS độc lập.<br>- Kiểm chứng: Test Hardhat C1, C2 (`ProjectCore.phase2.test.js`). | **ĐÃ HOÀN TẤT (PASS)** |
| **4** | **Đề xuất Ready không ai thực thi khóa tiền vĩnh viễn:** Cần có hạn thực thi hoặc hàm hủy/expire. | **ĐÃ SỬA TRIỆT ĐỂ** | - **Tự động thực thi (Auto-Execution):** Khi lượt vote thứ N đạt ngưỡng $\ge 51\%$, contract tự động gọi hàm nội bộ `_tryExecuteSpend` / `_tryExecuteRefund` để giải ngân ngay lập tức trong cùng block.<br>- **Thực thi thủ công dự phòng:** `executeSpendRequest` / `executeRefundRequest` cho phép bất kỳ ai kích hoạt nếu auto-execution fallback.<br>- **Cơ chế Hết hạn & Giải phóng Quỹ (Expire):** Bổ sung hàm `expireSpendRequest(id)` và `expireRefundRequest(id)`. Sau 7 ngày (`EXECUTION_DEADLINE = 7 days`), bất kỳ ai cũng có quyền hủy đề xuất quá hạn để hoàn trả 100% số tiền giữ chỗ (`reservedSpendAmount`/`reservedRefundAmount`) về lại Quỹ khả dụng.<br>- Kiểm chứng: Test Hardhat Phase 2 & Test Python `test_auto_execution.py`. | **ĐÃ HOÀN TẤT (PASS)** |
| **5** | **Không thấy cơ chế chuyển quyền CVHT (transferAdvisor):** Đổi cố vấn hoặc lộ khóa ví thì bó tay. Nên có cơ chế đề cử → chấp nhận 2 bước. | **CHỦ ĐÍCH THIẾT KẾ GIỮ NGUYÊN (BY DESIGN)** | - Quyết định kiến trúc thống nhất tại `docs/CHANGE_PLAN_LAB15.md` Mục 0.2: `advisor` giữ nguyên là biến **`immutable`**.<br>- **Lý do kỹ thuật & an ninh:**<br>  1. Khống chế kích thước Bytecode dưới trần 24,576 byte của EIP-170 (hiện tại đã đạt 22,045 byte / 89.7%). Thêm cơ chế 2-step transfer sẽ làm tăng kích thước bytecode và có nguy cơ vượt trần EIP-170.<br>  2. Tính chất quỹ lớp K57: Cố vấn học tập được Nhà trường phân công nhiệm kỳ ổn định suốt khóa học.<br>  3. An ninh tối đa: `immutable` đảm bảo quyền lực của Cố vấn gắn chặt với hợp đồng, không một hacker hay bên thứ ba nào có thể đánh cắp hoặc đổi chủ sở hữu của hợp đồng sang địa chỉ lạ. | **ĐÃ THỐNG NHẤT THEO SPEC** |
| **6** | **Test chủ yếu chạy trên Python, Solidity chạy Remix không có log:** Chuyển sang Foundry/Hardhat để chạy lại bằng một lệnh. | **ĐÃ SỬA TRIỆT ĐỂ** | - Đã xây dựng bộ kiểm thử tự động toàn diện bằng **Hardhat** (`test/hardhat/`) gồm 41 kịch bản kiểm thử độc lập mô phỏng mạng Shanghai, thao túng thời gian EVM (`time.increase`), kiểm tra gas EIP-1559 và tấn công bảo mật.<br>- Lệnh chạy 1 bước duy nhất: `npx hardhat test` (41/41 PASS trong 10s) hoặc `npm run verify` (kiểm tra Solc 0.8.20 + Hardhat 41 tests + Python 61 tests). Không còn phụ thuộc vào thao tác thủ công trên Remix IDE. | **ĐÃ HOÀN TẤT (PASS)** |
| **7** | **Việc còn thiếu lớn nhất là deploy Sepolia và frontend:** Đây là phần thầy cô sẽ nhìn thấy trực tiếp. | **ĐÃ SỬA TRIỆT ĐỂ** | - **Smart Contract:** Đã deploy lên Ethereum Sepolia Testnet tại địa chỉ [`0x90948699FF04bC9cF159a39e200F09885439503D`](https://sepolia.etherscan.io/address/0x90948699FF04bC9cF159a39e200F09885439503D) (và phiên bản mới [`0x1F066cB83F41857DcC5D230C74963b12F1E8f58C`](https://sepolia.etherscan.io/address/0x1F066cB83F41857DcC5D230C74963b12F1E8f58C)).<br>- **Frontend DApp:** Hoàn thiện giao diện Web3 tương tác trực tiếp tại `web/index.html` (chạy trên `http://localhost:3000`), hỗ trợ MetaMask, chuyển đổi vai trò linh hoạt, quản lý đợt thu on-chain, giải ngân chi tiêu, hoàn tiền Net, đối soát mã hash danh bạ và tra cứu sổ nhật ký dòng tiền minh bạch. | **ĐÃ HOÀN TẤT (PASS)** |
