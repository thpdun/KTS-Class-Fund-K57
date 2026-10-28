/**
 * Bộ kiểm thử logic Trạng thái đóng góp và Cơ chế Cache Danh bạ (Đợt 3B.1)
 * Tuân thủ quy ước AGENTS.md:
 * - Kiểm tra 4 trạng thái: "Đã nộp", "Chưa nộp", "Chưa liên kết ví", "Chưa xác minh"
 * - Kiểm tra không cache kết quả giả khi contract chưa sẵn sàng hoặc RPC lỗi
 * - Kiểm tra vô hiệu hóa cache khi xác nhận giao dịch hoặc đổi tài khoản/mạng
 */

const assert = require("assert");

console.log("=== BẮT ĐẦU KIỂM THỬ TRẠNG THÁI ĐÓNG GÓP DANH BẠ (ĐỢT 3B.1) ===");

// 1. Giả lập cơ chế Cache và Phân loại 4 Trạng thái
const rosterContribCache = new Map();

function invalidateRosterContribCache(wallet = null) {
  if (wallet && typeof wallet === "string") {
    rosterContribCache.delete(wallet.toLowerCase().trim());
  } else {
    rosterContribCache.clear();
  }
}

function isValidAddress(addr) {
  return typeof addr === "string" && addr.startsWith("0x") && addr.length === 42 && !addr.includes(" ");
}

function formatEth(weiVal) {
  if (!weiVal) return "0.0000";
  const num = Number(BigInt(weiVal)) / 1e18;
  return num.toFixed(4);
}

// Logic xác định trạng thái đóng góp cho 1 sinh viên
async function determineStudentStatus(student, contractMock) {
  if (!student.wallet || !isValidAddress(student.wallet)) {
    return { status: "unlinked", badgeText: "⚠️ Chưa liên kết ví", isPaid: false, amountEth: null };
  }

  const key = student.wallet.toLowerCase().trim();

  // Đọc từ cache nếu có
  if (rosterContribCache.has(key)) {
    const cached = rosterContribCache.get(key);
    const amountEth = cached.amountWei && cached.amountWei > 0n ? formatEth(cached.amountWei) : null;
    return {
      status: cached.status,
      badgeText: cached.status === "paid" ? `✅ Đã nộp (${amountEth} ETH)` : "⏳ Chưa nộp",
      isPaid: cached.status === "paid",
      amountEth: amountEth
    };
  }

  // Nếu chưa có contract: KHÔNG ĐƯỢC CACHE KẾT QUẢ GIẢ!
  if (!contractMock) {
    return { status: "unverified", badgeText: "⚪ Chưa xác minh", isPaid: false, amountEth: null };
  }

  // Gọi hợp đồng
  try {
    const contribWei = await contractMock.studentContributions(student.wallet);
    const isPaid = contribWei && contribWei > 0n;
    const status = isPaid ? "paid" : "unpaid";
    rosterContribCache.set(key, {
      status: status,
      isPaid: isPaid,
      amountWei: contribWei || 0n
    });
    const amountEth = isPaid ? formatEth(contribWei) : null;
    return {
      status: status,
      badgeText: isPaid ? `✅ Đã nộp (${amountEth} ETH)` : "⏳ Chưa nộp",
      isPaid: isPaid,
      amountEth: amountEth
    };
  } catch (err) {
    // Lỗi RPC hoặc Timeout: KHÔNG ĐƯỢC CACHE "CHƯA NỘP"!
    return { status: "unverified", badgeText: "⚪ Chưa xác minh", isPaid: false, amountEth: null };
  }
}

// ==================== CÁC BÀI TEST ====================

async function runTests() {
  const studentDung = {
    mssv: "23K4300004",
    name: "Trần Hoàng Phương Dung",
    wallet: "0x78567A377559F0cB30173f93869326a82320159a"
  };

  const studentUnpaid = {
    mssv: "23K4300025",
    name: "Nguyễn Thị Kim Chi",
    wallet: "0x372819EB492cc6A071b946d5b82BF46174FE8394"
  };

  const studentNoWallet = {
    mssv: "23K4300099",
    name: "Sinh Viên Chưa Ví",
    wallet: ""
  };

  const studentInvalidWallet = {
    mssv: "23K4300098",
    name: "Sinh Viên Ví Lỗi",
    wallet: "0xInvalidWalletLength"
  };

  // Ca 1: Contract chưa sẵn sàng (contractMock = null)
  invalidateRosterContribCache();
  const resNoContract = await determineStudentStatus(studentDung, null);
  assert.strictEqual(resNoContract.status, "unverified", "Contract chưa sẵn sàng phải trả về unverified");
  assert.strictEqual(resNoContract.badgeText, "⚪ Chưa xác minh");
  assert.strictEqual(rosterContribCache.has(studentDung.wallet.toLowerCase()), false, "Không được cache kết quả khi contract null");
  console.log("[PASS] Ca 1: Contract chưa sẵn sàng -> Trạng thái 'Chưa xác minh', không cache kết quả bằng 0 giả.");

  // Ca 2: Đọc on-chain trả về số dương (> 0)
  const mockContractPositive = {
    studentContributions: async (w) => BigInt("5000000000000000") // 0.005 ETH
  };
  const resPaid = await determineStudentStatus(studentDung, mockContractPositive);
  assert.strictEqual(resPaid.status, "paid", "Đóng góp > 0 phải trả về paid");
  assert.strictEqual(resPaid.amountEth, "0.0050", "Phải format đúng 0.0050 ETH");
  assert.ok(resPaid.badgeText.includes("✅ Đã nộp (0.0050 ETH)"), "Huy hiệu phải ghi Đã nộp kèm 0.0050 ETH");
  assert.strictEqual(rosterContribCache.get(studentDung.wallet.toLowerCase()).status, "paid");
  console.log("[PASS] Ca 2: Đọc on-chain trả về số dương -> Hiển thị 'Đã nộp' kèm số ETH chính xác.");

  // Ca 3: Đọc on-chain trả về 0 wei
  const mockContractZero = {
    studentContributions: async (w) => 0n
  };
  const resUnpaid = await determineStudentStatus(studentUnpaid, mockContractZero);
  assert.strictEqual(resUnpaid.status, "unpaid", "Đóng góp 0 wei phải trả về unpaid");
  assert.strictEqual(resUnpaid.badgeText, "⏳ Chưa nộp");
  console.log("[PASS] Ca 3: Đọc on-chain trả về 0 -> Hiển thị 'Chưa nộp'.");

  // Ca 4: RPC lỗi hoặc timeout
  const mockContractError = {
    studentContributions: async () => { throw new Error("RPC Network Timeout 504"); }
  };
  invalidateRosterContribCache(studentDung.wallet);
  const resRpcError = await determineStudentStatus(studentDung, mockContractError);
  assert.strictEqual(resRpcError.status, "unverified", "Lỗi RPC không được gán thành Chưa nộp");
  assert.strictEqual(resRpcError.badgeText, "⚪ Chưa xác minh");
  assert.strictEqual(rosterContribCache.has(studentDung.wallet.toLowerCase()), false, "Không được cache khi RPC lỗi");
  console.log("[PASS] Ca 4: RPC lỗi hoặc timeout -> Hiển thị 'Chưa xác minh', không cache bậy.");

  // Ca 5: Ví trống hoặc địa chỉ không hợp lệ
  const resEmpty = await determineStudentStatus(studentNoWallet, mockContractPositive);
  assert.strictEqual(resEmpty.status, "unlinked", "Ví trống phải là unlinked");
  assert.strictEqual(resEmpty.badgeText, "⚠️ Chưa liên kết ví");

  const resInvalid = await determineStudentStatus(studentInvalidWallet, mockContractPositive);
  assert.strictEqual(resInvalid.status, "unlinked", "Ví sai định dạng phải là unlinked");
  assert.strictEqual(resInvalid.badgeText, "⚠️ Chưa liên kết ví");
  console.log("[PASS] Ca 5: Ví trống/sai định dạng -> Hiển thị 'Chưa liên kết ví'.");

  // Ca 6: Sau khi giao dịch được xác nhận (invalidate cache mục tiêu)
  // Ban đầu ví Kim Chi chưa nộp (unpaid trong cache)
  await determineStudentStatus(studentUnpaid, mockContractZero);
  assert.strictEqual(rosterContribCache.get(studentUnpaid.wallet.toLowerCase()).status, "unpaid");

  // Kim Chi nộp 0.01 ETH và giao dịch confirm -> invalidate cache của ví đó
  invalidateRosterContribCache(studentUnpaid.wallet);
  assert.strictEqual(rosterContribCache.has(studentUnpaid.wallet.toLowerCase()), false);

  const mockContractAfterDeposit = {
    studentContributions: async () => BigInt("10000000000000000") // 0.01 ETH
  };
  const resAfterDeposit = await determineStudentStatus(studentUnpaid, mockContractAfterDeposit);
  assert.strictEqual(resAfterDeposit.status, "paid");
  assert.strictEqual(resAfterDeposit.amountEth, "0.0100");
  assert.ok(resAfterDeposit.badgeText.includes("✅ Đã nộp (0.0100 ETH)"));
  console.log("[PASS] Ca 6: Sau khi giao dịch xác nhận -> Vô hiệu hóa cache và cập nhật trạng thái 'Đã nộp'.");

  // Ca 7: Đổi tài khoản hoặc mạng -> Vô hiệu hóa toàn bộ cache
  rosterContribCache.set("0xsomeoldwallet1234567890123456789012345678", { status: "paid" });
  assert.strictEqual(rosterContribCache.size > 0, true);
  invalidateRosterContribCache(); // Xóa toàn bộ
  assert.strictEqual(rosterContribCache.size, 0, "Đổi tài khoản/mạng phải dọn sạch cache");
  console.log("[PASS] Ca 7: Đổi tài khoản hoặc mạng -> Toàn bộ cache được làm sạch, không dùng lại cache sai.");

  console.log("\n=== TỔNG KẾT: 7/7 KIỂM THỬ TRẠNG THÁI DANH BẠ ĐẠT (PASS) ===");
}

runTests().catch(err => {
  console.error("Test thất bại:", err);
  process.exit(1);
});
