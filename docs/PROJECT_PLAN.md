# KẾ HOẠCH DỰ ÁN KTS-CLASS-FUND (PROJECT PLAN)
**Dự án:** Quản lý Quỹ lớp Ngành Kinh tế Số (K57 - Trường Đại học Kinh tế, Đại học Huế)  
**Môn học:** ECO2432 – Tiền điện tử & Hợp đồng thông minh  
**Cập nhật lần cuối:** Sau Gate Review 1 (Lab 12)  
**Tình trạng kế hoạch:** Cập nhật hiện trạng thực tế và lập kế hoạch các chặng Lab 13–15

---

## 1. Giới thiệu dự án và Mục tiêu cốt lõi

### 1.1. Tên sản phẩm & Định vị
- **Tên sản phẩm:** **KTS-Class-Fund**
- **Đối tượng phục vụ:** Tập thể sinh viên, Ban cán sự lớp (BCS) và Cố vấn học tập (CVHT) ngành Kinh tế Số.
- **Vấn đề giải quyết:** Xóa bỏ sự thiếu minh bạch trong quản lý thu chi tiền mặt/tài khoản ngân hàng cá nhân; tự động hóa việc phân bổ chi phí dịch vụ vận hành (bù đắp phí Gas mạng lưới blockchain); lưu vết bất biến mọi giao dịch đóng góp và chi tiêu quỹ chung.

### 1.2. Quyết định nghiệp vụ cốt lõi đã xác nhận
1. **Dòng tiền nạp (Quy tắc R2 - Đã hoàn thành trong code hiện tại):** Mỗi khoản nạp ETH thành công của sinh viên được tự động trích **1%** (100 basis points) vào Quỹ dịch vụ vận hành (`adminFeePool`) và **99%** vào Quỹ lớp chính (`classFundBalance`).
2. **Quyền quản trị tối cao (Quy tắc R1 - Kế hoạch Lab 13):** Cố vấn học tập (`advisor`) là người duy nhất nắm quyền thêm mới, tạm khóa hoặc hủy tư cách thành viên Ban cán sự.
3. **Quyền rút quỹ dịch vụ (Quy tắc R11 - Kế hoạch Lab 13):** Cố vấn học tập là địa chỉ duy nhất có quyền rút tiền từ `adminFeePool` để hoàn bù chi phí Gas đã chi trả khi tương tác hợp đồng.
4. **Biểu quyết dân chủ $\ge 51\%$ & Giải ngân (Quy tắc R3, R4, R5, R6 - Kế hoạch Lab 13):** Biểu quyết là chức năng cốt lõi của hệ thống quản lý quỹ lớp, không loại bỏ. Thành viên BCS tạo đề xuất chi $\rightarrow$ các thành viên BCS bỏ phiếu (1 người = 1 phiếu, không double-voting) $\rightarrow$ kiểm tra tỷ lệ đồng ý đạt tối thiểu 51% (5100 basis points) và trong thời hạn 7 ngày $\rightarrow$ thực thi giải ngân qua lệnh gọi cấp thấp `.call`.
5. **Hoàn tiền an toàn (Quy tắc R7 tinh giản - Kế hoạch Lab 14):** Hỗ trợ trường hợp hoàn tiền nộp nhầm với điều kiện an toàn kép: số tiền hoàn không vượt quá số tiền sinh viên đã nộp (`refundAmount <= studentContributions[msg.sender]`) và không vượt quá số dư khả dụng của Quỹ lớp chính (`refundAmount <= classFundBalance`).
6. **An toàn tài chính (Anti-abuse):** Số tiền chi hoặc hoàn không bao giờ được vượt quá số dư khả dụng của Quỹ lớp chính; Quỹ dịch vụ vận hành được tách biệt độc lập; bảo toàn tổng số wei không thất thoát khi chia số nguyên.

---

## 2. Nhật ký tiến độ: Các mốc đã hoàn thành (Lab 8 – Lab 12)

| Mốc thời gian | Bài thực hành | Nội dung công việc thực tế | Kết quả đầu ra | Trạng thái |
| :---: | :--- | :--- | :--- | :---: |
| **Chặng 1** | **Lab 8** | Khởi tạo kho mã nguồn nhóm, cấu hình môi trường, lập đặc tả nghiệp vụ `SPEC.md` v0.1 và quy tắc kinh tế `ECONOMIC_RULES.md`. | Kho Git, đặc tả ban đầu | **HOÀN THÀNH** |
| **Chặng 1** | **Lab 9** | Viết phiên bản đầu tiên của hợp đồng thông minh `contracts/project/ProjectCore.sol` cho luồng nạp quỹ cơ bản. | Bytecode hợp đồng nạp tiền | **HOÀN THÀNH** |
| **Chặng 1** | **Lab 10** | Rà soát toàn diện (Audit) hợp đồng `ProjectCore.sol`, khắc phục lỗi thiếu hàm `receive()`, tối ưu hóa bytecode và cấu hình `indexed` cho sự kiện. | Báo cáo kiểm toán, bổ sung `receive()` | **HOÀN THÀNH** |
| **Chặng 2** | **Lab 11** | Cài đặt quy tắc kinh tế R2 (phân bổ 99% Quỹ lớp, 1% Quỹ dịch vụ vận hành theo Basis Points), xử lý số nguyên không lệch wei, xây dựng bộ test Python và test Solidity. | `ProjectCore.sol` cập nhật, bộ test 5 ca | **HOÀN THÀNH** |
| **Chặng 2** | **Lab 12** | Thực hiện Gate Review 1: Duyệt codebase, kiểm tra sức khỏe repo, rà soát khoảng cách đặc tả - mã nguồn, lập báo cáo thẩm định và điều chỉnh phạm vi. | `GATE_REVIEW_1.md`, `PROJECT_PLAN.md` | **ĐANG THỰC HIỆN** |

---

## 3. Đề xuất điều chỉnh và Tinh giản phạm vi kỹ thuật

> **NGUYÊN TẮC ĐIỀU CHỈNH CỦA NHÓM:**  
> - **Biểu quyết là chức năng cốt lõi:** Không tự động loại bỏ biểu quyết chỉ để giảm tải. Phải bảo toàn quy chế dân chủ của quỹ lớp.  
> - **Triển khai hoàn tiền ở trường hợp an toàn nhất:** Đưa vào trường hợp nộp nhầm với điều kiện rõ ràng, khả thi.  
> - **Giảm tải bằng cách hoãn các tính năng phụ trợ:** Cắt giảm/hoãn các thành phần phức tạp không bắt buộc theo SPEC (như IPFS, proxy voting, hàng đợi dọn dẹp đa trạng thái) thay vì cắt bỏ chức năng cốt lõi.

### 3.1. Phân định rõ 3 tầng thông tin của dự án

1. **Hiện trạng mã nguồn đã có (Đến hết Lab 11):**
   - Chỉ mới triển khai duy nhất **Quy tắc kinh tế R2**: Nạp ETH qua `deposit()` / `receive()`, tự động trích 1% vào `adminFeePool` và 99% vào `classFundBalance`.
   - Đã kiểm chứng qua 5 ca test tự động Python và thực nghiệm Remix VM đạt 100%.
   - **Chưa có:** Quản trị nhân sự BCS (R1), Rút phí vận hành (R11), Đề xuất chi (R3), Biểu quyết (R4, R5), Giải ngân (R6), Hoàn tiền (R7, R10).
2. **Kế hoạch triển khai kỹ thuật giai đoạn Lab 13–15:**
   - **Lab 13:** Cài đặt Phân quyền CVHT (R1), Rút phí (R11), Đề xuất chi & Biểu quyết $\ge 51\%$ (R3, R4, R5, R6).
   - **Lab 14:** Cài đặt Hoàn tiền an toàn (R7 tinh giản) & Kiểm thử tích hợp toàn diện, Đo lường Gas.
   - **Lab 15:** Kết nối DApp Frontend, tương tác ví MetaMask trên Sepolia.
3. **Nội dung quyết định nghiệp vụ đã chốt (Cập nhật sau Lab 14):**
   - Đang chờ Giảng viên hướng dẫn môn học ECO2432 đánh giá và xác nhận tại buổi Gate Review 1 (`CHỜ GIẢNG VIÊN XÁC NHẬN`).
   - **Cơ chế phê duyệt hoàn tiền:** Ban cán sự (BCS) biểu quyết dân chủ đạt $\ge 51\%$ trong thời hạn 7 ngày trước khi thực thi hoàn tiền.
   - **Tỷ lệ hoàn tiền:** Sinh viên nộp nhầm tự chịu 1% phí vận hành đã trích vào `adminFeePool`. Hoàn tiền trích 100% từ Quỹ lớp chính (`classFundBalance`), không hoàn bù phí từ `adminFeePool`.

### 3.2. Chi tiết phạm vi giữ lại cho phiên bản v0.1 (Ưu tiên cốt lõi)
- **Luồng nạp tiền & Trích phí (R2 - ĐÃ CÓ TRONG CODE):** 99% Quỹ lớp, 1% Quỹ vận hành.
- **Phân quyền Ban cán sự (R1 - KẾ HOẠCH LAB 13):** CVHT kích hoạt/hủy quyền thành viên BCS qua modifier `onlyAdvisor`.
- **Rút phí dịch vụ (R11 - KẾ HOẠCH LAB 13):** CVHT rút ETH từ `adminFeePool` để bù đắp phí Gas.
- **Quy trình Đề xuất chi & Biểu quyết $\ge 51\%$ tối thiểu (R3, R4, R5, R6 - KẾ HOẠCH LAB 13):**
  - *Bước 1 (Tạo đề xuất):* Thành viên BCS hợp lệ tạo đề xuất chi (`recipient`, `amount`, `description`) với `amount <= classFundBalance`.
  - *Bước 2 (Bỏ phiếu):* Các thành viên BCS bỏ phiếu (1 người = 1 phiếu, mapping `hasVoted` chống bỏ phiếu 2 lần).
  - *Bước 3 (Kiểm tra điều kiện):* Đạt tỷ lệ đồng ý tối thiểu 51% (5100 basis points) trên tổng số BCS hoạt động và trong thời hạn 7 ngày (`block.timestamp <= createdAt + 7 days`).
  - *Bước 4 (Thực thi):* Bất kỳ thành viên BCS nào gọi hàm thực thi khi đủ điều kiện, giải ngân qua `.call` và chuyển trạng thái `Executed`.
- **Luồng hoàn tiền an toàn (R7 tinh giản - KẾ HOẠCH LAB 14):**
  - Áp dụng riêng cho trường hợp sinh viên nộp nhầm tiền đóng góp.
  - Điều kiện an toàn kép: `refundAmount <= studentContributions[msg.sender]` và `refundAmount <= classFundBalance`.
  - Cập nhật số dư trước khi chuyển ETH (Checks-Effects-Interactions).

### 3.3. Phạm vi đề xuất hoãn / Tinh giản sang phiên bản v0.2 (Giảm tải kỹ thuật)
- **Hoãn lưu trữ mã băm IPFS CID (`proofHash`) & Upload file ảnh:** SPEC Mục 6 đã quy định việc lưu trữ file vật lý là ngoài phạm vi. Bỏ trường `bytes32 proofHash` để tinh giản giao diện web Lab 15 và tiết kiệm Gas lưu trữ on-chain.
- **Tinh giản cơ chế dọn dẹp hàng đợi quá hạn đa trạng thái phức tạp (R8, R9):** Thay vì xây dựng mảng hàng đợi đa trạng thái và hàm dọn dẹp riêng biệt, hợp đồng kiểm tra trực tiếp mốc thời gian `block.timestamp <= createdAt + 7 days` tại thời điểm bỏ phiếu và thực thi.
- **Loại bỏ cơ chế ủy quyền biểu quyết (Proxy Voting) / Phân bổ trọng số phiếu:** Đã được quy định Ngoài phạm vi trong Mục 6 SPEC; giữ mô hình đồng thuận dân chủ 1 thành viên BCS = 1 phiếu.
- **Giữ mô hình phân quyền phẳng (tránh RBAC đa cấp phức tạp):** Chỉ gồm 2 vai trò rõ ràng: Cố vấn học tập (Owner) và Ban cán sự (BCS).
- **Hoãn hỗ trợ ERC-20 Tokens (USDT/USDC) & Tiền pháp định (Fiat):** Tiếp tục bảo lưu trong v0.2, v0.1 thuần túy giao dịch bằng ETH.

---

## 4. Kế hoạch triển khai chi tiết cho các chặng tiếp theo (Lab 13 – Lab 15)

> **CẢNH BÁO QUY TRÌNH:** Tuyệt đối không đánh dấu các Lab 13–15 là hoàn thành trước khi thực hiện. Bảng kế hoạch dưới đây thể hiện lộ trình dự kiến.

### 4.1. Lab 13 — Hoàn thiện phân quyền CVHT & Luồng Biểu quyết cốt lõi
- **Mục tiêu:** Bổ sung đầy đủ quyền quản trị cho Cố vấn học tập (R1, R11) và hoàn thiện luồng đề xuất chi kèm cơ chế biểu quyết dân chủ $\ge 51\%$ (R3, R4, R5, R6).
- **Công việc cụ thể:**
  1. Xây dựng modifier `onlyAdvisor` và hàm quản lý danh sách Ban cán sự `setBCSMember(address member, bool status)` (R1).
  2. Xây dựng hàm `withdrawAdminFee(uint256 amount)` cho phép CVHT rút phí từ `adminFeePool` (R11), phát sự kiện `AdminFeeWithdrawn`.
  3. Xây dựng cấu trúc dữ liệu `SpendRequest` và hàm tạo yêu cầu chi `createSpendRequest(address payable recipient, uint256 amount, string memory description)` dành riêng cho thành viên BCS (R3).
  4. Xây dựng hàm bỏ phiếu `voteSpendRequest(uint256 requestId, bool support)` dành riêng cho BCS, chống double-voting, kiểm tra thời hạn 7 ngày (R4, R5).
  5. Xây dựng hàm thực thi giải ngân `executeSpendRequest(uint256 requestId)` kiểm tra ngưỡng $\ge 51\%$ (5100 basis points) và chuyển ETH qua `.call` theo nguyên tắc CEI (R6).
- **Đầu ra dự kiến:** Mã nguồn `contracts/project/ProjectCore.sol` nâng cấp, bộ test kiểm tra phân quyền truy cập và luồng biểu quyết.
- **Tiêu chí hoàn thành (DoD):** Biên dịch sạch, kiểm tra quyền chặt chẽ, đạt ngưỡng 51% mới cho giải ngân, chống double-voting và double-spending.
- **Người phụ trách:** (Dự kiến: Trần Hoàng Phương Dung), (Dự kiến: Võ Ngọc Tâm Phúc)
- **Hạn hoàn thành dự kiến:** 23/10/2026

### 4.2. Lab 14 — Triển khai Luồng Hoàn tiền an toàn & Kiểm thử tích hợp toàn diện
- **Mục tiêu:** Cài đặt luồng hoàn tiền an toàn (R7 tinh giản) cho trường hợp nộp nhầm; kiểm thử liên hoàn toàn bộ chu trình sống của dòng tiền (Nạp $\rightarrow$ Biểu quyết $\rightarrow$ Chi $\rightarrow$ Hoàn $\rightarrow$ Rút), đo lường và tối ưu hóa Gas.
- **Công việc cụ thể:**
  1. Xây dựng hàm hoàn tiền nộp nhầm an toàn theo phương án kinh tế được nhóm chốt, bảo đảm kiểm tra điều kiện kép `amount <= studentContributions[msg.sender]` và `amount <= classFundBalance`.
  2. Viết kịch bản kiểm thử tích hợp (Integration Test) kiểm tra tính toàn vẹn số dư qua chuỗi 5 giao dịch liên tiếp.
  3. Kiểm tra các điều kiện biên và gian lận: Rút quá số dư, biểu quyết sau hạn 7 ngày, nạp nhầm xin rút vượt mức.
  4. Đo lường lượng Gas tiêu thụ của từng hàm và lập bảng so sánh `evidence/Bảng gas.md`.
  5. Rà soát an toàn lần cuối theo checklist `AGENTS.md` (chống Reentrancy, Checks-Effects-Interactions).
- **Đầu ra dự kiến:** Mã nguồn `ProjectCore.sol` tích hợp hoàn tiền, file kịch bản kiểm thử tích hợp, bảng đo lường Gas tiêu thụ thực tế.
- **Tiêu chí hoàn thành (DoD):** 100% các ca kiểm thử tích hợp pass, không thất thoát wei, không còn cảnh báo bảo mật.
- **Người phụ trách:** (Dự kiến: Trần Hoàng Phương Dung), (Dự kiến: Võ Ngọc Tâm Phúc)
- **Hạn hoàn thành dự kiến:** 24/10/2026

### 4.3. Lab 15 — Kết nối DApp Frontend & Demo sản phẩm (Frontend Integration & Showcase)
- **Mục tiêu:** Kết nối giao diện người dùng `web/index.html` với Smart Contract đã triển khai trên mạng thử nghiệm Sepolia qua MetaMask và thư viện Ethers.js.
- **Công việc cụ thể:**
  1. Cập nhật `CONTRACT_ADDRESS` và `CONTRACT_ABI` mới nhất vào `web/index.html`.
  2. Bổ sung các khu vực giao diện: Hiển thị số dư Quỹ lớp chính (`classFundBalance`), hiển thị Quỹ dịch vụ vận hành (`adminFeePool`), nút nạp tiền, bảng đề xuất chi & nút biểu quyết/thực thi, giao diện xin hoàn tiền nộp nhầm.
  3. Xử lý thông báo lỗi thân thiện với người dùng (hiển thị rõ các custom errors).
  4. Triển khai hợp đồng lên mạng Sepolia Testnet, ghi lại mã giao dịch (tx hash) và quay video/chụp ảnh minh chứng tương tác thực tế.
- **Đầu ra dự kiến:** Ứng dụng DApp hoạt động ổn định trên nền tảng web, video minh chứng demo luồng nạp, biểu quyết, chi tiêu và theo dõi số dư.
- **Tiêu chí hoàn thành (DoD):** Sinh viên và BCS có thể tương tác đầy đủ các luồng qua MetaMask trên Sepolia, số dư cập nhật tức thời theo thời gian thực.
- **Người phụ trách:** (Dự kiến: Trần Hoàng Phương Dung), (Dự kiến: Võ Ngọc Tâm Phúc)
- **Hạn hoàn thành dự kiến:** 25/10/2026

---

## 5. Ma trận phân công trách nhiệm (RACI Matrix)

| Thành viên | Vai trò dự kiến | Lab 12 (Gate Review 1) | Lab 13 (Phân quyền & Rút phí) | Lab 14 (Kiểm thử tích hợp & Gas) | Lab 15 (DApp & Demo) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Trần Hoàng Phương Dung** (23K4300004) | Trưởng nhóm / Smart Contract Dev | R / A | R / A | R / A | R / A |
| **Võ Ngọc Tâm Phúc** (23K4300015) | Thành viên kỹ thuật / Kiểm thử | R / A | R / A | R / A | R / A |

*Ghi chú ký hiệu RACI:*
- **R (Responsible):** Người trực tiếp thực hiện công việc.
- **A (Accountable):** Người chịu trách nhiệm nghiệm thu cuối cùng.
- **C (Consulted):** Người được tham vấn chuyên môn (Giảng viên / Trợ lý AI).
- **I (Informed):** Người được thông báo tiến độ (Tập thể lớp).
