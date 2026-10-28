/**
 * KTS-Class-Fund-K57: Automated Test for Frontend DOM Cleanup & PII Protection
 * Stage 3B.4.3
 */
const fs = require('fs');

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
    this.style = { display: '' };
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

global.localStorage = {
  data: {},
  getItem: (k) => global.localStorage.data[k] || null,
  setItem: (k, v) => { global.localStorage.data[k] = v; },
  removeItem: (k) => { delete global.localStorage.data[k]; }
};

let alerts = [];
global.alert = (msg) => { alerts.push(msg); };
global.logToTerminal = () => {};
global.fetch = async () => ({ ok: true, json: async () => ({}) });

// Read web/index.html and extract relevant functions
const htmlContent = fs.readFileSync('web/index.html', 'utf8');

function extractFunc(name) {
  const match = htmlContent.match(new RegExp(`((?:async\\s+)?function\\s+${name}\\s*\\([\\s\\S]*?\\n\\s{4}\\})`, 'm'));
  if (!match) throw new Error(`Could not find function: ${name}`);
  return match[1];
}

const functionsToExtract = [
  'clearSensitiveClientData',
  'handleDisconnect',
  'invalidateRosterContribCache',
  'cancelEditRoster',
  'renderRosterTable',
  'updateRoleDisplay',
  'syncRolePermissionsUI',
  'lookupStudent',
  'shortenAddress'
];

let evalCode = `
var userAddress = null;
var signer = null;
var isAdvisor = false;
var isBcsMember = false;
var myStudentProfile = null;
var userSessionToken = null;
var classRoster = [];
var currentRosterFilter = 'all';
var rosterContribCache = new Map();
var contract = null;
var provider = null;
var CONFIG = { contractAddress: null, chainId: 11155111 };
function renderAnnouncementUI() {}
function renderPendingActions() {}
`;

for (const fn of functionsToExtract) {
  evalCode += '\n' + extractFunc(fn);
}

eval(evalCode);

console.log("=== BẮT ĐẦU KIỂM THỬ TỰ ĐỘNG DỌN DẸP DOM & BẢO VỆ PII (STAGE 3B.4.3) ===\n");

let passed = 0;
let total = 0;

function assert(condition, name, details = '') {
  total++;
  if (condition) {
    passed++;
    console.log(`  [PASS] Test ${total}: ${name}`);
  } else {
    console.error(`  [FAIL] Test ${total}: ${name} - ${details}`);
  }
}

// 1. Setup mock populated state
userAddress = "0x1111111111111111111111111111111111111111";
userSessionToken = "valid_session_token_123";
myStudentProfile = {
  name: "Nguyễn Văn A",
  mssv: "51800001",
  wallet: "0x1111111111111111111111111111111111111111",
  role: "bcs"
};
isBcsMember = true;
classRoster = [
  { name: "Nguyễn Văn A", mssv: "51800001", wallet: "0x1111111111111111111111111111111111111111", role: "bcs" },
  { name: "Trần Thị B", mssv: "51800002", wallet: "0x2222222222222222222222222222222222222222", role: "student" },
  { name: "Lê Văn C", mssv: "51800003", wallet: "0x3333333333333333333333333333333333333333", role: "student" }
];

// Seed DOM with populated rows
const tbody = getElementById("rosterTableBody");
tbody.innerHTML = `<tr><td>51800001</td><td>Nguyễn Văn A</td></tr><tr><td>51800002</td><td>Trần Thị B</td></tr>`;
getElementById("rosterCountBadge").textContent = "3";
getElementById("sidebarRosterBadge").textContent = "3";
getElementById("rosterStatTotal").textContent = "3 bạn";
getElementById("rosterStatBcs").textContent = "1 thành viên";
getElementById("rosterStatStudents").textContent = "2 bạn";
getElementById("rosterStatPaid").textContent = "0/3 (0%)";
getElementById("myTotalContribution").textContent = "0.0500 ETH";
getElementById("myPendingRefund").textContent = "0.0200 ETH";
getElementById("myAvailableRefund").textContent = "0.0200 ETH";
getElementById("rosterAdminSection").style.display = "block";

assert(tbody.innerHTML.includes("Nguyễn Văn A"), "State ban đầu chứa thông tin sinh viên trên DOM");

// 2. Test handleDisconnect()
(async () => {
  await handleDisconnect();

  assert(classRoster.length === 0, "handleDisconnect xóa sạch classRoster trong bộ nhớ");
  assert(myStudentProfile === null, "handleDisconnect xóa sạch myStudentProfile");
  assert(userSessionToken === null, "handleDisconnect xóa userSessionToken");
  assert(userAddress === null, "handleDisconnect đặt userAddress về null");

  assert(!tbody.innerHTML.includes("Nguyễn Văn A"), "handleDisconnect xóa họ tên sinh viên khỏi rosterTableBody");
  assert(!tbody.innerHTML.includes("51800001"), "handleDisconnect xóa MSSV khỏi rosterTableBody");
  assert(tbody.innerHTML.includes("🔒 Danh bạ sinh viên được bảo vệ dữ liệu cá nhân"), "rosterTableBody hiển thị placeholder bảo vệ dữ liệu");

  assert(getElementById("rosterCountBadge").textContent === "0", "rosterCountBadge được đặt về 0");
  assert(getElementById("sidebarRosterBadge").textContent === "0", "sidebarRosterBadge được đặt về 0");
  assert(getElementById("rosterStatTotal").textContent === "0 bạn", "rosterStatTotal được đặt về '0 bạn'");
  assert(getElementById("rosterStatBcs").textContent === "0 thành viên", "rosterStatBcs được đặt về '0 thành viên'");
  assert(getElementById("rosterStatStudents").textContent === "0 bạn", "rosterStatStudents được đặt về '0 bạn'");
  assert(getElementById("rosterStatPaid").textContent === "0/0 (0%)", "rosterStatPaid được đặt về '0/0 (0%)'");

  assert(getElementById("myTotalContribution").textContent === "0.0000 ETH", "myTotalContribution đặt về 0.0000 ETH");
  assert(getElementById("myPendingRefund").textContent === "0.0000 ETH", "myPendingRefund đặt về 0.0000 ETH");
  assert(getElementById("myAvailableRefund").textContent === "0.0000 ETH", "myAvailableRefund đặt về 0.0000 ETH");
  assert(getElementById("studentRefundTableBody").innerHTML.includes("Vui lòng kết nối ví"), "studentRefundTableBody reset về thông báo mời kết nối");
  assert(getElementById("rosterAdminSection").style.display === "none", "rosterAdminSection bị ẩn sau khi ngắt ví");

  // 3. Test clearSensitiveClientData(keepGuestUI = true) (kịch bản đổi ví hoặc hủy ký MetaMask)
  // Giả lập nạp lại dữ liệu
  classRoster = [
    { name: "Đặng Hoàng D", mssv: "51800004", wallet: "0x4444444444444444444444444444444444444444", role: "student" }
  ];
  userAddress = "0x9999999999999999999999999999999999999999";
  tbody.innerHTML = `<tr><td>51800004</td><td>Đặng Hoàng D</td></tr>`;
  getElementById("rosterCountBadge").textContent = "1";
  getElementById("quickStudentIdentity").innerHTML = "Đặng Hoàng D (51800004)";

  // Gọi dọn dẹp ở chế độ khách (sau khi hủy ký MetaMask hoặc đổi ví)
  clearSensitiveClientData(true);

  assert(classRoster.length === 0, "clearSensitiveClientData(true) xóa sạch classRoster trong bộ nhớ");
  assert(!tbody.innerHTML.includes("Đặng Hoàng D"), "clearSensitiveClientData(true) xóa họ tên khỏi DOM");
  assert(!tbody.innerHTML.includes("51800004"), "clearSensitiveClientData(true) xóa MSSV khỏi DOM");
  assert(getElementById("rosterCountBadge").textContent === "0", "rosterCountBadge đặt về 0 ở chế độ guest");
  assert(window.currentVerifiedRole === "guest", "currentVerifiedRole chuyển sang 'guest' an toàn");
  assert(getElementById("quickStudentIdentity").innerHTML.includes("Chưa ký xác thực danh tính"), "quickStudentIdentity hiển thị cảnh báo chưa xác thực thay vì tên sinh viên");
  assert(getElementById("rosterAdminSection").style.display === "none", "rosterAdminSection bị ẩn ở chế độ guest");

  // 4. Test renderRosterTable() khi classRoster rỗng
  tbody.innerHTML = "<tr><td>Dữ liệu cũ còn sót lại</td></tr>";
  getElementById("rosterStatTotal").textContent = "99 bạn";
  renderRosterTable();

  assert(!tbody.innerHTML.includes("Dữ liệu cũ còn sót lại"), "renderRosterTable xóa sạch dữ liệu cũ khi classRoster rỗng");
  assert(tbody.innerHTML.includes("🔒 Danh bạ sinh viên được bảo vệ dữ liệu cá nhân"), "renderRosterTable hiển thị placeholder bảo vệ khi danh bạ rỗng");
  assert(getElementById("rosterStatTotal").textContent === "0 bạn", "renderRosterTable reset rosterStatTotal về '0 bạn'");
  assert(getElementById("rosterCountBadge").textContent === "0", "renderRosterTable reset rosterCountBadge về '0'");

  console.log(`\n=== TỔNG KẾT KIỂM THỬ DOM CLEANUP: ${passed}/${total} PASS ===\n`);
  if (passed === total) {
    process.exit(0);
  } else {
    process.exit(1);
  }
})();
