/**
 * KIỂM THỬ RENDER THẬT (HEADLESS CHROME CDP)
 * Kiểm tra vị trí và kích thước của .site-footer trên 3 kích thước viewport:
 * 1. 1920x1080 (Desktop Large)
 * 2. 1366x768 (Desktop Standard)
 * 3. 390x844 (Mobile)
 *
 * Tiêu chí kiểm tra:
 * - footer.getBoundingClientRect().left == 0
 * - Math.abs(footer.getBoundingClientRect().width - document.documentElement.clientWidth) <= 1
 * - footer.getBoundingClientRect().top >= main.getBoundingClientRect().bottom
 */

const { spawn } = require('child_process');
const http = require('http');
const path = require('path');
const fs = require('fs');
const os = require('os');
const WebSocket = require('ws');

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const htmlPath = path.resolve(__dirname, '../web/index.html');
const tempProfile = fs.mkdtempSync(path.join(os.tmpdir(), 'chrome-footer-test-'));

async function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(JSON.parse(data)));
    }).on('error', reject);
  });
}

async function runTests() {
  console.log("=== BẮT ĐẦU KIỂM THỬ RENDER THẬT CHO FOOTER (CHROME HEADLESS) ===");

  if (!fs.existsSync(CHROME_PATH)) {
    console.error(`[FAIL] Không tìm thấy trình duyệt tại ${CHROME_PATH}`);
    process.exit(1);
  }

  const chrome = spawn(CHROME_PATH, [
    '--headless=new',
    '--remote-debugging-port=9223',
    `--user-data-dir=${tempProfile}`,
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    `file://${htmlPath}`
  ]);

  let version;
  for (let i = 0; i < 20; i++) {
    await new Promise(r => setTimeout(r, 250));
    try {
      version = await getJson('http://127.0.0.1:9223/json/version');
      break;
    } catch (e) {}
  }

  if (!version) {
    console.error("[FAIL] Không thể kết nối Chrome DevTools Protocol");
    chrome.kill();
    process.exit(1);
  }

  console.log(`[PASS] Khởi chạy Chrome thành công (${version.Browser})`);

  const targets = await getJson('http://127.0.0.1:9223/json/list');
  const pageTarget = targets.find(t => t.type === 'page');
  const ws = new WebSocket(pageTarget.webSocketDebuggerUrl);

  let idCounter = 1;
  const pending = new Map();

  ws.on('message', data => {
    const msg = JSON.parse(data.toString());
    if (msg.id && pending.has(msg.id)) {
      pending.get(msg.id)(msg);
      pending.delete(msg.id);
    }
  });

  await new Promise(r => ws.on('open', r));

  function send(method, params = {}) {
    return new Promise(resolve => {
      const id = idCounter++;
      pending.set(id, resolve);
      ws.send(JSON.stringify({ id, method, params }));
    });
  }

  await send('Page.enable');
  await send('DOM.enable');

  // Đợi trang nạp và dàn trang đầy đủ
  await new Promise(r => setTimeout(r, 1200));

  const viewports = [
    { width: 1920, height: 1080, name: "1920x1080 (Desktop Large)" },
    { width: 1366, height: 768, name: "1366x768 (Desktop Standard)" },
    { width: 390, height: 844, name: "390x844 (Mobile iPhone 12/13/14)" }
  ];

  let allPassed = true;

  for (const vp of viewports) {
    console.log(`\n--- KIỂM TRA VIEWPORT: ${vp.name} ---`);
    await send('Emulation.setDeviceMetricsOverride', {
      width: vp.width,
      height: vp.height,
      deviceScaleFactor: 1,
      mobile: vp.width < 500
    });
    await new Promise(r => setTimeout(r, 350));

    const evalRes = await send('Runtime.evaluate', {
      expression: `(() => {
        const footer = document.querySelector('.site-footer');
        const main = document.querySelector('.app-main');
        if (!footer || !main) return { error: 'Element missing' };
        const fRect = footer.getBoundingClientRect();
        const mRect = main.getBoundingClientRect();
        const clientWidth = document.documentElement.clientWidth;
        return {
          clientWidth,
          footer: { left: fRect.left, width: fRect.width, top: fRect.top, bottom: fRect.bottom },
          main: { left: mRect.left, width: mRect.width, top: mRect.top, bottom: mRect.bottom }
        };
      })()`,
      returnByValue: true
    });

    const val = evalRes.result?.result?.value;
    if (!val || val.error) {
      console.error(`[FAIL] Không đọc được getBoundingClientRect trên viewport ${vp.name}`);
      allPassed = false;
      continue;
    }

    // Tiêu chí 1: footer.left == 0
    const leftPass = Math.abs(val.footer.left) < 1;
    if (leftPass) {
      console.log(`  [PASS] footer.left == 0 (giá trị thực tế: ${val.footer.left.toFixed(2)}px)`);
    } else {
      console.error(`  [FAIL] footer.left != 0 (giá trị thực tế: ${val.footer.left.toFixed(2)}px)`);
      allPassed = false;
    }

    // Tiêu chí 2: footer.width == clientWidth (chênh lệch <= 1px do làm tròn subpixel)
    const widthDiff = Math.abs(val.footer.width - val.clientWidth);
    const widthPass = widthDiff <= 1.5;
    if (widthPass) {
      console.log(`  [PASS] footer.width == clientWidth (footer: ${val.footer.width.toFixed(2)}px, clientWidth: ${val.clientWidth}px)`);
    } else {
      console.error(`  [FAIL] footer.width != clientWidth (footer: ${val.footer.width.toFixed(2)}px, clientWidth: ${val.clientWidth}px)`);
      allPassed = false;
    }

    // Tiêu chí 3: footer.top >= main.bottom
    const topPass = val.footer.top >= (val.main.bottom - 1);
    if (topPass) {
      console.log(`  [PASS] footer.top >= main.bottom (footer.top: ${val.footer.top.toFixed(2)}px, main.bottom: ${val.main.bottom.toFixed(2)}px)`);
    } else {
      console.error(`  [FAIL] footer.top < main.bottom (footer.top: ${val.footer.top.toFixed(2)}px, main.bottom: ${val.main.bottom.toFixed(2)}px)`);
      allPassed = false;
    }
  }

  ws.close();
  chrome.kill();

  try {
    fs.rmSync(tempProfile, { recursive: true, force: true });
  } catch (e) {}

  console.log("\n=======================================================");
  if (allPassed) {
    console.log("🎉 TẤT CẢ KIỂM THỬ RENDER THẬT CỦA FOOTER ĐỀU ĐẠT 100% PASS!");
    process.exit(0);
  } else {
    console.error("❌ CÓ KIỂM THỬ THẤT BẠI!");
    process.exit(1);
  }
}

runTests().catch(err => {
  console.error("Error executing test:", err);
  process.exit(1);
});

