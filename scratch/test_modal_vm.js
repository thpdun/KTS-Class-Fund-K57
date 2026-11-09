const fs = require('fs');
const vm = require('vm');

const html = fs.readFileSync('web/index.html', 'utf-8');

const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/i);
if (!scriptMatch) {
  console.error("No script tag found!");
  process.exit(1);
}

class MockElement {
  constructor(id, tag = 'div') {
    this.id = id;
    this.tagName = tag.toUpperCase();
    this.style = {};
    const classes = new Set();
    this.classList = {
      classes: classes,
      add: (...tokens) => tokens.forEach(t => classes.add(t)),
      remove: (...tokens) => tokens.forEach(t => classes.delete(t)),
      contains: (t) => classes.has(t),
    };
    this.children = [];
    this.textContent = '';
    this.innerHTML = '';
  }
  setAttribute(k, v) { this[k] = v; }
  getAttribute(k) { return this[k]; }
  focus() { this.focused = true; }
  closest() { return this; }
}

const elements = {};
function getOrCreate(id) {
  if (!elements[id]) {
    elements[id] = new MockElement(id);
  }
  return elements[id];
}

[
  "dapp-workspace", "workspaceModalBox", "actionModalIcon", "actionModalTitle", "actionModalSub",
  "panelStudent", "panelBCS", "panelAdvisor", "panelHistory",
  "sectionDepositForm", "sectionRefundForm", "sectionBcsCreateSpend", "sectionBcsManageCollection",
  "sectionAdvisorManageBcs", "sectionAdvisorWithdrawFee", "sectionAdvisorStudentMonitor",
  "roleDetailContainer", "inputDepositAmount", "inputRefundAmount", "inputSpendRecipient",
  "bcsSpendTableBody", "flowLedgerTableBody", "btnConnectWallet", "walletBtnText"
].forEach(id => getOrCreate(id));

const mockStore = {};
const mockLocalStorage = {
  getItem: (k) => mockStore[k] || null,
  setItem: (k, v) => { mockStore[k] = String(v); },
  removeItem: (k) => { delete mockStore[k]; }
};

const mockDocument = {
  getElementById: (id) => getOrCreate(id),
  querySelector: () => null,
  querySelectorAll: () => [],
  addEventListener: () => {},
  body: new MockElement('body', 'body')
};

const context = {
  document: mockDocument,
  window: {
    currentVerifiedRole: "student",
    addEventListener: () => {},
  },
  localStorage: mockLocalStorage,
  console: console,
  setTimeout: (fn) => fn(),
  ethers: { formatEther: () => "0" },
  activeBcsCount: 3,
  allFlowItems: [],
  syncRolePermissionsUI: () => {},
  formatEth: () => "0",
  shortenAddress: (a) => a,
};

vm.createContext(context);

try {
  vm.runInContext(scriptMatch[1], context);
  console.log("✓ Script evaluated cleanly!");

  // Test 1: openActionModal('deposit') as student
  context.window.currentVerifiedRole = "student";
  context.openActionModal('deposit');
  const ws = elements['dapp-workspace'];
  const pStudent = elements['panelStudent'];
  const secDep = elements['sectionDepositForm'];
  const secRef = elements['sectionRefundForm'];
  const pBCS = elements['panelBCS'];

  if (ws.style.display !== 'flex' || !ws.classList.contains('show')) {
    throw new Error(`openActionModal('deposit') failed: display=${ws.style.display}, hasShow=${ws.classList.contains('show')}`);
  }
  if (pStudent.style.display !== 'block') {
    throw new Error("panelStudent not displayed!");
  }
  if (secDep.style.display !== 'block') {
    throw new Error("sectionDepositForm not displayed!");
  }
  if (secRef.style.display !== 'none') {
    throw new Error("sectionRefundForm should be hidden in deposit action!");
  }
  if (pBCS.style.display !== 'none') {
    throw new Error("panelBCS should be hidden in deposit action!");
  }
  console.log("✓ Test 1: openActionModal('deposit') displays ONLY deposit form cleanly!");

  // Test 2: closeActionModal()
  context.closeActionModal();
  if (ws.style.display !== 'none' || ws.classList.contains('show')) {
    throw new Error("closeActionModal() failed to hide modal!");
  }
  console.log("✓ Test 2: closeActionModal() closes cleanly!");

  // Test 3: openActionModal('spend') as BCS member
  context.window.currentVerifiedRole = "bcs";
  context.openActionModal('spend');
  const secSpend = elements['sectionBcsCreateSpend'];
  if (pBCS.style.display !== 'block' || secSpend.style.display !== 'block') {
    throw new Error("spend modal failed to display BCS spend create form!");
  }
  if (pStudent.style.display !== 'none') {
    throw new Error("panelStudent should be hidden in spend action!");
  }
  console.log("✓ Test 3: openActionModal('spend') as BCS displays ONLY spend form cleanly!");

  // Test 4 (Cheat/Security): Unauthorized role (student) attempts to open spend modal
  context.closeActionModal();
  context.window.currentVerifiedRole = "student";
  context.openActionModal('spend');
  if (secSpend.style.display === 'block') {
    throw new Error("Security breach: student was able to display BCS spend form!");
  }
  console.log("✓ Test 4 (Cheat/Security): Student attempt to open spend modal is safely blocked without showing creation form!");

  console.log("\n🎉 ALL 4 FOCUSED MODAL CONTROLLER TESTS PASSED 100%!");
} catch (err) {
  console.error("Test failed:", err);
  process.exit(1);
}
