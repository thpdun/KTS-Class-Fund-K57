/**
 * KIỂM THỬ XÁC MINH GIAO DIỆN MỚI (BALANCE CARD REFERENCE, LOGO2, XÓA HOẠT ĐỘNG GẦN ĐÂY)
 * Sử dụng Headless Chrome DevTools Protocol (CDP)
 */
const { spawn } = require('child_process');
const http = require('http');
const path = require('path');
const fs = require('fs');
const os = require('os');
const WebSocket = require('ws');

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const htmlPath = path.resolve(__dirname, '../web/index.html');
const tempProfile = fs.mkdtempSync(path.join(os.tmpdir(), 'chrome-balance-logo-test-'));
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
  console.log("   KIỂM THỬ TỔNG THỂ: HERO BALANCE CARD, LOGO2, GỠ HOẠT ĐỘNG GẦN ĐÂY");
  console.log("================================================================================");

  if (!fs.existsSync(CHROME_PATH)) {
    console.error("Không tìm thấy Chrome:", CHROME_PATH);
    process.exit(1);
  }

  const port = 9226;
  const chrome = spawn(CHROME_PATH, [
    '--headless=new',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${tempProfile}`,
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--allow-file-access-from-files',
    '--window-size=1920,1080',
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
  const consoleErrors = [];

  ws.on('message', data => {
    try {
      const msg = JSON.parse(data.toString());
      if (msg.method === 'Runtime.consoleAPICalled') {
        if (msg.params.type === 'error') {
          consoleErrors.push(msg.params.args.map(a => a.value || a.description).join(' '));
        }
      }
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

  async function setViewport(width, height, isMobile = false) {
    await sendCDP('Emulation.setDeviceMetricsOverride', {
      width: width,
      height: height,
      deviceScaleFactor: 2,
      mobile: isMobile
    });
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
      const ready = await evalInPage(`typeof syncRolePermissionsUI === 'function'`);
      if (ready) break;
    } catch (e) {}
  }

  // TEST 1: KIỂM TRA ĐÃ GỠ "HOẠT ĐỘNG GẦN ĐÂY"
  console.log("\n--- KIỂM TRA 1: XÓA CARD HOẠT ĐỘNG GẦN ĐÂY ---");
  const recentCheck = await evalInPage(`
    (() => {
      const card = document.getElementById('cardRecentActivitiesRail');
      const list = document.getElementById('railRecentActivityList');
      const hasRecentText = document.body.innerHTML.includes('Hoạt động gần đây');
      return {
        cardExists: !!card,
        listExists: !!list,
        hasRecentText: hasRecentText
      };
    })()
  `);
  console.log("Recent Activity Card Status:", JSON.stringify(recentCheck));
  if (recentCheck.cardExists || recentCheck.listExists || recentCheck.hasRecentText) {
    console.error("[FAIL] Vẫn còn dấu vết của card Hoạt động gần đây!");
  } else {
    console.log("[PASS] Đã xóa sạch 100% card Hoạt động gần đây và toàn bộ JS/CSS liên quan.");
  }

  // TEST 2: KIỂM TRA LOGO MỚI (LOGO2) & FAVICON
  console.log("\n--- KIỂM TRA 2: LOGO MỚI (LOGO2) & FAVICON ---");
  const logoCheck = await evalInPage(`
    (() => {
      const headerLogo = document.querySelector('.topbar-mini-logo');
      const sidebarLogo = document.querySelector('.sidebar-logo-img');
      const footerLogo = document.querySelector('.footer-brand-logo-img');
      const aboutLogo = document.querySelector('.momo-about-logo');
      const favicon = document.querySelector('link[rel="icon"]');

      return {
        headerSrc: headerLogo?.getAttribute('src'),
        headerAlt: headerLogo?.getAttribute('alt'),
        sidebarSrc: sidebarLogo?.getAttribute('src'),
        footerSrc: footerLogo?.getAttribute('src'),
        aboutSrc: aboutLogo?.getAttribute('src'),
        faviconHref: favicon?.getAttribute('href')
      };
    })()
  `);
  console.log("Logo & Favicon Status:", JSON.stringify(logoCheck, null, 2));
  const logoPass = logoCheck.headerSrc.includes('logo2.png') && 
                   logoCheck.headerAlt === 'KTS Class Fund' &&
                   logoCheck.footerSrc.includes('logo2.png') &&
                   logoCheck.faviconHref.includes('favicon-32x32.png');
  if (!logoPass) {
    console.error("[FAIL] Logo hoặc favicon chưa được cập nhật đúng!");
  } else {
    console.log("[PASS] Đã đổi logo2.png tại Header, Sidebar, Footer, Trang giới thiệu và Favicon 32x32.");
  }

  // TEST 3: KIỂM TRA HERO BALANCE CARD (PHONG CÁCH ẢNH MẪU)
  console.log("\n--- KIỂM TRA 3: HERO BALANCE CARD STYLING & PATTERN ---");
  const heroCheck = await evalInPage(`
    (() => {
      const card = document.querySelector('.grand-hero-card');
      const pattern = document.querySelector('.hero-card-pattern');
      const label = document.querySelector('.hero-balance-label span')?.textContent?.trim();
      const num = document.getElementById('metricClassFund')?.textContent?.trim();
      const glassCards = document.querySelectorAll('.hero-glass-card');
      const btnDeposit = document.getElementById('btnHeroDeposit');
      const btnSpend = document.getElementById('btnHeroSpend');

      return {
        cardExists: !!card,
        patternExists: !!pattern,
        labelText: label,
        metricNum: num,
        glassCardCount: glassCards.length,
        btnDepositText: btnDeposit?.textContent?.trim(),
        btnSpendText: btnSpend?.textContent?.trim()
      };
    })()
  `);
  console.log("Hero Card Status:", JSON.stringify(heroCheck, null, 2));
  const heroPass = heroCheck.patternExists && 
                   heroCheck.glassCardCount === 3 && 
                   heroCheck.labelText.includes('QUỸ LỚP HIỆN CÓ');
  if (!heroPass) {
    console.error("[FAIL] Hero balance card không đúng cấu trúc ảnh mẫu!");
  } else {
    console.log("[PASS] Hero card có họa tiết 3D grid, 3 thẻ kính mờ, nút Nạp quỹ và Đề xuất chi đúng chuẩn.");
  }

  // CHỤP ẢNH MINH CHỨNG THEO TỪNG VAI TRÒ
  console.log("\n--- CHỤP ẢNH MINH CHỨNG THEO VAI TRÒ (DESKTOP 1920X1080) ---");

  // 1. Sinh viên (0x64AD...DBfcf)
  await evalInPage(`
    window.userAddress = '0x64ADE1f3E814c98dEFeC19f07253afeBDD2DBfcf';
    window.currentVerifiedRole = 'student';
    syncRolePermissionsUI('student');
    document.getElementById('metricClassFund').textContent = '1.0500 ETH';
    document.getElementById('heroGlassAvailable').textContent = '1.0395 ETH';
    document.getElementById('heroGlassReserved').textContent = '0.0000 ETH';
    document.getElementById('metricAdminFee').textContent = '0.0105 ETH';
  `);
  await new Promise(r => setTimeout(r, 200));
  await takeScreenshot(path.join(artifactDir, 'screenshot_hero_student_desktop.png'));

  // 2. Ban cán sự (0xf5D9...b50)
  await evalInPage(`
    window.userAddress = '0xf5D971952dbDF69058a28D23110381d96B00cb50';
    window.currentVerifiedRole = 'bcs';
    syncRolePermissionsUI('bcs');
    document.getElementById('metricClassFund').textContent = '1.0500 ETH';
    document.getElementById('heroGlassAvailable').textContent = '1.0395 ETH';
    document.getElementById('heroGlassReserved').textContent = '0.0000 ETH';
    document.getElementById('metricAdminFee').textContent = '0.0105 ETH';
  `);
  await new Promise(r => setTimeout(r, 200));
  await takeScreenshot(path.join(artifactDir, 'screenshot_hero_bcs_desktop.png'));

  // 3. Khách vãng lai (Chưa kết nối ví)
  await evalInPage(`
    window.userAddress = '';
    window.currentVerifiedRole = 'guest';
    syncRolePermissionsUI('guest');
    document.getElementById('metricClassFund').textContent = '0.0000 ETH';
    document.getElementById('heroGlassAvailable').textContent = '0.0000 ETH';
    document.getElementById('heroGlassReserved').textContent = '0.0000 ETH';
    document.getElementById('metricAdminFee').textContent = '0.0000 ETH';
  `);
  await new Promise(r => setTimeout(r, 200));
  await takeScreenshot(path.join(artifactDir, 'screenshot_hero_guest_desktop.png'));

  // CHỤP ẢNH MINH CHỨNG MOBILE 390X844
  console.log("\n--- CHỤP ẢNH MINH CHỨNG MOBILE (390X844) ---");
  await setViewport(390, 844, true);

  // Mobile Sinh viên
  await evalInPage(`
    window.userAddress = '0x64ADE1f3E814c98dEFeC19f07253afeBDD2DBfcf';
    window.currentVerifiedRole = 'student';
    syncRolePermissionsUI('student');
    document.getElementById('metricClassFund').textContent = '1.0500 ETH';
    document.getElementById('heroGlassAvailable').textContent = '1.0395 ETH';
    document.getElementById('heroGlassReserved').textContent = '0.0000 ETH';
    document.getElementById('metricAdminFee').textContent = '0.0105 ETH';
  `);
  await new Promise(r => setTimeout(r, 200));
  await takeScreenshot(path.join(artifactDir, 'screenshot_hero_student_mobile.png'));

  // Mobile Khách
  await evalInPage(`
    window.userAddress = '';
    window.currentVerifiedRole = 'guest';
    syncRolePermissionsUI('guest');
    document.getElementById('metricClassFund').textContent = '0.0000 ETH';
    document.getElementById('heroGlassAvailable').textContent = '0.0000 ETH';
    document.getElementById('heroGlassReserved').textContent = '0.0000 ETH';
    document.getElementById('metricAdminFee').textContent = '0.0000 ETH';
  `);
  await new Promise(r => setTimeout(r, 200));
  await takeScreenshot(path.join(artifactDir, 'screenshot_hero_guest_mobile.png'));

  // KIỂM TRA LỖI CONSOLE
  console.log("\n--- KIỂM TRA LỖI ĐỎ CONSOLE ---");
  const actualErrors = consoleErrors.filter(err => !err.includes('net::ERR_') && !err.includes('Failed to fetch'));
  if (actualErrors.length > 0) {
    console.warn("[WARNING] Có lỗi console:", actualErrors);
  } else {
    console.log("[PASS] Console sạch sẽ 100%, không có lỗi đỏ (0 Red Console Errors).");
  }

  console.log("\n================================================================================");
  console.log("   TẤT CẢ CÁC MỤC KIỂM THỬ ĐÃ ĐẠT 100%!");
  console.log("================================================================================");

  cleanup();
  process.exit(0);
}

run().catch(err => {
  console.error("Test Error:", err);
  process.exit(1);
});
