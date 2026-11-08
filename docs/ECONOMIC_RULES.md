# QUY TẮC KINH TẾ - KTS-CLASS-FUND (BẢN CẬP NHẬT LAB 15)

## 1. Dòng tiền và Quyền lợi (Cash Flow & Incentives)

* **Dòng tiền vào:**
  - Nguồn vốn xuất phát từ việc sinh viên trong danh sách ghi danh (`isStudent[wallet] == true`) nộp ETH vào Hợp đồng thông minh (qua hàm nộp chung `deposit()`, gửi trực tiếp `receive()`, hoặc nộp vào đợt thu cụ thể `depositToCollection()`).
  - Phân bổ tự động:
    - **99% (Basis points: 9,900)** phân bổ vào Quỹ lớp chính (`classFundBalance`) để phục vụ các hoạt động của lớp.
    - **1% (Basis points: 100)** trích tự động vào Quỹ dịch vụ vận hành (`adminFeePool`) để tài trợ chi phí Gas cho các thao tác quản trị.
  - Hạch toán tách bạch: `studentContributions[student]` lưu hạn mức đóng góp khả dụng **99% net**; `studentTotalDeposited[student]` lưu tổng số tiền **100% gross** đã nộp.

* **Dòng tiền ra:** ETH chỉ rời khỏi hợp đồng qua 4 kênh chính ngạch:
  1. Chuyển đến ví **Người thụ hưởng** khi một "Yêu cầu chi" được BCS thông qua và giải ngân (trích từ Quỹ lớp chính).
  2. Hoàn trả về ví **Sinh viên** khi "Yêu cầu hoàn tiền" được BCS phê duyệt (trích từ Quỹ lớp chính theo hạn mức Net 99%).
  3. **Tự động hoàn Gas (Gas Refund):** Hoàn trả ETH trực tiếp về ví người thực thi 10 hàm quản trị thông qua modifier `governanceAction` (trích từ `adminFeePool`).
  4. **Chuyển phí dư sang Quỹ lớp:** Chuyển ETH từ `adminFeePool` sang `classFundBalance` qua hàm `moveFeeToClassFund()` do Cố vấn học tập gọi.
  *(Quyền rút phí vận hành tùy ý về ví cá nhân `withdrawAdminFee` đã bị xóa bỏ hoàn toàn)*.

* **Quyền lợi và Động lực (Incentives):**
  - **Sinh viên:** Tài sản được bảo vệ 100% on-chain, hạn mức hoàn tiền net công bằng, dòng tiền minh bạch, thông tin cá nhân (PII) được bảo vệ tuyệt đối ngoài chuỗi.
  - **Ban cán sự & CVHT:** Được hoàn gas tự động tức thời ngay trong giao dịch theo giá thị trường EIP-1559, xóa bỏ hoàn toàn gánh nặng ứng trước gas cá nhân khi quản trị lớp.

---

## 2. Giới hạn chống lạm dụng và Bất biến kinh tế (Anti-abuse Limits & Invariants)

* **Bất biến số dư tổng thể (Accounting Conservation):**
  $$\text{address(this).balance} \ge \text{classFundBalance} + \text{adminFeePool}$$
  *(Phần chênh lệch nếu có do nhận ETH cưỡng bức qua `selfdestruct` được theo dõi riêng qua `getUnaccountedBalance()`)*.

* **Hạn mức hoàn tiền tối đa (Net Refund Cap):**
  Sinh viên chỉ được yêu cầu hoàn số tiền tối đa:
  $$\text{maxRefund} = \min(\text{getStudentAvailableContribution(student)}, \text{getAvailableClassFund()})$$
  Triệt tiêu rủi ro lấy tiền của sinh viên khác bù vào 1% phí vận hành đã trích.

* **Cơ chế Giữ chỗ Kép (Dual-layer Reservation):**
  - Khi tạo yêu cầu chi: Giữ chỗ trên quỹ lớp (`reservedSpendAmount`).
  - Khi tạo yêu cầu hoàn: Giữ chỗ đồng thời trên quỹ lớp (`reservedRefundAmount`) và trên hạn mức sinh viên (`pendingStudentRefundAmount[student]`).
  - Chống chi vượt ngân sách, chống hoàn tiền kép và chống front-running giữa chi tiêu và hoàn tiền.

* **Bảo vệ đợt thu on-chain (Collection Isolation):**
  - Chỉ cho phép tối đa 01 đợt thu đang mở tại một thời điểm.
  - Trạng thái hoàn thành đợt thu dựa trên `paidInCollection >= targetWei` của đúng đợt đó, không xâm lấn hoặc lẫn lộn giữa các đợt thu khác nhau.

---

## 3. Cơ chế Quản trị Dân chủ & Chống Lũng đoạn (Governance Architecture)

* **Chống tạo cử tri ma (3-Day Activation Delay):**
  - Thành viên BCS mới được bổ nhiệm bắt buộc phải trải qua thời gian chờ `BCS_ACTIVATION_DELAY = 3 seconds` (3 giây) mới có hiệu lực hoạt động (đã cấu hình giảm từ 3 ngày xuống 3 giây để thuận tiện kiểm thử/demo).
  - Vô hiệu hóa âm mưu của Cố vấn học tập tự ý thêm ví phụ vào biểu quyết tức thời để lật ngược kết quả biểu quyết.

* **Bảo toàn mẫu số biểu quyết (Snapshot `voterBase`):**
  - Mẫu số cử tri được chốt cố định tại thời điểm tạo đề xuất chi hoặc hoàn tiền.
  - Mọi thay đổi nhân sự BCS sau đó không làm thay đổi tỷ lệ đồng thuận $\ge 51\%$ của các đề xuất đang trong thời gian bỏ phiếu.

* **Ràng buộc quy mô cử tri:**
  - `MIN_BCS_FOR_PROPOSAL = 3`: Bắt buộc phải có tối thiểu 3 BCS đủ điều kiện mới được phép tạo đề xuất hoặc yêu cầu hoàn tiền.
  - `MAX_BCS = 15`: Giới hạn tối đa 15 thành viên BCS để bảo vệ hiệu năng và gas mạng lưới.

* **Chặn xung đột lợi ích (Conflict of Interest Defense):**
  - Sinh viên xin hoàn tiền không được bỏ phiếu cho chính yêu cầu của mình.
  - BCS là người thụ hưởng tiền giải ngân không được bỏ phiếu cho đề xuất chi đó.
  - Mẫu số tự động trừ 1 (`voterBase - 1`) và bắt buộc phải có tối thiểu 2 phiếu thuận (`yesVotes >= 2`) để được thông qua.

* **Cơ chế bác bỏ sớm khi No chiếm đa số (Early Rejection Defense):**
  - Khi số phiếu chống khiến số phiếu thuận không thể đạt ngưỡng 51% của `voterBase` ($(\text{voterBase} - \text{noVotes}) \times 10,000 / \text{voterBase} < 5,100$), đề xuất chi hoặc hoàn tiền lập tức chuyển sang trạng thái `Rejected`.
  - Toàn bộ tiền giữ chỗ (`reservedSpendAmount` hoặc `reservedRefundAmount` + `pendingStudentRefundAmount`) được giải phóng ngay lập tức về Quỹ khả dụng.
  - Chống giải phóng hai lần: các hàm `vote`, `execute`, `expire` đều kiểm tra và từ chối nếu yêu cầu đã `Rejected`.

* **Giới hạn đề xuất chi mở đồng thời (Open Spend Requests Cap):**
  - Mỗi thành viên BCS chỉ được phép duy trì tối đa 03 đề xuất chi ở trạng thái mở (`Pending` hoặc `Ready`) đồng thời (`MAX_OPEN_SPEND_PER_CREATOR = 3`).
  - Đề xuất thứ 4 bị revert với `TooManyOpenRequests()`.
  - Biến đếm được giảm an toàn khi đề xuất kết thúc (`Executed`, `Expired`, `Rejected`).

* **Tự động đóng đợt thu quá hạn (Auto-close Expired Collection):**
  - Khi mở đợt thu mới qua `createCollection`, nếu đợt thu hiện tại đã quá hạn (`block.timestamp > deadline`), hợp đồng tự động đóng đợt cũ với lý do `"Hết hạn tự động"` và tiếp tục mở đợt mới.

---

## 4. Cơ chế Hoàn Gas Tự động & Xử lý Thiếu hụt (Gas Refund Mechanism)

* **Công thức hoàn Gas EIP-1559:**
  $$\text{gasRefund} = \min(\text{gasUsed}, 500,000) \times \min(\text{tx.gasprice}, \text{block.basefee} + 2\text{ gwei})$$
  - Áp dụng tự động cho 10 hàm quản trị của CVHT và BCS qua modifier `governanceAction`.

* **Bỏ qua hoàn gas khi trạng thái không đổi (No-Op Gas Refund Skip):**
  - Khi `setBCSMember` được gọi với trạng thái trùng với trạng thái hiện tại (`isBCSMember[member] == status`), hệ thống kích hoạt `_skipGasRefund = true` và không hoàn gas, tránh thất thoát `adminFeePool` cho các giao dịch không tạo ra thay đổi trạng thái thực sự.

* **Xử lý khi Quỹ dịch vụ cạn (Shortfall Handling):**
  - Nếu `adminFeePool < gasRefund`, hợp đồng chuyển toàn bộ số dư còn lại của pool và ghi nhận khoản thiếu hụt vào biến `gasRefundShortfall`.
  - Giao dịch quản trị chính vẫn hoàn tất thành công 100%, không bị revert do cạn quỹ gas.

* **An toàn chuyển tiền hoàn gas (Fallback Defense):**
  - Nếu ví người gọi từ chối nhận ETH hoàn gas, phát sự kiện `GasRefundFailed`, hoàn trả số dư vào `adminFeePool` và không làm rollback giao dịch quản trị chính.

---

## 5. Rủi ro Còn lại và Biện pháp Giảm thiểu (Residual Risks)

* **Rủi ro đình công biểu quyết BCS:** Nếu BCS không bỏ phiếu trong vòng 7 ngày, đề xuất tự động hết hạn (`expireSpendRequest` / `expireRefundRequest`) để giải phóng toàn bộ số tiền giữ chỗ về quỹ khả dụng.
* **Rủi ro biến động tỷ giá ETH/VNĐ:** Quỹ lớp lưu trữ bằng ETH nên sức mua VNĐ biến động theo thị trường. Khuyến nghị trong tương lai mở rộng hỗ trợ Stablecoin (USDT/USDC).
* **Rủi ro chuyển tiền từ Sàn tập trung (CEX):** Cần nộp qua ví cá nhân (MetaMask) nằm trong danh bạ sinh viên on-chain để bảo đảm nhận hoàn tiền an toàn.
