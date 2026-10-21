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

