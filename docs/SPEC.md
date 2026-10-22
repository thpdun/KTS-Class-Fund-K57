**ĐẶC TẢ NGHIỆP VỤ KTS-CLASS-FUND (PHIÊN BẢN V0.1)**

## 1. Mục đích

Hệ thống KTS-Class-Fund là hợp đồng thông minh quản lý quỹ lớp phi tập trung, giúp minh bạch hóa dòng tiền thu chi, phân quyền phê duyệt dân chủ và giải quyết yêu cầu giải ngân hoặc hoàn tiền một cách minh bạch cho tập thể sinh viên, Ban cán sự và Cố vấn học tập ngành Kinh tế Số.

## 2. Đầu vào

* **Từ Cố vấn học tập (CVHT / Owner):**
* `bcsAddress`: Kiểu `address` - Địa chỉ ví của thành viên Ban cán sự cần thêm mới hoặc xóa.
* `status`: Kiểu `bool` - Trạng thái hoạt động (`true`: kích hoạt, `false`: hủy quyền) của thành viên Ban cán sự.


* **Từ Sinh viên (Student):**
* `msg.value`: Kiểu `uint256` (đơn vị: wei) - Số lượng ETH gửi kèm giao dịch để đóng góp vào quỹ lớp.
* `refundAmount`: Kiểu `uint256` (đơn vị: wei) - Số tiền yêu cầu hoàn lại trong trường hợp nộp nhầm hoặc nộp sai.
* `proofHash`: Kiểu `bytes32` - Mã băm (hash) hoặc CID IPFS đại diện cho minh chứng giao dịch chuyển tiền nhầm.
* `reason`: Kiểu `string` - Lý do chi tiết gửi kèm yêu cầu xin hoàn tiền.


* **Từ Ban cán sự (BCS):**
* `recipient`: Kiểu `address payable` - Địa chỉ ví của người thụ hưởng nhận tiền giải ngân từ quỹ.
* `amount`: Kiểu `uint256` (đơn vị: wei) - Số lượng ETH đề xuất chi cho hoạt động của lớp.
* `description`: Kiểu `string` - Nội dung, mục đích chi tiêu của khoản tiền.
* `requestId`: Kiểu `uint256` - Mã định danh duy nhất của yêu cầu chi cần bỏ phiếu hoặc thực thi giải ngân.
* `refundId`: Kiểu `uint256` - Mã định danh duy nhất của yêu cầu xin hoàn tiền từ sinh viên cần xét duyệt.
* `support`: Kiểu `bool` - Lựa chọn biểu quyết (`true`: đồng ý/duyệt, `false`: không đồng ý/bác bỏ).



## 3. Quy tắc nghiệp vụ

* **R1**: Chỉ địa chỉ ví của Cố vấn học tập (người khởi tạo hợp đồng) mới có quyền thêm mới, cập nhật hoặc xóa thành viên trong danh sách Ban cán sự.
* **R2**: Mọi sinh viên đều có quyền gửi ETH vào quỹ lớp. Khi giao dịch nạp tiền thành công (`msg.value > 0`), hệ thống tự động trích 1% (100 điểm cơ bản - basis points) vào Quỹ dịch vụ vận hành (`adminFeePool`). 99% số tiền còn lại được cộng vào số dư khả dụng của quỹ lớp chính.
* **R3**: Chỉ thành viên Ban cán sự đang hoạt động mới có quyền tạo yêu cầu chi tiền từ quỹ và số tiền đề xuất chi không được vượt quá số dư khả dụng hiện có của quỹ lớp chính.
* **R4**: Mỗi thành viên Ban cán sự chỉ được bỏ phiếu một lần duy nhất cho mỗi yêu cầu chi; yêu cầu chi sẽ tự động chuyển sang trạng thái "Sẵn sàng thực thi" khi đạt tỷ lệ đồng ý tối thiểu 51% (tương đương 5100 basis points) trên tổng số thành viên Ban cán sự tại thời điểm kiểm tra.
* **R5**: Một yêu cầu chi CHỈ CÓ THỂ được gọi hàm thực thi giải ngân khi và chỉ khi nó đã đạt tỷ lệ đồng ý tối thiểu 51%. Nếu sau 7 ngày không đạt đủ 51% phiếu thuận, yêu cầu đó sẽ tự động hết hạn (Expired) và không thể thực thi.
* **R6**: Khi một yêu cầu chi được thực thi giải ngân thành công, toàn bộ số tiền đề xuất phải được chuyển trực tiếp đến địa chỉ ví thụ hưởng bằng lệnh gọi cấp thấp (`call`) và yêu cầu phải chuyển sang trạng thái "Đã thực thi" để chống thực thi lặp lại.
* **R7**: Sinh viên nộp thừa hoặc nộp sai có quyền tạo yêu cầu hoàn tiền kèm mã minh chứng (`proofHash`), và số tiền này chỉ được hoàn trả về ví sinh viên khi được Ban cán sự biểu quyết thông qua.
* **R8**: Hệ thống chỉ cho phép tồn tại tối đa 01 yêu cầu chi ở trạng thái 'Đang chờ duyệt' (Pending) tại một thời điểm. Phải xử lý xong (thực thi hoặc hủy) yêu cầu hiện tại thì BCS mới được tạo yêu cầu chi mới.
* **R9**: Hủy và dọn dẹp yêu cầu chi:
* **Hủy chủ động**: Cố vấn học tập (CVHT) hoặc người tạo yêu cầu CHỈ CÓ QUYỀN gọi hàm Hủy (Cancel) khi yêu cầu chưa đạt 51% (đang Pending). Khi đã đạt 51% (chuyển sang Ready), quyền Hủy bị vô hiệu hóa.
* **Dọn dẹp quá hạn**: Nếu một yêu cầu chi tồn tại quá 7 ngày kể từ lúc tạo mà vẫn chưa được giải ngân thành công, BẤT KỲ TÀI KHOẢN NÀO cũng có thể gọi hàm "Đánh dấu hết hạn" (Expire) để dọn dẹp, giải phóng hệ thống cho yêu cầu chi mới.
* **R10**: Sinh viên có quyền tự Hủy (Cancel) yêu cầu hoàn tiền đang ở trạng thái 'Đang chờ duyệt' của chính mình. Yêu cầu xin hoàn tiền KHÔNG bị áp dụng cơ chế tự động dọn dẹp sau 7 ngày để bảo vệ tài sản của người nộp nhầm.
* **R11**: Chỉ Cố vấn học tập (Owner) mới có quyền gọi hàm rút tiền (`withdrawAdminFee`) từ Quỹ dịch vụ vận hành (`adminFeePool`) về ví cá nhân nhằm mục đích bù đắp chi phí Gas.

## 4. Đầu ra

* **Tài sản chuyển giao (ETH Transfer):**
* Chuyển số ETH giải ngân tương ứng tới địa chỉ ví thụ hưởng (`recipient`) khi yêu cầu chi được thực thi thành công.
* Chuyển số ETH hoàn trả về địa chỉ ví của sinh viên khi yêu cầu xin hoàn tiền được Ban cán sự phê duyệt.
* Chuyển số ETH từ `adminFeePool` về ví CVHT khi có lệnh rút phí quản lý.


* **Trạng thái lưu trữ trên hợp đồng (State):**
* Trạng thái yêu cầu chi: Đang chờ duyệt (`Pending`), Sẵn sàng thực thi (`Ready`), Đã thực thi (`Executed`), Bị bác bỏ (`Rejected`).
* Trạng thái yêu cầu hoàn tiền: Đang chờ duyệt (`Pending`), Đã chấp thuận (`Approved`), Bị bác bỏ (`Rejected`), Đã hoàn tiền (`Refunded`).
* Dữ liệu lưu trữ: Tổng số dư quỹ lớp chính, Quỹ dịch vụ vận hành (`adminFeePool`), danh sách và số lượng thành viên Ban cán sự đang hoạt động, lịch sử biểu quyết của từng thành viên.


* **Sự kiện ghi nhận trên Blockchain (Events):**
* Ghi nhận thông tin thay đổi nhân sự Ban cán sự (`BCSMemberUpdated`).
* Ghi nhận lịch sử giao dịch nộp quỹ của sinh viên (`FundDeposited`).
* Ghi nhận việc thu phí dịch vụ quản lý (`AdminFeeCollected`).
* Ghi nhận việc rút phí dịch vụ quản lý (`AdminFeeWithdrawn`).
* Ghi nhận thông tin khởi tạo, biểu quyết và giải ngân yêu cầu chi (`SpendRequestCreated`, `SpendRequestVoted`, `SpendRequestExecuted`).
* Ghi nhận thông tin tạo và xét duyệt yêu cầu hoàn tiền (`RefundRequested`, `RefundProcessed`).


* **Giao diện hiển thị (DApp / Block Explorer):**
* Bảng điều khiển minh bạch hiển thị số dư thực tế, tổng quỹ thu vào, tổng quỹ đã chi và số dư Quỹ dịch vụ vận hành.
* Danh sách lịch sử đóng quỹ của sinh viên theo thời gian thực.
* Bảng danh sách các yêu cầu chi tiêu kèm tiến độ biểu quyết, thời hạn mở khóa 7 ngày và nút bấm thực thi giải ngân.
* Bảng quản lý và tra cứu tiến độ các yêu cầu xin hoàn tiền.



## 5. Trường hợp ngoại lệ

* Nếu tài khoản không phải là Cố vấn học tập thực hiện thao tác quản lý Ban cán sự hoặc rút tiền từ Quỹ dịch vụ vận hành, hệ thống phải từ chối giao dịch (revert).
* Nếu tài khoản không thuộc danh sách Ban cán sự đang hoạt động thực hiện tạo yêu cầu chi, bỏ phiếu hoặc gọi hàm thực thi giải ngân thì hệ thống phải từ chối giao dịch (revert).
* Nếu một thành viên Ban cán sự cố gắng bỏ phiếu nhiều lần cho cùng một yêu cầu chi tiêu thì hệ thống phải từ chối giao dịch (revert).
* Nếu gọi hàm thực thi giải ngân khi yêu cầu chi chưa đạt tối thiểu 51% phiếu đồng ý và chưa đủ 7 ngày thì hệ thống phải từ chối giao dịch (revert).
* Nếu gọi thực thi giải ngân cho một yêu cầu chi đã ở trạng thái "Đã thực thi" thì hệ thống phải từ chối giao dịch (revert).
* Nếu số dư khả dụng trong quỹ chính không đủ để thực hiện giải ngân cho yêu cầu chi hoặc hoàn tiền thì hệ thống phải từ chối giao dịch (revert).
* Nếu sinh viên gửi yêu cầu xin hoàn tiền với số tiền bằng 0 hoặc lớn hơn số tiền thực tế sinh viên đó đã nộp vào quỹ thì hệ thống phải từ chối giao dịch (revert).
* Nếu một sinh viên đang có 1 yêu cầu hoàn tiền 'Đang chờ duyệt' mà tiếp tục tạo thêm yêu cầu hoàn tiền mới, hệ thống phải từ chối (revert) và báo lỗi Spam.

## 6. Ngoài phạm vi

* Lưu trữ trực tiếp tệp tin ảnh minh chứng hoàn tiền trên hợp đồng thông minh blockchain.
* Cơ chế tự động kích hoạt giải ngân khi hết hạn 7 ngày mà không cần tương tác (Smart contract không tự chạy ngầm).
* Hỗ trợ thanh toán hoặc quy đổi tiền pháp định (Fiat/VND) và các loại token ERC-20 khác.
* Tích hợp hệ thống quản lý danh tính sinh viên tập trung (SSO/Portal trường học).
* Cơ chế ủy quyền bỏ phiếu (proxy voting) hoặc phân bổ trọng số phiếu bầu khác nhau giữa các thành viên Ban cán sự.

---

## 7. Phụ lục Lab 14: Quy trình Hoàn tiền có Biểu quyết Ban Cán sự (Governance-Controlled Refund R7)

Để ngăn chặn việc thành viên tự ý rút tiền trực tiếp khỏi quỹ lớp mà không có sự đồng thuận của tập thể, hệ thống chuẩn hóa quy trình hoàn tiền R7 theo cơ chế kiểm soát nghiêm ngặt 3 bước có biểu quyết Ban cán sự (BCS) tương tự quy trình đề xuất chi tiêu:

**Sinh viên gửi yêu cầu hoàn tiền $\rightarrow$ BCS biểu quyết ($\ge 51\%$) $\rightarrow$ Thực thi hoàn tiền $\rightarrow$ Giải phóng giữ chỗ & Chuyển ETH.**

1. **Bước 1 — Tạo yêu cầu hoàn tiền (`createRefundRequest`):**
   - Người gọi (`msg.sender`) tự tạo yêu cầu hoàn tiền cho chính mình kèm lý do mô tả (`reason`).
   - `amount > 0`: Chặn yêu cầu 0 wei bằng lỗi tùy biến `ZeroAmount()`.
   - `amount <= getStudentAvailableContribution(msg.sender)`: Hạn mức hoàn tiền khả dụng của sinh viên được tính bằng tổng đóng góp trừ đi các khoản đang trong yêu cầu hoàn tiền chờ duyệt (`pendingStudentRefundAmount[msg.sender]`). Nếu vượt quá hoặc người chưa từng đóng góp, revert `InsufficientContribution(requested, available)`.
   - `amount <= getAvailableClassFund()`: Số tiền hoàn không được vượt quá số dư khả dụng thực tế của Quỹ lớp chính (sau khi trừ cả `reservedSpendAmount` lẫn `reservedRefundAmount`). Nếu vượt quá, revert `InsufficientAvailableFund(requested, available)`.
   - Cơ chế giữ chỗ kép an toàn (Dual-layer Reservation): Tăng đồng thời `reservedRefundAmount += amount` (giữ chỗ trên quỹ lớp) và `pendingStudentRefundAmount[msg.sender] += amount` (giữ chỗ trên hạn mức của chính sinh viên).
   - Tuyệt đối không tự động chuyển ETH ra khỏi hợp đồng tại bước tạo yêu cầu.
   - Phát sự kiện `RefundRequestCreated(requestId, applicant, amount, reason)`.

2. **Bước 2 — Ban cán sự biểu quyết (`voteRefundRequest`):**
   - Chỉ thành viên Ban cán sự hợp lệ và đang hoạt động mới có quyền bỏ phiếu (`onlyActiveBCS`).
   - Mỗi thành viên BCS chỉ được bỏ phiếu một lần duy nhất cho mỗi yêu cầu (`AlreadyVotedRefund`).
   - Thời hạn biểu quyết cố định 7 ngày (`VOTING_PERIOD = 7 days`). Sau thời hạn này, cấm bỏ phiếu (`RefundVotingPeriodEnded`).
   - Ngưỡng thông qua: Khi số phiếu thuận đạt tối thiểu 51% (5,100 basis points) trên tổng số BCS hoạt động hiện hành (`activeBCSCount`), yêu cầu tự động chuyển sang trạng thái Sẵn sàng thực thi (`Ready`).
   - Phát sự kiện `RefundRequestVoted` và `RefundRequestReady`.
   - Dọn dẹp quá hạn (`expireRefundRequest`): Nếu sau 7 ngày không đạt đủ 51% phiếu thuận, bất kỳ ai cũng có thể gọi hàm dọn dẹp để chuyển sang trạng thái `Expired`, giải phóng toàn bộ số tiền giữ chỗ kép về quỹ khả dụng.

3. **Bước 3 — Thực thi hoàn tiền (`executeRefundRequest`):**
   - Chỉ yêu cầu đã đạt trạng thái `Ready` và chưa hết hạn mới được phép thực thi (`InvalidRefundStatus`).
   - Xác minh lại hạn mức đóng góp và số dư quỹ lớp trước khi giải ngân.
   - Tuân thủ nghiêm ngặt nguyên tắc Checks-Effects-Interactions (CEI): Cập nhật trạng thái `req.status = Executed`, trừ `studentContributions[applicant]`, trừ `classFundBalance`, giải phóng `reservedRefundAmount` và `pendingStudentRefundAmount[applicant]` TRƯỚC KHI thực hiện lệnh chuyển ETH.
   - Tiền hoàn trả chuyển trực tiếp đến địa chỉ ví của chính sinh viên đã tạo yêu cầu (`req.applicant`) qua low-level call `.call{value: req.amount}("")`. Không ai có thể thay đổi địa chỉ nhận tiền.
   - Nếu chuyển ETH thất bại, toàn bộ giao dịch revert `ETHTransferFailed()` và rollback 100% kế toán.
   - Chặn Reentrancy và chống thực thi hai lần (`RefundAlreadyExecuted`).
   - Phát sự kiện `RefundRequestExecuted(requestId, applicant, amount)`.

4. **Bảo toàn quy tắc kinh tế 99%/1%:**
   - Khoản tiền hoàn trả trích 100% từ Quỹ lớp chính (`classFundBalance`).
   - Khoản phí dịch vụ vận hành 1% đã trích vào `adminFeePool` tại thời điểm nộp quỹ được giữ nguyên (sinh viên chịu khoản phí vận hành này để bù đắp chi phí Gas mạng lưới).
   - Tuyệt đối không tồn tại bất kỳ hàm `refund()` công khai nào cho phép sinh viên rút tiền trực tiếp bỏ qua biểu quyết của BCS.
