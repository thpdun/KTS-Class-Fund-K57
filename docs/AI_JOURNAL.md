## Lần 1: Rà soát Quy tắc Kinh tế (Lab 8)
**Prompt:** Bạn là người dùng thận trọng. Chỉ dựa trên SPEC và ECONOMIC_RULES dưới đây, hãy nêu 5 cách một người có thể lạm dụng quy tắc...
**AI trả về:** Trình bày 5 lỗ hổng nghiêm trọng gồm: Lợi dụng 7 ngày để rút tiền, Thao túng tỷ lệ 51% bằng quyền CVHT, Tiền hoàn bị kẹt do thiếu phí gas, Tạo nhiều lệnh rút cạn quỹ, và Spam hoàn tiền 1 wei.
**Đánh giá:** AI phân tích chính xác. Các lỗ hổng logic này hoàn toàn có thể xảy ra trong thực tế.
**Cách sửa:**
- Nhóm đã sửa lại quy tắc R2, R5 và bổ sung R8 vào tệp SPEC.md để bít lỗ hổng 7 ngày, chặn tạo nhiều lệnh cùng lúc và chặn spam 1 wei.
- Nhóm quyết định chấp nhận rủi ro lạm quyền của CVHT và rủi ro đùn đẩy phí gas, ghi chú rõ ràng vào Mục 4 của tệp ECONOMIC_RULES.md vì việc sửa code sẽ làm dự án v0.1 quá phức tạp.
**Ai phát hiện:** Công cụ AI.
## Lab 9 - Hợp đồng đầu tiên: Két tiết kiệm và ProjectCore
**Prompt:** Dựa vào tệp docs/SPEC.md và AGENTS.md, hãy viết mã nguồn Solidity cho contracts/project/ProjectCore.sol thực hiện luồng nạp quỹ lớp.
**AI trả về:** Sinh ra hợp đồng ProjectCore chứa hàm `depositFund()` và gọi chéo từ hàm `deposit()`.
**Đánh giá:** Phải sửa.
**Chỗ sai:** Gặp lỗi biên dịch `DeclarationError: Undeclared identifier. "deposit`due to function ordering/aliasing logic inside the contract.
**Cách sửa:** Gom logic nạp tiền trực tiếp vào một hàm `deposit()` duy nhất, loại bỏ hàm gọi chéo trung gian để tối ưu mã nguồn.
**Ai phát hiện:** Sinh viên phát hiện khi biên dịch trên Remix.
## Lab 10 - Rà soát và Kiểm toán mã nguồn ProjectCore.sol
**Prompt:** Dựa vào tệp contracts/project/ProjectCore.sol, AGENTS.md và docs/SPEC.md, hãy tiến hành audit (rà soát) toàn diện hợp đồng này theo tiêu chuẩn kỹ thuật (CEI, Custom Errors) và quy tắc nghiệp vụ (R2, R5, R7 SPEC).
**AI trả về:** Báo cáo kiểm toán chi tiết (Audit Scorecard) đánh giá đạt toàn bộ các tiêu chí kỹ thuật và nghiệp vụ. Đồng thời đưa ra 2 điểm cải tiến: (1) Bổ sung hàm receive() để hỗ trợ nạp tiền trực tiếp từ ví không qua DApp, và (2) Tối ưu hóa hàm getStudentContribution do biến public đã tự sinh getter.
**Đánh giá:** Rất chất lượng, giúp rà soát chặt chẽ tính tuân thủ quy tắc kinh tế và tối ưu trải nghiệm người dùng.
**Chỗ sai:** Không phát hiện lỗi logic hoặc lỗ hổng bảo mật nghiêm trọng (Reentrancy, Access Control).
**Cách sửa / Cải tiến:** Ghi nhận các điểm cải tiến về tối ưu bytecode và tính năng receive() cho giao dịch trực tiếp.
**Ai phát hiện:** Công cụ AI rà soát và Sinh viên kiểm duyệt kết quả kiểm toán.
# DANH SÁCH CÁC ĐIỂM PHÁT HIỆN & ĐỀ XUẤT CẢI TIẾN 

## 1. Chi tiết các phát hiện trong quá trình Audit ProjectCore.sol

### Phát hiện 1: Thiếu hàm `receive()` nhận ETH trực tiếp từ ví cá nhân
- **Vị trí:** Ngoài hàm `deposit()`, hợp đồng hiện tại thiếu phương thức nhận ETH mặc định.
- **Hậu quả:** Nếu người dùng hoặc sinh viên chuyển ETH thẳng từ ví MetaMask đến địa chỉ hợp đồng mà không gọi cụ thể hàm `deposit()`, giao dịch sẽ bị Revert do hợp đồng không có hàm nhận.
- **Cách tái hiện:** Mở Remix, chọn một tài khoản ví phụ, nhập giá trị Value (ví dụ 1 ETH), dán địa chỉ contract vào ô tương tác hoặc gửi trực tiếp không qua giao diện $\rightarrow$ Giao dịch thất bại.
- **Cách sửa:** Bổ sung hàm `receive() external payable` tích hợp logic kiểm tra số dư và phát sự kiện.

### Phát hiện 2: Hàm tra cứu `getStudentContribution` bị trùng lặp với getter mặc định
- **Vị trí:** Phần cuối hợp đồng (`getStudentContribution(address student)`).
- **Hậu quả:** Làm tăng dung lượng bytecode không cần thiết khi deploy vì biến `studentContributions` đã ở phạm vi `public` (Solidity tự sinh hàm getter).
- **Cách tái hiện:** Biên dịch hợp đồng trên Remix và kiểm tra thông số bytecode.
- **Cách sửa:** Giữ nguyên để tăng tính tường minh cho người mới đọc hoặc lược bỏ để tối ưu mã nguồn.

---

## 2. Bảng tổng hợp đánh giá và sửa lỗi (Audit Scorecard & Fix Log)

| Lỗi | Mô tả | Ai phát hiện | Cách khắc phục |
| :--- | :--- | :--- | :--- |
| **1** | Hợp đồng thiếu hàm `receive()` để nhận các giao dịch chuyển ETH trực tiếp từ ví cá nhân không qua giao diện DApp. | AI | Bổ sung hàm `receive() external payable` kết hợp kiểm tra `ZeroAmount()` và phát sự kiện `FundDeposited`. |
| **2** | Tồn tại hàm `getStudentContribution` thủ công trong khi biến `studentContributions` khai báo `public` đã tự sinh sẵn hàm getter. | AI | Giữ nguyên để phục vụ mục đích đọc hiểu mã nguồn hoặc lược bỏ để tối ưu bytecode. |
| **3** | Kiểm tra tính minh bạch sự kiện `FundDeposited` đảm bảo tham số `student` được đánh dấu `indexed` để tiện lợi cho frontend lọc dữ liệu. | Sinh viên | Giữ nguyên và cấu hình đúng chuẩn từ khóa `indexed`. |
| **4** | Kiểm tra tính hợp lệ của tham số `advisor` trong `constructor` nhằm tránh trường hợp gán nhầm địa chỉ `address(0)`. | Sinh viên | Bổ sung điều kiện kiểm tra `require(advisor != address(0), "Invalid advisor");` khi khởi tạo hợp đồng. |

---

## Lab 11 - Cài quy tắc kinh tế vào sản phẩm (Quy tắc R2)

**Prompt:** Bạn là một Senior Solidity Developer đồng thời là chuyên viên kiểm thử nghiệp vụ blockchain. Hãy thực hiện Lab 11 – Cài quy tắc kinh tế vào sản phẩm của dự án KTS-Class-Fund, tuân thủ sổ tay thực hành ECO2432... [Triển khai DUY NHẤT quy tắc kinh tế R2: nạp ETH tự động phân bổ 99% vào Quỹ lớp chính và 1% vào Quỹ dịch vụ vận hành adminFeePool, tính theo basis points, kiểm thử tự động, CEI].

**AI trả về:**
- Cập nhật hợp đồng `contracts/project/ProjectCore.sol`:
  - Thêm hằng số basis points: `FEE_BPS = 100`, `BPS_DENOMINATOR = 10_000`.
  - Thêm biến trạng thái: `classFundBalance` (Quỹ lớp chính) và `adminFeePool` (Quỹ vận hành).
  - Giữ nguyên `studentContributions` ghi nhận 100% tiền gốc phục vụ quy tắc hoàn tiền.
  - Thêm sự kiện `AdminFeeCollected(address indexed student, uint256 feeAmount)`.
  - Gom logic nạp tiền và phân bổ vào hàm nội bộ `_processDeposit()` dùng chung cho cả `deposit()` và `receive()`.
  - Hàm `getFundBalance()` trả về số dư khả dụng Quỹ lớp chính (`classFundBalance`), bổ sung `getTotalContractBalance()` tra cứu tổng ETH thực tế.
- Xây dựng 2 bộ kiểm thử tự động:
  - `test/ProjectCore_test.sol`: Kiểm thử đơn vị Solidity cho Remix IDE (Solidity Unit Testing).
  - `test/test_economic_rules.py`: Kiểm thử tự động trên Python 3.10+ theo chuẩn AGENTS.md (đổi wei sang ETH trước khi hiển thị, kiểm thử giá trị biên, số nguyên và gian lận).

**Đánh giá:** Dùng được, chất lượng xuất sắc. Đáp ứng đầy đủ quy tắc kinh tế R2, bảo toàn số dư (không thất thoát wei), chuẩn CEI, không dùng floating point và không làm hỏng cấu trúc hiện tại.

**Chỗ sai phát hiện:**
1. Khi chạy file `test/test_economic_rules.py` lần đầu trên Windows PowerShell, gặp lỗi `UnicodeEncodeError: 'charmap' codec can't encode character` do bảng mã console mặc định là cp1252 khi in chuỗi tiếng Việt.
2. Kiểm tra framework kiểm thử: Repo không có sẵn Hardhat/Foundry vì khóa học thiết kế xoay quanh Remix IDE và Python starter kit (`hce-web3-starter`). Không được tự ý cài thêm framework nặng làm ô nhiễm `package.json`.

**Cách sửa:**
1. Thêm đoạn mã tự động cấu hình bảng mã UTF-8 `sys.stdout.reconfigure(encoding='utf-8')` trong file test Python.
2. Xác minh biên dịch bằng `npx solc` (solc `0.8.37`) và chạy kiểm thử tự động toàn diện qua Python (`test/test_economic_rules.py` pass 5/5 ca), đồng thời tạo file test Solidity `test/ProjectCore_test.sol` để chạy trên Remix IDE.

**Ai phát hiện:** AI và Sinh viên kiểm duyệt phát hiện và khắc phục ngay trong phiên làm việc.

---

## Lab 12 - Gate Review 1: Duyệt Codebase và Phạm vi

**Prompt:** Bạn là Senior Smart Contract Reviewer, Technical Lead và trợ lý kỹ thuật cho dự án môn học ECO2432 – Tiền điện tử & Hợp đồng thông minh. Thực hiện LAB 12 — GATE REVIEW 1: DUYỆT CODEBASE VÀ PHẠM VI trong repo nhóm `KTS-Class-Fund`... [Rà soát sức khỏe repo từ Lab 8 đến 11, đối chiếu README, SPEC, ECONOMIC_RULES với ProjectCore.sol, kiểm tra ca hợp lệ/vi phạm, tạo `docs/GATE_REVIEW_1.md` và `docs/PROJECT_PLAN.md`, đề xuất kết luận và giữ trạng thái CHỜ GIẢNG VIÊN XÁC NHẬN].

**AI trả về:**
- Rà soát toàn bộ codebase và tài liệu hiện có, kiểm tra trạng thái Git sạch sẽ trên nhánh `main`.
- Đánh giá sức khỏe repo theo 5 nhóm tiêu chí: README, Tính nhất quán tài liệu, Hợp đồng ProjectCore, Ca hợp lệ/vi phạm, Lịch sử Git.
- Phát hiện khoảng cách lớn giữa đặc tả ban đầu (11 quy tắc R1–R11) và mã nguồn thực tế (mới triển khai duy nhất R2).
- Tạo tài liệu `docs/GATE_REVIEW_1.md` với bảng kiểm tra chi tiết, phân tích rủi ro, 3 việc ưu tiên hàng đầu, đề xuất thu hẹp phạm vi hợp lý và đề xuất kỹ thuật nội bộ "Qua có điều kiện", để trống phần `CHỜ GIẢNG VIÊN XÁC NHẬN`.
- Tạo mới `docs/PROJECT_PLAN.md` cập nhật tiến độ Lab 8–12 và lập kế hoạch chi tiết cho Lab 13–15 kèm tiêu chí hoàn thành (DoD) và ma trận RACI.

**Đánh giá:** Dùng được, tính khách quan và chuẩn mực kỹ thuật cao. Không giả lập kết quả thành công ảo, phản ánh đúng tình trạng code và tài liệu.

**Chỗ sai / Điểm phát hiện:**
1. File `docs/PROJECT_PLAN.md` chưa từng được tạo trong repo từ các Lab trước; tồn tại 2 file mẫu khung rỗng ở thư mục gốc (`SPEC.md` và `AI_JOURNAL.md`) dễ gây nhầm lẫn nếu không truy xuất vào thư mục `docs/`.
2. Nội dung `README.md` bị lệch pha với hiện trạng mã nguồn: mô tả các tính năng biểu quyết 51%, thời hạn 7 ngày, xử lý hoàn tiền như thể đã chạy, trong khi hợp đồng `ProjectCore.sol` mới chỉ có nạp tiền R2; chưa có hướng dẫn chạy test cụ thể.
3. Hợp đồng `ProjectCore.sol` đã trích 1% vào `adminFeePool` nhưng chưa có hàm `withdrawAdminFee()` để Cố vấn học tập rút phí bù đắp gas, gây nguy cơ ứ đọng ETH phí.

**Cách sửa / Biện pháp xử lý:**
1. Tạo mới tài liệu kế hoạch chuẩn `docs/PROJECT_PLAN.md` và báo cáo cổng kiểm duyệt `docs/GATE_REVIEW_1.md`.
2. Đã hoàn thiện cập nhật `README.md` khớp 100% với mã nguồn hiện tại, bổ sung hướng dẫn chạy test chi tiết từng bước cho cả Python (`test/test_economic_rules.py`) và Remix VM (`test/ProjectCore_test.sol`), bảng đối chiếu Expected vs Observed; cập nhật 2 tiêu chí README tương ứng trong `docs/GATE_REVIEW_1.md` sang trạng thái ĐẠT.
3. **Rà soát lại đề xuất thu hẹp phạm vi theo chỉ đạo của nhóm:** 
   - Không loại bỏ biểu quyết vì đây là chức năng cốt lõi của quỹ lớp. Giữ trọn vẹn quy tắc R4/R5: Ban cán sự bỏ phiếu với ngưỡng $\ge 51\%$ (5100 basis points) và thời hạn 7 ngày.
   - Giữ lại trường hợp hoàn tiền an toàn (R7 tinh giản) cho trường hợp nộp nhầm với điều kiện an toàn kép (`refundAmount <= studentContributions` và `<= classFundBalance`).
   - Tinh giản tải bằng cách hoãn các tính năng phụ trợ không bắt buộc: hoãn mã băm IPFS CID (`proofHash`), hoãn hàng đợi dọn dẹp đa trạng thái phức tạp, loại bỏ cơ chế ủy quyền biểu quyết (proxy voting) và token ERC-20.

**Ai phát hiện:** 
- AI ban đầu đề xuất cắt bỏ biểu quyết để giảm tải; Nhóm sinh viên phản biện và yêu cầu bảo toàn tính năng cốt lõi (biểu quyết 51%) cùng luồng hoàn tiền an toàn. AI và nhóm cùng rà soát lại và thống nhất tinh giản các tính năng phụ trợ thay thế.

**Phần sinh viên cần tự xác minh:**
- Trình tài liệu `docs/GATE_REVIEW_1.md` cho Giảng viên hướng dẫn tại buổi Gate Review 1 để nhận xét và xin chữ ký/kết luận chính thức.
- Thảo luận nội bộ nhóm để chốt 2 câu hỏi nghiệp vụ trước Lab 13: (1) Tỷ lệ hoàn tiền nộp nhầm là 99% hay 100%, (2) Quyền phê duyệt hoàn tiền thuộc về ai (CVHT trực tiếp hay BCS biểu quyết).
- Thống nhất phân công vai trò chính thức giữa các thành viên nhóm cho các mốc Lab 13, 14, 15 trong `docs/PROJECT_PLAN.md`.

## LAB 14: HOÀN TIỀN AN TOÀN, KIỂM THỬ TÍCH HỢP VÀ TỐI ƯU GAS

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
