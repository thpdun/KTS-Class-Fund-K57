# CHANGE_PLAN_LAB15 — Kế hoạch nâng cấp ProjectCore (đã thống nhất với nhóm)

> Tài liệu này là **NGUỒN SỰ THẬT** cho đợt nâng cấp. Nếu prompt hoặc code hiện tại mâu thuẫn với tài liệu, hãy **dừng lại và hỏi**.
> Theo `AGENTS.md`: không tự suy đoán quy tắc kinh tế; giải thích ngắn gọn lựa chọn thiết kế trước khi đưa mã; nêu tối thiểu 3 ca kiểm thử, trong đó có 1 ca gian lận.

---

## 0. Ràng buộc chung

1. Chỉ sửa trong phạm vi các mục A–G bên dưới. Không refactor ngoài phạm vi.
2. `advisor` **giữ nguyên `immutable`** (không thêm chuyển quyền Cố vấn).
3. **Không deploy**, không commit/push, **không tạo thêm file `.bak`**.
4. Không thêm thư viện ngoài (hợp đồng hiện không `import`). Khóa chống reentrancy tự viết nội bộ.
5. Tuân thủ 7 quy tắc Solidity trong `AGENTS.md`: event cho mọi thay đổi trạng thái; kiểm tra quyền rõ ràng; CEI; `call{value}` có kiểm tra kết quả; custom `error`; không `tx.origin`; phần trăm bằng basis point.
6. Giữ nguyên tên hàm/sự kiện/lỗi hiện có, trừ khi mục dưới nói rõ đổi hoặc xóa.
7. Mỗi phase phải cập nhật **đủ 3 lớp**: `ProjectCore.sol`, `test/test_economic_rules.py` (bản mô phỏng Python phải phản ánh đúng logic mới), và `test/ProjectCore_test.sol` + `test/ProjectCore_integration_test.sol`.
8. Báo cáo kết quả theo thực tế: chỉ ghi PASS cho lệnh **đã thực sự chạy**. Test Solidity chỉ mới biên dịch (chưa chạy Remix) phải ghi rõ "CHƯA CHẠY TRÊN REMIX".

---

## A. Kế toán hoàn tiền theo số net (Phase 1)

**Vấn đề:** hiện `studentContributions` ghi 100% tiền gốc nhưng quỹ lớp chỉ nhận 99%. Nạp 10 ETH thì quỹ nhận 9,9; xin hoàn 10 ETH bị chặn, xin hoàn 9,9 thì 0,1 còn lại kẹt vĩnh viễn trong sổ (hoặc lấy từ tiền của người khác).

**Quy tắc:**
```
phí         = nạp × FEE_BPS / 10000          (làm tròn xuống, như code hiện tại)
phần quỹ    = nạp − phí                      → ghi vào studentContributions (số NET)
hoàn tối đa = phần quỹ − đã hoàn − đang chờ duyệt
điều kiện   = số xin hoàn ≤ min(hoàn tối đa, quỹ khả dụng)
```
- Phí 1% **không được hoàn** (chính sách đã chốt trong `docs/AUDIT_REPORT.md`).
- `_processDeposit`: `studentContributions[sender] += classFundAmount` (net).
- Thêm `mapping(address => uint256) public studentTotalDeposited` ghi số gốc (gross), chỉ để hiển thị.
- Thêm view `getStudentMaxRefund(address)` = `min(getStudentAvailableContribution, getAvailableClassFund)`.
- Cập nhật NatSpec đang ghi "100% tiền gốc" và mọi nhãn tương ứng.
- Bất biến cần test: `address(this).balance == classFundBalance + adminFeePool` (khi không có ETH bị ép gửi).

**Test tối thiểu:** (1) nạp 10 → net 9,9, hoàn tối đa 9,9, sau khi hoàn hết `studentContributions == 0` (không còn sổ kẹt); (2) nạp 99 wei (phí 0) và 101 wei (phí 1); (3) **gian lận:** A nạp 10, B nạp 10, A xin hoàn 10 → bị từ chối; (4) hoàn nhiều lần cộng lại không vượt net.

---

## B. Snapshot biểu quyết, kích hoạt trễ, tối thiểu 3 BCS (Phase 2)

**Vấn đề:** ngưỡng 51% dùng `activeBCSCount` tại thời điểm gọi, nên Cố vấn thêm/xóa BCS giữa chừng sẽ đổi kết quả đề xuất đang chạy.

**Hằng số (đặt tên rõ, public constant):**
`BCS_ACTIVATION_DELAY = 3 days`, `MIN_BCS_FOR_PROPOSAL = 3`, `MAX_BCS = 15`.

**Quy tắc:**
- Lưu danh sách BCS (`address[] bcsList`, kèm chỉ mục để gỡ O(1)) và `mapping(address => uint256) memberSince`.
- `setBCSMember(m, true)`: thêm vào danh sách, `isBCSMember = true`, `memberSince[m] = block.timestamp + BCS_ACTIVATION_DELAY`. Vượt `MAX_BCS` thì revert `MaxBCSReached`. Thêm lại BCS đã gỡ thì tính lại mốc kích hoạt.
- `setBCSMember(m, false)`: gỡ khỏi danh sách, `isBCSMember = false`.
- Modifier `onlyActiveBCS` = `isBCSMember[msg.sender] && block.timestamp >= memberSince[msg.sender]`.
- Thêm view `eligibleBCSCount(uint256 atTimestamp)` (đếm thành viên có `memberSince <= atTimestamp`) và `isEligibleVoterAt(address, uint256)`. Vòng lặp chỉ chạy trên danh sách tối đa `MAX_BCS`.
- **Khi tạo đề xuất chi hoặc yêu cầu hoàn tiền:** tính `eligible = eligibleBCSCount(block.timestamp)`. Nếu `eligible < MIN_BCS_FOR_PROPOSAL` thì revert `NotEnoughBCS(eligible, MIN_BCS_FOR_PROPOSAL)`. Lưu `voterBase` (xem mục C) vào đề xuất. Cả sinh viên tạo yêu cầu hoàn tiền cũng bị chặn nếu chưa đủ 3 BCS.
- **Khi bỏ phiếu:** chỉ chấp nhận người có `isBCSMember[msg.sender] && memberSince[msg.sender] <= req.createdAt`.
- **Mọi phép tính ngưỡng 51%** (`voteSpendRequest`, `voteRefundRequest`, `executeSpendRequest`, `executeRefundRequest`, `_tryExecuteSpend`, `_tryExecuteRefund`) dùng `req.voterBase` thay cho `activeBCSCount`.
- BCS bị gỡ **sau khi** đã bỏ phiếu: phiếu giữ nguyên. Bị gỡ **trước khi** bỏ phiếu: không bỏ phiếu được; đề xuất có thể hết hạn. Hành vi này là chấp nhận được, ghi rõ trong tài liệu.
- Giữ nguyên cơ chế tự thực thi khi đạt ngưỡng.

**Test tối thiểu:** (1) thêm BCS mới giữa chừng không đổi `voterBase` của đề xuất đang chạy; (2) BCS mới chưa đủ 3 ngày không tạo/bỏ phiếu được; (3) gỡ BCS giữa chừng không đổi mẫu số; (4) dưới 3 BCS không tạo được đề xuất; (5) **gian lận:** Cố vấn thêm 3 ví "ma" ngay trước lúc bỏ phiếu → các ví đó không có quyền trên đề xuất hiện hữu.

---

## C. Xung đột lợi ích (Phase 2, cùng phase với B)

- **Yêu cầu hoàn tiền:** người nộp đơn (`applicant`) không được bỏ phiếu cho yêu cầu của mình: revert `ConflictOfInterest()`. Nếu người đó là BCS đủ điều kiện tại thời điểm tạo thì `voterBase = eligible − 1`; nếu không phải BCS thì `voterBase = eligible`.
- **Đề xuất chi:** nếu `recipient` là BCS đủ điều kiện tại thời điểm tạo thì người đó không được bỏ phiếu (`ConflictOfInterest()`), `voterBase = eligible − 1`. Nếu `recipient` **không** phải BCS thì mọi BCS (kể cả người tạo) bỏ phiếu bình thường.
- Bất biến cần test: mọi đề xuất được duyệt đều có `yesVotes >= 2` (vì `voterBase >= 2` và ngưỡng 51%).
- Khoản trả công cho BCS **không** đi qua đề xuất chi mà đi qua cơ chế phí (mục F).

**Test tối thiểu:** (1) 3 BCS, 1 người tự xin hoàn tiền: người đó bị chặn bỏ phiếu, cần đủ 2 phiếu thuận của 2 người còn lại; (2) recipient là BCS bị chặn bỏ phiếu; (3) recipient không phải BCS: các BCS còn lại bỏ phiếu bình thường; (4) **gian lận:** BCS tự bỏ phiếu thuận cho yêu cầu hoàn tiền của chính mình.

---

## D. Danh sách sinh viên trên chuỗi + hash roster (Phase 3)

- `mapping(address => bool) public isStudent`, `uint256 public enrolledCount`.
- `setStudents(address[] calldata members, bool status)` — `onlyAdvisor`, tối đa `MAX_BATCH = 100` địa chỉ mỗi lần (revert `BatchTooLarge`); địa chỉ zero revert `InvalidAddress`; phát `StudentEnrollmentUpdated(student, status)` cho từng địa chỉ; cập nhật `enrolledCount` đúng.
- `deposit()` và `receive()`: revert `NotEnrolledStudent(address)` nếu `!isStudent[msg.sender]`. Người lạ gửi ETH bị revert nên không mất tiền (chỉ mất gas). **Không** thêm hàm `donate()`.
- Gỡ khỏi danh sách **không** chặn quyền tạo yêu cầu hoàn tiền (nếu còn `studentContributions`).
- `setBCSMember(m, true)` yêu cầu `isStudent[m]` (revert `BCSMustBeEnrolledStudent`). Không cho gỡ student đang là BCS (revert `StudentIsBCS`).
- Cố vấn không được là student (revert `AdvisorCannotBeStudent`).
- `commitRoster(bytes32 hash)` — `onlyAdvisor`, lưu `rosterHash`, phát `RosterCommitted(hash, by, at)`.
- Thêm view `getUnaccountedBalance()` = `max(0, address(this).balance − classFundBalance − adminFeePool)` (phát hiện ETH bị ép gửi). Chỉ có view, **chưa** có hàm xử lý phần dư.
- **Backend:** thêm hàm tính hash roster chuẩn hóa trong `backend/import_roster.py` (sắp xếp theo `mssv`, JSON chuẩn `sort_keys=True`, `ensure_ascii=False`, `separators=(",", ":")`, `keccak256` hoặc `sha256` → `bytes32`; ghi rõ thuật toán đã chọn) và endpoint `GET /api/roster/hash`. Không đưa tên/MSSV lên chuỗi, chỉ đưa hash.

**Test tối thiểu:** (1) ví lạ gọi `deposit()` bị revert, số dư không đổi; (2) ví lạ gửi ETH trực tiếp (`receive`) bị revert; (3) student bị gỡ khỏi danh sách vẫn xin hoàn tiền được; (4) **gian lận:** người không phải Cố vấn gọi `setStudents`, và batch vượt 100 địa chỉ bị revert.

---

## E. Đợt thu nộp quỹ trên chuỗi (Phase 4)

**Vấn đề:** thông báo đang nằm trong `backend/announcements.json` (sửa/xóa được không dấu vết); "đã nộp" hiện là `contribution > 0` tích lũy; giao dịch nạp không gắn với đợt thu nào.

**Quy tắc:**
```
struct Collection {
    uint256 id; uint256 targetWei; uint64 deadline; string purpose;
    address creator; uint64 createdAt; bool closed; uint64 closedAt;
    uint256 expectedPayers;   // = enrolledCount tại thời điểm tạo
    uint256 paidCount;        // số sinh viên đã đạt targetWei
}
```
- `createCollection(uint256 targetWei, uint64 deadline, string purpose)` — `onlyActiveBCS`; `targetWei > 0`, `deadline > block.timestamp`, `purpose` không rỗng (giới hạn độ dài hợp lý); chỉ cho phép **một đợt thu đang mở** tại một thời điểm (revert `CollectionStillOpen`). Phát `CollectionCreated`.
- `closeCollection(uint256 id, string reason)` — `onlyActiveBCS`; phát `CollectionClosed`. **Không có hàm sửa** mức đóng/hạn nộp sau khi tạo.
- `depositToCollection(uint256 id) payable`: chỉ khi đợt chưa đóng và `block.timestamp <= deadline` (nếu không: revert `CollectionClosed`/`CollectionExpired`); vẫn áp dụng toàn bộ logic nạp (phí 1%, net, whitelist); ghi `paidInCollection[id][student] += msg.value` (số gốc); khi lần đầu đạt `>= targetWei` thì `paidCount++`. `deposit()`/`receive()` giữ nguyên là nạp vào quỹ chung (không thuộc đợt nào). **Không** đổi `deposit()` thành có tham số (tránh ABI overload gây lỗi ethers).
- View: `collectionCount`, `getCollection(id)`, `hasPaidInCollection(id, student)`, `paidInCollection(id, student)`.
- "Đã nộp" = `paidInCollection >= targetWei` của đúng đợt đó.

**Test tối thiểu:** (1) nạp đủ mức vào đúng đợt → đã nộp, `paidCount` tăng 1 lần duy nhất; (2) nạp thiếu mức → chưa đã nộp; (3) nạp vào đợt quá hạn/đã đóng bị revert; (4) **gian lận:** sinh viên đã nộp đợt cũ không được tính là đã nộp đợt mới; người không phải BCS gọi `createCollection` bị chặn.

---

## F. Phí vận hành: hoàn gas tự động (Phase 5)

**Bỏ** `withdrawAdminFee`, sự kiện `AdminFeeWithdrawn` và mọi tham chiếu (test, UI, tài liệu R11) — thay bằng cơ chế dưới đây.

**Hằng số đề xuất:** `GAS_REFUND_OVERHEAD = 30000` (xấp xỉ 21.000 gas giao dịch cơ bản + calldata), `MAX_REFUND_GAS_UNITS = 500000`, `MAX_GAS_PRICE_PREMIUM = 2 gwei`.

**Công thức (trong modifier `governanceAction`, đo `gasStart = gasleft()` ở đầu và hoàn ở cuối):**
```
gasUsed = (gasStart − gasleft()) + GAS_REFUND_OVERHEAD
units   = min(gasUsed, MAX_REFUND_GAS_UNITS)
price   = min(tx.gasprice, block.basefee + MAX_GAS_PRICE_PREMIUM)
owed    = units × price
paid    = min(owed, adminFeePool)            // hết quỹ thì hoàn phần còn lại
shortfall = owed − paid                       // người thực thi tự chịu
```
- **Effects trước:** `adminFeePool -= paid`, sau đó gửi ETH bằng `call` tới `msg.sender`. Nếu gửi thất bại thì **hoàn lại** `adminFeePool += paid`, phát `GasRefundFailed`, **không revert** giao dịch chính.
- Quỹ phí cạn **không bao giờ** chặn hành động quản trị.
- Phát `GasRefunded(to, gasUnits, gasPrice, paid, shortfall)`.
- Người nhận hoàn gas là `msg.sender` (không dùng `tx.origin`), và chỉ khi `msg.sender` là Cố vấn hoặc BCS đã kích hoạt.
- Khóa chống reentrancy (tự viết) bao trùm cả hàm lẫn bước hoàn gas.
- **Áp dụng hoàn gas cho:** `setBCSMember`, `setStudents`, `commitRoster`, `createCollection`, `closeCollection`, `createSpendRequest`, `voteSpendRequest`, `voteRefundRequest`, `executeSpendRequest`, và `executeRefundRequest` (chỉ khi người gọi là BCS/Cố vấn).
- **Không hoàn gas cho:** `deposit`, `receive`, `depositToCollection`, `createRefundRequest`, các hàm `expire*`, `moveFeeToClassFund`.
- Giao dịch bị revert thì không được hoàn gas (đặc tính của EVM).
- Thêm `moveFeeToClassFund(uint256 amount)` — `onlyAdvisor`; `amount > 0` và `<= adminFeePool`; `adminFeePool -= amount; classFundBalance += amount;` chỉ đổi sổ, **không có ETH ra khỏi hợp đồng**; phát `FeeMovedToClassFund`.
- Cập nhật bản mô phỏng Python: viết hàm thuần `compute_gas_refund(gas_used, gas_price, basefee, pool)` dùng cùng công thức.

**Test tối thiểu:** (1) hoàn đúng công thức khi quỹ đủ; (2) quỹ phí không đủ → hoàn phần còn lại, `shortfall > 0`, hành động chính vẫn thành công; (3) quỹ phí = 0 → hành động chính vẫn chạy; (4) **gian lận:** `tx.gasprice` rất cao chỉ được hoàn tới trần `basefee + 2 gwei`; người nhận hoàn gas là hợp đồng độc hại cố reentrancy bị chặn; (5) `moveFeeToClassFund` bởi người không phải Cố vấn bị chặn, và bất biến `balance == classFundBalance + adminFeePool` giữ nguyên.

---

## G. Đồng bộ giao diện, backend, tài liệu (Phase 6)

- Cập nhật `CONTRACT_ABI` trong `web/index.html` (dòng ~6091) cho khớp hợp đồng mới.
- Giao diện: bỏ nút/panel "rút phí vận hành", thêm "chuyển phí dư sang quỹ lớp" (Cố vấn), hiển thị hoàn gas, quản lý danh sách sinh viên (Cố vấn dán danh sách ví từ roster), tạo/đóng đợt thu (BCS), trạng thái "đã nộp" theo từng đợt, hiển thị "hoàn tối đa X ETH (đã trừ 1% phí)", so khớp hash roster với hash trên chuỗi.
- Đợt thu lấy từ sự kiện/hàm trên chuỗi. `backend/announcements.json` không còn là nguồn sự thật; xử lý tương thích ngược sao cho `test_announcement_lifecycle.py` và các test backend khác vẫn chạy (cập nhật test có giải thích nếu hành vi thay đổi). Đợt thu quá `deadline` phải hiển thị là "đã hết hạn" chứ không phải "đang diễn ra".
- Tài liệu: cập nhật `README.md`, `SPEC.md` (gốc) và `docs/SPEC.md`, `docs/ECONOMIC_RULES.md`, thêm phần bổ sung vào `docs/AUDIT_REPORT.md`, ghi `AI_JOURNAL.md`. Bảng "Expected vs Observed" chỉ ghi kết quả đã chạy thật.

---

## H. Điểm cần nhóm xác nhận (giá trị mặc định đề xuất — hỏi lại nếu không chắc)

| # | Điểm | Mặc định |
|---|---|---|
| 1 | `MAX_BCS` | 15 (để chặn vòng lặp vô hạn) |
| 2 | `GAS_REFUND_OVERHEAD` / `MAX_REFUND_GAS_UNITS` / premium | 30.000 / 500.000 / 2 gwei |
| 3 | Số đợt thu mở cùng lúc | Chỉ 1 |
| 4 | Nạp vào đợt đã đóng/quá hạn | Bị revert; người nạp muộn dùng `deposit()` quỹ chung |
| 5 | Cố vấn có thể là student | Không |
| 6 | Gỡ student đang là BCS | Bị chặn (phải gỡ BCS trước) |
| 7 | Ai tạo/đóng đợt thu | BCS (Cố vấn không) |
| 8 | ETH bị ép gửi (selfdestruct) | Chỉ có view, chưa có hàm xử lý |

---

## I. Tiêu chí hoàn thành mỗi phase

1. `python test/test_economic_rules.py` chạy xong, báo kết quả thật.
2. `npx solc --bin contracts/project/ProjectCore.sol test/ProjectCore_test.sol test/ProjectCore_integration_test.sol` biên dịch không lỗi.
3. Test cũ bị ảnh hưởng đã được cập nhật kèm giải thích; không xóa test để "cho qua".
4. Có bản tóm tắt thay đổi: file nào, hàm nào, lý do, và các điểm còn mơ hồ.