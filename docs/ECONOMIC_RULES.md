# QUY TẮC KINH TẾ - KTS-Class-Fund

## 1. Dòng tiền và Quyền lợi (Cash Flow & Incentives)

* **Dòng tiền vào:** Nguồn vốn duy nhất của hệ thống đến từ việc sinh viên trong lớp tự nguyện chuyển ETH (đơn vị: wei) từ ví cá nhân vào địa chỉ của Hợp đồng thông minh (Smart Contract). Hợp đồng đóng vai trò là két sắt chung.
* **Dòng tiền ra:** ETH chỉ rời khỏi hợp đồng qua hai đường:
1. Chuyển đến ví của **Người thụ hưởng** (nhà cung cấp dịch vụ, ban tổ chức sự kiện) khi một "Yêu cầu chi" được Ban cán sự (BCS) thông qua và thực thi.
2. Hoàn trả về ví của **Sinh viên** khi "Yêu cầu hoàn tiền" (do nộp nhầm/sai) được BCS phê duyệt.


* **Quyền lợi và Động lực (Incentives):**
* **Sinh viên:** Được bảo vệ tài sản nhờ cơ chế minh bạch 100% on-chain. Mọi giao dịch thu/chi đều công khai, ngăn chặn tuyệt đối tình trạng thủ quỹ lạm dụng tiền lớp.
* **Ban cán sự:** Được giải phóng khỏi áp lực và rủi ro khi phải giữ tiền mặt hoặc tiền trong tài khoản ngân hàng cá nhân; các quyết định chi tiêu mang tính tập thể, phân tán trách nhiệm.



## 2. Giới hạn chống lạm dụng (Anti-abuse Limits)

* **Chống rút cạn quỹ (Over-spending Prevention):** Bất kỳ "Yêu cầu chi" hay "Yêu cầu hoàn tiền" nào có giá trị lớn hơn tổng số dư khả dụng (`address(this).balance`) tại thời điểm thực thi đều bị hệ thống chặn lại và giao dịch sẽ thất bại (revert).
* **Chống bỏ phiếu kép (Double Voting):** Một địa chỉ ví thuộc BCS chỉ được phép ghi nhận 1 phiếu (đồng ý hoặc bác bỏ) cho mỗi mã định danh yêu cầu (`requestId` hoặc `refundId`). Không thể bỏ phiếu lại để gian lận tỷ lệ % đồng thuận.
* **Chống thực thi lặp (Double-spending):** Khi một "Yêu cầu chi" đã được giải ngân thành công, trạng thái của nó lập tức chuyển thành `Executed`. Bất kỳ ai cố tình gọi lại hàm thực thi cho yêu cầu đó sẽ bị hợp đồng từ chối.
* **Chống xả rác yêu cầu hoàn tiền (Spam/Fraudulent Refunds):** Sinh viên không thể tạo yêu cầu hoàn lại số tiền lớn hơn tổng số tiền họ đã thực tế đóng góp vào quỹ tính đến thời điểm hiện tại.

## 3. Quyền quản trị (Governance Rights)

* **Quyền nhân sự tối cao (Owner/Admin):** Cố vấn học tập (CVHT) là người duy nhất nắm quyền sinh sát về mặt tổ chức (thêm mới, tạm khóa, hoặc xóa thành viên khỏi danh sách BCS). Tuy nhiên, **CVHT bị tước hoàn toàn quyền tự ý rút tiền** khỏi hợp đồng.
* **Cơ chế đồng thuận đa số (Majority Consensus):** Trọng số phiếu bầu của mọi thành viên BCS là ngang nhau (1 người = 1 phiếu). Một yêu cầu chi chỉ đạt trạng thái "Sẵn sàng thực thi" khi tỷ lệ phiếu thuận $\ge$ 51% (5100 basis points) trên tổng số BCS hiện hành.
* **Phân tán quyền thực thi (Decentralized Execution):** Hợp đồng không tự động chuyển tiền. Khi yêu cầu chi đã đủ điều kiện (đạt 51% phiếu HOẶC hết thời gian chờ 7 ngày), **bất kỳ** thành viên BCS nào cũng có quyền bấm nút gọi hàm thực thi. Người thực thi sẽ là người chi trả phí Gas cho giao dịch đó, thể hiện trách nhiệm đóng góp cho tập thể.

## 4. Tình huống người dùng bị thiệt (User Disadvantage Scenarios)

* **Rủi ro mất khóa quản trị:** Nếu CVHT làm mất 12 từ khóa khôi phục (Private Key) của ví Owner, lớp sẽ vĩnh viễn mất khả năng cập nhật danh sách BCS các năm học sau. (Được chấp nhận trong phiên bản v0.1 vì chưa cài đặt hàm `transferOwnership`).
* **Tiền bị khóa vĩnh viễn (Deadlocked Funds):** Nếu Ban cán sự đình công (không ai vào bỏ phiếu duyệt chi) và cũng không có ai chịu bỏ tiền túi trả phí Gas để gọi hàm thực thi sau khi hết hạn 7 ngày, số ETH đó sẽ nằm kẹt vĩnh viễn trong hợp đồng mà sinh viên không thể tự rút lại.
* **Rủi ro chuyển nhầm từ Sàn giao dịch (CEX - Cảnh báo khi Mainnet):** Nếu sinh viên nộp quỹ bằng cách chuyển trực tiếp ETH từ sàn (như Binance/OKX) thay vì dùng ví cá nhân (MetaMask), khi xảy ra lỗi và được duyệt hoàn tiền, tiền sẽ bị Smart Contract trả về ví tổng của sàn và sinh viên có nguy cơ mất trắng số tiền hoàn lại này do không nắm Private Key của ví sàn. [Ghi chú bản v0.1]: Trong phạm vi đồ án chạy trên mạng thử nghiệm Sepolia, sinh viên sử dụng Sepolia ETH từ Faucet qua ví MetaMask nên rủi ro này tạm thời không xảy ra. Tuy nhiên, đây là rủi ro nghiệp vụ bắt buộc phải đưa vào cảnh báo trên giao diện (UI) nếu dự án tiến lên Mainnet.
* **Rủi ro tỷ giá (Price Volatility - Hạn chế của hệ thống):** Do thiết kế quỹ lớp lưu trữ trực tiếp bằng đồng tiền gốc của mạng lưới (ETH) thay vì đồng ổn định giá (Stablecoin như USDT), sức mua của quỹ lớp tính theo tiền pháp định (VNĐ) sẽ biến động mạnh theo thị trường. Tập thể lớp phải chấp nhận rủi ro đầu tư này khi lưu trữ quỹ bằng Crypto. [Ghi chú bản v0.1]: Quỹ hiện sử dụng Sepolia ETH (không có giá trị thực tế) nên rủi ro tỷ giá không gây thiệt hại tài chính. Ở các phiên bản mở rộng thực tế, giải pháp tối ưu là nâng cấp hợp đồng hỗ trợ nhận nộp quỹ bằng ERC-20 Token (ví dụ: USDT/USDC) để triệt tiêu hoàn toàn rủi ro này.
* **Rủi ro lạm quyền từ Cố vấn học tập (Admin Trust Assumption):** Hệ thống v0.1 cho phép CVHT thay đổi nhân sự BCS ngay lập tức kể cả khi đang có yêu cầu chi chờ duyệt. Nếu CVHT có ý đồ xấu, họ có thể xóa các BCS đang bỏ phiếu chống để thao túng tỷ lệ đạt 51%. Tập thể lớp phải đặt niềm tin tuyệt đối vào đạo đức của CVHT, hoặc nâng cấp lên phiên bản v0.2 có cơ chế khóa thay đổi nhân sự (Timelock).
* **Rủi ro đùn đẩy phí Gas khi hoàn tiền:** Để duyệt yêu cầu hoàn tiền cho sinh viên nộp sai, thành viên BCS phải tự bỏ tiền túi trả phí Gas mạng lưới để bấm duyệt. Do không có cơ chế hoàn phí Gas, BCS có thể chần chừ hoặc đùn đẩy trách nhiệm, dẫn đến việc tiền hoàn của sinh viên bị kẹt lại lâu hơn dự kiến.
* **Rủi ro BCS ưu tiên chi tiêu để chặn hoàn tiền (Front-running Refund):** Hệ thống v0.1 không tạm khóa (Escrow) số dư khi có yêu cầu hoàn tiền nhằm tối ưu độ phức tạp của mã nguồn. Nếu BCS cố tình tạo và duyệt nhanh lệnh chi tiêu để làm cạn quỹ trước khi hoàn tiền cho sinh viên, sinh viên sẽ bị mất quyền lợi. Tập thể lớp cần giám sát lịch sử on-chain để phát hiện hành vi lạm quyền này.
* **Rủi ro tấn công Sybil xả rác:** Do quỹ lớp không yêu cầu phí đặt cọc (Staking fee) khi tạo yêu cầu hoàn tiền, kẻ gian có thể dùng nhiều ví gửi 1 wei để tạo hàng loạt yêu cầu hoàn tiền rác. BCS sẽ phải bỏ qua các yêu cầu này bằng mắt thường trên giao diện thay vì tốn phí Gas để bác bỏ từng lệnh.
* **Rủi ro nghẽn biểu quyết do BCS ngừng hoạt động (Deadlock Quorum):** Tỷ lệ 51% luôn được tính trên tổng số thành viên BCS được ghi nhận trong hợp đồng. Nếu một số thành viên mất khóa ví hoặc không hoạt động, yêu cầu có thể không bao giờ đạt đủ 51%. Cách khắc phục bằng quy trình: CVHT phải giám sát và sử dụng quyền quản trị (R1) để xóa các "thành viên ma" này khỏi hợp đồng, qua đó tự động hạ mức trần của tỷ lệ 51% xuống mức thực tế.