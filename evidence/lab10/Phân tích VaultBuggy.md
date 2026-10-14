# BÁO CÁO PHÂN TÍCH LỖ HỔNG HỢP ĐỒNG VAULTBUGGY (LAB 10)

- **Hợp đồng kiểm toán:** `VaultBuggy.sol` (thuộc thư mục `contracts/training/VaultBuggy.sol`)
- **Vai trò:** Kiểm toán viên bảo mật hợp đồng thông minh (Smart Contract Auditor)
- **Chuẩn quy ước:** Tuân thủ hướng dẫn và nguyên tắc dự án tại `AGENTS.md`

---

## 1. TỔNG QUAN HỢP ĐỒNG

Hợp đồng `VaultBuggy` được thiết kế với mục đích làm một két sắt cá nhân có khóa thời gian (Time-locked Vault), cho phép người dùng nạp ETH và chỉ cho phép chủ sở hữu (`owner`) rút tiền ra khi đã hết hạn khóa (`unlockTime`).

Tuy nhiên, qua rà soát mã nguồn, hợp đồng chứa nhiều lỗi nghiêm trọng về kiểm soát quyền truy cập, logic điều kiện thời gian, quản lý dữ liệu nhạy cảm trên blockchain và kỹ thuật chuyển tiền ETH.

---

## 2. BẢNG TỔNG HỢP LỖ HỔNG THEO MỨC ĐỘ NGHIÊM TRỌNG

| STT | Tên lỗ hổng | Mức độ nghiêm trọng | Vị trí (Dòng) | Tác động chính |
| :---: | :--- | :---: | :---: | :--- |
| **1** | **Thiếu kiểm soát quyền truy cập (Missing Access Control)** | **Nghiêm trọng (Critical)** | Dòng 18 – 21 | Bất kỳ ai cũng có thể rút cạn tiền trong két. |
| **2** | **Đảo ngược logic khóa thời gian (Inverted Time Lock Logic)** | **Nghiêm trọng (Critical)** | Dòng 19 | Rút được tiền khi đang khóa; tiền bị kẹt vĩnh viễn sau khi hết hạn. |
| **3** | **Lộ mã PIN trên On-chain & Biến rác (Broken Privacy & Dead Code)** | **Trung bình (Medium)** | Dòng 8, 10, 13 | Mã PIN `private` vẫn đọc được công khai; tốn gas vô ích. |
| **4** | **Lỗi từ chối dịch vụ do giới hạn 2300 gas của `.transfer()`** | **Trung bình (Medium)** | Dòng 20 | Kẹt tiền nếu chủ sở hữu là ví hợp đồng (Smart Contract Wallet / Multi-sig). |
| **5** | **Thiếu phát sự kiện (`event`) lưu vết giao dịch** | **Thấp (Low)** | Dòng 16, 18 – 21 | Không thể theo dõi lịch sử nạp/rút tiền trên DApp hay Block Explorer. |
| **6** | **Thiếu kiểm tra giá trị bằng 0 (`Zero Check`)** | **Thấp (Low)** | Dòng 16, 20 | Cho phép nạp 0 wei (spam giao dịch) và rút tiền khi số dư bằng 0. |
| **7** | **Lãng phí gas (Không dùng `immutable` và dùng `string` thay cho `custom error`)** | **Thông tin (Info)** | Dòng 6, 7, 19 | Tốn chi phí deploy và chi phí thực thi giao dịch. |

---

## 3. PHÂN TÍCH CHI TIẾT TỪNG LỖ HỔNG

### 3.1. Lỗ hổng 1: Thiếu kiểm soát quyền truy cập (Missing Access Control)
- **Mức độ:** **Nghiêm trọng (Critical)**
- **Vị trí:** Dòng 18 – 21 trong hàm `withdraw()`:
  ```solidity
  function withdraw() external {
      require(block.timestamp <= unlockTime, "Chua den han rut tien");
      payable(msg.sender).transfer(address(this).balance);
  }
  ```
- **Khai thác thế nào:**
  - Hàm `withdraw()` có phạm vi hiển thị `external` nhưng hoàn toàn không có bất kỳ điều kiện nào để kiểm tra danh tính người gọi (thiếu `require(msg.sender == owner)`).
  - Lệnh chuyển tiền lại dùng `payable(msg.sender)` thay vì `payable(owner)`.
  - **Kịch bản tấn công:** Bất kỳ kẻ tấn công hoặc ví lạ nào chỉ cần gửi giao dịch gọi hàm `withdraw()` thì toàn bộ số dư ETH trong hợp đồng sẽ được chuyển thẳng về ví của kẻ tấn công đó.
- **Cách sửa:**
  - Bổ sung kiểm tra quyền sở hữu ngay dòng đầu tiên của hàm `withdraw()` bằng custom error theo quy chuẩn `AGENTS.md`:
  ```solidity
  if (msg.sender != owner) revert NotOwner();
  ```

---

### 3.2. Lỗ hổng 2: Đảo ngược logic khóa thời gian (Inverted Time Lock Logic)
- **Mức độ:** **Nghiêm trọng (Critical)**
- **Vị trí:** Dòng 19:
  ```solidity
  require(block.timestamp <= unlockTime, "Chua den han rut tien");
  ```
- **Khai thác thế nào:**
  - Biểu thức điều kiện sử dụng toán tử nhỏ hơn hoặc bằng (`<= unlockTime`), ngược hoàn toàn so với bản chất của két khóa thời gian (phải là `>= unlockTime`).
  - **Hệ quả kép:**
    1. **Rút non trước hạn:** Người dùng có thể rút tiền ngay trong khoảng thời gian két đang bị khóa (`block.timestamp <= unlockTime`), phá vỡ hoàn toàn cam kết tiết kiệm.
    2. **Đóng băng tài sản vĩnh viễn (Permanent Fund Lock / Deadlock):** Ngay khi thời gian thực tế vượt qua mốc mở khóa (`block.timestamp > unlockTime`), điều kiện `require` sẽ luôn trả về `false`. Tiền sẽ bị giam vĩnh viễn trong hợp đồng và không một ai có thể lấy lại.
- **Cách sửa:**
  - Đổi dấu so sánh thành `>=` (hoặc chặn revert nếu `block.timestamp < unlockTime`):
  ```solidity
  if (block.timestamp < unlockTime) revert StillLocked(unlockTime, block.timestamp);
  ```

---

### 3.3. Lỗ hổng 3: Ảo tưởng về tính riêng tư của biến `private` & Biến rác không dùng
- **Mức độ:** **Trung bình (Medium)**
- **Vị trí:** Dòng 8, 10, 13:
  ```solidity
  uint256 private emergencyPin;
  // ...
  emergencyPin = pin;
  ```
- **Khai thác thế nào:**
  - Từ khóa `private` trong Solidity chỉ có tác dụng ở tầng biên dịch (ngăn các hợp đồng khác gọi hoặc kế thừa trực tiếp), **hoàn toàn không có tính bảo mật trên blockchain**.
  - Kẻ tấn công có thể đọc trực tiếp giá trị của `emergencyPin` bằng lệnh RPC `web3.eth.getStorageAt(vaultAddress, 2)` (đọc slot lưu trữ số 2) hoặc tra cứu trực tiếp dữ liệu input trong giao dịch deploy trên Etherscan.
  - Ngoài ra, biến `emergencyPin` này không bao giờ được đọc hay sử dụng trong bất kỳ hàm nào của hợp đồng (Dead Code), gây lãng phí phí gas lưu trữ on-chain.
- **Cách sửa:**
  - Không bao giờ lưu trữ mật khẩu, mã PIN hoặc dữ liệu nhạy cảm dạng văn bản rõ (plaintext) trên blockchain.
  - Nếu không có chức năng cứu hộ khẩn cấp cần mã PIN, hãy xóa bỏ hoàn toàn biến `emergencyPin` và tham số `pin` trong hàm khởi tạo `constructor`.

---

### 3.4. Lỗ hổng 4: Rủi ro Từ chối dịch vụ (DoS) do giới hạn 2300 gas của `.transfer()`
- **Mức độ:** **Trung bình (Medium)**
- **Vị trí:** Dòng 20:
  ```solidity
  payable(msg.sender).transfer(address(this).balance);
  ```
- **Khai thác thế nào:**
  - Phương thức `.transfer()` bị giới hạn cứng ở mức 2300 đơn vị gas.
  - Nếu `owner` là một ví hợp đồng thông minh (như Gnosis Safe, ví đa chữ ký, ví Account Abstraction) mà hàm `receive()` hoặc `fallback()` tiêu tốn nhiều hơn 2300 gas, giao dịch rút tiền sẽ luôn bị hoàn tác (Out of Gas), dẫn đến việc tiền bị kẹt vĩnh viễn.
- **Cách sửa:**
  - Tuân thủ quy tắc số 4 của `AGENTS.md` (chuyển ETH bằng `call` và kiểm tra kết quả; không dùng `transfer`):
  ```solidity
  (bool ok, ) = payable(owner).call{value: amount}("");
  if (!ok) revert TransferFailed();
  ```

---

### 3.5. Lỗ hổng 5: Thiếu phát sự kiện (`event`) khi thay đổi trạng thái
- **Mức độ:** **Thấp (Low)**
- **Vị trí:** Dòng 16 (`deposit`) và Dòng 18 – 21 (`withdraw`)
- **Tác động:**
  - Cả hai hàm đều làm biến động số dư ETH của hợp đồng nhưng không phát ra bất kỳ sự kiện nào.
  - Vi phạm quy tắc số 1 trong `AGENTS.md` (*"Mọi hàm làm thay đổi trạng thái phải phát event"*). Giao diện người dùng (DApp) và các dịch vụ truy vấn (Indexer) không thể bắt sự kiện để hiển thị lịch sử nạp/rút tiền theo thời gian thực.
- **Cách sửa:**
  - Khai báo và phát hai sự kiện:
  ```solidity
  event Deposited(address indexed from, uint256 amount);
  event Withdrawn(address indexed to, uint256 amount);
  ```

---

### 3.6. Lỗ hổng 6: Thiếu kiểm tra giá trị bằng 0 (`Zero Check`)
- **Mức độ:** **Thấp (Low)**
- **Vị trí:** Dòng 16 và Dòng 20
- **Tác động:**
  - Hàm `deposit()` rỗng cho phép người dùng nạp giao dịch `msg.value == 0`, gây lãng phí gas và spam dữ liệu rác.
  - Hàm `withdraw()` không kiểm tra số dư hiện tại trong két. Nếu két có số dư bằng 0 mà vẫn gọi rút thì lệnh `.transfer(0)` vẫn chạy, gây tốn gas vô ích.
- **Cách sửa:**
  - Trong `deposit()`: Kiểm tra `if (msg.value == 0) revert ZeroAmount();`
  - Trong `withdraw()`: Kiểm tra `if (amount == 0) revert NothingToWithdraw();`

---

### 3.7. Lỗ hổng 7: Lãng phí gas (Thiếu `immutable` và dùng chuỗi lỗi dài)
- **Mức độ:** **Thông tin (Info)**
- **Vị trí:** Dòng 6, 7 và Dòng 19
- **Tác động:**
  - `owner` và `unlockTime` chỉ được gán giá trị 1 lần trong `constructor` nhưng không được đánh dấu `immutable`, khiến mỗi lần đọc biến phải đọc từ Storage thay vì Bytecode (tốn thêm gas).
  - Chuỗi thông báo lỗi `require(..., "Chua den han rut tien")` tốn nhiều bytecode deploy và gas thực thi hơn so với Custom Errors.
- **Cách sửa:**
  - Thêm từ khóa `immutable`: `address public immutable owner;` và `uint256 public immutable unlockTime;`.
  - Dùng Custom Error thay cho chuỗi `require`.

---

## 4. HỢP ĐỒNG ĐÃ ĐƯỢC CHUẨN HÓA VÀ KHẮC PHỤC HOÀN TOÀN

Mã nguồn chuẩn hóa đã khắc phục toàn bộ 7 lỗ hổng trên, tuân thủ 100% quy ước `AGENTS.md` (được lưu tại `contracts/training/TimeLockVault.sol`):

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title TimeLockVault - Két tiết kiệm có khóa thời gian (Bản chuẩn bảo mật)
contract TimeLockVault {
    address public immutable owner;
    uint256 public immutable unlockTime;

    event Deposited(address indexed from, uint256 amount);
    event Withdrawn(address indexed to, uint256 amount);

    error NotOwner();
    error StillLocked(uint256 unlockAt, uint256 currentTime);
    error NothingToWithdraw();
    error ZeroAmount();
    error TransferFailed();

    constructor(uint256 lockDurationSeconds) {
        owner = msg.sender;
        unlockTime = block.timestamp + lockDurationSeconds;
    }

    function deposit() external payable {
        if (msg.value == 0) revert ZeroAmount();
        emit Deposited(msg.sender, msg.value);
    }

    function withdraw() external {
        // 1. Checks
        if (msg.sender != owner) revert NotOwner();
        if (block.timestamp < unlockTime) revert StillLocked(unlockTime, block.timestamp);

        uint256 amount = address(this).balance;
        if (amount == 0) revert NothingToWithdraw();

        // 2. Effects
        emit Withdrawn(owner, amount);

        // 3. Interactions
        (bool ok, ) = payable(owner).call{value: amount}("");
        if (!ok) revert TransferFailed();
    }
}
```

---

## 5. BẢNG SO SÁNH TRƯỚC VÀ SAU KHI SỬA LỖI

| Tiêu chí | Hợp đồng gốc (`VaultBuggy.sol`) | Hợp đồng chuẩn (`TimeLockVault.sol`) |
| :--- | :--- | :--- |
| **Kiểm soát quyền** | Không kiểm tra (Bất kỳ ai cũng rút được) | Chặn bằng `if (msg.sender != owner) revert NotOwner();` |
| **Logic thời gian** | `block.timestamp <= unlockTime` (Sai ngược) | `block.timestamp < unlockTime` (Đúng chuẩn mở khóa) |
| **Dữ liệu nhạy cảm** | Chứa `emergencyPin` lộ công khai trên on-chain | Loại bỏ hoàn toàn biến thừa và không an toàn |
| **Phương thức chuyển ETH** | Dùng `.transfer()` (Nguy cơ kẹt do hạn mức 2300 gas) | Dùng `.call{value: amount}("")` và kiểm tra kết quả `ok` |
| **Sự kiện (Event)** | Không phát sự kiện nào | Phát đầy đủ `Deposited` và `Withdrawn` |
| **Kiểm tra biên (Zero)** | Bỏ qua kiểm tra `msg.value` và `balance` | Chặn `ZeroAmount()` và `NothingToWithdraw()` |
| **Xử lý lỗi & Tối ưu Gas** | Dùng `require` với chuỗi dài | Dùng `Custom Error` và biến `immutable` |
