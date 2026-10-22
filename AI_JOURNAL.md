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
