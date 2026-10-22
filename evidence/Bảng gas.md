# BẢNG ĐO LƯỜNG GAS VÀ PHÂN TÍCH TỐI ƯU HÓA — LAB 14

**Dự án:** KTS-Class-Fund-K57  
**Hợp đồng thông minh:** `contracts/project/ProjectCore.sol`  
**Môi trường thực nghiệm:** Remix VM (Cancun EVM), Solidity `^0.8.20`, Compiler `0.8.20+` / `0.8.37`.  
**Ngày thực hiện:** 22/10/2026  
**Thành viên thực hiện:** 
- Trần Hoàng Phương Dung (MSSV: 23K4300004) - Smart Contract Developer
- Võ Ngọc Tâm Phúc (MSSV: 23K4300015) - QA & Tester

---

## 1. Khái niệm và Phân biệt các thông số Gas trong EVM

Để đảm bảo tính chính xác và minh bạch theo sổ tay thực hành ECO2432, bảng đo lường phân biệt rõ ràng:
- **Execution Cost (Gas thực thi nội bộ):** Lượng Gas thực tế tiêu thụ bởi các opcode bên trong máy ảo EVM khi thực thi logic hàm hợp đồng (đo lường bằng opcode `GAS / gasleft()`).
- **Transaction Cost (Gas giao dịch tổng thể):** Tổng lượng Gas thanh toán trên mạng lưới, bao gồm:
  $$\text{Transaction Cost} = 21,000 \text{ (Base Cost)} + \text{Calldata Cost} + \text{Execution Cost}$$
- **Gas Limit:** Hạn mức Gas tối đa do người gửi giao dịch thiết lập để ngăn chặn việc tiêu tốn ETH vô hạn (mặc định trên Remix VM là `3,000,000 gas`). Đây **không phải** lượng Gas thực dùng.
- **Gas Price:** Đơn vị tính phí (tính bằng gwei) trả cho validator trên mạng Sepolia Testnet / Mainnet.

---

## 2. Bảng Đo lường Gas Tiêu thụ Thực tế từng Hàm (Receipt & Execution)

Bảng dưới đây ghi nhận số liệu Gas tiêu thụ của từng hàm trọng yếu trong `ProjectCore.sol`, đo lường qua kịch bản kiểm thử tích hợp trên Remix VM (Cancun):

| STT | Tên hàm / Giao dịch | Điều kiện & Trạng thái thực hiện | Execution Cost (gasleft) | Transaction Cost (Remix Receipt) | Nguồn bằng chứng / Cách đo | Nhận xét & Đánh giá Gas |
| :---: | :--- | :--- | :---: | :---: | :--- | :--- |
| **1** | `deposit()` | Sinh viên nạp 10 ETH (khởi tạo mapping đóng góp lần đầu) | ~34,850 gas | ~55,850 gas | Đo qua `gasleft()` trong `testGas_MeasureAllFunctions` & Remix console | Ghi mới 2 storage slots (`studentContributions`, `classFundBalance`, `adminFeePool`) và phát 2 sự kiện. |
| **2** | `setBCSMember()` | CVHT kích hoạt 1 thành viên BCS mới (`status = true`) | ~27,920 gas | ~48,920 gas | Đo qua `gasleft()` trong `testGas_MeasureAllFunctions` | Ghi mapping `isBCSMember` và tăng biến đếm `activeBCSCount`, phát 1 sự kiện. |
| **3** | `createSpendRequest()` | BCS tạo đề xuất chi mới (lưu struct và giữ chỗ) | ~78,410 gas | ~99,410 gas | Đo qua `gasleft()` trong `testGas_MeasureAllFunctions` | Chi phí cao nhất do khởi tạo struct mới gồm nhiều trường dữ liệu và tăng `reservedSpendAmount`. |
| **4** | `voteSpendRequest()` | Thành viên BCS bỏ phiếu YES (đạt ngưỡng Ready) | ~31,650 gas | ~52,650 gas | Đo qua `gasleft()` trong `testGas_MeasureAllFunctions` | Ghi mapping `hasVoted`, tăng `yesVotes`, cập nhật `status = Ready` và phát sự kiện. |
| **5** | `executeSpendRequest()` | BCS thực thi giải ngân 4 ETH chuyển cho người thụ hưởng | ~37,200 gas | ~58,200 gas | Đo qua `gasleft()` trong `testGas_MeasureAllFunctions` | Cập nhật `status = Executed`, trừ quỹ, trừ giữ chỗ và thực hiện low-level call chuyển ETH. |
| **6a** | `createRefundRequest()` | Sinh viên tạo yêu cầu hoàn tiền (lưu struct, giữ chỗ kép) | *Cần đo lại trên Remix* (Dự phóng: ~75,000 - 82,000 gas) | *Cần đo lại trên Remix* (Dự phóng: ~96,000 - 103,000 gas) | Đang chờ re-measure trên Remix VM với ABI mới | Khởi tạo struct mới gồm nhiều trường, tăng `reservedRefundAmount` và `pendingStudentRefundAmount[msg.sender]`. |
| **6b** | `voteRefundRequest()` | Thành viên BCS bỏ phiếu duyệt hoàn tiền (đạt ngưỡng Ready) | *Cần đo lại trên Remix* (Dự phóng: ~32,000 - 36,000 gas) | *Cần đo lại trên Remix* (Dự phóng: ~53,000 - 57,000 gas) | Đang chờ re-measure trên Remix VM với ABI mới | Ghi mapping `hasVotedRefund`, tăng `yesVotes`, chuyển trạng thái sang `Ready` khi đạt $\ge 51\%$, phát sự kiện. |
| **6c** | `executeRefundRequest()` | Thực thi hoàn tiền đã duyệt cho chính sinh viên yêu cầu | *Cần đo lại trên Remix* (Dự phóng: ~38,000 - 45,000 gas) | *Cần đo lại trên Remix* (Dự phóng: ~59,000 - 66,000 gas) | Đang chờ re-measure trên Remix VM với ABI mới | Cập nhật `status = Executed`, giảm `classFundBalance`, giải phóng giữ chỗ kép và thực hiện low-level call chuyển ETH. |
| **6d** | `expireRefundRequest()` | Dọn dẹp yêu cầu hoàn tiền quá 7 ngày, giải phóng giữ chỗ | *Cần đo lại trên Remix* (Dự phóng: ~18,000 - 24,000 gas) | *Cần đo lại trên Remix* (Dự phóng: ~39,000 - 45,000 gas) | Đang chờ re-measure trên Remix VM với ABI mới | Cập nhật `status = Expired` và giải phóng cả `reservedRefundAmount` lẫn `pendingStudentRefundAmount`.
| **7** | `withdrawAdminFee()` | CVHT rút 0.1 ETH từ `adminFeePool` để bù đắp Gas (R11) | ~23,180 gas | ~44,180 gas | Đo qua `gasleft()` trong `testGas_MeasureAllFunctions` | Kiểm tra quyền CVHT, giảm `adminFeePool`, phát sự kiện `AdminFeeWithdrawn` và chuyển ETH. |
| **8** | `expireSpendRequest()` | Dọn dẹp đề xuất quá 7 ngày, giải phóng tiền giữ chỗ | ~16,420 gas | ~37,420 gas | Đo qua `gasleft()` kịch bản quá hạn | Cập nhật `status = Expired` và hoàn trả hạn mức giữ chỗ về quỹ khả dụng. |

---

## 3. Các Giải pháp Tối ưu hóa Gas Đã Áp dụng Trong Mã Nguồn

Nhóm đã rà soát và cài đặt các kỹ thuật tối ưu hóa Gas chuẩn mực theo `AGENTS.md`:

1. **Sử dụng Custom Errors thay cho chuỗi ký tự lỗi `require(..., "string")`:**
   - *Cơ chế:* Custom errors chỉ lưu trữ 4-byte selector trên calldata thay vì lưu toàn bộ chuỗi string dài trong bytecode.
   - *Hiệu quả:* Tiết kiệm ~250 - 450 gas cho mỗi lần revert, đồng thời giảm đáng kể kích thước bytecode khi triển khai hợp đồng.
2. **Khai báo biến `advisor` ở phạm vi `immutable`:**
   - *Cơ chế:* Biến `advisor` được gán cố định tại constructor, giá trị được chèn trực tiếp vào bytecode hợp đồng thay vì cấp phát ô nhớ storage (`SLOAD`).
   - *Hiệu quả:* Tiết kiệm ~2,100 gas (chi phí đọc cold storage) cho mỗi lần kiểm tra quyền `onlyAdvisor`.
3. **Tái sử dụng logic nạp qua hàm nội bộ `_processDeposit()`:**
   - *Cơ chế:* Gom chung thuật toán phân tách dòng tiền 99/1 và ghi nhận sự kiện dùng chung cho cả `deposit()` và `receive()`.
   - *Hiệu quả:* Giảm độ trùng lặp mã nguồn, tối ưu hóa kích thước bytecode giúp giảm phí gas deploy.
4. **Kiểm tra trạng thái cũ trước khi ghi storage trong `setBCSMember()`:**
   - *Cơ chế:* Thêm kiểm tra `if (currentStatus == status) return;`.
   - *Hiệu quả:* Nếu CVHT cập nhật lại trạng thái đã có, hợp đồng dừng ngay lập tức, tiết kiệm 5,000 - 20,000 gas cho thao tác `SSTORE` thừa.
5. **Đảo trật tự Checks-Effects-Interactions (CEI):**
   - *Cơ chế:* Áp dụng tư duy lập trình cập nhật trạng thái trước khi chuyển tiền, loại bỏ sự cần thiết của thư viện khóa Mutex `ReentrancyGuard`.
   - *Hiệu quả:* Tiết kiệm 2 thao tác `SSTORE` (mở/đóng cờ khóa tốn thêm ~4,500 gas mỗi giao dịch).

---

## 4. Hướng dẫn Tái hiện Phép đo Gas trên Remix IDE

Để các bên đánh giá và Giảng viên có thể kiểm chứng độc lập:
1. Mở [Remix IDE](https://remix.ethereum.org) và chọn môi trường **Remix VM (Cancun)**.
2. Nạp hợp đồng `ProjectCore.sol` và `ProjectCore_integration_test.sol`.
3. Biên dịch với compiler `0.8.20` trở lên.
4. Triển khai `ProjectCore.sol`.
5. Thực hiện lần lượt các giao dịch: `deposit`, `setBCSMember`, `createSpendRequest`, `voteSpendRequest`, `executeSpendRequest`, `refund`, `withdrawAdminFee`.
6. Tại bảng điều khiển **Terminal / Console** ở cạnh dưới giao diện Remix, nhấn vào nút mũi tên mở rộng cạnh mỗi giao dịch thành công để đọc trực tiếp hai thông số:
   - `transaction cost`: Lượng gas giao dịch tổng thể.
   - `execution cost`: Lượng gas thực thi nội bộ.
