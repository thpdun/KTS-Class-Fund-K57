# KTS-Class-Fund

Nhóm xây dựng hệ thống KTS-Class-Fund cho sinh viên và ban cán sự lớp ngành Kinh tế Số (Trường Đại học Kinh tế - Đại học Huế) để giải quyết vấn đề minh bạch trong thu chi và tự động hóa quản lý quỹ lớp.

## Giới thiệu dự án
KTS-Class-Fund là một giải pháp hợp đồng thông minh (Smart Contract) giúp minh bạch hóa dòng tiền của tập thể lớp. Hệ thống áp dụng cơ chế phân quyền rõ ràng, đảm bảo tính dân chủ thông qua việc bỏ phiếu cho các khoản chi và lưu trữ toàn bộ lịch sử giao dịch không thể sửa đổi trên blockchain.

## Phân quyền và Tính năng cốt lõi

**1. Quản trị viên (Cố vấn học tập)**
- Là người khởi tạo hợp đồng thông minh.
- Có đặc quyền cao nhất trong việc quản lý nhân sự: thêm, sửa, xóa các thành viên thuộc Ban cán sự lớp.

**2. Ban cán sự lớp**
- **Đề xuất chi:** Khởi tạo các yêu cầu chi tiêu từ quỹ chung.
- **Bỏ phiếu giải ngân:** Tham gia bỏ phiếu đồng ý hoặc bác bỏ yêu cầu chi. Khi một yêu cầu đạt từ 51% phiếu đồng ý trở lên, trạng thái sẽ chuyển sang "sẵn sàng thực thi".
- **Thực thi giải ngân:** Bất kỳ thành viên nào trong ban cán sự cũng có thể gọi hàm để thực thi giải ngân ngay khi yêu cầu đạt điều kiện, hoặc hệ thống sẽ cho phép tự động thực thi khi hết hạn 7 ngày kể từ lúc tạo yêu cầu chi.
- **Xử lý hoàn tiền:** Xem xét minh chứng và bỏ phiếu quyết định (đồng ý/bác bỏ) đối với các yêu cầu xin hoàn lại tiền từ sinh viên.

**3. Sinh viên trong lớp**
- **Đóng quỹ & Tra cứu:** Nộp tiền vào quỹ chung và có quyền xem toàn bộ lịch sử thu/chi của lớp theo thời gian thực.
- **Yêu cầu hoàn tiền:** Trong trường hợp thao tác nộp quỹ sai số tiền, sinh viên có thể nộp minh chứng giao dịch và tạo yêu cầu hoàn lại tiền để Ban cán sự xét duyệt.

## Thành viên nhóm
| Họ và tên | Mã sinh viên |
| :--- | :--- |
| Trần Hoàng Phương Dung | 23K4300004 |
# ECO2432 Web3 Starter

Kho khởi đầu dùng xuyên suốt 15 bài thực hành.

## Bắt đầu (thay cho bước "Fork kho" trong sổ tay)

Sổ tay ghi "Fork kho `hce-web3-starter`". Học kỳ này kho được phát dạng tệp nén, nên làm như sau:

1. Giải nén thư mục này vào máy, mở bằng Antigravity.
2. Đọc `AGENTS.md` trước khi yêu cầu công cụ AI sinh mã.
3. Sao chép `SPEC.md` và `AI_JOURNAL.md` cho từng bài.
4. Chỉ dùng ví thử nghiệm và mạng Sepolia; không dùng khóa ví có tiền thật.

Đưa lên GitHub (làm khi đã có tài khoản; cần trước khi nộp Lab 1):

```bash
git init -b main
git add .
git commit -m "chore: thiet lap moi truong lam viec"
git remote add origin https://github.com/<tai-khoan>/<ten-repo>.git   # repo tạo TRỐNG trên GitHub
git push -u origin main
```

Lab 8 (repo nhóm): một thành viên tạo repo trống mới, đưa nội dung thư mục này lên theo đúng các
lệnh trên, rồi mời các thành viên khác làm collaborator.

## Cấu trúc

- `contracts/training/`: hợp đồng mẫu dùng ở Lab 9, 10, 11 và 13
  (`TimeLockVault`, `VaultBuggy`, `ClassPoint`, `VulnerableBank`).
- `contracts/lab04/ClubTokens.sol`: ba token dùng cho Lab 4.
- `web/index.html`: giao diện mẫu dùng ở Lab 15.
- `prompt_templates.md`: mẫu câu lệnh có yêu cầu và tiêu chí kiểm chứng rõ ràng.

Các hợp đồng có chữ `Buggy`, `Vulnerable` hoặc cảnh báo trong mã đều chứa lỗi có chủ đích.

## Chạy hợp đồng

- Cách chính: mở Remix IDE (`https://remix.ethereum.org`), tạo tệp, dán mã. Remix tự tải thư viện
  `@openzeppelin/...`, không cần cài gì.
- Nếu Antigravity gạch đỏ dòng `import "@openzeppelin/..."`: đó là do máy chưa có thư viện, mã
  không sai. Muốn hết gạch đỏ thì cài Node.js rồi chạy `npm install` trong thư mục này (không bắt buộc).
