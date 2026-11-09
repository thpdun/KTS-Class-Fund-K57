const { spawn } = require('child_process');
const http = require('http');
const path = require('path');
const fs = require('fs');
const os = require('os');
const WebSocket = require('ws');

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const htmlPath = path.resolve(__dirname, '../web/index.html');
const tempProfile = fs.mkdtempSync(path.join(os.tmpdir(), 'chrome-cdp-'));

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
  const chrome = spawn(CHROME_PATH, [
    '--headless=new',
    '--remote-debugging-port=9222',
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
      version = await getJson('http://127.0.0.1:9222/json/version');
      break;
    } catch (e) {}
  }

  if (!version) {
    console.error("Could not connect to Chrome CDP");
    chrome.kill();
    return;
  }

  const targets = await getJson('http://127.0.0.1:9222/json/list');
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

  // Let page load
  await new Promise(r => setTimeout(r, 1000));

  // Check parent chain & computed styles
  const diagRes = await send('Runtime.evaluate', {
    expression: `(() => {
      const footer = document.querySelector('.site-footer');
      if (!footer) return { error: 'footer not found' };
      const parents = [];
      let cur = footer.parentElement;
      while (cur) {
        const cs = window.getComputedStyle(cur);
        parents.push({
          tag: cur.tagName.toLowerCase(),
          id: cur.id,
          className: cur.className,
          display: cs.display,
          flexDirection: cs.flexDirection,
          flexWrap: cs.flexWrap,
          gridTemplateColumns: cs.gridTemplateColumns
        });
        cur = cur.parentElement;
      }
      return { parents };
    })()`,
    returnByValue: true
  });

  console.log("=== DIAGNOSTIC OF <footer> PARENTS IN REAL CHROME ===");
  console.log(JSON.stringify(diagRes.result?.result?.value || diagRes, null, 2));

  // Test across 3 viewports: 1920x1080, 1366x768, 390x844
  const viewports = [
    { width: 1920, height: 1080, name: "1920x1080 (Desktop Large)" },
    { width: 1366, height: 768, name: "1366x768 (Desktop Standard)" },
    { width: 390, height: 844, name: "390x844 (Mobile iPhone 12/13/14)" }
  ];

  console.log("\n=== TESTING CURRENT VIEWPORT MEASUREMENTS ===");
  for (const vp of viewports) {
    await send('Emulation.setDeviceMetricsOverride', {
      width: vp.width,
      height: vp.height,
      deviceScaleFactor: 1,
      mobile: vp.width < 500
    });
    await new Promise(r => setTimeout(r, 300));

    const evalRes = await send('Runtime.evaluate', {
      expression: `(() => {
        const footer = document.querySelector('.site-footer');
        const main = document.querySelector('.app-main');
        const fRect = footer.getBoundingClientRect();
        const mRect = main ? main.getBoundingClientRect() : null;
        return {
          clientWidth: document.documentElement.clientWidth,
          footer: {
            left: fRect.left,
            width: fRect.width,
            top: fRect.top,
            bottom: fRect.bottom
          },
          main: mRect ? {
            left: mRect.left,
            width: mRect.width,
            top: mRect.top,
            bottom: mRect.bottom
          } : null
        };
      })()`,
      returnByValue: true
    });
    console.log(`Viewport ${vp.name}:`, JSON.stringify(evalRes.result?.result?.value || evalRes, null, 2));
  }

  ws.close();
  chrome.kill();
}

run().catch(console.error);
