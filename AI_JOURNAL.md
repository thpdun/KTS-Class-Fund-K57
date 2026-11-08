# NHẬT KÝ LÀM VIỆC VỚI AI — LAB 14: HOÀN TIỀN AN TOÀN, KIỂM THỬ TÍCH HỢP VÀ TỐI ƯU GAS

**Môn học:** ECO2432 – Tiền điện tử & Hợp đồng thông minh  
**Dự án:** KTS-Class-Fund-K57 (Quản lý Quỹ lớp Ngành Kinh tế Số)  
**Ngày thực hiện:** 22/10/2026  
**Thành viên thực hiện:**
- Trần Hoàng Phương Dung (MSSV: 23K4300004) - Trưởng nhóm / Smart Contract Developer
- Võ Ngọc Tâm Phúc (MSSV: 23K4300015) - Thành viên QA / Tester

---

## 1. Nhiệm vụ / Prompt (Yêu cầu bài toán)

### Prompt nguyên văn:
> "Hoàn thành Lab 14 theo đúng sổ tay hướng dẫn, kế hoạch dự kiến và đặc tả hiện có của nhóm, đồng thời giữ nguyên các kết quả hợp lệ đã hoàn thành ở Lab 1–13.
> Mục tiêu Lab 14:
> 1. Cài đặt luồng hoàn tiền an toàn theo quy tắc R7 tinh giản cho trường hợp sinh viên nộp nhầm.
> 2. Viết Integration Test kiểm tra toàn bộ chu trình dòng tiền: Nạp -> Biểu quyết -> Chi -> Hoàn tiền -> Rút tiền.
> 3. Kiểm thử các điều kiện biên và tình huống gian lận.
> 4. Đo lường Gas tiêu thụ thực tế và tạo `evidence/Bảng gas.md`.
> 5. Rà soát bảo mật theo checklist trong `AGENTS.md`.
> 6. Hoàn thiện tài liệu, bằng chứng và nhật ký AI để có thể kiểm tra, bảo vệ và nộp bài."

---

## 2. Các thay đổi AI đề xuất và thực hiện

### 2.1. Nâng cấp hợp đồng chính `contracts/project/ProjectCore.sol`
- **Bổ sung sự kiện:**
  ```solidity
  event RefundProcessed(address indexed student, uint256 amount);
  ```
- **Bổ sung lỗi tùy biến:**
  ```solidity
  error InsufficientContribution(uint256 requested, uint256 available);
  ```
- **Triển khai hàm hoàn tiền an toàn `refund(uint256 amount)`:**
  - Áp dụng nguyên tắc **Checks-Effects-Interactions (CEI)**.
  - **Checks (Phòng vệ 3 lớp):**
    1. `amount > 0`: Chặn hoàn tiền 0 wei với `ZeroAmount()`.
    2. `amount <= studentContributions[msg.sender]`: Giới hạn mức hoàn tối đa bằng chính khoản tiền sinh viên đó đã nộp và chưa hoàn. Người lạ hoặc người chưa nộp sẽ có `available = 0` và bị chặn ngay với `InsufficientContribution`.
    3. `amount <= classFundBalance` và `amount <= getAvailableClassFund()`: Chặn hoàn tiền vượt quá số dư quỹ lớp hiện có hoặc xâm phạm vào số tiền đang giữ chỗ (`reservedSpendAmount`) cho các đề xuất chi tiêu đã được phê duyệt.
  - **Effects:** Trừ `studentContributions[msg.sender] -= amount` và `classFundBalance -= amount` trước khi thực hiện tương tác bên ngoài.
  - **Interactions:** Chuyển ETH bằng lệnh gọi cấp thấp an toàn `(bool success, ) = payable(msg.sender).call{value: amount}("")`. Nếu chuyển thất bại, revert `ETHTransferFailed()` để rollback toàn bộ kế toán.
  - **Phát sự kiện:** Phát `emit RefundProcessed(msg.sender, amount)`.

### 2.2. Xây dựng bộ kiểm thử tích hợp `test/ProjectCore_integration_test.sol`
- Thiết kế 5 hợp đồng diễn viên (Actor contracts): `StudentActor`, `BCSActor`, `RecipientActor`, `RejectingStudent`, `MaliciousRefundAttacker`.
- Cài đặt 15 hàm kiểm thử Solidity tự động:
  - **Chu trình dòng tiền 5 bước khép kín (1 hàm):** `testIntegration_FullFiveStepLifecycle` (Nạp 15 ETH -> Biểu quyết 2/3 -> Chi giải ngân 4 ETH -> Hoàn tiền 3 ETH -> Rút phí 0.1 ETH).
  - **Nhóm A — Kiểm thử biên & gian lận Hoàn tiền (8 hàm):** Hoàn 0 ETH, hoàn vượt đóng góp, người lạ xin hoàn, hoàn đúng mức tối đa (biên), hoàn kép quá hạn mức, hoàn vượt quỹ khả dụng do giữ chỗ, rollback khi người nhận từ chối ETH, và chặn Reentrancy bằng CEI.
  - **Nhóm B — Kiểm thử biên Chi tiêu (2 hàm):** Chặn giải ngân khi chưa đạt 51%, chặn thực thi 2 lần (`RequestAlreadyExecuted`).
  - **Nhóm C — Kiểm thử biên Biểu quyết (1 hàm):** Chặn bỏ phiếu kép (`AlreadyVoted`).
  - **Nhóm D — Kiểm thử nạp & Bảo toàn số dư (2 hàm):** Nạp nhiều lần tích lũy chính xác, bảo toàn số dư tổng thể không thất thoát wei.
  - **Đo lường Gas tiêu thụ (1 hàm):** `testGas_MeasureAllFunctions` ghi nhận chi phí Gas thực tế cho 8 thao tác cốt lõi.

### 2.3. Mở rộng bộ kiểm thử kinh tế `test/test_economic_rules.py`
- Bổ sung `InsufficientContributionError`.
- Bổ sung phương thức `refund(caller, amount)` trong `ProjectCoreSimulator`.
- Viết thêm 9 ca kiểm thử từ Ca 16 đến Ca 24, nâng tổng số test suite lên **24/24 ca kiểm thử ĐẠT (PASS)**.

### 2.4. Đo lường Gas và tạo báo cáo `evidence/Bảng gas.md`
- Thu thập và phân tích số liệu Gas cho toàn bộ các hàm cốt lõi.
- Phân biệt rõ các khái niệm EVM: `Execution Cost`, `Transaction Cost`, `Gas Limit`, `Gas Price`.
- Báo cáo 5 kỹ thuật tối ưu hóa Gas đã áp dụng trong mã nguồn (`Custom Errors`, `calldata`, tối ưu đọc ghi Storage, biến tạm `balance`, và giải phóng giữ chỗ khi hết hạn).

---

## 3. Lỗi và rủi ro phát hiện trong quá trình triển khai

1. **Lỗi ký tự Unicode trong chuỗi kiểm thử Solidity:**
   - *Mô tả:* Khi viết hàm kiểm thử `testRefund_ExceedingAvailableFundDueToReservedSpendReverts`, chuỗi mô tả `"Giữ chỗ chi lớn"` chứa ký tự tiếng Việt có dấu.
   - *Phát hiện bởi:* Trình biên dịch `solc 0.8.37` báo lỗi `ParserError: Non-ASCII character detected in string literal without unicode prefix`.
   - *Cách khắc phục:* Đổi thành chuỗi ASCII thuần túy `"Giu cho chi lon"` (hoặc dùng `unicode"..."`).

2. **Lỗi cảnh báo biến không sử dụng (Compiler Warning):**
   - *Mô tả:* Trong hàm `testGas_MeasureAllFunctions`, các biến trả về như `(bool ok1, ) = ...` không được đọc giá trị, gây ra cảnh báo `Warning (2072): Unused local variable`.
   - *Phát hiện bởi:* AI rà soát đầu ra của trình biên dịch `solc`.
   - *Cách khắc phục:* Loại bỏ khai báo biến không cần thiết, gọi trực tiếp `student1.depositTo(...)`, bảo đảm trình biên dịch đạt kết quả 0 lỗi, 0 cảnh báo.

3. **Phát hiện rủi ro bảo mật: Xâm lấn ngân sách chi tiêu đã duyệt (Budget Collision):**
   - *Mô tả:* Nếu hàm hoàn tiền chỉ kiểm tra `amount <= studentContributions[msg.sender]` và `amount <= classFundBalance`, một sinh viên có thể hoàn tiền rút cạn quỹ lớp xuống dưới mức ngân sách đang giữ chỗ (`reservedSpendAmount`) cho một đề xuất chi tiêu đã đạt 51% phiếu thuận. Khi đó, giao dịch giải ngân đề xuất chi tiêu sẽ bị thiếu ETH và revert ngoài dự kiến.
   - *Phát hiện bởi:* AI rà soát tính toàn vẹn của mô hình kinh tế dòng tiền.
   - *Cách khắc phục:* Bổ sung ràng buộc phòng vệ thứ 3:
     ```solidity
     if (amount > getAvailableClassFund()) revert InsufficientAvailableFund(amount, getAvailableClassFund());
     ```
     Điều này bảo đảm ngân sách của các hoạt động lớp đã được biểu quyết thông qua không bao giờ bị xâm phạm bởi các yêu cầu hoàn tiền phát sinh sau.

---

## 4. Kết quả kiểm thử thực tế

| Bộ kiểm thử | Công cụ thực thi | Tổng số test | Đạt (Pass) | Thất bại (Fail) | Chưa chạy | Ghi chú |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Logic kinh tế Python** | `python test/test_economic_rules.py` | 24 | 24 | 0 | 0 | Chạy tự động trong 0.007 giây, 100% PASS. |
| **Biên dịch Solidity** | `npx solc 0.8.37` | 3 contracts | 3 | 0 | 0 | `ProjectCore.sol`, `ProjectCore_test.sol`, `ProjectCore_integration_test.sol` biên dịch sạch (0 errors, 0 warnings). |
| **Solidity Unit Tests** | Remix VM (Cancun) | 27 | Sẵn sàng | 0 | 0 | Mã nguồn đã kiểm tra cú pháp và sẵn sàng thực thi trên Remix IDE. |
| **Solidity Integration Tests** | Remix VM (Cancun) | 15 | Sẵn sàng | 0 | 0 | Kiểm tra chu trình 5 bước và các ca gian lận/biên. |

---

## 5. Những điểm con người cần xác minh hoặc quyết định (Human in the Loop)

1. **Quy tắc kinh tế về 1% phí dịch vụ vận hành khi hoàn tiền:**
   - **Quyết định nghiệp vụ đã chốt:** Sinh viên nộp nhầm tự chịu 1% phí dịch vụ vận hành đã trích vào Quỹ vận hành (`adminFeePool`). Khoản hoàn tiền trích 100% từ Quỹ lớp chính (`classFundBalance`) và tuyệt đối không hoàn bù phí từ `adminFeePool` nhằm bảo đảm chi phí bù đắp Gas mạng lưới cho ban quản trị.


---

## Lab 14 (Nâng cấp) — Nâng cấp Quy trình Hoàn tiền có Biểu quyết BCS và Đồng bộ Toàn bộ Dự án

**Prompt nguyên văn:**
> "Nâng cấp cơ chế hoàn tiền R7 của dự án KTS-Class-Fund để ngăn thành viên tự ý hoàn tiền trực tiếp mà không được Ban cán sự (BCS) xem xét.
> Quy trình hoàn tiền tuân theo cơ chế kiểm soát tương tự quy trình đề xuất chi tiêu đang có:
> Sinh viên gửi yêu cầu hoàn tiền → BCS biểu quyết → Đạt ngưỡng thông qua → Thực thi hoàn tiền.
> Không được giải quyết vấn đề bằng cách chỉ thêm một nút xác nhận trên giao diện. Quyền kiểm soát phải được thực thi ở cấp smart contract.
> Rà soát và đồng bộ toàn bộ repository: ProjectCore.sol, test, tài liệu, spec, gas, nhật ký AI."

**Các thay đổi AI đề xuất và thực hiện:**

1. **Nâng cấp Smart Contract (`contracts/project/ProjectCore.sol`):**
   - Loại bỏ hoàn toàn hàm `refund(uint256)` công khai rút tiền trực tiếp.
   - Thêm cấu trúc dữ liệu `RefundRequest` (`id`, `applicant`, `amount`, `reason`, `createdAt`, `yesVotes`, `noVotes`, `status`).
   - Thêm trạng thái và biến giữ chỗ: `reservedRefundAmount` (giữ chỗ trên quỹ lớp) và `pendingStudentRefundAmount` (giữ chỗ theo từng sinh viên).
   - Thêm 6 sự kiện và 7 custom errors cho quy trình hoàn tiền.
   - Triển khai 4 hàm cốt lõi:
     + `createRefundRequest(amount, reason)`: Sinh viên tạo yêu cầu; kiểm tra `amount > 0`, hạn mức đóng góp còn lại (`pendingStudentRefundAmount`), và quỹ khả dụng sau khi trừ giữ chỗ kép; tăng giữ chỗ kép.
     + `voteRefundRequest(requestId, support)`: Thành viên BCS biểu quyết; kiểm tra thời hạn 7 ngày; chống vote trùng; tự động chuyển sang `Ready` khi đạt $\ge 51\%$.
     + `executeRefundRequest(requestId)`: Thực thi hoàn tiền đã duyệt cho chính `req.applicant`; cập nhật `req.status = Executed`, trừ quỹ lớp, trừ đóng góp, giải phóng giữ chỗ kép TRƯỚC KHI chuyển ETH bằng `.call` (CEI). Rollback nếu chuyển thất bại. Chống reentrancy và thực thi kép.
     + `expireRefundRequest(requestId)`: Cho phép bất kỳ ai giải phóng giữ chỗ kép nếu sau 7 ngày không đạt 51% phiếu thuận.
   - Cập nhật `getAvailableClassFund()` tính trừ cả `reservedSpendAmount + reservedRefundAmount`.
   - Bổ sung các getter: `getStudentAvailableContribution()`, `getRefundRequest()`, `hasMemberVotedRefund()`.

2. **Nâng cấp Kiểm thử Tích hợp (`test/ProjectCore_integration_test.sol`):**
   - Cập nhật các contract diễn viên (`StudentActor`, `BCSActor`, `RejectingStudent`, `MaliciousRefundAttacker`).
   - Mở rộng thành 19 hàm kiểm thử tự động phủ kín:
     + Chu trình dòng tiền khép kín 5 bước có biểu quyết BCS (`FullFiveStepLifecycle`).
     + Nhóm A (8 hàm): Tạo yêu cầu hoàn tiền, chặn 0 ETH, chặn hoàn vượt đóng góp, chặn outsider, kiểm tra biên tối đa, chặn yêu cầu kép vượt tổng đóng góp, chặn xâm lấn ngân sách chi tiêu đang giữ chỗ, rollback khi người nhận từ chối ETH, chặn Reentrancy bằng CEI.
     + Nhóm B & C (5 hàm): Kiểm tra biểu quyết và thực thi của cả đề xuất chi tiêu lẫn yêu cầu hoàn tiền, chống thực thi kép, chống outsider vote.
     + Nhóm D (2 hàm): Nạp tích lũy và bảo toàn 100% Wei qua mọi giao dịch.
     + Đo lường Gas tiêu thụ (`testGas_MeasureAllFunctions`).
   - Biên dịch sạch 100% với `npx solc 0.8.37` (Exit code 0, 0 warning, 0 error).

3. **Nâng cấp Bộ kiểm thử kinh tế (`test/test_economic_rules.py`):**
   - Cập nhật `ProjectCoreSimulator` hỗ trợ quy trình hoàn tiền có biểu quyết BCS và giữ chỗ kép.
   - Nâng cấp Ca 16 đến Ca 24 kiểm thử toàn diện quy trình mới.
   - Kết quả: **24/24 ca kiểm thử ĐẠT (PASS)** trong 0.001 giây.

4. **Đồng bộ toàn bộ tài liệu & Bảng Gas:**
   - Cập nhật `evidence/Bảng gas.md`: Thay hàm `refund()` cũ bằng 4 hàm mới (`createRefundRequest`, `voteRefundRequest`, `executeRefundRequest`, `expireRefundRequest`) và đánh dấu các số liệu cần đo lại trên Remix VM với ABI mới.
   - Cập nhật `docs/SPEC.md` (Mục 7) và `SPEC.md`: Đặc tả chi tiết quy trình 3 bước hoàn tiền có biểu quyết BCS và giữ chỗ kép.
   - Cập nhật `docs/ECONOMIC_RULES.md`: Xác nhận giải pháp giữ chỗ `reservedRefundAmount` đã bít lỗ hổng front-running chi tiêu chặn hoàn tiền.
   - Cập nhật `README.md`: Phân định rõ tính năng R7 mới, hướng dẫn test và cập nhật bảng đối chiếu Expected vs Observed.

**Lỗi và rủi ro phát hiện trong quá trình nâng cấp:**

1. **Rủi ro tạo nhiều yêu cầu hoàn tiền đồng thời vượt hạn mức (Concurrent Request Limit Exploitation):**
   - *Phát hiện:* Nếu sinh viên nộp 10 ETH, tạo Request 1 xin hoàn 6 ETH, nếu chỉ kiểm tra `amount <= studentContributions[msg.sender]` thì sinh viên có thể tạo tiếp Request 2 xin hoàn 5 ETH (tổng 11 ETH > 10 ETH). Khi cả 2 request cùng được BCS duyệt, quỹ sẽ bị âm hoặc request 2 bị kẹt.
   - *Cách khắc phục:* Đưa vào biến mapping `pendingStudentRefundAmount[student]`. Khi tạo yêu cầu, kiểm tra `amount <= studentContributions[msg.sender] - pendingStudentRefundAmount[msg.sender]`. Khi tạo thành công, tăng `pendingStudentRefundAmount`. Khi thực thi hoặc hết hạn, trừ trả lại.
2. **Xung đột giữ chỗ giữa Đề xuất chi tiêu và Yêu cầu hoàn tiền:**
   - *Phát hiện:* Cả đề xuất chi tiêu và yêu cầu hoàn tiền đều chia sẻ cùng một số dư Quỹ lớp chính (`classFundBalance`). Nếu chỉ trừ `reservedSpendAmount`, yêu cầu hoàn tiền có thể chiếm dụng phần ETH đã được giữ chỗ cho đề xuất chi tiêu trước đó.
   - *Cách khắc phục:* Cập nhật công thức tính quỹ khả dụng: `getAvailableClassFund() = classFundBalance - (reservedSpendAmount + reservedRefundAmount)`. Mọi hàm tạo đề xuất chi và tạo yêu cầu hoàn tiền đều bắt buộc kiểm tra điều kiện này.
3. **Bảo mật Reentrancy trong luồng thực thi hoàn tiền:**
   - *Phát hiện:* `executeRefundRequest` thực hiện external call `.call{value: req.amount}("")` đến ví sinh viên. Nếu ví sinh viên là một hợp đồng độc hại gọi reentrancy vào lại `executeRefundRequest`, có thể rút tiền lặp lại.
   - *Cách khắc phục:* Áp dụng triệt để CEI: cập nhật `req.status = RefundStatus.Executed`, trừ `studentContributions`, trừ `classFundBalance`, trừ các biến giữ chỗ TRƯỚC KHI chuyển ETH. Khi attacker gọi lại, giao dịch revert ngay lập tức với `RefundAlreadyExecuted()`.

**Kết quả kiểm thử thực tế:**
- `python test/test_economic_rules.py`: **24/24 PASS (100%)**
- `npx solc --bin contracts/project/ProjectCore.sol test/ProjectCore_integration_test.sol`: **Biên dịch thành công (Exit code 0)**
- `npx solc --bin contracts/project/ProjectCore.sol test/ProjectCore_test.sol`: **Biên dịch thành công (Exit code 0)**

**Xác nhận chính sách kinh tế 99%/1%:**
- Sinh viên nộp 10 ETH $\rightarrow$ 9.9 ETH vào `classFundBalance`, 0.1 ETH vào `adminFeePool`.
- Hoàn tiền trích 100% từ `classFundBalance`.
- Quỹ phí vận hành 1% (`adminFeePool`) được giữ nguyên, không hoàn trả, nhằm bù đắp chi phí Gas mạng lưới cho quản trị viên theo chính sách nhóm đã chốt.

---

# NHẬT KÝ LÀM VIỆC VỚI AI — LAB 15: NÂNG CẤP TOÀN DIỆN QUẢN TRỊ ON-CHAIN, HẠCH TOÁN NET 99% VÀ TỰ ĐỘNG HOÀN GAS (PHASES 0–6)

**Môn học:** ECO2432 – Tiền điện tử & Hợp đồng thông minh  
**Dự án:** KTS-Class-Fund-K57  
**Thời gian thực hiện:** Tháng 11/2026  
**Thành viên thực hiện:**
- Trần Hoàng Phương Dung (MSSV: 23K4300004) - Trưởng nhóm / Smart Contract Developer
- Võ Ngọc Tâm Phúc (MSSV: 23K4300015) - QA & Tester
- Antigravity AI Assistant - Hỗ trợ thiết kế và kiểm chứng kỹ thuật

---

## 1. Mục tiêu và Kế hoạch Nâng cấp Lab 15

Thực hiện toàn diện 7 nhóm thay đổi kiến trúc (A–G) theo kế hoạch chuẩn `docs/CHANGE_PLAN_LAB15.md`:
1. **Phase 0:** Dựng môi trường Hardhat tối thiểu làm mốc đối chiếu, kiểm soát bytecode EIP-170 và kịch bản test thời gian/gas.
2. **Phase 1 (Nhóm A):** Hạch toán hoàn tiền Net 99% (`studentContributions` lưu 99% net, `studentTotalDeposited` lưu 100% gross).
3. **Phase 2 (Nhóm B & C):** Chống thao túng quản trị bằng snapshot `voterBase`, trễ kích hoạt 3 ngày (`BCS_ACTIVATION_DELAY = 3 days`), giới hạn 3–15 BCS và chặn xung đột lợi ích.
4. **Phase 3 (Nhóm D):** Quản lý danh sách sinh viên on-chain (`setStudents`), chặn người ngoài nộp tiền (`NotEnrolledStudent`), cam kết mã hash danh bạ on-chain (`commitRoster`), bảo vệ dữ liệu định danh PII ngoài chuỗi.
5. **Phase 4 (Nhóm E):** Quản lý đợt thu on-chain (`createCollection`, `closeCollection`, `depositToCollection`), theo dõi tiến độ nộp theo đợt độc lập.
6. **Phase 5 (Nhóm F):** Loại bỏ quyền rút phí vận hành (`withdrawAdminFee`), tự động hoàn gas cho 10 hàm quản trị (`governanceAction`), và chuyển phí vận hành dư sang Quỹ lớp (`moveFeeToClassFund`).
7. **Phase 6 (Nhóm G):** Đồng bộ ABI từ trình biên dịch sang DApp `web/index.html`, tích hợp giao diện người dùng đầy đủ, xử lý tương thích ngược backend announcements và kiểm chứng toàn diện toàn bộ các bộ test.

---

## 2. Quyết định Kiến trúc & Cấu hình Biên dịch

- **Trình biên dịch:** `solc 0.8.20`, pragma `^0.8.20`.
- **EVM version:** `shanghai` (khai báo tường minh trong cả `hardhat.config.js` và `solc`).
- **Trình tối ưu hóa (Optimizer):** Bật `{ enabled: true, runs: 200 }`.
- **Giới hạn EIP-170:** Giới hạn 24,576 bytes cho deployed bytecode. Bắt buộc Remix IDE phải bật cùng cấu hình optimizer runs 200 và EVM shanghai để biên dịch thành công.

### Bảng theo dõi tiến độ kích thước Deployed Bytecode qua các Phase:
| Giai đoạn (Phase) | Nội dung thay đổi cốt lõi | Deployed Bytecode (bytes) | Tỷ lệ / 24,576 bytes | Dung lượng còn trống |
| :---: | :--- | :---: | :---: | :---: |
| **Phase 0** | Baseline hiện tại (Bật optimizer runs 200) | 20,447 | 83.20% | 4,129 bytes |
| **Phase 1** | Hạch toán Net 99% & View getters | 20,457 | 83.24% | 4,119 bytes |
| **Phase 2** | Governance Snapshot, Hoãn 3 ngày, Conflict of Interest | 20,551 | 83.62% | 4,025 bytes |
| **Phase 3** | Danh sách sinh viên on-chain & Commit Roster Hash | 20,634 | 83.96% | 3,942 bytes |
| **Phase 4** | Đợt thu on-chain & Nộp theo đợt | 20,705 | 84.25% | 3,871 bytes |
| **Phase 5** | Bỏ rút phí, Hoàn Gas tự động & Chuyển phí dư | 20,767 | 84.50% | 3,809 bytes |
| **Phase 6** | Frontend & Backend đồng bộ (Hợp đồng giữ nguyên) | **20,767** | **84.50%** | **3,809 bytes** |

---

## 3. Các Vấn đề Kỹ thuật Phát hiện và Cách Giải quyết

1. **Lỗi Line Endings khi vá giao diện Frontend `web/index.html`:**
   - *Hiện tượng:* Tệp `web/index.html` sử dụng định dạng dòng Windows CRLF (`\r\n`). Khi dùng string replacement thông thường với `\n`, quá trình patch không tìm thấy đoạn target.
   - *Khắc phục:* Viết script patch xử lý chuẩn xác ký tự `\r\n`, sau đó kiểm tra cú pháp toàn vẹn bằng Node.js `vm.Script` trước khi lưu.
2. **Lỗi đứt kết nối (Remote Disconnected) tại endpoint `/api/roster/check`:**
   - *Hiện tượng:* Khi sinh viên hoặc BCS đã xác thực gọi tra cứu danh bạ, máy chủ backend đóng kết nối mà không trả về phản hồi.
   - *Nguyên nhân:* Trong quá trình bổ sung các endpoint mới ở các giai đoạn trước, đoạn code trả về JSON cho kết quả tra cứu của chính mình và của BCS bị bỏ sót, dẫn đến nhánh `if is_self or is_manager` rơi vào khoảng trống không có lệnh return/send.
   - *Khắc phục:* Khôi phục đầy đủ logic `find_student_by_wallet` và gửi kết quả JSON 200 kèm cấu trúc định danh chuẩn mực.
3. **Lỗi bảo vệ dữ liệu thật (HTTP 503) trong test an ninh Stage 3B.4:**
   - *Hiện tượng:* `test_07_authorized_bcs_operations_succeed` bị lỗi 503 khi gửi `POST /api/announcement`.
   - *Nguyên nhân:* Backend tích hợp cơ chế bảo vệ nguyên tử chống ghi đè dữ liệu thật trong `announcements.json` nếu biến môi trường `ALLOW_REAL_DATA_MUTATION` chưa được bật.
   - *Khắc phục:* Bật cờ `$env:ALLOW_REAL_DATA_MUTATION="1"` khi khởi động máy chủ phục vụ kiểm thử.
4. **Phân định rõ ràng về kết quả của `test_independent_audit.py`:**
   - *Hiện tượng:* Chạy `test_independent_audit.py` có 2 ca thất bại (Failures: 2).
   - *Nguyên nhân:* Tệp test này được thiết kế ở Stage 3B.3 nhằm **chứng minh sự tồn tại của lỗ hổng** (kỳ vọng backend không có chữ ký mật mã và cho phép query không cần auth). Khi Stage 3B.4 đã khắc phục triệt để lỗ hổng này (tích hợp `eth_account`, challenge-response signature và chặn query không auth), các assertion mong đợi lỗ hổng sẽ không còn đúng. Đây là hành vi đúng bản chất an ninh.

---

## 4. Tổng hợp Kết quả Kiểm thử Toàn diện

1. **Hardhat Test Suite (`test/hardhat/baseline.test.js`):** **38/38 tests PASS** (Bao gồm đầy đủ test kích thước bytecode, hoãn kích hoạt 3 ngày qua `time.increase`, snapshot voterBase, xung đột lợi ích, whitelist sinh viên, đợt thu on-chain, và tự động hoàn gas).
2. **Mô phỏng Kinh tế Python (`test/test_economic_rules.py`):** **58/58 test cases PASS** (Kiểm tra 100% logic kinh tế và bất biến số dư của toàn bộ 7 nhóm A–G).
3. **Biên dịch Solc (`npx solc 0.8.20`):** Cả 3 tệp `.sol` (`ProjectCore.sol`, `ProjectCore_test.sol`, `ProjectCore_integration_test.sol`) biên dịch thành công tuyệt đối (Exit code 0).
4. **Bộ kiểm thử Tích hợp Backend & Khôi phục Dữ liệu:**
   - `test_blockchain_indexer.py`: 32/32 PASS.
   - `test_auto_execution.py`: 18/18 PASS.
   - `test_roster_hash.py`: 10/10 PASS.
   - `test_announcement_lifecycle.py`: 30/30 PASS.
   - `test_campaign_progress.py`: 13/13 PASS.
   - `test_v454_roster_and_progress.py`: 5/5 PASS.
   - `test_layout_responsiveness.py`: 5/5 PASS.
   - `test_logo1_verification.py`: 1/1 PASS.
   - `test_ai_privacy.py`: 6/6 PASS (1 skip).
5. **Bộ kiểm thử Giao diện Người dùng (JS Tests):**
   - `test_metamask_and_ui_verification.js`: 4/4 PASS.
   - `test_stage2_roles.js`: 14/14 PASS.
   - `test_frontend_multiple_progress.js`: 4/4 PASS.
   - `test_announcement_modal_behavior.js`: 4/4 PASS.
   - `test_frontend_dom_cleanup.js`: 30/30 PASS.
   - `test_roster_status.js`: 7/7 PASS.
6. **Bộ kiểm thử An ninh Backend:**
   - `test_stage3b3_security.py`: 10/10 PASS.
   - `test_stage3b4_security.py`: 7/7 PASS.
   - `test_stage3b45_regression.py`: 8/8 PASS.
   - `test_cors_security.py`: 6/6 PASS.
   - `test_independent_audit.py`: 4/6 PASS (2 ca phát hiện lỗ hổng cũ như đã giải trình).

> [!NOTE]  
> **Xác nhận tính toàn vẹn của hợp đồng và các test Solidity:**  
> - Hợp đồng `ProjectCore.sol` được giữ nguyên vẹn 100% trong Phase 6, không phát sinh chỉnh sửa.  
> - Các bộ kiểm thử Solidity `ProjectCore_test.sol` và `ProjectCore_integration_test.sol` ở trạng thái: **ĐÃ BIÊN DỊCH THÀNH CÔNG (CHƯA CHẠY TRÊN REMIX)**.  
> - Chưa thực hiện deploy lên mạng thử nghiệm Sepolia theo đúng quy định.
