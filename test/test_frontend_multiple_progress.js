/**
 * KTS-Class-Fund-K57: Frontend DOM & Multiple Progress Bars Test Suite
 * Stage 4: Real DOM rendering & verification for Multiple Independent Progress Cards
 */

const fs = require('fs');
const assert = require('assert');

class FakeClassList {
  constructor() {
    this.classes = new Set();
  }
  add(cls) { this.classes.add(cls); }
  remove(cls) { this.classes.delete(cls); }
  contains(cls) { return this.classes.has(cls); }
}

class FakeElement {
  constructor(id) {
    this.id = id;
    this.style = { display: '', width: '' };
    this.classList = new FakeClassList();
    this.textContent = '';
    this.innerHTML = '';
    this.value = '';
    this.className = '';
  }
}

const elements = {};
function getElementById(id) {
  if (!elements[id]) {
    elements[id] = new FakeElement(id);
  }
  return elements[id];
}

global.document = {
  getElementById,
  querySelectorAll: () => []
};

global.window = {
  currentVerifiedRole: 'none',
  location: { reload: () => {} }
};

global.classRoster = [
  { studentId: "240001", fullName: "Nguyễn Văn A" },
  { studentId: "240002", fullName: "Trần Thị B" },
  { studentId: "240003", fullName: "Lê Văn C" },
  { studentId: "240004", fullName: "Phạm Minh D" },
  { studentId: "240005", fullName: "Hoàng Gia E" },
  { studentId: "240006", fullName: "Vũ Thị F" },
  { studentId: "240007", fullName: "Đặng Hoàng G" },
];
global.userAddress = "0x85ac8f0ca75f2e3fda073bc566659c011208da74";
global.isBcsMember = false;
global.isAdvisor = false;
global.getAnnouncementHistory = () => (global.classAnnouncementHistory || []);
global.updatePersonalStatusBox = () => {};

global.localStorage = {
  data: {},
  getItem: (k) => global.localStorage.data[k] || null,
  setItem: (k, v) => { global.localStorage.data[k] = v; },
  removeItem: (k) => { delete global.localStorage.data[k]; }
};

global.escapeHtml = (s) => (s ? String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;') : '');
global.logToTerminal = () => {};
global.AI_BACKEND_URL = "http://localhost:8000";

// Read web/index.html
const htmlContent = fs.readFileSync('web/index.html', 'utf8');

// Extract functions
function extractFunction(name) {
  const marker = `function ${name}`;
  const start = htmlContent.indexOf(marker);
  if (start === -1) throw new Error(`Could not find function ${name}`);
  let depth = 0;
  let bodyStart = htmlContent.indexOf('{', start);
  let i = bodyStart;
  for (; i < htmlContent.length; i++) {
    if (htmlContent[i] === '{') depth++;
    else if (htmlContent[i] === '}') {
      depth--;
      if (depth === 0) break;
    }
  }
  return htmlContent.substring(start, i + 1);
}

// Evaluate extracted functions in global scope
const fnRenderMultiple = extractFunction('renderMultipleProgressCards');
const fnRenderHistory = extractFunction('renderAnnouncementHistoryUI');
const fnRenderUI = extractFunction('renderAnnouncementUI');
const fnSaveActive = extractFunction('saveActiveNotifications');
const fnGetActive = extractFunction('getActiveNotifications');

eval(`
${fnSaveActive}
${fnGetActive}
${fnRenderMultiple}
${fnRenderHistory}
${fnRenderUI}
`);

console.log("=== BẮT ĐẦU KIỂM THỬ FRONTEND MULTIPLE PROGRESS CARDS ===");

// -------------------------------------------------------------
// Test Case 1: 2 thông báo A và B cùng active -> Sinh ra 2 thẻ tiến độ độc lập
// -------------------------------------------------------------
console.log("\n[Test 1] 2 thông báo hoạt động đồng thời (A và B):");
const mockActiveList = [
  {
    id: "ann-A",
    title: "Đợt thu A - Mua tài liệu K57",
    targetAmountEth: "0.0100",
    classSize: 7,
    deadline: "23:59 ngày 15/12/2026",
    purpose: "Mua tài liệu học phần",
    status: "active",
    progress: {
      headcountPercent: 43,
      contributingWalletsCount: 3,
      classSize: 7,
      raisedEth: "0.0030",
      targetAmountEth: "0.0100",
      financialPercent: 30,
      hasFinancialTarget: true,
      totalTransactionsCount: 3
    }
  },
  {
    id: "ann-B",
    title: "Đợt thu B - Quỹ dã ngoại K57",
    targetAmountEth: "0.0200",
    classSize: 7,
    deadline: "23:59 ngày 20/12/2026",
    purpose: "Chi phí teambuilding",
    status: "active",
    progress: {
      headcountPercent: 14,
      contributingWalletsCount: 1,
      classSize: 7,
      raisedEth: "0.0020",
      targetAmountEth: "0.0200",
      financialPercent: 10,
      hasFinancialTarget: true,
      totalTransactionsCount: 1
    }
  }
];

renderMultipleProgressCards(mockActiveList);
const container = document.getElementById("activeProgressCardsContainer");
assert.ok(container.innerHTML.includes('id="progress-card-ann-A"'), "Phải có card riêng cho ann-A");
assert.ok(container.innerHTML.includes('id="progress-card-ann-B"'), "Phải có card riêng cho ann-B");
assert.ok(container.innerHTML.includes('id="progress-bar-ann-A"'), "Phải có thanh progress-bar riêng cho ann-A");
assert.ok(container.innerHTML.includes('id="progress-bar-ann-B"'), "Phải có thanh progress-bar riêng cho ann-B");
assert.ok(container.innerHTML.includes("3/7 ví đã đóng góp"), "Card A phải hiển thị đúng số ví đã đóng góp: 3/7 ví");
assert.ok(container.innerHTML.includes("1/7 ví đã đóng góp"), "Card B phải hiển thị đúng số ví đã đóng góp: 1/7 ví");
assert.ok(container.innerHTML.includes("0.0030 / 0.0100 ETH"), "Card A phải hiển thị đúng số ETH đã thu");
assert.ok(container.innerHTML.includes("0.0020 / 0.0200 ETH"), "Card B phải hiển thị đúng số ETH đã thu");
assert.ok(container.innerHTML.includes("initiateCampaignContribution('ann-A'"), "Card A phải có nút nộp riêng cho đợt A");
assert.ok(container.innerHTML.includes("initiateCampaignContribution('ann-B'"), "Card B phải có nút nộp riêng cho đợt B");
console.log("  -> PASS: 2 thẻ tiến độ độc lập hiển thị chính xác mọi chỉ số và nút nộp riêng.");

// -------------------------------------------------------------
// Test Case 2: Trạng thái 0 đợt thu active -> Hiển thị thẻ rỗng 0%
// -------------------------------------------------------------
console.log("\n[Test 2] Không có đợt thu nào đang active (0 đợt thu):");
renderMultipleProgressCards([]);
assert.ok(container.innerHTML.includes("Chưa có đợt thu quỹ nào đang hoạt động"), "Phải có thông báo trạng thái rỗng");
assert.ok(container.innerHTML.includes("0%"), "Tiến độ phải là 0%");
assert.ok(container.innerHTML.includes("0/0 ví"), "Hiển thị 0/0 ví đã nộp");
console.log("  -> PASS: Trạng thái rỗng hiển thị chuẩn xác 0% và thông điệp rõ ràng.");

// -------------------------------------------------------------
// Test Case 3: Nút nộp quỹ chung ẩn/hiện tùy thuộc vào có thông báo active hay không
// -------------------------------------------------------------
console.log("\n[Test 3] Nút nộp quỹ chung ẩn khi không có đợt thu active:");
global.classActiveNotifications = [];
renderAnnouncementUI();
const btnDeposit = document.getElementById("btnDepositAction");
assert.strictEqual(btnDeposit.style.display, "none", "btnDeposit phải display='none' khi không có đợt thu active");

global.classActiveNotifications = mockActiveList;
renderAnnouncementUI();
assert.strictEqual(btnDeposit.style.display, "block", "btnDeposit phải display='block' khi có đợt thu active");
console.log("  -> PASS: Nút nộp tiền tự động ẩn/hiện chuẩn xác.");

// -------------------------------------------------------------
// Test Case 4: Lịch sử đợt thu hiển thị finalProgress và adjustedFinalProgress
// -------------------------------------------------------------
console.log("\n[Test 4] Hiển thị lịch sử với finalProgress snapshot và kiểm toán:");
global.classAnnouncementHistory = [
  {
    id: "ann-C-closed",
    title: "Đợt thu C đã kết thúc",
    targetAmountEth: "0.0100",
    classSize: 7,
    status: "completed",
    endedAt: "2026-11-04T12:00:00+07:00",
    endReason: "Đã đạt mục tiêu",
    finalProgress: {
      notificationId: "ann-C-closed",
      contributingWalletsCount: 7,
      classSize: 7,
      headcountPercent: 100,
      raisedEth: "0.0100",
      targetAmountEth: "0.0100",
      hasFinancialTarget: true,
      financialPercent: 100,
      isFrozen: true
    },
    adjustedFinalProgress: {
      adjustmentReason: "Bổ sung sinh viên nộp trễ trước giờ đóng sổ",
      contributingWalletsCount: 7,
      classSize: 7,
      headcountPercent: 100,
      raisedEth: "0.0110",
      targetAmountEth: "0.0100",
      hasFinancialTarget: true,
      financialPercent: 110,
      adjustedAt: "2026-11-04T14:00:00+07:00",
      adjustedBy: "0x85ac8f0ca75f2e3fda073bc566659c011208da74"
    }
  }
];

renderAnnouncementHistoryUI();
const histContainer = document.getElementById("annHistoryListContainer");
assert.ok(histContainer.innerHTML.includes("7/7 ví đã đóng góp (100%) - Đã chốt sổ"), "Phải hiển thị snapshot chốt sổ finalProgress");
assert.ok(histContainer.innerHTML.includes("Số liệu điều chỉnh sau kiểm toán"), "Phải hiển thị khối số liệu điều chỉnh kiểm toán");
assert.ok(histContainer.innerHTML.includes("Bổ sung sinh viên nộp trễ trước giờ đóng sổ"), "Phải hiển thị lý do điều chỉnh");
console.log("  -> PASS: Lịch sử đợt thu hiển thị snapshot chốt sổ và khối kiểm toán điều chỉnh minh bạch.");

console.log("\n🎉 TẤT CẢ 4 KỊCH BẢN KIỂM THỬ FRONTEND ĐỀU THÀNH CÔNG (100% PASS)!");
