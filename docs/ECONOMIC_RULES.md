**QUY TẮC KINH TẾ - KTS-CLASS-FUND**

## 1. Dòng tiền và Quyền lợi (Cash Flow & Incentives)

* **Dòng tiền vào:** Nguồn vốn của hệ thống đến từ việc sinh viên nộp ETH (đơn vị: wei) vào địa chỉ Hợp đồng thông minh. Khi nhận tiền, hợp đồng tự động phân bổ:
* **99%** cộng vào Quỹ lớp chính để phục vụ các hoạt động tập thể.
* **1% (100 basis points)** trích tự động vào Quỹ dịch vụ vận hành (`adminFeePool`).
* **Dòng tiền ra:** ETH chỉ rời khỏi hợp đồng qua ba đường:
1. Chuyển đến ví của **Người thụ hưởng** khi một "Yêu cầu chi" được thông qua và thực thi (trích từ Quỹ lớp chính).
2. Hoàn trả về ví của **Sinh viên** khi "Yêu cầu hoàn tiền" được phê duyệt (trích từ Quỹ lớp chính).
3. Chuyển về ví của **Cố vấn học tập** khi thực hiện lệnh rút phí vận hành (trích riêng từ Quỹ dịch vụ vận hành).
* **Quyền lợi và Động lực (Incentives):**
* **Sinh viên:** Được bảo vệ tài sản nhờ cơ chế minh bạch 100% on-chain, ngăn chặn tình trạng lạm dụng quỹ.
* **Ban cán sự & CVHT:** Được hỗ trợ chi trả phí Gas mạng lưới thông qua Quỹ dịch vụ vận hành, loại bỏ rào cản tài chính cá nhân khi tham gia quản trị; các quyết định chi tiêu mang tính tập thể, phân tán trách nhiệm.
## 2. Giới hạn chống lạm dụng (Anti-abuse Limits)

* **Chống rút cạn quỹ (Over-spending Prevention):** Yêu cầu chi hay hoàn tiền có giá trị lớn hơn số dư khả dụng của Quỹ lớp chính đều bị hệ thống chặn lại (revert). Quỹ dịch vụ vận hành được tách biệt hoàn toàn khỏi số dư này.
* **Chống bỏ phiếu kép (Double Voting):** Một địa chỉ ví thuộc BCS chỉ được phép ghi nhận 1 phiếu (đồng ý hoặc bác bỏ) cho mỗi mã định danh yêu cầu. Không thể bỏ phiếu lại.
* **Chống thực thi lặp (Double-spending):** Khi một "Yêu cầu chi" đã được giải ngân thành công, trạng thái chuyển thành `Executed`. Bất kỳ ai cố tình gọi lại hàm thực thi sẽ bị từ chối.
* **Chống xả rác yêu cầu hoàn tiền (Spam/Fraudulent Refunds):** Sinh viên không thể tạo yêu cầu hoàn lại số tiền lớn hơn tổng số tiền họ đã thực tế đóng góp tính đến thời điểm hiện tại.

## 3. Quyền quản trị (Governance Rights)

* **Quyền nhân sự tối cao (Owner/Admin):** Cố vấn học tập (CVHT) là người duy nhất nắm quyền thêm mới, tạm khóa, hoặc xóa thành viên BCS.
* **Quyền rút quỹ dịch vụ:** CVHT là địa chỉ duy nhất có quyền gọi hàm `withdrawAdminFee()` để rút số dư từ `adminFeePool` về ví nhằm trang trải chi phí Gas cho các thao tác quản trị. CVHT bị cấm hoàn toàn việc tự ý rút tiền từ Quỹ lớp chính.
* **Cơ chế đồng thuận đa số (Majority Consensus):** Trọng số phiếu bầu của mọi thành viên BCS là ngang nhau (1 người = 1 phiếu). Yêu cầu chi chỉ "Sẵn sàng thực thi" khi đạt $\ge$ 51% (5100 basis points) trên tổng số BCS hiện hành.
* **Phân tán quyền thực thi (Decentralized Execution):** Khi yêu cầu chi đã đủ điều kiện (đạt 51% phiếu HOẶC hết thời gian chờ 7 ngày), bất kỳ thành viên BCS nào cũng có thể gọi hàm thực thi. Người thực thi trả trước phí Gas và được CVHT hoàn bù lại từ Quỹ dịch vụ vận hành.

## 4. Tình huống người dùng bị thiệt (User Disadvantage Scenarios)

* **Rủi ro mất khóa quản trị:** Nếu CVHT làm mất Private Key của ví Owner, lớp sẽ vĩnh viễn mất khả năng cập nhật danh sách BCS và không thể rút Quỹ dịch vụ vận hành. (Chấp nhận trong v0.1).
* **Tiền bị khóa vĩnh viễn (Deadlocked Funds):** Nếu BCS đình công không bỏ phiếu và không ai chịu trả phí Gas để gọi hàm thực thi sau 7 ngày, ETH sẽ kẹt vĩnh viễn trong hợp đồng.
* **Rủi ro chuyển nhầm từ Sàn giao dịch (CEX):** Nếu sinh viên nộp bằng cách chuyển trực tiếp từ sàn (Binance/OKX) thay vì ví cá nhân (MetaMask), khi được duyệt hoàn tiền, tiền sẽ bị trả về ví tổng của sàn và nguy cơ mất trắng. Đây là rủi ro nghiệp vụ bắt buộc cảnh báo trên giao diện khi Mainnet.
* **Rủi ro tỷ giá (Price Volatility):** Do lưu trữ bằng ETH thay vì Stablecoin, sức mua của quỹ lớp tính theo VNĐ sẽ biến động. Giải pháp tối ưu cho tương lai là hỗ trợ ERC-20 Token (USDT/USDC).
* **Rủi ro lạm quyền từ Cố vấn học tập (Admin Trust Assumption):** CVHT có thể thay đổi nhân sự BCS ngay lập tức kể cả khi đang có yêu cầu chi chờ duyệt để thao túng tỷ lệ 51%. Tập thể lớp phải giám sát lịch sử thay đổi trên chuỗi.
* **Rủi ro BCS ưu tiên chi tiêu để chặn hoàn tiền (Front-running Refund) — Đã khắc phục trong Lab 14:** Khi sinh viên tạo yêu cầu hoàn tiền (`createRefundRequest`), hệ thống tự động khóa giữ chỗ số dư (`reservedRefundAmount`) trên Quỹ lớp chính. Đề xuất chi tiêu phát sinh sau không thể xâm phạm ngân sách đang giữ chỗ này, loại bỏ rủi ro front-running rút cạn quỹ.
* **Rủi ro tấn công Sybil xả rác:** Kẻ gian có thể dùng nhiều ví gửi 1 wei để tạo hàng loạt yêu cầu hoàn tiền rác. BCS sẽ phải bỏ qua các yêu cầu này bằng mắt thường trên giao diện.
* **Rủi ro nghẽn biểu quyết do BCS ngừng hoạt động:** Tỷ lệ 51% luôn tính trên tổng số thành viên BCS được ghi nhận. Nếu nhiều thành viên mất ví, yêu cầu sẽ không thể đạt 51%. CVHT phải chủ động dùng quyền quản trị để xóa "thành viên ma", hạ mức trần của tỷ lệ 51% xuống thực tế.