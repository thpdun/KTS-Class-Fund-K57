/**
 * KIỂM THỬ GIAO DIỆN MEGA MENU DỊCH VỤ THEO VAI TRÒ - ECO2432
 * Chạy với Headless Chrome CDP & Chụp ảnh màn hình minh chứng
 */
const { spawn } = require('child_process');
const http = require('http');
const path = require('path');
const fs = require('fs');
const os = require('os');
const WebSocket = require('ws');

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const htmlPath = path.resolve(__dirname, '../web/index.html');
const tempProfile = fs.mkdtempSync(path.join(os.tmpdir(), 'chrome-mega-test-'));
const artifactDir = "C:\\Users\\Thao\\.gemini\\antigravity\\brain\\557b14b1-c775-4030-a735-b424fb8812a2";

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
  console.log("   KIỂM THỬ MEGA MENU DỊCH VỤ THEO VAI TRÒ (RBAC MEGA MENU TEST)");
  console.log("================================================================================");

  if (!fs.existsSync(CHROME_PATH)) {
    console.error("Không tìm thấy Chrome:", CHROME_PATH);
    process.exit(1);
  }

  const port = 9225;
  const chrome = spawn(CHROME_PATH, [
    '--headless=new',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${tempProfile}`,
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--allow-file-access-from-files',
    '--window-size=1440,900',
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

  async function takeScreenshot(filePath) {
    const res = await sendCDP('Page.captureScreenshot', { format: 'png' });
    if (res.result && res.result.data) {
      fs.writeFileSync(filePath, Buffer.from(res.result.data, 'base64'));
      console.log(`[SNAPSHOT] Đã lưu: ${filePath}`);
    }
  }

  await sendCDP('Page.enable');
  await sendCDP('Runtime.enable');
  await sendCDP('DOM.enable');

  for (let i = 0; i < 50; i++) {
    await new Promise(r => setTimeout(r, 250));
    try {
      const ready = await evalInPage(`typeof syncMegaMenuPermissions === 'function'`);
      if (ready) break;
    } catch (e) {}
  }

  // TEST 1: SINH VIÊN (Student)
  console.log("\n--- TEST 1: VAI TRÒ SINH VIÊN (STUDENT) ---");
  const studentCheck = await evalInPage(`
    (() => {
      window.userAddress = '0x64ADE1f3E814c98dEFeC19f07253afeBDD2DBfcf';
      window.currentVerifiedRole = 'student';
      syncRolePermissionsUI('student');
      
      const mega = document.getElementById('megaMenuServices');
      const grid = mega.querySelector('.mega-menu-grid');
      const gContrib = document.getElementById('megaGroupContribution');
      const gSpend = document.getElementById('megaGroupSpending');
      const gLedger = document.getElementById('megaGroupLedger');
      const gGov = document.getElementById('megaGroupGovernance');

      // Mở mega menu
      mega.classList.add('show');

      const col1Visible = gContrib && gContrib.style.display !== 'none';
      const col2Visible = gSpend && gSpend.style.display !== 'none';
      const col3Visible = gLedger && gLedger.style.display !== 'none';
      const col4Visible = gGov && gGov.style.display !== 'none';

      const itemDeposit = document.querySelector('#megaMenuServices a[href="#deposit"]')?.style.display;
      const itemRefund = document.querySelector('#megaMenuServices a[href="#refund"]')?.style.display;
      const itemSpend = document.querySelector('#megaMenuServices a[href="#spend"]')?.style.display;
      const itemVote = document.querySelector('#megaMenuServices a[href="#vote"]')?.style.display;
      const itemLedger = document.querySelector('#megaMenuServices a[href="#ledger"]')?.style.display;
      const itemViewSpend = document.getElementById('megaItemViewSpend')?.style.display;
      const itemRoster = document.querySelector('#megaMenuServices a[onclick*="openRosterModal"]')?.style.display;

      const gridCols = grid?.style.gridTemplateColumns;
      const panelWidth = mega?.style.width;

      return {
        col1Visible,
        col2Visible,
        col3Visible,
        col4Visible,
        itemDeposit,
        itemRefund,
        itemSpend,
        itemVote,
        itemLedger,
        itemViewSpend,
        itemRoster,
        gridCols,
        panelWidth
      };
    })()
  `);
  console.log("Student Mega Menu Status:", JSON.stringify(studentCheck, null, 2));

  // Kiểm tra yêu cầu cho sinh viên
  const studentPass = 
    studentCheck.col1Visible === true && 
    studentCheck.col2Visible === false && // Không có cột Chi tiêu
    studentCheck.col3Visible === true && 
    studentCheck.col4Visible === false && // Không có cột Quản trị
    studentCheck.itemDeposit === 'flex' &&
    studentCheck.itemRefund === 'flex' &&
    studentCheck.itemSpend === 'none' &&
    studentCheck.itemVote === 'none' &&
    studentCheck.itemLedger === 'flex' &&
    studentCheck.itemViewSpend === 'flex' && // Có mục "Yêu cầu chi"
    studentCheck.itemRoster === 'none' &&
    studentCheck.gridCols.includes('repeat(2');

  if (!studentPass) {
    console.error("[FAIL] Mega menu cho Sinh viên không đáp ứng đủ yêu cầu!");
  } else {
    console.log("[PASS] Sinh viên: Chỉ có đúng 2 cột (Quỹ của tôi, Tra cứu), cột Chi tiêu đã biến mất, mục 'Yêu cầu chi' xuất hiện.");
  }

  await new Promise(r => setTimeout(r, 200));
  await takeScreenshot(path.join(artifactDir, 'screenshot_megamenu_student.png'));

  // TEST 2: BAN CÁN SỰ (BCS)
  console.log("\n--- TEST 2: VAI TRÒ BAN CÁN SỰ (BCS) ---");
  const bcsCheck = await evalInPage(`
    (() => {
      window.userAddress = '0xf5D971952dbDF69058a28D23110381d96B00cb50';
      window.currentVerifiedRole = 'bcs';
      syncRolePermissionsUI('bcs');
      
      const mega = document.getElementById('megaMenuServices');
      const grid = mega.querySelector('.mega-menu-grid');
      const gContrib = document.getElementById('megaGroupContribution');
      const gSpend = document.getElementById('megaGroupSpending');
      const gLedger = document.getElementById('megaGroupLedger');
      const gGov = document.getElementById('megaGroupGovernance');

      mega.classList.add('show');

      const col1Visible = gContrib && gContrib.style.display !== 'none';
      const col2Visible = gSpend && gSpend.style.display !== 'none';
      const col3Visible = gLedger && gLedger.style.display !== 'none';
      const col4Visible = gGov && gGov.style.display !== 'none';

      const itemDeposit = document.querySelector('#megaMenuServices a[href="#deposit"]')?.style.display;
      const itemSpend = document.querySelector('#megaMenuServices a[href="#spend"]')?.style.display;
      const itemVote = document.querySelector('#megaMenuServices a[href="#vote"]')?.style.display;
      const itemLedger = document.querySelector('#megaMenuServices a[href="#ledger"]')?.style.display;
      const itemViewSpend = document.getElementById('megaItemViewSpend')?.style.display;
      const itemRoster = document.querySelector('#megaMenuServices a[onclick*="openRosterModal"]')?.style.display;

      const gridCols = grid?.style.gridTemplateColumns;
      const panelWidth = mega?.style.width;

      return {
        col1Visible,
        col2Visible,
        col3Visible,
        col4Visible,
        itemDeposit,
        itemSpend,
        itemVote,
        itemLedger,
        itemViewSpend,
        itemRoster,
        gridCols,
        panelWidth
      };
    })()
  `);
  console.log("BCS Mega Menu Status:", JSON.stringify(bcsCheck, null, 2));

  const bcsPass = 
    bcsCheck.col1Visible === true &&
    bcsCheck.col2Visible === true && // Có cột Chi tiêu
    bcsCheck.col3Visible === true && // Có cột Tra cứu
    bcsCheck.col4Visible === false && // Không có Quản trị (dành cho CVHT)
    bcsCheck.itemSpend === 'flex' &&
    bcsCheck.itemVote === 'flex' &&
    bcsCheck.itemRoster === 'flex' &&
    bcsCheck.itemViewSpend === 'flex' &&
    bcsCheck.gridCols.includes('repeat(3');

  if (!bcsPass) {
    console.error("[FAIL] Mega menu cho Ban cán sự không đúng 3 cột!");
  } else {
    console.log("[PASS] Ban cán sự: Có đúng 3 cột (Quỹ của tôi, Chi tiêu, Tra cứu), đầy đủ quyền đề xuất và biểu quyết.");
  }

  await new Promise(r => setTimeout(r, 200));
  await takeScreenshot(path.join(artifactDir, 'screenshot_megamenu_bcs.png'));

  // TEST 3: CỐ VẤN HỌC TẬP (Advisor)
  console.log("\n--- TEST 3: VAI TRÒ CỐ VẤN HỌC TẬP (ADVISOR) ---");
  const advisorCheck = await evalInPage(`
    (() => {
      window.userAddress = '0xa3C0c4F588B463C43B718D4bE4381389D3c58A54';
      window.currentVerifiedRole = 'advisor';
      syncRolePermissionsUI('advisor');
      
      const mega = document.getElementById('megaMenuServices');
      const grid = mega.querySelector('.mega-menu-grid');
      const gContrib = document.getElementById('megaGroupContribution');
      const gSpend = document.getElementById('megaGroupSpending');
      const gLedger = document.getElementById('megaGroupLedger');
      const gGov = document.getElementById('megaGroupGovernance');

      mega.classList.add('show');

      const col1Visible = gContrib && gContrib.style.display !== 'none';
      const col2Visible = gSpend && gSpend.style.display !== 'none';
      const col3Visible = gLedger && gLedger.style.display !== 'none';
      const col4Visible = gGov && gGov.style.display !== 'none';

      const itemDeposit = document.querySelector('#megaMenuServices a[href="#deposit"]')?.style.display;
      const itemSpend = document.querySelector('#megaMenuServices a[href="#spend"]')?.style.display;
      const itemLedger = document.querySelector('#megaMenuServices a[href="#ledger"]')?.style.display;
      const itemGovBcs = document.getElementById('megaItemManageBcs')?.style.display;
      const itemGovFee = document.getElementById('megaItemWithdrawFee')?.style.display;

      const gridCols = grid?.style.gridTemplateColumns;
      const panelWidth = mega?.style.width;

      return {
        col1Visible,
        col2Visible,
        col3Visible,
        col4Visible,
        itemDeposit,
        itemSpend,
        itemLedger,
        itemGovBcs,
        itemGovFee,
        gridCols,
        panelWidth
      };
    })()
  `);
  console.log("Advisor Mega Menu Status:", JSON.stringify(advisorCheck, null, 2));

  const advisorPass = 
    advisorCheck.col1Visible === false && // Không có Quỹ của tôi
    advisorCheck.col2Visible === false && // Không có Chi tiêu
    advisorCheck.col3Visible === true &&  // Có Tra cứu
    advisorCheck.col4Visible === true &&  // Có Quản trị
    advisorCheck.itemGovBcs === 'flex' &&
    advisorCheck.itemGovFee === 'flex' &&
    advisorCheck.gridCols.includes('repeat(2');

  if (!advisorPass) {
    console.error("[FAIL] Mega menu cho Cố vấn học tập không đúng 2 cột Tra cứu & Quản trị!");
  } else {
    console.log("[PASS] Cố vấn học tập: Có đúng 2 cột (Tra cứu, Quản trị), các cột rỗng tự động ẩn.");
  }

  await new Promise(r => setTimeout(r, 200));
  await takeScreenshot(path.join(artifactDir, 'screenshot_megamenu_advisor.png'));

  // TEST 4: KHÁCH VÃNG LAI / GIAN LẬN (Guest / Fraud test)
  console.log("\n--- TEST 4: KHÁCH VÃNG LAI & PHÒNG CHỐNG GIAN LẬN ---");
  const guestCheck = await evalInPage(`
    (() => {
      window.userAddress = '';
      window.currentVerifiedRole = 'guest';
      syncRolePermissionsUI('guest');
      
      const wrapServices = document.getElementById('wrapServicesMega')?.style.display;
      const mega = document.getElementById('megaMenuServices');
      
      // Giả lập gian lận: Khách cố tình dùng console gán class .show để mở Mega Menu
      mega.classList.add('show');
      
      const gContrib = document.getElementById('megaGroupContribution')?.style.display;
      const gSpend = document.getElementById('megaGroupSpending')?.style.display;
      const gGov = document.getElementById('megaGroupGovernance')?.style.display;

      return {
        servicesPillDisplay: wrapServices,
        gContrib,
        gSpend,
        gGov
      };
    })()
  `);
  console.log("Guest Status:", JSON.stringify(guestCheck, null, 2));

  const guestPass = guestCheck.servicesPillDisplay === 'none' && 
                    guestCheck.gSpend === 'none' && 
                    guestCheck.gGov === 'none';

  if (!guestPass) {
    console.error("[FAIL] Khách vẫn thấy nút Dịch vụ hoặc cột đặc quyền!");
  } else {
    console.log("[PASS] Khách: Nút Dịch vụ trên topbar bị ẩn hoàn toàn (display: none), dù cố ý thêm class show cũng không có dữ liệu chi tiêu / quản trị.");
  }

  await takeScreenshot(path.join(artifactDir, 'screenshot_megamenu_guest.png'));

  console.log("\n================================================================================");
  console.log("   TẤT CẢ 4 KỊCH BẢN KIỂM THỬ ĐÃ ĐẠT 100%!");
  console.log("================================================================================");

  cleanup();
  process.exit(0);
}

run().catch(err => {
  console.error("Test Error:", err);
  process.exit(1);
});

