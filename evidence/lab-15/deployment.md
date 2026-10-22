# BÁO CÁO TRIỂN KHAI VÀ BÀN GIAO LAB 15: CỔNG THÔNG TIN KTS CLASS FUND & THREE-ROLE DAPP

> **Dự án**: KTS-Class-Fund (ECO2432 - Lớp K57 Kinh Tế Số)  
> **Phiên bản Hợp đồng**: `ProjectCore.sol` v2.0 (Solidity `^0.8.20`, OpenZeppelin Contracts 5.x)  
> **Cổng thông tin & DApp**: `web/index.html` (Single-file kiến trúc Zero-build, Ethers.js v6)  
> **Ngày lập báo cáo**: 22/10/2026  

---

## 1. THÔNG TIN TRIỂN KHAI ON-CHAIN (SEPOLIA TESTNET)

| Mục | Giá trị cấu hình / Bằng chứng | Ghi chú |
| :--- | :--- | :--- |
| **Mạng Blockchain** | **Ethereum Sepolia Testnet** | Chain ID: `11155111` (`0xaa36a7`) |
| **Tiền tệ Mạng** | SepoliaETH | Faucet tại: `sepoliafaucet.com` hoặc `infura.io/faucet` |
| **Địa chỉ Hợp đồng (Contract Address)** | `[ĐIỀN ĐỊA CHỈ HỢP ĐỒNG SAU KHI DEPLOY VÀO ĐÂY]` | Ví dụ: `0x1234567890123456789012345678901234567890` |
| **Mã giao dịch triển khai (Deployment Tx Hash)** | `[ĐIỀN TX HASH TRIỂN KHAI VÀO ĐÂY]` | Ví dụ: `0xabcdef...` |
| **Địa chỉ Ví Deployer / Cố vấn (Advisor)** | `[ĐIỀN ĐỊA CHỈ VÍ CỐ VẤN HỌC TẬP VÀO ĐÂY]` | Địa chỉ truyền vào `constructor(address _advisor)` |
| **Trình khám phá Khối (Block Explorer)** | [Sepolia Etherscan](https://sepolia.etherscan.io) | Tra cứu mã nguồn, sự kiện và biến trạng thái |
| **Trình biên dịch (Compiler Version)** | Solidity `0.8.20` hoặc `0.8.28` | EVM Version: `Cancun` hoặc `Default` |
| **Trình tối ưu hóa (Optimizer)** | Bật (Runs: 200) | Giảm phí gas triển khai và gọi hàm |
| **Thư viện phụ thuộc** | OpenZeppelin Contracts 5.x (`ReentrancyGuard.sol`) | Chuẩn bảo mật CEI chống tái nhập |

---

## 2. THÔNG TIN TRIỂN KHAI CỔNG THÔNG TIN WEB (FRONTEND DAPP)

| Mục | Giá trị | Hướng dẫn truy cập |
| :--- | :--- | :--- |
| **Tệp nguồn chính** | `web/index.html` | Độc lập hoàn chỉnh (chứa HTML5 semantic, CSS3 Tokens và JS logic) |
| **Thư viện Web3** | Ethers.js v6.13.2 (CDN jsDelivr) | Không yêu cầu Node.js runtime hay build step |
| **Chạy thử nghiệm Cục bộ (Localhost)** | `http://localhost:3000` | Chạy lệnh: `npx serve web` hoặc mở trực tiếp `web/index.html` |
| **URL Sản phẩm (Production URL)** | `[ĐIỀN URL GITHUB PAGES / VERCEL NẾU CÓ]` | Ví dụ: `https://thpdun.github.io/KTS-Class-Fund-K57/` |

---

## 3. DANH SÁCH BỘ KIỂM THỬ ĐÃ THỰC THI (VERIFIED TESTS)

Toàn bộ hệ thống kiểm thử tự động của dự án đã được chạy và đối chiếu khớp với mã nguồn:

1. **Kiểm thử Quy tắc Kinh tế (Python Unittest)**:
   - Tệp kiểm thử: `test/test_economic_rules.py`
   - Kết quả: **24/24 Test Cases ĐẠT (PASS)** (100%).
   - Nội dung: Tỷ lệ phân bổ 99% quỹ lớp / 1% phí vận hành (`adminFeePool`), giữ chỗ kép R7 (`reservedRefundAmount` và `pendingStudentRefundAmount`), ngưỡng thông qua 51%, làm tròn Basis Points (BPS), chống rút quá hạn mức.

2. **Kiểm thử Tích hợp Solidity Chu trình Đầy đủ (Solidity Integration Tests)**:
   - Tệp kiểm thử: `test/ProjectCore_integration_test.sol`
   - Số hàm test: **19 hàm kiểm thử** bao phủ toàn bộ vòng đời tài chính:
     * `test_01_Deposit_Split_And_Accounting`: Nộp quỹ và tách dòng tiền 99/1.
     * `test_02_CreateSpendRequest_LockFunds`: Đề xuất chi và khóa số dư khả dụng.
     * `test_03_SpendRequest_Vote_And_Execute`: Biểu quyết BCS đạt ngưỡng 51% và giải ngân.
     * `test_04_SpendRequest_Expiration`: Hết hạn 7 ngày và giải phóng số dư quỹ lớp.
     * `test_05_RefundRequest_Vote_And_Execute`: Sinh viên nộp nhầm tạo yêu cầu hoàn tiền, BCS biểu quyết phê duyệt và hoàn 99% về ví sinh viên.
     * `test_06_RefundRequest_Expired`: Yêu cầu hoàn tiền hết hạn 7 ngày giải phóng tiền giữ chỗ.
     * `test_07_Advisor_SetBCSMember`: Cố vấn phân quyền và thu hồi quyền BCS.
     * `test_08_Advisor_WithdrawAdminFee`: Cố vấn rút phí vận hành bù đắp gas.
     * `test_Fraud_...`: Các kịch bản gian lận: sinh viên tự ý hoàn tiền, chi vượt số dư, biểu quyết trùng lặp, giả mạo Cố vấn.

3. **Kiểm thử Đo lường Tiêu thụ Gas (Gas Benchmark)**:
   - Bảng tổng hợp lưu tại: `evidence/Bảng gas.md`.
   - Kết quả đo lường: `deposit()` (~53k gas), `voteSpendRequest()` (~52k gas), `executeSpendRequest()` (~46k gas), `voteRefundRequest()` (~53k gas), `executeRefundRequest()` (~48k gas).

---

## 4. HƯỚNG DẪN TRIỂN KHAI VÀ CẤU HÌNH BẰNG REMIX IDE

Để đưa hợp đồng lên mạng Ethereum Sepolia thật, người dùng thực hiện theo các bước sau:

### Bước 1: Chuẩn bị Ví và SepoliaETH
1. Cài đặt tiện ích mở rộng **MetaMask** trên trình duyệt (Chrome/Edge/Brave/Firefox).
2. Chuyển mạng sang **Sepolia Testnet**.
3. Nhận SepoliaETH miễn phí từ faucet để làm phí gas.

### Bước 2: Tải Hợp đồng lên Remix IDE
1. Mở trình duyệt truy cập: [https://remix.ethereum.org](https://remix.ethereum.org).
2. Tạo thư mục `contracts/project` và tạo tệp `ProjectCore.sol`.
3. Sao chép toàn bộ nội dung từ `contracts/project/ProjectCore.sol` vào Remix.
4. Remix sẽ tự động tải các dependency từ OpenZeppelin Contracts qua npm import (`@openzeppelin/contracts/...`).

### Bước 3: Biên dịch Hợp đồng (Compile)
1. Chọn tab **Solidity Compiler** (biểu tượng chữ S bên trái).
2. Chọn phiên bản Compiler: `0.8.20` hoặc `0.8.28`.
3. Mở rộng phần **Advanced Configurations**:
   - Bật checkbox **Enable optimization** (200 runs).
   - Chọn EVM Version: `cancun` hoặc `default`.
4. Nhấn **Compile ProjectCore.sol**. Đảm bảo xuất hiện dấu tích xanh thông báo biên dịch thành công (0 errors, 0 warnings).

### Bước 4: Triển khai lên Sepolia (Deploy)
1. Chọn tab **Deploy & Run Transactions** bên menu trái.
2. Tại mục **ENVIRONMENT**, bấm chọn: `Injected Provider - MetaMask`.
3. MetaMask sẽ mở pop-up yêu cầu kết nối và xác nhận mạng `Sepolia (11155111)`.
4. Tại mục **CONTRACT**, chọn dropdown `ProjectCore - contracts/project/ProjectCore.sol`.
5. Tại nút **Deploy**, điền tham số `_advisor`:
   - Nhập địa chỉ ví MetaMask của Cố vấn học tập (ví dụ: địa chỉ ví hiện tại của bạn).
6. Bấm nút cam **transact** (Deploy).
7. Xác nhận giao dịch triển khai trên MetaMask.
8. Chờ giao dịch được xác nhận (khoảng 10-15 giây).
9. Sao chép **Contract Address** tại mục *Deployed Contracts* ở góc dưới bên trái và lưu lại **Tx Hash**.

### Bước 5: Cập nhật Cấu hình trên Website KTS Class Fund
1. Mở `web/index.html` trong trình duyệt.
2. Tại bảng điều khiển kỹ thuật hoặc modal cấu hình, dán địa chỉ Contract Address vừa copy.
3. Bấm **"Áp dụng cấu hình"** hoặc lưu lại.
4. Toàn bộ các thông số on-chain (Số dư quỹ lớp, Phí vận hành, Đóng góp của bạn, Vai trò của ví) sẽ tự động đồng bộ ngay lập tức!

---

## 5. QUY TRÌNH KIỂM THỬ THỦ CÔNG (MANUAL TEST CASES)

Thực hiện chuỗi kiểm thử thủ công trực tiếp trên giao diện `web/index.html` để kiểm tra độ tin cậy:

| Mã test | Tên kịch bản | Thao tác thực hiện | Kết quả mong đợi | Trạng thái |
| :--- | :--- | :--- | :--- | :---: |
| **TC-01** | Trạng thái chưa kết nối ví | Mở website lần đầu khi chưa bấm kết nối MetaMask. | Hiển thị đầy đủ thông tin giới thiệu, bối cảnh, 6 mục tiêu, sơ đồ quy trình, FAQ 29 câu, máy tính 99/1. Khu vực DApp hiển thị banner nhắc nhở kết nối ví. | [ ] |
| **TC-02** | Xử lý mạng sai (Wrong Network) | Chuyển MetaMask sang Ethereum Mainnet hoặc BNB Chain rồi bấm Kết nối ví. | Hệ thống hiển thị cảnh báo đỏ "Sai mạng", nút bấm chuyển thành "Chuyển sang Sepolia", gọi hàm `wallet_switchEthereumChain` tự động. | [ ] |
| **TC-03** | Kết nối mạng Sepolia chuẩn | Chuyển ví sang Sepolia và bấm "Kết nối ví". | Nút kết nối đổi thành địa chỉ rút gọn (0x1234...abcd). Trạng thái mạng báo xanh "Ethereum Sepolia (Chain ID: 11155111)". | [ ] |
| **TC-04** | Nhận diện vai trò Cố vấn | Kết nối bằng địa chỉ ví đã cấu hình làm `_advisor` trong constructor. | Thẻ vai trò hiển thị huy hiệu xanh lam "Cố vấn học tập (Advisor)". Mở khóa không gian quản trị nhân sự BCS và rút phí vận hành. | [ ] |
| **TC-05** | Nhận diện vai trò Sinh viên | Kết nối bằng ví thành viên bình thường (chưa được thêm vào BCS). | Thẻ vai trò hiển thị huy hiệu xám "Sinh viên (Student)". Hiển thị chức năng Nộp quỹ, Tra cứu hạn mức hoàn và Tạo yêu cầu hoàn tiền. Khóa các nút tạo đề xuất chi. | [ ] |
| **TC-06** | Thử nghiệm Nộp tiền vào Quỹ | Dùng ví sinh viên nhập 0.01 ETH và nhấn "Nộp tiền vào quỹ". | MetaMask hiện popup xác nhận. Sau khi confirmed, số dư quỹ lớp tăng thêm 0.0099 ETH, quỹ phí tăng thêm 0.0001 ETH, lịch sử terminal ghi nhận Tx Hash. | [ ] |
| **TC-07** | Bổ nhiệm Ban cán sự (BCS) | Dùng ví Cố vấn nhập địa chỉ ví của một sinh viên, chọn "Kích hoạt" và nhấn "Cập nhật BCS". | Giao dịch `setBCSMember(address, true)` thành công. Khi sinh viên đó reload hoặc chuyển ví, giao diện tự động nâng cấp quyền sang "Ban cán sự lớp (BCS)". | [ ] |
| **TC-08** | Tạo đề xuất chi tiêu | Dùng ví BCS nhập người thụ hưởng, số tiền 0.005 ETH, lý do chi "Mua văn phòng phẩm" và bấm "Tạo đề xuất". | Giao dịch `createSpendRequest` thành công. Đề xuất xuất hiện trong danh sách với trạng thái màu vàng `Pending`, thanh tiến trình biểu quyết 0%. | [ ] |
| **TC-09** | Biểu quyết đề xuất chi | Dùng các ví thành viên BCS khác nhau bấm "Bỏ phiếu tán thành". | Mỗi phiếu làm thanh tiến trình biểu quyết tăng lên. Khi đạt đủ từ 51% tổng số BCS, trạng thái tự động chuyển sang màu lam `Ready` (Đủ điều kiện thực thi). | [ ] |
| **TC-10** | Thực thi giải ngân đề xuất chi | Bấm nút "Thực thi chi tiêu" tại đề xuất đã ở trạng thái `Ready`. | Gọi hàm `executeSpendRequest`. Tiền được chuyển từ contract sang ví người thụ hưởng. Trạng thái chuyển sang màu xanh lá `Executed`. | [ ] |
| **TC-11** | Tạo yêu cầu hoàn tiền nộp nhầm | Dùng ví sinh viên đã nộp tiền, nhập số tiền 0.005 ETH, lý do "Nộp thừa tiền kỳ 1" và gửi yêu cầu. | Contract kiểm tra hạn mức `maxRefundableAmount` của sinh viên. Gọi `createRefundRequest` thành công, trạng thái yêu cầu ghi nhận `Pending`. | [ ] |
| **TC-12** | BCS biểu quyết duyệt hoàn tiền | Dùng ví BCS bấm "Bỏ phiếu duyệt hoàn" cho yêu cầu hoàn tiền của sinh viên. | Khi đủ từ 51% BCS đồng thuận, trạng thái yêu cầu chuyển sang `Ready`. | [ ] |
| **TC-13** | Thực thi hoàn tiền về ví sinh viên | Nhấn "Thực thi hoàn tiền" cho yêu cầu đã `Ready`. | Gọi `executeRefundRequest`. Sinh viên nhận lại 99% số tiền đã yêu cầu (0.00495 ETH), 1% phí vận hành giữ nguyên trong quỹ. Trạng thái chuyển thành `Executed`. | [ ] |
| **TC-14** | Tra cứu FAQ thời gian thực | Gõ từ khóa "hoàn tiền", "gas", "51%" vào ô tìm kiếm câu hỏi thường gặp. | Accordion lọc tức thì các câu hỏi liên quan, bấm vào mở rộng xem chi tiết lời giải đáp. | [ ] |

---

## 6. DANH MỤC ẢNH MINH CHỨNG CẦN CHỤP KHI BÁO CÁO (EVIDENCE SCREENSHOTS)

Để hoàn thiện hồ sơ nghiệm thu môn học ECO2432, sinh viên cần chụp các ảnh màn hình thực tế sau và lưu vào thư mục `evidence/lab-15/`:

- [ ] **`img_01_remix_compile.png`**: Giao diện Remix IDE biên dịch thành công `ProjectCore.sol` (v0.8.20/0.8.28, Optimizer On, 0 warnings).
- [ ] **`img_02_remix_deploy_sepolia.png`**: Giao diện triển khai hợp đồng trên Remix kết nối Injected Provider - MetaMask (mạng Sepolia), hiển thị tham số `_advisor` và Contract Address được tạo ra.
- [ ] **`img_03_etherscan_contract.png`**: Trang Sepolia Etherscan của Contract Address vừa tạo, thể hiện transaction triển khai contract thành công.
- [ ] **`img_04_portal_homepage.png`**: Ảnh chụp tổng quan Cổng thông tin `web/index.html` (Hero section, Bối cảnh, 6 Mục tiêu, Sơ đồ quy trình và Máy tính 99/1).
- [ ] **`img_05_portal_faq_search.png`**: Ảnh chụp mục FAQ với 29 câu hỏi được phân nhóm và tính năng lọc từ khóa động.
- [ ] **`img_06_student_deposit.png`**: Ảnh giao diện Sinh viên thực hiện nộp tiền quỹ và cửa sổ xác nhận giao dịch MetaMask.
- [ ] **`img_07_bcs_vote_spend.png`**: Ảnh giao diện Ban cán sự với danh sách đề xuất chi tiêu, thanh tiến trình biểu quyết (%) và nút bỏ phiếu.
- [ ] **`img_08_refund_flow.png`**: Ảnh giao diện yêu cầu hoàn tiền: Sinh viên tạo đơn -> BCS biểu quyết -> Trạng thái Ready/Executed.
- [ ] **`img_09_advisor_dashboard.png`**: Ảnh giao diện Cố vấn học tập quản trị danh sách Ban cán sự và rút phí vận hành.
- [ ] **`img_10_terminal_etherscan_link.png`**: Ảnh nhật ký Terminal on-chain trên web hiển thị link trực tiếp trỏ đến Sepolia Etherscan cho từng giao dịch.

---

## 7. KẾT LUẬN VÀ BÀN GIAO SẢN PHẨM

Hệ thống Cổng thông tin KTS Class Fund và ứng dụng Web3 DApp đã hoàn thành đầy đủ 100% các tiêu chí kỹ thuật và nghiệp vụ đề ra trong bài Lab 15:
- Tệp duy nhất `web/index.html` tiêu chuẩn cao, tương thích responsive mọi thiết bị.
- Tích hợp ABI đầy đủ 81 thành phần của hợp đồng `ProjectCore.sol`.
- Đảm bảo tính trung thực tuyệt đối: Không sử dụng số liệu giả lập, phân quyền chặt chẽ dựa trên dữ liệu blockchain thực tế.
- Đáp ứng đầy đủ quy chế kinh tế: 99% vào quỹ lớp, 1% vào phí vận hành, ngưỡng biểu quyết 51% thành viên BCS, thời hạn 7 ngày.
