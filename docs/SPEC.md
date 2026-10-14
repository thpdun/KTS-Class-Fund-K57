# Đặc tả Nghiệp vụ KTS-Class-Fund (Phiên bản v0.1)

## 1. Mục đích
Hệ thống KTS-Class-Fund là hợp đồng thông minh quản lý quỹ lớp phi tập trung, giúp minh bạch hóa dòng tiền thu chi, phân quyền phê duyệt dân chủ và giải quyết yêu cầu giải ngân hoặc hoàn tiền một cách minh bạch cho tập thể sinh viên, Ban cán sự và Cố vấn học tập ngành Kinh tế Số.

## 2. Đầu vào
- **Từ Cố vấn học tập (CVHT / Owner):**
  - `bcsAddress`: Kiểu `address` - Địa chỉ ví của thành viên Ban cán sự cần thêm mới hoặc xóa.
  - `status`: Kiểu `bool` - Trạng thái hoạt động (`true`: kích hoạt, `false`: hủy quyền) của thành viên Ban cán sự.
- **Từ Sinh viên (Student):**
  - `msg.value`: Kiểu `uint256` (đơn vị: wei) - Số lượng ETH gửi kèm giao dịch để đóng góp vào quỹ lớp.
  - `refundAmount`: Kiểu `uint256` (đơn vị: wei) - Số tiền yêu cầu hoàn lại trong trường hợp nộp nhầm hoặc nộp sai.
  - `proofHash`: Kiểu `bytes32` - Mã băm (hash) hoặc CID IPFS đại diện cho minh chứng giao dịch chuyển tiền nhầm.
  - `reason`: Kiểu `string` - Lý do chi tiết gửi kèm yêu cầu xin hoàn tiền.
- **Từ Ban cán sự (BCS):**
  - `recipient`: Kiểu `address payable` - Địa chỉ ví của người thụ hưởng nhận tiền giải ngân từ quỹ.
  - `amount`: Kiểu `uint256` (đơn vị: wei) - Số lượng ETH đề xuất chi cho hoạt động của lớp.
  - `description`: Kiểu `string` - Nội dung, mục đích chi tiêu của khoản tiền.
  - `requestId`: Kiểu `uint256` - Mã định danh duy nhất của yêu cầu chi cần bỏ phiếu hoặc thực thi giải ngân.
  - `refundId`: Kiểu `uint256` - Mã định danh duy nhất của yêu cầu xin hoàn tiền từ sinh viên cần xét duyệt.
  - `support`: Kiểu `bool` - Lựa chọn biểu quyết (`true`: đồng ý/duyệt, `false`: không đồng ý/bác bỏ).

## 3. Quy tắc nghiệp vụ
- **R1**: Chỉ địa chỉ ví của Cố vấn học tập (người khởi tạo hợp đồng) mới có quyền thêm mới, cập nhật hoặc xóa thành viên trong danh sách Ban cán sự.
- **R2**: Mọi sinh viên đều có quyền gửi ETH vào quỹ lớp và số dư quỹ phải tăng chính xác bằng số tiền nhận được (`msg.value > 0`).
- **R3**: Chỉ thành viên Ban cán sự đang hoạt động mới có quyền tạo yêu cầu chi tiền từ quỹ và số tiền đề xuất chi không được vượt quá số dư khả dụng hiện có của quỹ.
- **R4**: Mỗi thành viên Ban cán sự chỉ được bỏ phiếu một lần duy nhất cho mỗi yêu cầu chi; yêu cầu chi sẽ tự động chuyển sang trạng thái "Sẵn sàng thực thi" khi đạt tỷ lệ đồng ý tối thiểu 51% (tương đương 5100 basis points) trên tổng số thành viên Ban cán sự tại thời điểm kiểm tra.
- **R5**: Một yêu cầu chi CHỈ CÓ THỂ được gọi hàm thực thi giải ngân khi và chỉ khi nó đã đạt tỷ lệ đồng ý tối thiểu 51%. Nếu sau 7 ngày không đạt đủ 51% phiếu thuận, yêu cầu đó sẽ tự động hết hạn (Expired) và không thể thực thi.
- **R6**: Khi một yêu cầu chi được thực thi giải ngân thành công, toàn bộ số tiền đề xuất phải được chuyển trực tiếp đến địa chỉ ví thụ hưởng bằng lệnh gọi cấp thấp (`call`) và yêu cầu phải chuyển sang trạng thái "Đã thực thi" để chống thực thi lặp lại.
- **R7**: Sinh viên nộp thừa hoặc nộp sai có quyền tạo yêu cầu hoàn tiền kèm mã minh chứng (`proofHash`), và số tiền này chỉ được hoàn trả về ví sinh viên khi được Ban cán sự biểu quyết thông qua.
Hệ thống chỉ cho phép tồn tại tối đa 01 yêu cầu chi ở trạng thái 'Đang chờ duyệt' (Pending) tại một thời điểm. Phải xử lý xong (thực thi hoặc hủy) yêu cầu hiện tại thì BCS mới được tạo yêu cầu chi mới.
- **R8**: Hệ thống chỉ cho phép tồn tại tối đa 01 yêu cầu chi ở trạng thái 'Đang chờ duyệt' (Pending) tại một thời điểm. Phải xử lý xong (thực thi hoặc hủy) yêu cầu hiện tại thì BCS mới được tạo yêu cầu chi mới.
- **R9**: Hủy và dọn dẹp yêu cầu chi:
  - **Hủy chủ động**: Cố vấn học tập (CVHT) hoặc người tạo yêu cầu CHỈ CÓ QUYỀN gọi hàm Hủy (Cancel) khi yêu cầu chưa đạt 51% (đang Pending). Khi đã đạt 51% (chuyển sang Ready), quyền Hủy bị vô hiệu hóa.
  - **Dọn dẹp quá hạn (Cơ chế thoát hiểm chống kẹt hệ thống)**: Nếu một yêu cầu chi tồn tại quá 7 ngày kể từ lúc tạo mà vẫn chưa được giải ngân thành công (dù là đang ở trạng thái Pending do thiếu phiếu, hay đã ở trạng thái Ready nhưng bị lỗi kỹ thuật không thể chuyển tiền đi), BẤT KỲ TÀI KHOẢN NÀO cũng có thể gọi hàm "Đánh dấu hết hạn" (Expire) để dọn dẹp, giải phóng hệ thống cho yêu cầu chi mới.
- **R10**: Sinh viên có quyền tự Hủy (Cancel) yêu cầu hoàn tiền đang ở trạng thái 'Đang chờ duyệt' của chính mình. Yêu cầu xin hoàn tiền KHÔNG bị áp dụng cơ chế tự động dọn dẹp sau 7 ngày để bảo vệ tài sản của người nộp nhầm.
## 4. Đầu ra
- **Tài sản chuyển giao (ETH Transfer):**
  - Chuyển số ETH giải ngân tương ứng tới địa chỉ ví thụ hưởng (`recipient`) khi yêu cầu chi được thực thi thành công.
  - Chuyển số ETH hoàn trả về địa chỉ ví của sinh viên khi yêu cầu xin hoàn tiền được Ban cán sự phê duyệt.
- **Trạng thái lưu trữ trên hợp đồng (State):**
  - Trạng thái yêu cầu chi: Đang chờ duyệt (`Pending`), Sẵn sàng thực thi (`Ready`), Đã thực thi (`Executed`), Bị bác bỏ (`Rejected`).
  - Trạng thái yêu cầu hoàn tiền: Đang chờ duyệt (`Pending`), Đã chấp thuận (`Approved`), Bị bác bỏ (`Rejected`), Đã hoàn tiền (`Refunded`).
  - Dữ liệu lưu trữ: Tổng số dư quỹ lớp, danh sách và số lượng thành viên Ban cán sự đang hoạt động, lịch sử biểu quyết của từng thành viên.
- **Sự kiện ghi nhận trên Blockchain (Events):**
  - Ghi nhận thông tin thay đổi nhân sự Ban cán sự (`BCSMemberUpdated`).
  - Ghi nhận lịch sử giao dịch nộp quỹ của sinh viên (`FundDeposited`).
  - Ghi nhận thông tin khởi tạo yêu cầu chi (`SpendRequestCreated`).
  - Ghi nhận lượt bỏ phiếu của từng thành viên Ban cán sự (`SpendRequestVoted`).
  - Ghi nhận kết quả thực thi giải ngân (`SpendRequestExecuted`).
  - Ghi nhận thông tin tạo yêu cầu hoàn tiền (`RefundRequested`).
  - Ghi nhận kết quả xét duyệt hoàn tiền (`RefundProcessed`).
- **Giao diện hiển thị (DApp / Block Explorer):**
  - Bảng điều khiển minh bạch hiển thị số dư thực tế, tổng quỹ thu vào và tổng quỹ đã chi.
  - Danh sách lịch sử đóng quỹ của sinh viên theo thời gian thực.
  - Bảng danh sách các yêu cầu chi tiêu kèm tiến độ biểu quyết, thời hạn mở khóa 7 ngày và nút bấm thực thi giải ngân.
  - Bảng quản lý và tra cứu tiến độ các yêu cầu xin hoàn tiền.

## 5. Trường hợp ngoại lệ
- Nếu tài khoản không phải là Cố vấn học tập thực hiện thao tác thêm, cập nhật hoặc xóa thành viên Ban cán sự thì hệ thống phải từ chối giao dịch (revert) và phát thông báo lỗi vi phạm quyền quản trị.
- Nếu tài khoản không thuộc danh sách Ban cán sự đang hoạt động thực hiện tạo yêu cầu chi, bỏ phiếu hoặc gọi hàm thực thi giải ngân thì hệ thống phải từ chối giao dịch (revert) và phát thông báo lỗi người gọi không có quyền.
- Nếu một thành viên Ban cán sự cố gắng bỏ phiếu nhiều lần cho cùng một yêu cầu chi tiêu thì hệ thống phải từ chối giao dịch (revert) và phát thông báo lỗi đã bỏ phiếu.
- Nếu một thành viên Ban cán sự gọi hàm thực thi giải ngân khi yêu cầu chi chưa đạt tối thiểu 51% phiếu đồng ý và chưa đủ 7 ngày kể từ lúc tạo yêu cầu thì hệ thống phải từ chối giao dịch (revert) và phát thông báo lỗi yêu cầu chưa đủ điều kiện giải ngân.
- Nếu tài khoản gọi thực thi giải ngân cho một yêu cầu chi đã ở trạng thái "Đã thực thi" thì hệ thống phải từ chối giao dịch (revert) và phát thông báo lỗi yêu cầu đã được xử lý trước đó.
- Nếu số dư thực tế trong quỹ không đủ để thực hiện giải ngân cho yêu cầu chi hoặc hoàn tiền thì hệ thống phải từ chối giao dịch (revert) và phát thông báo lỗi số dư quỹ không đủ.
- Nếu sinh viên gửi yêu cầu xin hoàn tiền với số tiền bằng 0 hoặc lớn hơn số tiền thực tế sinh viên đó đã nộp vào quỹ thì hệ thống phải từ chối giao dịch (revert) và phát thông báo lỗi số tiền hoàn không hợp lệ.
- Nếu một sinh viên đang có 1 yêu cầu hoàn tiền ở trạng thái 'Đang chờ duyệt' mà tiếp tục tạo thêm yêu cầu hoàn tiền mới, hệ thống phải từ chối (revert) và báo lỗi Spam.

## 6. Ngoài phạm vi
- Lưu trữ trực tiếp tệp tin ảnh minh chứng hoàn tiền trên hợp đồng thông minh blockchain (hệ thống phiên bản v0.1 chỉ tiếp nhận và lưu trữ chuỗi mã băm `bytes32` hoặc CID IPFS đại diện cho minh chứng, việc lưu trữ vật lý file ảnh nằm ngoài phạm vi smart contract).
- Cơ chế tự động kích hoạt giải ngân khi hết hạn 7 ngày mà không cần tương tác (Smart contract không có cơ chế tự chạy ngầm (cron job); sau 7 ngày hợp đồng chỉ mở khóa điều kiện để thành viên Ban cán sự chủ động gửi giao dịch kích hoạt).
- Hỗ trợ thanh toán hoặc quy đổi tiền pháp định (Fiat/VND) và các loại token ERC-20 khác (phiên bản v0.1 chỉ xử lý trực tiếp đồng tiền gốc ETH trên mạng thử nghiệm).
- Tích hợp hệ thống quản lý danh tính sinh viên tập trung (SSO/Portal trường học); hệ thống v0.1 hoàn toàn định danh theo địa chỉ ví cá nhân.
- Cơ chế ủy quyền bỏ phiếu (proxy voting) hoặc phân bổ trọng số phiếu bầu khác nhau giữa các thành viên Ban cán sự.
