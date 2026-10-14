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