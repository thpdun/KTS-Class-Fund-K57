/**
 * KIỂM THỬ TOÀN DIỆN HỆ THỐNG PHÂN QUYỀN (RBAC) - ECO2432
 * Chạy với Headless Chrome CDP & HTTP Fetch
 */
const { spawn } = require('child_process');
const http = require('http');
const path = require('path');
const fs = require('fs');
const os = require('os');
const WebSocket = require('ws');

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const htmlPath = path.resolve(__dirname, '../web/index.html');
const tempProfile = fs.mkdtempSync(path.join(os.tmpdir(), 'chrome-rbac-test-'));

async function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(JSON.parse(data)));
    }).on('error', reject);
  });
}

async function run() {
  console.log("================================================================================");
  console.log("   KIỂM THỬ TÍCH HỢP HỆ THỐNG PHÂN QUYỀN (RBAC) - HEADLESS CHROME CDP");
  console.log("================================================================================");

  if (!fs.existsSync(CHROME_PATH)) {
    console.error("Không tìm thấy Chrome:", CHROME_PATH);
    process.exit(1);
  }

  const port = 9224;
  const chrome = spawn(CHROME_PATH, [
    '--headless=new',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${tempProfile}`,
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--allow-file-access-from-files',
    `file://${htmlPath}`
  ]);

  let killed = false;
  function cleanup() {
    if (!killed) {
      killed = true;
      try { chrome.kill(); } catch (e) {}
      try { fs.rmSync(tempProfile, { recursive: true, force: true }); } catch (e) {}
    }
  }
  process.on('exit', cleanup);
  process.on('SIGINT', cleanup);

  let version;
  for (let i = 0; i < 30; i++) {
    await new Promise(r => setTimeout(r, 250));
    try {
      version = await getJson(`http://127.0.0.1:${port}/json/version`);
      if (version) break;
    } catch (e) {}
  }

  if (!version) {
    console.error("[FAIL] Không thể kết nối Chrome DevTools Protocol");
    cleanup();
    process.exit(1);
  }
  console.log(`[PASS] Khởi chạy Chrome thành công (${version.Browser})`);

  const targets = await getJson(`http://127.0.0.1:${port}/json/list`);
  const pageTarget = targets.find(t => t.type === 'page') || targets[0];
  const ws = new WebSocket(pageTarget.webSocketDebuggerUrl);

  let idCounter = 1;
  const pending = new Map();

  ws.on('message', data => {
    try {
      const msg = JSON.parse(data.toString());
      if (msg.id && pending.has(msg.id)) {
        pending.get(msg.id)(msg);
        pending.delete(msg.id);
      }
    } catch (e) {}
  });

  await new Promise(r => ws.on('open', r));

  function sendCDP(method, params = {}) {
    return new Promise(resolve => {
      const id = idCounter++;
      pending.set(id, resolve);
      ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async function evalInPage(expression) {
    const res = await sendCDP('Runtime.evaluate', {
      expression: expression,
      returnByValue: true,
      awaitPromise: true
    });
    if (res.result && res.result.exceptionDetails) {
      throw new Error(JSON.stringify(res.result.exceptionDetails));
    }
    return res.result?.result?.value;
  }

  await sendCDP('Page.enable');
  await sendCDP('Runtime.enable');
  for (let i = 0; i < 50; i++) {
    await new Promise(r => setTimeout(r, 250));
    try {
      const ready = await evalInPage(`typeof syncRolePermissionsUI === 'function'`);
      if (ready) break;
    } catch (e) {}
  }

  console.log("\n--- TEST 1: KHÁCH VÃNG LAI (GUEST / DISCONNECTED) ---");
  const guestResult = await evalInPage(`
    (() => {
      syncRolePermissionsUI('guest');
      const cDep = document.getElementById('cardActionDeposit')?.style.display;
      const cRef = document.getElementById('cardActionRefund')?.style.display;
      const cSpd = document.getElementById('cardActionSpend')?.style.display;
      const cVot = document.getElementById('cardActionVote')?.style.display;
      const cLed = document.getElementById('cardActionLedger')?.style.display;
      const cMem = document.getElementById('cardActionMembers')?.style.display;
      const cGov = document.getElementById('cardActionGovernance')?.style.display;
      const navServ = document.getElementById('wrapServicesMega')?.style.display;
      const navLed = document.getElementById('navLinkLedger')?.style.display;
      const svcSection = document.querySelector('.action-service-section')?.style.display;

      return {
        actionSectionHidden: (svcSection === 'none'),
        servicesDropdownHidden: (navServ === 'none'),
        ledgerLinkVisible: (navLed === 'inline-flex'),
        connectBtnVisible: (document.getElementById('btnConnectWallet')?.style.display !== 'none')
      };
    })()
  `);
  console.log("Khách:", JSON.stringify(guestResult));
  if (!guestResult.actionSectionHidden || !guestResult.servicesDropdownHidden || !guestResult.ledgerLinkVisible) {
    console.error("[FAIL] Phân quyền Khách không đúng yêu cầu!");
  } else {
    console.log("[PASS] Khách: Khối dịch vụ nhanh bị ẩn, có thể xem Sổ quỹ công khai qua menu trên cùng.");
  }

  console.log("\n--- TEST 2: VAI TRÒ SINH VIÊN (STUDENT) ---");
  const studentResult = await evalInPage(`
    (() => {
      syncRolePermissionsUI('student');
      const cDep = document.getElementById('cardActionDeposit')?.style.display;
      const cRef = document.getElementById('cardActionRefund')?.style.display;
      const cSpd = document.getElementById('cardActionSpend')?.style.display;
      const cVot = document.getElementById('cardActionVote')?.style.display;
      const cLed = document.getElementById('cardActionLedger')?.style.display;
      const cMem = document.getElementById('cardActionMembers')?.style.display;
      const cGov = document.getElementById('cardActionGovernance')?.style.display;
      const megaGov = document.getElementById('megaGroupGovernance')?.style.display;
      const navLed = document.getElementById('navLinkLedger')?.style.display;

      return {
        deposit: cDep, // flex
        refund: cRef,   // flex
        spend: cSpd,    // none
        vote: cVot,     // none
        ledger: cLed,   // flex
        members: cMem,  // none
        gov: cGov,      // none
        megaGov: megaGov, // none
        navLed: navLed  // inline-flex
      };
    })()
  `);
  console.log("Sinh viên:", JSON.stringify(studentResult));
  if (studentResult.deposit !== 'flex' || studentResult.refund !== 'flex' || studentResult.ledger !== 'flex' || studentResult.spend !== 'none' || studentResult.vote !== 'none' || studentResult.members !== 'none' || studentResult.gov !== 'none' || studentResult.navLed !== 'inline-flex') {
    console.error("[FAIL] Phân quyền Sinh viên không đúng yêu cầu!");
  } else {
    console.log("[PASS] Sinh viên: Có Nạp quỹ, Xin hoàn tiền, Sổ dòng tiền (cả thẻ MoMo & Topbar link). Không có Đề xuất chi, Biểu quyết, Quản trị, Danh bạ.");
  }

  console.log("\n--- TEST 3: VAI TRÒ BAN CÁN SỰ (BCS) ---");
  const bcsResult = await evalInPage(`
    (() => {
      syncRolePermissionsUI('bcs');
      const cDep = document.getElementById('cardActionDeposit')?.style.display;
      const cRef = document.getElementById('cardActionRefund')?.style.display;
      const cSpd = document.getElementById('cardActionSpend')?.style.display;
      const cVot = document.getElementById('cardActionVote')?.style.display;
      const cLed = document.getElementById('cardActionLedger')?.style.display;
      const cMem = document.getElementById('cardActionMembers')?.style.display;
      const cGov = document.getElementById('cardActionGovernance')?.style.display;
      const advSec = document.getElementById('sectionAdvancedSettings')?.style.display;

      return {
        deposit: cDep, // flex
        refund: cRef,   // flex
        spend: cSpd,    // flex
        vote: cVot,     // flex
        ledger: cLed,   // flex
        members: cMem,  // flex
        gov: cGov,      // none
        advSec: advSec  // none
      };
    })()
  `);
  console.log("BCS:", JSON.stringify(bcsResult));
  if (bcsResult.deposit !== 'flex' || bcsResult.spend !== 'flex' || bcsResult.vote !== 'flex' || bcsResult.ledger !== 'flex' || bcsResult.members !== 'flex' || bcsResult.gov !== 'none') {
    console.error("[FAIL] Phân quyền BCS không đúng yêu cầu!");
  } else {
    console.log("[PASS] BCS có đủ quyền của Sinh viên + Đề xuất chi, Biểu quyết, Sổ dòng tiền, Thành viên. KHÔNG có Quản trị CVHT.");
  }

  console.log("\n--- TEST 4: VAI TRÒ CỐ VẤN HỌC TẬP (ADVISOR) ---");
  const advResult = await evalInPage(`
    (() => {
      syncRolePermissionsUI('advisor');
      const cDep = document.getElementById('cardActionDeposit')?.style.display;
      const cRef = document.getElementById('cardActionRefund')?.style.display;
      const cSpd = document.getElementById('cardActionSpend')?.style.display;
      const cVot = document.getElementById('cardActionVote')?.style.display;
      const cLed = document.getElementById('cardActionLedger')?.style.display;
      const cMem = document.getElementById('cardActionMembers')?.style.display;
      const cGov = document.getElementById('cardActionGovernance')?.style.display;
      const advSec = document.getElementById('sectionAdvancedSettings')?.style.display;

      return {
        deposit: cDep, // none
        refund: cRef,   // none
        spend: cSpd,    // none
        vote: cVot,     // none
        ledger: cLed,   // flex
        members: cMem,  // flex
        gov: cGov,      // flex
        advSec: advSec  // block
      };
    })()
  `);
  console.log("Cố vấn:", JSON.stringify(advResult));
  if (advResult.deposit !== 'none' || advResult.gov !== 'flex' || advResult.members !== 'flex' || advResult.ledger !== 'flex' || advResult.advSec !== 'block') {
    console.error("[FAIL] Phân quyền Cố vấn học tập không đúng yêu cầu!");
  } else {
    console.log("[PASS] Cố vấn có Quản trị CVHT, Thành viên, Sổ dòng tiền. Không có nút nạp quỹ cá nhân.");
  }

  console.log("\n--- TEST 5: BẢO VỆ CHỐNG GỌI MODAL TRỰC TIẾP TỪ DEVTOOLS (STUDENT / GUEST) ---");
  const devtoolsSecurityTest = await evalInPage(`
    (() => {
      syncRolePermissionsUI('student');
      let lastToast = null;
      window.showToast = (msg, type) => { lastToast = { msg, type }; };
      window.__onToast = (msg, type) => { lastToast = { msg, type }; };

      // Thử gọi openActionModal('spend') khi đang là sinh viên
      openActionModal('spend');
      const spendToast = lastToast;

      // Thử gọi openRosterModal() khi đang là sinh viên
      lastToast = null;
      const modalEl = document.getElementById('rosterModal');
      if (modalEl) modalEl.classList.remove('open');
      openRosterModal();
      const rosterToast = lastToast;
      const rosterModalOpen = modalEl?.classList.contains('open');

      // Thử gọi openBcsPersonnelModal() khi đang là sinh viên
      lastToast = null;
      const bcsModalEl = document.getElementById('bcsPersonnelModal');
      if (bcsModalEl) bcsModalEl.classList.remove('open');
      openBcsPersonnelModal();
      const bcsToast = lastToast;
      const bcsModalOpen = bcsModalEl?.classList.contains('open');

      return {
        spendToast: spendToast?.msg,
        rosterToast: rosterToast?.msg,
        rosterModalOpen: rosterModalOpen,
        bcsToast: bcsToast?.msg,
        bcsModalOpen: bcsModalOpen,
        spendBlocked: Boolean(spendToast && spendToast.msg.includes('không có quyền')),
        rosterBlocked: Boolean(rosterToast && rosterToast.msg.includes('không có quyền') && !rosterModalOpen),
        bcsBlocked: Boolean(bcsToast && bcsToast.msg.includes('không có quyền') && !bcsModalOpen)
      };
    })()
  `);
  console.log("DevTools Security:", JSON.stringify(devtoolsSecurityTest));
  if (!devtoolsSecurityTest.spendBlocked || !devtoolsSecurityTest.rosterBlocked || !devtoolsSecurityTest.bcsBlocked) {
    console.error("[FAIL] Bảo vệ modal chống gọi trực tiếp chưa đạt!");
  } else {
    console.log("[PASS] Sinh viên gọi trực tiếp openActionModal('spend'), openRosterModal, openBcsPersonnelModal đều bị chặn và hiện toast cảnh báo.");
  }

  console.log("\n--- TEST 6: PHÂN QUYỀN DANH BẠ (BCS KHÔNG ĐƯỢC SỬA HOẶC THÊM BCS) ---");
  const rosterBcsTest = await evalInPage(`
    (() => {
      syncRolePermissionsUI('bcs');
      window.isAdvisor = false;
      window.isBcsMember = true;
      window.userSessionToken = 'dummy-token';

      openRosterModal();
      const fRole = document.getElementById('formRosterRole');
      const isRoleDisabled = fRole?.disabled;
      const roleVal = fRole?.value;

      let toastMsg = null;
      window.showToast = (m) => { toastMsg = m; };
      window.__onToast = (m) => { toastMsg = m; };
      editRosterStudent('23K4300001');

      return {
        isRoleDisabled: isRoleDisabled,
        roleVal: roleVal,
        editBlocked: Boolean(toastMsg && toastMsg.includes('không có quyền'))
      };
    })()
  `);
  console.log("Roster BCS Test:", JSON.stringify(rosterBcsTest));
  if (!rosterBcsTest.isRoleDisabled || !rosterBcsTest.editBlocked) {
    console.error("[FAIL] Phân quyền form danh bạ với BCS chưa đạt!");
  } else {
    console.log("[PASS] Form danh bạ khóa cứng vai trò 'Sinh viên' với BCS và chặn gọi hàm sửa sinh viên.");
  }

  console.log("\n--- TEST 7: MINH BẠCH TÀI CHÍNH & CHẾ ĐỘ XEM-ONLY CHO SINH VIÊN ---");
  const studentViewOnlyTest = await evalInPage(`
    (() => {
      syncRolePermissionsUI('student');
      window.userAddress = '0x64ADE1f3E814c98dEFeC19f07253afeBDD2DBfcf';
      window.myStudentProfile = { mssv: '23K4300005', name: 'Trần Thị Bình Dương', role: 'student' };

      // 1. Mở Sổ dòng tiền
      navigateTo('ledger');
      const pHistoryVisible = (document.getElementById('panelHistory')?.style.display === 'block');

      // 2. Mở Bảng đề xuất chi tiêu trong chế độ xem
      openActionModal('vote');
      const pBcsVisible = (document.getElementById('panelBCS')?.style.display === 'block');
      const title = document.getElementById('actionModalTitle')?.textContent || '';
      const secSpendCreateHidden = (document.getElementById('sectionBcsCreateSpend')?.style.display === 'none');
      const secBcsColHidden = (document.getElementById('sectionBcsManageCollection')?.style.display === 'none');

      return {
        pHistoryVisible: pHistoryVisible,
        pBcsVisible: pBcsVisible,
        titleContainsViewOnly: title.includes('Chế độ xem'),
        secSpendCreateHidden: secSpendCreateHidden,
        secBcsColHidden: secBcsColHidden
      };
    })()
  `);
  console.log("Student View-Only Test:", JSON.stringify(studentViewOnlyTest));
  if (!studentViewOnlyTest.pHistoryVisible || !studentViewOnlyTest.pBcsVisible || !studentViewOnlyTest.titleContainsViewOnly || !studentViewOnlyTest.secSpendCreateHidden) {
    console.error("[FAIL] Chế độ xem-only tài chính cho Sinh viên chưa đúng!");
  } else {
    console.log("[PASS] Sinh viên xem được Sổ dòng tiền & Danh sách đề xuất chi ở chế độ XEM-ONLY (ẩn form tạo chi, ẩn form đợt thu).");
  }

  console.log("\n--- TEST 8: ẨN DANH THÀNH VIÊN KHÁC & XEM LÝ DO CHI TIẾT ĐẦY ĐỦ (STUDENT PRIVACY & FULL REASON) ---");
  const anonymityTest = await evalInPage(`
    (async () => {
      // 1. Chuẩn bị danh bạ thực tế
      window.classRoster = [
        { mssv: '23K4300004', name: 'Trần Hoàng Phương Dung', wallet: '0x78567A377559F0cB30173f93869326a82320159a', role: 'bcs' },
        { mssv: '23K4300005', name: 'Trần Thị Bình Dương', wallet: '0x64ADE1f3E814c98dEFeC19f07253afeBDD2DBfcf', role: 'student' },
        { mssv: '23K4300015', name: 'Võ Ngọc Tâm Phúc', wallet: '0xf5D971952dbDF69058a28D23110381d96B00cb50', role: 'bcs' }
      ];

      // Đề xuất chi có lý do chi tiết dài chứa cả MSSV và địa chỉ ví 0x đầy đủ
      const detailedReason = 'Thanh toán tiền in ấn tài liệu cho bạn 23K4300004 ví 0x78567A377559F0cB30173f93869326a82320159a phục vụ hội thảo học tập K57';

      // Giả lập contract trả về đề xuất #1 cho Phương Dung
      window.contract = {
        getSpendRequest: async (id) => {
          return [1n, '0x78567A377559F0cB30173f93869326a82320159a', 100000000000000000n, detailedReason, '0xf5D971952dbDF69058a28D23110381d96B00cb50', 1700000000n, 2n, 0n, 0n];
        },
        hasVoted: async () => false
      };

      // Đăng nhập với ví sinh viên 0x64ADE1f3E814c98dEFeC19f07253afeBDD2DBfcf
      window.userAddress = '0x64ADE1f3E814c98dEFeC19f07253afeBDD2DBfcf';
      window.myStudentProfile = { mssv: '23K4300005', name: 'Trần Thị Bình Dương', role: 'student' };

      // Góc nhìn Sinh viên xem đề xuất #1 (Người nhận là Phương Dung)
      syncRolePermissionsUI('student');
      await loadSpendRequests(1, 3);
      const studentHtml = document.getElementById('bcsSpendTableBody')?.innerHTML || '';

      const studentSeesOtherName = studentHtml.includes('Trần Hoàng Phương Dung');
      const studentSeesRawMssv = studentHtml.includes('23K4300004');
      const studentSeesFull0x = studentHtml.includes('0x78567A377559F0cB30173f93869326a82320159a');
      const studentSeesFullDetail = studentHtml.includes('Thanh toán tiền in ấn tài liệu cho bạn') && studentHtml.includes('phục vụ hội thảo học tập K57');
      const studentHasVoteBtn = studentHtml.includes('voteSpend') || studentHtml.includes('executeSpend') || studentHtml.includes('Đồng ý') || studentHtml.includes('Giải ngân');

      // Đăng nhập với chính ví người nhận (Phương Dung) để kiểm tra nhãn "Bạn"
      window.userAddress = '0x78567A377559F0cB30173f93869326a82320159a';
      window.myStudentProfile = { mssv: '23K4300004', name: 'Trần Hoàng Phương Dung', role: 'student' };
      syncRolePermissionsUI('student');
      await loadSpendRequests(1, 3);
      const myOwnHtml = document.getElementById('bcsSpendTableBody')?.innerHTML || '';
      const containsMyTag = myOwnHtml.includes('Bạn');

      // Góc nhìn Ban cán sự khác (Tâm Phúc xem Phương Dung -> thấy đầy đủ họ tên & MSSV & lý do nguyên bản)
      window.userAddress = '0xf5D971952dbDF69058a28D23110381d96B00cb50';
      window.myStudentProfile = { mssv: '23K4300015', name: 'Võ Ngọc Tâm Phúc', role: 'bcs' };
      syncRolePermissionsUI('bcs');
      await loadSpendRequests(1, 3);
      const bcsHtml = document.getElementById('bcsSpendTableBody')?.innerHTML || '';
      const bcsSeesFullName = bcsHtml.includes('Trần Hoàng Phương Dung') && bcsHtml.includes('23K4300004');

      // Kiểm tra ma trận quyền mới
      const newPermChecks = {
        viewSpendProposals: hasPermission('viewSpendProposals', 'student'),
        viewCashflow: hasPermission('viewCashflow', 'student'),
        viewCollections: hasPermission('viewCollections', 'student'),
        viewRefundSummary: hasPermission('viewRefundSummary', 'student'),
        viewRoster: hasPermission('viewRoster', 'student'),
        viewBcsList: hasPermission('viewBcsList', 'student'),
        manageMembers: hasPermission('manageMembers', 'student'),
        advisorAdmin: hasPermission('advisorAdmin', 'student')
      };

      return {
        studentSeesOtherName,
        studentSeesRawMssv,
        studentSeesFull0x,
        studentSeesFullDetail,
        studentHasVoteBtn,
        containsMyTag,
        bcsSeesFullName,
        newPermChecks
      };
    })()
  `);
  console.log("Anonymity & Reason Test:", JSON.stringify(anonymityTest));
  const p = anonymityTest.newPermChecks;
  const permPass = p.viewSpendProposals && p.viewCashflow && p.viewCollections && p.viewRefundSummary &&
    !p.viewRoster && !p.viewBcsList && !p.manageMembers && !p.advisorAdmin;

  if (anonymityTest.studentSeesOtherName || anonymityTest.studentSeesRawMssv || anonymityTest.studentSeesFull0x || !anonymityTest.studentSeesFullDetail || anonymityTest.studentHasVoteBtn || !anonymityTest.containsMyTag || !anonymityTest.bcsSeesFullName || !permPass) {
    console.error("[FAIL] Bảo vệ quyền riêng tư & xem chi tiết lý do chi chưa đạt!");
  } else {
    console.log("[PASS] Sinh viên xem lý do đầy đủ chi tiết, tự động che MSSV/0x người khác; không có nút vote/giải ngân; ma trận ROLE_PERMISSIONS đạt chuẩn 100%.");
  }

  cleanup();
  process.exit(0);
}

run().catch(err => {
  console.error("Test Error:", err);
  process.exit(1);
});
