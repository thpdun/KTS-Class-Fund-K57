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
  - **Hoãn kích hoạt 3 ngày (`BCS_ACTIVATION_DELAY = 3 days`):** Thành viên BCS mới được thêm phải đủ 3 ngày mới được tạo đề xuất hoặc bỏ phiếu, chặn việc CVHT bổ nhiệm tức thời ví ma để lũng đoạn biểu quyết.
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
> **Lưu ý quan trọng về môi trường kiểm chứng:** Hợp đồng `ProjectCore.sol` tính đến hết Lab 15 **CHƯA ĐƯỢC TRIỂN KHAI (DEPLOY) LÊN MẠNG SEPOLIA TESTNET**. Mọi kết quả hoạt động hiện tại được kiểm chứng trên môi trường giả lập Python cục bộ (`test/test_economic_rules.py`), Hardhat test suite (`test/hardhat/ProjectCore.*.test.js`), trình biên dịch `solc 0.8.20`, và các kiểm thử Solidity (`test/ProjectCore_test.sol` & `test/ProjectCore_integration_test.sol`). Các tệp kiểm thử Solidity ở trạng thái: **ĐÃ BIÊN DỊCH THÀNH CÔNG (CHƯA CHẠY TRÊN REMIX)**.

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
| **Kiểm thử Sepolia** | On-chain public testnet | Sepolia ETH | Triển khai và tương tác on-chain qua MetaMask. | **CHƯA KIỂM THỬ** (Tuân thủ yêu cầu không deploy ở Phase 6). | *Chờ chỉ đạo* |
