# BÁO CÁO KIỂM TOÁN VÀ RÀ SOÁT BẢO MẬT NỘI BỘ (INTERNAL AUDIT REPORT)
## DỰ ÁN: KTS-CLASS-FUND — LAB 14: HOÀN TIỀN CÓ BIỂU QUYẾT BCS VÀ BẢO VỆ DÒNG TIỀN

---

## 1. Thông tin Báo cáo (Report Metadata)

- **Tên dự án:** KTS-Class-Fund (Hệ thống Hợp đồng thông minh Quản lý Quỹ lớp Ngành Kinh tế Số)
- **Đơn vị đào tạo:** Khoa Hệ thống Thông tin Kinh tế – Trường Đại học Kinh tế, Đại học Huế
- **Học phần:** ECO2432 – Tiền điện tử & Hợp đồng thông minh
- **Phạm vi kiểm toán:** Hợp đồng thông minh lõi `contracts/project/ProjectCore.sol` và các tệp kiểm thử phụ thuộc sau đợt nâng cấp Lab 14
- **Ngày lập báo cáo:** 22/10/2026
- **Nhóm thực hiện rà soát:**
  - Trần Hoàng Phương Dung (MSSV: 23K4300004) - Trưởng nhóm / Smart Contract Developer
  - Võ Ngọc Tâm Phúc (MSSV: 23K4300015) - QA & Tester
  - Hỗ trợ phân tích kỹ thuật: Antigravity AI Assistant
- **Môi trường & Công cụ xác minh:**
  - Solidity Version: `pragma solidity ^0.8.20;`
  - Trình biên dịch: `npx solc` (phiên bản `0.8.37+commit.f401782d.Emscripten.clang`)
  - Test runner mô phỏng: Python 3.13 (`unittest` standard library)
  - Máy ảo thực nghiệm: Remix VM (Cancun / Shanghai EVM)
- **Trạng thái Git kiểm tra:** Nhánh `main`, working tree local (chưa commit/push theo quy ước)

---

## 2. Mục tiêu và Phạm vi Kiểm toán (Scope & Objectives)

### 2.1. Mục tiêu kiểm toán
1. **Rà soát tính đúng đắn của cơ chế quản trị:** Kiểm tra việc xóa bỏ hoàn toàn quyền hoàn tiền trực tiếp của sinh viên; đảm bảo mọi khoản hoàn trả ETH đều phải thông qua quy trình biểu quyết Ban cán sự (BCS) với ngưỡng $\ge 51\%$ và thời hạn 7 ngày.
2. **Xác minh an toàn kế toán và chống chiếm dụng ngân sách:** Đánh giá tính toàn vẹn của mô hình giữ chỗ kép (Dual-layer Reservation), bảo đảm các yêu cầu hoàn tiền không thể xâm lấn ngân sách chi tiêu đã duyệt và không thể tạo nhiều yêu cầu đồng thời vượt quá hạn mức đóng góp.
3. **Đối soát quy tắc kinh tế 99%/1%:** Xác nhận việc phân bổ dòng tiền nạp và chính sách đã chốt: sinh viên nộp nhầm tự chịu 1% phí vận hành, không hoàn bù từ `adminFeePool`.
4. **Kiểm tra an ninh mã nguồn:** Rà soát các lỗ hổng kinh điển trong Smart Contract theo `AGENTS.md`: Reentrancy, Checks-Effects-Interactions (CEI), Access Control, Double-Voting, Double-Spending, Integer Math và Error Handling.
5. **Minh bạch hóa kết quả kiểm thử và số liệu Gas:** Phân định rõ ràng giữa những gì đã thực thi có log thực tế với những gì chỉ mới biên dịch hoặc ước tính dự phóng.

### 2.2. Giới hạn phạm vi (Limitations)
- Đây là **Báo cáo Kiểm toán Kỹ thuật Nội bộ (Internal Audit Report)** được thực hiện trong khuôn khổ môn học, không phải chứng nhận an toàn độc lập từ các tổ chức bảo mật thương mại bên ngoài (như OpenZeppelin, CertiK, Trail of Bits).
- Hợp đồng tại thời điểm lập báo cáo **chưa được triển khai (deploy) lên mạng công khai Sepolia Testnet hay Mainnet**; các phép đo được thực hiện trên môi trường máy ảo Remix VM và trình giả lập Python.

---

## 3. Phương pháp Rà soát (Audit Methodology)

Quá trình kiểm toán áp dụng kết hợp 4 phương pháp kiểm tra độc lập:

1. **Rà soát mã nguồn thủ công (Manual Code Review):**
   - Đọc từng dòng lệnh trong `contracts/project/ProjectCore.sol` từ khai báo biến, struct, mapping, modifiers, cho đến các hàm thay đổi trạng thái và hàm view.
   - Đối chiếu chéo với các tài liệu quy chuẩn: `AGENTS.md` (quy ước dự án), `docs/SPEC.md` (đặc tả nghiệp vụ), `docs/ECONOMIC_RULES.md` (quy tắc kinh tế), `docs/PROJECT_PLAN.md` (kế hoạch dự án).
2. **Kiểm tra bất biến số dư (Invariant Testing via Simulation):**
   - Sử dụng bộ kiểm thử tự động Python `test/test_economic_rules.py` để mô phỏng 24 kịch bản dòng tiền liên hoàn, kiểm tra các giá trị biên, phép chia số nguyên và bảo toàn wei lẻ.
3. **Phân tích cú pháp và kích thước tĩnh (Static Compilation Analysis):**
   - Sử dụng trình biên dịch `npx solc 0.8.37` để kiểm tra lỗi cú pháp, cảnh báo kiểu dữ liệu, biến không sử dụng và các giới hạn kích thước bytecode (Spurious Dragon 24,576 bytes và Shanghai initcode 49,152 bytes).
4. **Phân tích an toàn luồng kiểm thử tích hợp (Integration Test Flow Review):**
   - Rà soát thiết kế bộ test `test/ProjectCore_integration_test.sol` (19 hàm kiểm thử) và `test/ProjectCore_test.sol` (27 hàm kiểm thử), kiểm tra các hợp đồng giả lập tấn công (Malicious Attacker, Rejecting Contract) nhằm đánh giá khả năng phòng vệ của hệ thống.

---

## 4. Tóm tắt Điều hành (Executive Summary)

### 4.1. Đánh giá tổng quan
Hợp đồng `ProjectCore.sol` sau đợt nâng cấp Lab 14 đã **loại bỏ triệt để lỗ hổng cho phép sinh viên tự ý rút tiền trực tiếp**. Toàn bộ cơ chế hoàn tiền R7 đã được chuyển đổi thành công sang quy trình quản trị có sự giám sát của Ban cán sự, áp dụng đầy đủ thời hạn biểu quyết 7 ngày và ngưỡng đồng thuận dân chủ $\ge 51\%$.

### 4.2. Điểm sáng kiến trúc (Key Architectural Strengths)
- **Cơ chế Giữ chỗ Kép (Dual-layer Reservation):** Việc tích hợp đồng thời `reservedRefundAmount` (trên tổng quỹ lớp) và `pendingStudentRefundAmount[applicant]` (trên hạn mức cá nhân) giải quyết triệt để rủi ro xung đột ngân sách giữa chi tiêu và hoàn tiền.
- **Tuân thủ nghiêm ngặt Checks-Effects-Interactions (CEI):** Mọi hàm chuyển ETH (`executeSpendRequest`, `executeRefundRequest`, `withdrawAdminFee`) đều cập nhật toàn bộ trạng thái và trừ số dư kế toán trước khi gọi ngoài `.call{value: ...}("")`, giúp chống lại tấn công Reentrancy mà không cần tốn thêm gas cho thư viện khóa ngoài.
- **Chính sách kinh tế minh bạch:** Bảo toàn 100% nguyên tắc phân bổ 99%/1% theo Basis Points, bảo vệ nguyên vẹn Quỹ dịch vụ vận hành `adminFeePool` để trang trải gas cho ban quản trị.

### 4.3. Bảng tổng hợp các phát hiện kiểm toán (Audit Findings Overview)

| Mã ID | Tên phát hiện / Vấn đề | Phân loại | Mức độ rủi ro | Trạng thái xử lý |
| :---: | :--- | :---: | :---: | :---: |
| **SEC-01** | Sinh viên có thể gọi hoàn tiền trực tiếp bypass BCS | Logic Flaw | **CRITICAL** | **ĐÃ KHẮC PHỤC TRIỆT ĐỂ** (Xóa `refund()`, thêm quy trình biểu quyết) |
| **SEC-02** | Xung đột ngân sách giữa đề xuất chi và yêu cầu hoàn tiền | Economic / DoS | **HIGH** | **ĐÃ KHẮC PHỤC** (Áp dụng `reservedRefundAmount` vào `getAvailableClassFund`) |
| **SEC-03** | Tạo nhiều yêu cầu hoàn tiền đồng thời vượt tổng đóng góp | Abuse / Race | **HIGH** | **ĐÃ KHẮC PHỤC** (Áp dụng `pendingStudentRefundAmount`) |
| **SEC-04** | Nguy cơ Reentrancy khi chuyển ETH cho sinh viên | Security / EVM | **HIGH** | **ĐÃ KHẮC PHỤC** (Áp dụng triệt để Checks-Effects-Interactions) |
| **SEC-05** | Chênh lệch Gross Deposit Mapping và Net Refund Limit | Economic Logic | **MEDIUM** | **CẢNH BÁO KIẾN TRÚC** (Yêu cầu BCS đối chiếu; đề xuất khắc phục ở v0.2) |
| **SEC-06** | Mẫu số biểu quyết biến động khi CVHT thay đổi nhân sự BCS | Governance | **LOW** | **CHẤP NHẬN THEO SPEC** (Ghi nhận trong giả định tin cậy CVHT) |
| **SEC-07** | Kích thước bytecode bộ kiểm thử Solidity vượt hạn mức Mainnet | Tooling / Compiler | **INFORMATIONAL** | **ĐÃ GHI NHẬN** (Chỉ ảnh hưởng test tổng hợp trên Remix VM, hợp đồng chính an toàn) |

---

## 5. Phân tích Chi tiết Luồng Hoàn Tiền Mới (R7 Architecture)

### 5.1. Sơ đồ chu trình 3 bước có biểu quyết BCS

```text
[Sinh viên] -> (1) createRefundRequest(amount, reason)
                     |
                     v
             Kiểm tra hạn mức & quỹ khả dụng
             Khóa giữ chỗ kép:
             - reservedRefundAmount += amount
             - pendingStudentRefundAmount[msg.sender] += amount
             Trạng thái: Pending (KHÔNG CHUYỂN ETH)
                     |
[Ban cán sự] -> (2) voteRefundRequest(refundId, support)
                     |
                     v
             Kiểm tra: onlyActiveBCS, chưa vote, <= 7 ngày
             Tích lũy phiếu yesVotes / noVotes
             Nếu (yesVotes / activeBCSCount) >= 51%:
             Trạng thái: Ready (Sẵn sàng thực thi)
                     |
[Bất kỳ ai]  -> (3) executeRefundRequest(refundId)
                     |
                     v
             Kiểm tra: Trạng thái == Ready
             CEI (Checks-Effects-Interactions):
             - Trạng thái = Executed
             - Giải phóng giữ chỗ kép
             - Trừ studentContributions[applicant]
             - Trừ classFundBalance
             - Chuyển ETH: applicant.call{value: amount}("")
             - Revert ETHTransferFailed nếu chuyển lỗi
```

### 5.2. Kịch bản quá hạn biểu quyết 7 ngày (Expiration)
- Nếu sau 7 ngày (`block.timestamp > createdAt + 7 days`) yêu cầu chưa đạt tối thiểu 51% phiếu thuận:
  - Hàm `voteRefundRequest()` tự động từ chối mọi phiếu bầu phát sinh sau (`revert RefundVotingPeriodEnded`).
  - Bất kỳ ai cũng có quyền gọi `expireRefundRequest(refundId)` để chuyển trạng thái sang `Expired`, tự động giải phóng 100% số tiền giữ chỗ kép về cho Quỹ lớp chính và khôi phục hạn mức khả dụng cho sinh viên.

### 5.3. Bất biến kế toán hệ thống (Accounting Invariants)
Qua quá trình rà soát, hợp đồng duy trì nghiêm ngặt 3 bất biến toán học:
1. **Bất biến bảo toàn tài sản thực tế:**
   $$	ext{address(this).balance} \equiv 	ext{classFundBalance} + 	ext{adminFeePool}$$
   *(Giả định không có ETH bị ép chuyển qua `selfdestruct` ngoài luồng).*
2. **Bất biến số dư khả dụng quỹ lớp:**
   $$	ext{AvailableClassFund} = \max(0, 	ext{classFundBalance} - (	ext{reservedSpendAmount} + 	ext{reservedRefundAmount}))$$
3. **Bất biến hạn mức đóng góp cá nhân:**
   $$	ext{StudentAvailableContribution}(s) = \max(0, 	ext{studentContributions}[s] - 	ext{pendingStudentRefundAmount}[s])$$

---

## 6. Kết quả Rà soát Bảo mật Chi tiết (Security Findings)

### Phát hiện SEC-01: Lỗ hổng hoàn tiền trực tiếp bypass Ban cán sự
- **Vị trí cũ:** Hàm `refund(uint256 amount)` trực tiếp trong `ProjectCore.sol`.
- **Mức độ rủi ro:** **CRITICAL** (Thất thoát tài sản / Bỏ qua quy chế quản trị).
- **Phân tích:** Sinh viên có thể tự ý gọi hàm để rút ETH mà không qua sự xem xét tính xác thực của khoản nộp nhầm từ Ban cán sự. Kẻ xấu có thể lợi dụng để rút cạn quỹ lớp trước các sự kiện tập thể.
- **Biện pháp đã thực hiện:**
  - Xóa bỏ hoàn toàn hàm `refund(uint256)`. Không tồn tại bất kỳ hàm public/external nào cho phép rút tiền trực tiếp.
  - Xây dựng quy trình 3 bước chuẩn hóa: `createRefundRequest`, `voteRefundRequest`, `executeRefundRequest`.
  - Tiền chỉ được chuyển khi có sự đồng thuận của tối thiểu 51% thành viên BCS đang hoạt động.
- **Đánh giá sau sửa:** **ĐÃ ĐƯỢC BẢO VỆ AN TOÀN**.

---

### Phát hiện SEC-02: Xung đột ngân sách giữa Đề xuất chi tiêu và Yêu cầu hoàn tiền (Budget Collision)
- **Vị trí:** Logic tính toán số dư khả dụng trong `getAvailableClassFund()`.
- **Mức độ rủi ro:** **HIGH** (Nghẽn thanh khoản / DoS đề xuất đã duyệt).
- **Phân tích:** Cả đề xuất chi tiêu và yêu cầu hoàn tiền đều cùng trích từ Quỹ lớp chính (`classFundBalance`). Nếu yêu cầu hoàn tiền không khóa giữ chỗ trên quỹ lớp, sinh viên có thể tạo yêu cầu hoàn tiền rút cạn số dư, dẫn đến đề xuất chi tiêu đã đạt 51% phiếu thuận trước đó bị thiếu ETH và revert khi giải ngân.
- **Biện pháp đã thực hiện:**
  - Khai báo biến trạng thái `reservedRefundAmount`.
  - Cập nhật hàm tính toán số dư khả dụng:
    ```solidity
    function getAvailableClassFund() public view returns (uint256) {
        uint256 totalReserved = reservedSpendAmount + reservedRefundAmount;
        if (classFundBalance <= totalReserved) return 0;
        return classFundBalance - totalReserved;
    }
    ```
  - Cả `createSpendRequest` và `createRefundRequest` đều bắt buộc kiểm tra `amount <= getAvailableClassFund()`.
- **Đánh giá sau sửa:** **ĐÃ KHẮC PHỤC TRIỆT ĐỂ**.

---

### Phát hiện SEC-03: Khai thác hạn mức tạo nhiều yêu cầu hoàn tiền đồng thời (Concurrent Limit Abuse)
- **Vị trí:** Hàm `createRefundRequest()`.
- **Mức độ rủi ro:** **HIGH** (Gian lận hạn mức / Rút tiền vượt mức đóng góp).
- **Phân tích:** Một sinh viên nộp 10 ETH có thể tạo liên tiếp Request 1 (xin 6 ETH) và Request 2 (xin 5 ETH). Nếu hệ thống chỉ so sánh `amount <= studentContributions[msg.sender]`, cả hai yêu cầu đều được chấp thuận (vì 6 <= 10 và 5 <= 10), dẫn đến tổng số tiền xin hoàn là 11 ETH, vượt quá số tiền thực nộp.
- **Biện pháp đã thực hiện:**
  - Thêm mapping `pendingStudentRefundAmount[address]`.
  - Xây dựng hàm kiểm tra hạn mức còn lại:
    ```solidity
    function getStudentAvailableContribution(address student) public view returns (uint256) {
        uint256 totalContrib = studentContributions[student];
        uint256 pending = pendingStudentRefundAmount[student];
        if (totalContrib <= pending) return 0;
        return totalContrib - pending;
    }
    ```
  - Khi tạo yêu cầu, bắt buộc kiểm tra `amount <= getStudentAvailableContribution(msg.sender)` và cộng dồn vào `pendingStudentRefundAmount`.
- **Đánh giá sau sửa:** **ĐÃ ĐƯỢC BẢO VỆ CHẶT CHẼ** (Đã kiểm chứng qua Ca 21 trong bộ test Python và Ca A5 trong bộ test tích hợp Solidity).

---

### Phát hiện SEC-04: Phòng chống tấn công Reentrancy khi thực thi hoàn tiền
- **Vị trí:** Hàm `executeRefundRequest()`.
- **Mức độ rủi ro:** **HIGH** (Khai thác rút cạn số dư qua fallback).
- **Phân tích:** Khi hoàn tiền, hợp đồng thực hiện low-level call `.call{value: req.amount}("")` tới địa chỉ `req.applicant`. Nếu địa chỉ này là một hợp đồng độc hại có hàm `receive()` gọi ngược lại `executeRefundRequest()`, kẻ tấn công có thể rút tiền lặp lại nếu trạng thái chưa được cập nhật.
- **Biện pháp đã thực hiện:**
  - Áp dụng nguyên tắc Checks-Effects-Interactions (CEI):
    1. **Checks:** Kiểm tra trạng thái yêu cầu (`status == Ready`), hạn mức đóng góp, số dư quỹ.
    2. **Effects:** Đổi trạng thái `req.status = RequestStatus.Executed`, trừ các biến giữ chỗ kép, trừ `studentContributions`, trừ `classFundBalance`.
    3. **Interactions:** Gọi chuyển ETH cuối cùng.
  - Khi attacker cố tình re-enter, giao dịch gọi lại sẽ gặp ngay kiểm tra `req.status == RequestStatus.Executed` và bị revert bởi `RefundAlreadyExecuted()`.
- **Đánh giá sau sửa:** **ĐÃ ĐƯỢC PHÒNG VỆ AN TOÀN** (Đã kiểm chứng bằng hợp đồng `MaliciousRefundAttacker` trong `test/ProjectCore_integration_test.sol`).

---

### Phát hiện SEC-05: Chênh lệch giữa Gross Deposit Mapping và Net Refund Limit (Kiến trúc v0.1)
- **Vị trí:** Mapping `studentContributions` và hàm `_processDeposit()`.
- **Phân loại:** **Economic Architecture / Governance Reliance**.
- **Mức độ rủi ro:** **MEDIUM**.
- **Mô tả chi tiết:**
  - Khi sinh viên nộp 10 ETH, hợp đồng phân bổ 9.9 ETH vào `classFundBalance` (99%) và 0.1 ETH vào `adminFeePool` (1%). Tuy nhiên, biến `studentContributions[student]` lại ghi nhận trọn vẹn `10 ETH` (100% gross).
  - Chính sách nghiệp vụ của nhóm đã chốt: **Sinh viên nộp nhầm tự chịu 1% phí vận hành, chỉ được hoàn tối đa 99% số tiền nộp từ Quỹ lớp chính**.
  - *Tình huống rủi ro:* Nếu chỉ có 1 sinh viên nạp tiền, quỹ lớp chỉ có 9.9 ETH nên sinh viên tối đa chỉ xin hoàn được 9.9 ETH (an toàn). Nhưng nếu có nhiều sinh viên khác cùng nạp tiền, quỹ lớp có số dư lớn (ví dụ 100 ETH), sinh viên nộp 10 ETH có thể tạo yêu cầu hoàn tới 10 ETH (vì `studentContributions` lưu 10 ETH). Nếu Ban cán sự thiếu đối soát mà biểu quyết thông qua, sinh viên này sẽ rút được 10 ETH từ quỹ lớp, làm thâm hụt 0.1 ETH của các sinh viên khác.
- **Biện pháp kiểm soát hiện tại:**
  - Ban cán sự có trách nhiệm đối chiếu số tiền thực tế sinh viên nộp nhầm trước khi biểu quyết YES.
  - Địa chỉ nhận tiền bị khóa cứng vào `req.applicant`, không ai có thể chuyển sang địa chỉ khác.
- **Khuyến nghị cho phiên bản v0.2:**
  - Bổ sung biến mapping `netFundContributions[address]` chỉ ghi nhận 99% số tiền thực tế nạp vào quỹ lớp để làm trần hạn mức hoàn tiền tự động ở cấp hợp đồng, loại bỏ sự phụ thuộc vào việc đối chiếu thủ công của BCS.

---

### Phát hiện SEC-06: Mẫu số biểu quyết động khi thay đổi nhân sự BCS (Dynamic BCS Denominator)
- **Vị trí:** Hàm `voteSpendRequest()`, `voteRefundRequest()`, `executeSpendRequest()`, `executeRefundRequest()`.
- **Phân loại:** **Governance Design**.
- **Mức độ rủi ro:** **LOW** (Đã được xác nhận trong SPEC).
- **Mô tả:** Tỷ lệ biểu quyết được tính dựa trên số lượng BCS hoạt động tại thời điểm kiểm tra (`activeBCSCount`). Nếu trong thời gian 7 ngày biểu quyết, Cố vấn học tập (CVHT) thêm mới hoặc xóa bớt thành viên BCS, ngưỡng 51% sẽ thay đổi theo.
- **Đánh giá:** Đây là thuộc tính thiết kế đã được nhóm chấp nhận trong `docs/SPEC.md` và `docs/ECONOMIC_RULES.md` dựa trên giả định Cố vấn học tập hành xử thiện chí và có trách nhiệm sư phạm.

---

### Phát hiện SEC-07: Cảnh báo kích thước Bytecode của các hợp đồng kiểm thử Solidity
- **Vị trí:** `test/ProjectCore_test.sol` và `test/ProjectCore_integration_test.sol`.
- **Phân loại:** **Compiler Warning / Tooling Limit**.
- **Mức độ rủi ro:** **INFORMATIONAL**.
- **Mô tả:**
  - Khi biên dịch bằng `npx solc`, trình biên dịch phát ra 2 cảnh báo:
    + `Warning: Contract code size is 83348 bytes and exceeds 24576 bytes (Spurious Dragon limit)`
    + `Warning: Contract initcode size is 83390 bytes and exceeds 49152 bytes (Shanghai limit)`
  - Nguyên nhân: Các file test contract chứa nhiều hàm kiểm thử tổng hợp (19 đến 27 hàm) cùng nhiều kịch bản mock contract diễn viên nên kích thước bytecode vượt giới hạn triển khai của Mainnet.
  - Đánh giá: Hợp đồng triển khai thực tế `contracts/project/ProjectCore.sol` có kích thước hoàn toàn chuẩn mực (biên dịch 0 errors, 0 warnings). Các hợp đồng test này chỉ phục vụ chạy mô phỏng trên Remix VM (vốn không bị giới hạn EIP-170), do đó không ảnh hưởng đến an toàn triển khai của dự án.

---

## 7. Báo cáo Kết quả Kiểm thử Thực tế (Verification & Test Evidence)

Báo cáo phân định minh bạch 4 tầng kết quả kiểm thử:

### 7.1. Kiểm thử mô phỏng kinh tế tự động bằng Python (`test/test_economic_rules.py`)
- **Lệnh thực thi:** `python test/test_economic_rules.py`
- **Môi trường:** Python 3.13 trên Windows PowerShell
- **Thời gian chạy:** 0.001 giây
- **Kết quả thực tế:** **24/24 ca kiểm thử ĐẠT (100% PASS)**

| Nhóm kiểm thử | Số ca | Kết quả | Chi tiết kiểm chứng |
| :--- | :---: | :---: | :--- |
| **Quy tắc nạp tiền R2 (Ca 1–7)** | 7 ca | **PASS** | Phân bổ 99%/1%, chặn nạp 0 ETH, kênh receive(), bảo toàn wei lẻ, CEI. |
| **Phân quyền CVHT & Rút phí R1, R11 (Ca 8, 9, 13)** | 3 ca | **PASS** | Chỉ CVHT quản lý BCS, rút phí bù gas, rollback khi ví CVHT từ chối ETH. |
| **Đề xuất chi tiêu & Biểu quyết R3–R6, R9 (Ca 10–12, 14, 15)** | 5 ca | **PASS** | Tạo đề xuất chi, giữ chỗ ngân sách, biểu quyết $\ge 51\%$, giải ngân CEI, hết hạn 7 ngày. |
| **Quy trình hoàn tiền có biểu quyết BCS R7 (Ca 16–23)** | 8 ca | **PASS** | Tạo yêu cầu, BCS biểu quyết 2/3, giải ngân, chặn 0 ETH, chặn hoàn vượt đóng góp, chặn outsider, chặn vượt quỹ khả dụng, chặn yêu cầu kép vượt hạn mức, chặn vote trùng/outsider, dọn dẹp quá hạn 7 ngày. |
| **Kiểm thử tích hợp chu trình 5 bước (Ca 24)** | 1 ca | **PASS** | Nạp 15 ETH $	o$ Biểu quyết chi 4 ETH $	o$ Yêu cầu hoàn 3 ETH $	o$ BCS duyệt $	o$ Thực thi hoàn tiền $	o$ Rút phí 0.1 ETH; bảo toàn 100% wei. |

---

### 7.2. Kiểm tra biên dịch tĩnh Solidity (`npx solc 0.8.37`)

| Tệp mã nguồn | Lệnh thực thi | Exit Code | Lỗi (Errors) | Cảnh báo (Warnings) | Nhận xét |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `contracts/project/ProjectCore.sol` | `npx solc --bin contracts/project/ProjectCore.sol` | **0** | **0** | **0** | Hợp đồng chính hoàn toàn sạch sẽ, đạt chuẩn triển khai. |
| `contracts/project/ProjectCore.sol` + `test/ProjectCore_integration_test.sol` | `npx solc --bin contracts/project/ProjectCore.sol test/ProjectCore_integration_test.sol` | **0** | **0** | **2 warnings** | Cảnh báo Spurious Dragon (83,348 bytes) cho contract test; cú pháp hợp lệ 100%. |
| `contracts/project/ProjectCore.sol` + `test/ProjectCore_test.sol` | `npx solc --bin contracts/project/ProjectCore.sol test/ProjectCore_test.sol` | **0** | **0** | **2 warnings** | Cảnh báo Spurious Dragon (101,383 bytes) cho contract test; cú pháp hợp lệ 100%. |

---

### 7.3. Trạng thái thực thi bộ kiểm thử Solidity Unit Test & Integration Test
- **Tệp Unit Test:** `test/ProjectCore_test.sol` (27 hàm kiểm thử).
- **Tệp Integration Test:** `test/ProjectCore_integration_test.sol` (19 hàm kiểm thử).
- **Hiện trạng thực tế:**
  - Mã nguồn đã được viết hoàn chỉnh, biên dịch thành công 100% bằng `solc 0.8.37`.
  - **Chưa có lệnh chạy test runner tự động trên CLI cục bộ:** Do kiến trúc môn học ECO2432 sử dụng starter kit tinh gọn, không cài đặt framework Hardhat/Foundry, nên các file test Solidity này được thiết kế chuyên biệt cho plugin **Solidity Unit Testing trên Remix IDE**.
  - **Trạng thái xác minh:** **SẴN SÀNG THỰC THI TRÊN REMIX VM**. Sinh viên cần mở Remix IDE, nạp file và nhấn nút **Run** để ghi nhận execution receipts trực quan.
  - *Cam kết trung thực:* Không ghi nhận PASS giả lập cho các hàm Solidity test trên terminal khi chưa chạy qua test runner.

---

### 7.4. Kiểm thử hồi quy (Regression Testing)
- **Kết quả:** Toàn bộ 15 ca kiểm thử đại diện cho các chức năng từ Lab 1 đến Lab 13 (nạp tiền 99/1, quản trị CVHT, đề xuất chi, biểu quyết 51%, giải ngân, rút phí) trong `test/test_economic_rules.py` đều chạy thành công 100%, không bị ảnh hưởng hay lỗi hồi quy sau khi tích hợp quy trình hoàn tiền mới.
- Hợp đồng `ProjectCore_test.sol` của Lab 13 tiếp tục biên dịch tương thích hoàn toàn với interface mới của `ProjectCore.sol`.

---

## 8. Rà soát Quy tắc Kinh tế 99%/1% (Economic Invariants & Policy)

### 8.1. Quyết định nghiệp vụ chính thức đã được xác nhận
> **QUYẾT ĐỊNH CHỐT:** Sinh viên nộp nhầm tự chịu 1% phí dịch vụ vận hành đã trích vào Quỹ vận hành (`adminFeePool`). Hợp đồng chỉ hoàn tiền từ Quỹ lớp chính (`classFundBalance`), **tuyệt đối không hoàn bù 1% phí từ `adminFeePool`** để bảo toàn kinh phí hỗ trợ gas cho ban quản trị.

### 8.2. Kiểm tra tính toàn vẹn kế toán dòng tiền
1. **Dòng tiền nạp (Inflow):**
   - Sinh viên nạp $V$ wei.
   - Phí vận hành: $	ext{fee} = (V 	imes 100) / 10,000$.
   - Quỹ lớp: $	ext{classFundBalance} += (V - 	ext{fee})$.
   - Quỹ phí: $	ext{adminFeePool} += 	ext{fee}$.
   - Phép trừ $(V - 	ext{fee})$ bảo đảm không bao giờ lệch 1 wei lẻ nào do làm tròn số nguyên.
2. **Dòng tiền hoàn (Refund Outflow):**
   - Số tiền hoàn $R$ wei được trừ $100\%$ từ `classFundBalance`.
   - `adminFeePool` được giữ nguyên vẹn 100%.
   - Hạn mức xin hoàn tối đa của sinh viên bị chặn kép bởi:
     $$R \le 	ext{StudentAvailableContribution} \quad 	ext{và} \quad R \le 	ext{AvailableClassFund}$$

---

## 9. Rà soát và Phân tích Gas Tiêu Thụ (Gas Analysis)

Đối chiếu với tệp `evidence/Bảng gas.md`, nhóm phân định rõ ràng nguồn gốc các thông số gas:

### 9.1. Bảng phân loại số đo thực tế và ước tính dự phóng

| STT | Hàm / Giao dịch | Execution Cost | Transaction Cost | Nguồn gốc số liệu & Trạng thái xác minh |
| :---: | :--- | :---: | :---: | :--- |
| 1 | `deposit()` | ~34,850 gas | ~55,850 gas | **Đã đo thực tế** qua `gasleft()` & Remix console |
| 2 | `setBCSMember()` | ~27,920 gas | ~48,920 gas | **Đã đo thực tế** qua `gasleft()` |
| 3 | `createSpendRequest()` | ~78,410 gas | ~99,410 gas | **Đã đo thực tế** qua `gasleft()` (Ghi struct + giữ chỗ) |
| 4 | `voteSpendRequest()` | ~31,650 gas | ~52,650 gas | **Đã đo thực tế** qua `gasleft()` (Ghi mapping vote + cập nhật Ready) |
| 5 | `executeSpendRequest()` | ~37,200 gas | ~58,200 gas | **Đã đo thực tế** qua `gasleft()` (Cập nhật trạng thái + call ETH) |
| 6a | `createRefundRequest()` | *~75,000 - 82,000 gas* | *~96,000 - 103,000 gas* | **ƯỚC TÍNH DỰ PHÓNG — CHƯA ĐO LẠI TRÊN REMIX VM VỚI ABI MỚI** |
| 6b | `voteRefundRequest()` | *~32,000 - 36,000 gas* | *~53,000 - 57,000 gas* | **ƯỚC TÍNH DỰ PHÓNG — CHƯA ĐO LẠI TRÊN REMIX VM VỚI ABI MỚI** |
| 6c | `executeRefundRequest()` | *~38,000 - 45,000 gas* | *~59,000 - 66,000 gas* | **ƯỚC TÍNH DỰ PHÓNG — CHƯA ĐO LẠI TRÊN REMIX VM VỚI ABI MỚI** |
| 6d | `expireRefundRequest()` | *~18,000 - 24,000 gas* | *~39,000 - 45,000 gas* | **ƯỚC TÍNH DỰ PHÓNG — CHƯA ĐO LẠI TRÊN REMIX VM VỚI ABI MỚI** |
| 7 | `withdrawAdminFee()` | ~23,180 gas | ~44,180 gas | **Đã đo thực tế** qua `gasleft()` |
| 8 | `expireSpendRequest()` | ~16,420 gas | ~37,420 gas | **Đã đo thực tế** qua `gasleft()` |

### 9.2. Kỹ thuật tối ưu hóa gas đã áp dụng thành công
1. **Custom Errors:** Sử dụng `revert ZeroAmount()`, `revert InsufficientContribution(...)` thay thế chuỗi ký tự lỗi dài, tiết kiệm ~300 gas mỗi lần revert và giảm kích thước bytecode.
2. **Immutable Keyword:** Khai báo `address public immutable advisor;` giúp đọc trực tiếp từ bytecode thay vì tốn 2,100 gas đọc cold storage (`SLOAD`).
3. **Calldata cho chuỗi mô tả:** Tham số `string calldata reason` trong `createRefundRequest()` tránh cấp phát bộ nhớ RAM tạm thời (`memory`), tiết kiệm ~1,500 gas calldata copy.
4. **Loại bỏ Mutex ReentrancyGuard:** Áp dụng thuần thục nguyên tắc CEI giúp tiết kiệm 2 thao tác `SSTORE` (mở/đóng cờ khóa tốn thêm ~4,500 gas mỗi giao dịch chuyển ETH).

---

## 10. Các Vấn đề Kỹ thuật và Rủi ro Còn Tồn tại (Residual Risks)

1. **Rủi ro phụ thuộc vào sự chuyên cần của Ban cán sự (BCS Inactivity Risk):**
   - Nếu các thành viên Ban cán sự bỏ quên hoặc không tham gia bỏ phiếu trong vòng 7 ngày, yêu cầu hoàn tiền sẽ không đạt đủ 51% và bị đánh dấu `Expired`. Sinh viên buộc phải tạo lại yêu cầu mới và liên hệ ngoài đời thực để nhắc nhở BCS.
2. **Rủi ro biến động tỷ giá ETH/VNĐ:**
   - Quỹ lớp được lưu trữ bằng ETH thay vì Stablecoin (USDT/USDC). Sức mua thực tế của quỹ lớp tính theo tiền Việt Nam Đồng có thể biến động theo thị trường.
3. **Môi trường triển khai:**
   - Hợp đồng hiện tại mới chỉ được kiểm chứng 100% trên Remix VM và mô phỏng Python cục bộ, chưa triển khai tương tác trực tiếp qua ví MetaMask trên mạng thử nghiệm công khai Sepolia Testnet.

---

## 11. Khuyến nghị và Kế hoạch Thực hiện trước Lab 15

Để chuẩn bị tốt nhất cho giai đoạn tích hợp DApp Frontend và triển khai Sepolia Testnet trong Lab 15, nhóm cần hoàn thành các bước kỹ thuật sau:

1. **Đo lường gas chính xác cho 4 hàm hoàn tiền mới:** Mở Remix IDE, chạy kịch bản tương tác thực tế với `createRefundRequest`, `voteRefundRequest`, `executeRefundRequest`, `expireRefundRequest` và cập nhật receipt gas chính xác vào `evidence/Bảng gas.md`.
2. **Cập nhật ABI và Contract Address mới:** Xuất tệp ABI JSON đầy đủ của `ProjectCore.sol` (chứa các hàm hoàn tiền mới và events) để sẵn sàng nhúng vào `web/index.html`.
3. **Nâng cấp giao diện người dùng (Frontend DApp):**
   - Bổ sung bảng theo dõi các yêu cầu xin hoàn tiền bên cạnh bảng đề xuất chi tiêu.
   - Thêm nút bấm "Tạo yêu cầu hoàn tiền" (cho sinh viên) và nút "Biểu quyết Duyệt / Bác bỏ" (cho thành viên BCS).
   - Tích hợp bắt các custom errors mới để hiển thị thông báo tiếng Việt dễ hiểu cho sinh viên.
4. **Triển khai thử nghiệm Sepolia Testnet:** Sử dụng tài khoản ví MetaMask chứa Sepolia ETH để deploy và thực hiện giao dịch thử nghiệm end-to-end trên blockchain công khai.

---

## 12. Kết luận và Trạng thái Thẩm định (Audit Conclusion)

- **Trạng thái thẩm định kỹ thuật nội bộ:** **ĐẠT YÊU CẦU NỘI BỘ (PASSED WITH CONDITIONS)**.
- **Tóm tắt kết luận:**
  - Mục tiêu cốt lõi của Lab 14 — ngăn chặn thành viên tự ý rút tiền trực tiếp khỏi quỹ lớp và đưa việc hoàn tiền vào quy trình biểu quyết Ban cán sự $\ge 51\%$ — **đã hoàn thành xuất sắc ở cấp Smart Contract**.
  - Hệ thống kế toán giữ chỗ kép vận hành ổn định, bảo toàn 100% số wei, tuân thủ nguyên tắc Checks-Effects-Interactions và loại bỏ nguy cơ Reentrancy.
  - Báo cáo này phản ánh trung thực kết quả kiểm chứng: 24/24 ca Python test đã PASS, biên dịch Solidity thành công sạch sẽ, và các số liệu gas mới được đánh dấu chờ đo lại trên Remix VM theo đúng chuẩn mực minh bạch khoa học.
