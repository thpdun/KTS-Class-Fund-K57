/**
 * KTS-Class-Fund-K57: Test Suite Giai đoạn 2 - Phân hệ vai trò & Hiển thị chức năng
 * Kiểm tra 11 tình huống theo đặc tả yêu cầu của Giai đoạn 2
 */
const fs = require('fs');

// 1. Tạo môi trường DOM giả lập tối giản cho Node.js
class FakeClassList {
  constructor() {
    this.classes = new Set();
  }
  add(cls) { this.classes.add(cls); }
  remove(cls) { this.classes.delete(cls); }
  contains(cls) { return this.classes.has(cls); }
  has(cls) { return this.classes.has(cls); }
  toggle(cls) {
    if (this.classes.has(cls)) this.classes.delete(cls);
    else this.classes.add(cls);
  }
}

class FakeElement {
  constructor(id, tagName = 'div') {
    this.id = id;
    this.tagName = tagName.toUpperCase();
    this.style = { display: '' };
    this.classList = new FakeClassList();
    this.textContent = '';
    this.innerHTML = '';
    this.value = '';
    this.listeners = {};
  }
  addEventListener(event, fn) {
    this.listeners[event] = fn;
  }
  click() {
    if (this.listeners['click']) this.listeners['click']();
  }
  scrollIntoView() {}
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
let alertLogs = [];
global.alert = (msg) => { alertLogs.push(msg); };
global.logToTerminal = (msg) => {};

// 2. Trích xuất chính xác từ inline script
const scriptContent = fs.readFileSync('scratch/test_inline_script_0.js', 'utf8');

function extractFunction(name) {
  const pattern = new RegExp(`((?:async\\s+)?function\\s+${name}\\s*\\([\\s\\S]*?\\n\\s{4}\\})`, 'm');
  const match = scriptContent.match(pattern);
  if (!match) {
    throw new Error(`Could not extract function: ${name}`);
  }
  return match[1];
}

const functionsToLoad = [
  'ensureCorrectNetwork',
  'syncRolePermissionsUI',
  'selectRoleView',
  'closeRoleDetail',
  'doDeposit',
  'doCreateRefund',
  'doCreateSpend',
  'voteSpend',
  'executeSpend',
  'voteRefund',
  'executeRefund',
  'doSetBCS',
  'doWithdrawFee'
];

let codeToEval = `
  var isAdvisor = false;
  var isBcsMember = false;
  var userAddress = null;
  var signer = null;
  var contract = null;
  var myStudentProfile = null;
  var CONFIG = { chainId: 11155111 };
  var currentDetailRole = null;
  var allFlowItems = [];

  function promptSwitchSepoliaModal() {}
  function shortenAddress(a) { return a ? a.slice(0,6) + '...' : ''; }
  function renderFlowLedgerTable() {}
  function refreshContractData() {}
`;

for (const fn of functionsToLoad) {
  codeToEval += '\n' + extractFunction(fn);
}

eval(codeToEval);

console.log("=== BẮT ĐẦU KIỂM THỬ 11 TÌNH HUỐNG GIAI ĐOẠN 2 ===\n");

let passed = 0;
let total = 0;

function assert(condition, testName, details = '') {
  total++;
  if (condition) {
    console.log(`[PASS] ${testName}`);
    passed++;
  } else {
    console.error(`[FAIL] ${testName}: ${details}`);
  }
}

// TÌNH HUỐNG 1: Chưa kết nối ví
syncRolePermissionsUI('none');
assert(
  getElementById('sectionDepositForm').style.display === 'none' &&
  getElementById('sectionRefundForm').style.display === 'none' &&
  getElementById('noticeStudentNeedWallet').style.display === 'block' &&
  getElementById('sectionBcsCreateSpend').style.display === 'none' &&
  getElementById('noticeBcsRestricted').style.display === 'block' &&
  getElementById('sectionAdvisorManageBcs').style.display === 'none' &&
  getElementById('sectionAdvisorWithdrawFee').style.display === 'none' &&
  getElementById('noticeAdvisorRestricted').style.display === 'block',
  "Tình huống 1: Chưa kết nối ví -> Ẩn toàn bộ biểu mẫu giao dịch, hiển thị lời nhắc kết nối ví rõ ràng"
);

// TÌNH HUỐNG 2: Kết nối ví Sinh viên hợp lệ
syncRolePermissionsUI('student');
assert(
  getElementById('sectionDepositForm').style.display === 'block' &&
  getElementById('sectionRefundForm').style.display === 'block' &&
  getElementById('noticeStudentNeedWallet').style.display === 'none' &&
  getElementById('sectionBcsCreateSpend').style.display === 'none' &&
  getElementById('noticeBcsRestricted').style.display === 'block' &&
  getElementById('sectionAdvisorManageBcs').style.display === 'none' &&
  getElementById('sectionAdvisorWithdrawFee').style.display === 'none' &&
  getElementById('noticeAdvisorRestricted').style.display === 'block',
  "Tình huống 2: Kết nối ví Sinh viên -> Hiển thị nộp quỹ/hoàn tiền; Ẩn tạo chi tiêu, rút phí, quản lý BCS"
);

// TÌNH HUỐNG 3: Kết nối ví BCS hợp lệ
syncRolePermissionsUI('bcs');
assert(
  getElementById('sectionDepositForm').style.display === 'block' &&
  getElementById('sectionRefundForm').style.display === 'block' &&
  getElementById('sectionBcsCreateSpend').style.display === 'block' &&
  getElementById('noticeBcsRestricted').style.display === 'none' &&
  getElementById('sectionAdvisorManageBcs').style.display === 'none' &&
  getElementById('sectionAdvisorWithdrawFee').style.display === 'none' &&
  getElementById('noticeAdvisorRestricted').style.display === 'block',
  "Tình huống 3: Kết nối ví Ban cán sự -> Hiển thị nộp quỹ, hoàn tiền, tạo đề xuất chi; Ẩn quyền CVHT"
);

// TÌNH HUỐNG 4: Kết nối ví CVHT hợp lệ
syncRolePermissionsUI('advisor');
assert(
  getElementById('sectionDepositForm').style.display === 'none' &&
  getElementById('sectionRefundForm').style.display === 'none' &&
  getElementById('noticeStudentAdvisorView').style.display === 'block' &&
  getElementById('sectionBcsCreateSpend').style.display === 'none' &&
  getElementById('noticeBcsRestricted').style.display === 'block' &&
  getElementById('sectionAdvisorManageBcs').style.display === 'block' &&
  getElementById('sectionAdvisorWithdrawFee').style.display === 'block' &&
  getElementById('noticeAdvisorRestricted').style.display === 'none',
  "Tình huống 4: Kết nối ví CVHT -> Hiển thị quản lý BCS và rút phí; Ẩn form nộp quỹ/tạo chi của sinh viên/BCS"
);

// TÌNH HUỐNG 5: Kết nối ví ngoài danh bạ
syncRolePermissionsUI('guest');
assert(
  getElementById('sectionDepositForm').style.display === 'none' &&
  getElementById('sectionRefundForm').style.display === 'none' &&
  getElementById('noticeStudentGuest').style.display === 'block' &&
  getElementById('sectionBcsCreateSpend').style.display === 'none' &&
  getElementById('noticeBcsRestricted').style.display === 'block' &&
  getElementById('sectionAdvisorManageBcs').style.display === 'none' &&
  getElementById('sectionAdvisorWithdrawFee').style.display === 'none' &&
  getElementById('noticeAdvisorRestricted').style.display === 'block',
  "Tình huống 5: Kết nối ví ngoài danh bạ -> Không cấp bất kỳ quyền thao tác nào, hiện thông báo liên hệ BCS"
);

// TÌNH HUỐNG 6: Chuyển từ ví BCS sang ví Sinh viên
syncRolePermissionsUI('bcs');
syncRolePermissionsUI('student');
assert(
  getElementById('sectionBcsCreateSpend').style.display === 'none' &&
  getElementById('noticeBcsRestricted').style.display === 'block' &&
  getElementById('sectionDepositForm').style.display === 'block',
  "Tình huống 6: Chuyển từ ví BCS sang ví Sinh viên -> Quyền tạo chi tiêu lập tức bị ẩn, trở về quyền SV"
);

// TÌNH HUỐNG 7: Chuyển từ ví CVHT sang ví không có quyền
syncRolePermissionsUI('advisor');
syncRolePermissionsUI('guest');
assert(
  getElementById('sectionAdvisorManageBcs').style.display === 'none' &&
  getElementById('sectionAdvisorWithdrawFee').style.display === 'none' &&
  getElementById('noticeAdvisorRestricted').style.display === 'block' &&
  getElementById('sectionDepositForm').style.display === 'none',
  "Tình huống 7: Chuyển từ ví CVHT sang ví không có quyền -> Ẩn ngay quản lý BCS và rút phí vận hành"
);

// TÌNH HUỐNG 8: Ngắt kết nối ví
syncRolePermissionsUI('none');
assert(
  window.currentVerifiedRole === 'none' &&
  getElementById('sectionDepositForm').style.display === 'none' &&
  getElementById('sectionBcsCreateSpend').style.display === 'none' &&
  getElementById('sectionAdvisorManageBcs').style.display === 'none' &&
  getElementById('noticeStudentNeedWallet').style.display === 'block',
  "Tình huống 8: Ngắt kết nối ví -> Trở về trạng thái none, ẩn mọi form nhạy cảm và hiện lời nhắc kết nối"
);

// TÌNH HUỐNG 9: Chuyển sang mạng khác Sepolia
provider = { getNetwork: async () => ({ chainId: 1 }) }; // Mainnet
ensureCorrectNetwork().then(async (isCorrect) => {
  assert(
    isCorrect === false,
    "Tình huống 9: Chuyển sang mạng khác Sepolia -> Bị chặn giao dịch (ensureCorrectNetwork trả về false)"
  );

  // TÌNH HUỐNG 10: Mở tab lịch sử dòng tiền khi chưa kết nối ví
  window.currentVerifiedRole = 'none';
  selectRoleView('history');
  assert(
    getElementById('panelHistory').style.display === 'flex' &&
    getElementById('btnRoleHistory').classList.has('active'),
    "Tình huống 10: Mở Lịch sử dòng tiền khi chưa kết nối ví -> Công khai, truy cập và xem bình thường"
  );

  // TÌNH HUỐNG 11: Kiểm tra chống gian lận & gọi hàm trái quyền (Security & Cheat testing)
  // 11a: Sinh viên đổi tab sang BCS
  window.currentVerifiedRole = 'student';
  selectRoleView('bcs');
  assert(
    getElementById('panelBCS').style.display === 'flex' &&
    getElementById('sectionBcsCreateSpend').style.display === 'none' &&
    getElementById('noticeBcsRestricted').style.display === 'block',
    "Tình huống 11a: Sinh viên bấm tab BCS -> Form tạo chi tiêu vẫn bị ẨN, không nhận được quyền BCS"
  );

  // 11b: Sinh viên gọi trực tiếp doCreateSpend() từ Console
  isBcsMember = false;
  signer = { getAddress: () => '0xStudent' };
  contract = {};
  provider = { getNetwork: async () => ({ chainId: 11155111 }) };
  alertLogs = [];
  await doCreateSpend();
  assert(
    alertLogs.some(m => m.includes("Từ chối quyền") && m.includes("Ban cán sự")),
    "Tình huống 11b (Gian lận): Sinh viên gọi trực tiếp doCreateSpend() -> Bị chặn với thông báo từ chối quyền"
  );

  // 11c: Sinh viên gọi trực tiếp doSetBCS() từ Console
  isAdvisor = false;
  alertLogs = [];
  await doSetBCS();
  assert(
    alertLogs.some(m => m.includes("Từ chối quyền") && m.includes("Cố vấn học tập")),
    "Tình huống 11c (Gian lận): Sinh viên gọi trực tiếp doSetBCS() -> Bị chặn với thông báo từ chối quyền"
  );

  // 11d: Sinh viên gọi trực tiếp doWithdrawFee() từ Console
  alertLogs = [];
  await doWithdrawFee();
  assert(
    alertLogs.some(m => m.includes("Từ chối quyền") && m.includes("Cố vấn học tập")),
    "Tình huống 11d (Gian lận): Sinh viên gọi trực tiếp doWithdrawFee() -> Bị chặn với thông báo từ chối quyền"
  );

  console.log(`\n=== TỔNG KẾT: ${passed}/${total} KIỂM THỬ ĐẠT (PASS) ===`);
  if (passed === total) {
    console.log("Tất cả các tình huống phân quyền Giai đoạn 2 đã HOÀN THÀNH XUẤT SẮC!");
  } else {
    process.exit(1);
  }
});
