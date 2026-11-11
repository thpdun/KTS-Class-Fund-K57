/** KIỂM THỬ: trang Về chúng tôi (nhóm phát triển) & nút chat AI tròn - Headless Chrome CDP */
const { spawn } = require('child_process');
const http = require('http');
const path = require('path');
const fs = require('fs');
const os = require('os');
const WebSocket = require('ws');

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const htmlPath = path.resolve(__dirname, '../web/index.html');
const tempProfile = fs.mkdtempSync(path.join(os.tmpdir(), 'chrome-chatfab-'));
const artifactDir = "C:\\Users\\Thao\\.gemini\\antigravity\\brain\\557b14b1-c775-4030-a735-b424fb8812a2";

const getJson = (url) => new Promise((resolve, reject) => {
  http.get(url, (res) => { let d = ''; res.on('data', c => d += c); res.on('end', () => resolve(JSON.parse(d))); }).on('error', reject);
});
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function run() {
  const port = 9227;
  const chrome = spawn(CHROME_PATH, ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${tempProfile}`,
    '--disable-gpu', '--no-first-run', '--allow-file-access-from-files', '--window-size=1920,1080', process.env.BASE_URL || `file://${htmlPath}`]);
  const cleanup = () => { try { chrome.kill(); } catch (e) {} try { fs.rmSync(tempProfile, { recursive: true, force: true }); } catch (e) {} };
  process.on('exit', cleanup);

  let version;
  for (let i = 0; i < 30; i++) { await sleep(250); try { version = await getJson(`http://127.0.0.1:${port}/json/version`); if (version) break; } catch (e) {} }
  if (!version) { console.error('[FAIL] CDP'); process.exit(1); }

  const targets = await getJson(`http://127.0.0.1:${port}/json/list`);
  const ws = new WebSocket((targets.find(t => t.type === 'page') || targets[0]).webSocketDebuggerUrl);
  let id = 1; const pending = new Map(); const errors = [];
  ws.on('message', d => {
    const m = JSON.parse(d.toString());
    if (m.method === 'Runtime.exceptionThrown') errors.push(m.params.exceptionDetails.text + ' ' + (m.params.exceptionDetails.exception?.description || ''));
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') errors.push(m.params.args.map(a => a.value || a.description).join(' '));
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  });
  await new Promise(r => ws.on('open', r));
  const send = (method, params = {}) => new Promise(res => { const i = id++; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
  const ev = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); if (r.result?.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails)); return r.result?.result?.value; };
  const shot = async (name) => { const r = await send('Page.captureScreenshot', { format: 'png' }); fs.writeFileSync(path.join(artifactDir, name), Buffer.from(r.result.data, 'base64')); console.log('[SNAPSHOT]', name); };
  const viewport = (w, h, mobile) => send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile });

  await send('Page.enable'); await send('Runtime.enable');
  for (let i = 0; i < 50; i++) { await sleep(250); try { if (await ev(`typeof syncRolePermissionsUI === 'function'`)) break; } catch (e) {} }

  let pass = true;
  const check = (ok, msg) => { console.log((ok ? '[PASS] ' : '[FAIL] ') + msg); if (!ok) pass = false; };

  for (const [label, vw, vh, mobile] of [['desktop', 1920, 1080, false], ['mobile', 390, 844, true]]) {
    await viewport(vw, vh, mobile);
    for (const [role, addr] of [['student', '0x64ADE1f3E814c98dEFeC19f07253afeBDD2DBfcf'], ['guest', '']]) {
      console.log(`\n--- ${label} / ${role} ---`);
      await ev(`window.userAddress='${addr}'; window.currentVerifiedRole='${role}'; syncRolePermissionsUI('${role}'); navigateToAbout('ve-chung-toi'); true`);
      await sleep(600);
      const about = await ev(`(() => {
        const list = document.querySelector('.dev-team-list');
        const t = list ? list.innerText : '';
        return { text: t, hasPlaceholder: document.body.innerHTML.includes('Chưa cập nhật thông tin nhóm'),
                 hasMssv: /23K\\d{7}/.test(list ? list.innerHTML : ''), has0x: /0x[0-9a-fA-F]{6,}/.test(list ? list.innerHTML : '') };
      })()`);
      check(about.text.includes('Trần Hoàng Phương Dung') && about.text.includes('Võ Ngọc Tâm Phúc'), `Hiển thị đúng 2 tên (${about.text.replace(/\s+/g, ' ')})`);
      check(!about.hasPlaceholder && !about.hasMssv && !about.has0x, 'Không placeholder, không MSSV/ví');
      await ev(`(() => { const y = document.querySelector('.dev-team-list').getBoundingClientRect().top + scrollY - innerHeight / 2; window.scrollTo(0, Math.max(0, y)); return true; })()`);
      await sleep(300);
      await shot(`screenshot_about_team_${role}_${label}.png`);

      const fab = await ev(`(() => { const b = document.getElementById('aiFabToggle'); const r = b.getBoundingClientRect(); const cs = getComputedStyle(b);
        return { w: Math.round(r.width), h: Math.round(r.height), radius: cs.borderRadius, text: b.innerText.trim(), aria: b.getAttribute('aria-label'), title: b.title,
                 bg: cs.backgroundImage, right: Math.round(innerWidth - r.right), bottom: Math.round(innerHeight - r.bottom), badge: document.getElementById('aiFabBadge').className }; })()`);
      console.log('FAB:', JSON.stringify(fab));
      check(fab.w === 56 && fab.h === 56 && fab.text === '' && fab.aria === 'Mở trợ lý AI Quỹ Lớp' && fab.title === 'Hỏi đáp AI Quỹ Lớp', 'Nút chat tròn 56x56, chỉ icon, có aria-label/title');
      check(fab.bg.includes('11, 93, 69'), 'Nền gradient xanh lá');
      if (mobile) check(fab.right === 16 && fab.bottom === 16, 'Cách mép 16px trên mobile');

      await ev(`document.getElementById('aiFabToggle').click(); true`);
      await sleep(500);
      await ev(`(() => { const i = document.getElementById('aiUserInput'); i.value = 'Xin chào'; document.getElementById('aiBtnSend').click(); return true; })()`);
      await sleep(2500);
      const chat = await ev(`(() => ({ open: document.getElementById('aiChatDrawer').classList.contains('open'),
        userMsgs: document.querySelectorAll('.ai-msg-user').length, total: document.querySelectorAll('#aiChatBody .ai-msg').length,
        headerBg: getComputedStyle(document.querySelector('.ai-chat-header')).backgroundImage }))()`);
      console.log('Chat:', JSON.stringify(chat));
      check(chat.open && chat.userMsgs >= 1, 'Mở được khung chat và gửi được tin nhắn');
      check(chat.headerBg.includes('11, 93, 69'), 'Header chat gradient xanh lá');
      await shot(`screenshot_chat_open_${role}_${label}.png`);
      await ev(`document.getElementById('aiBtnClose').click(); document.querySelectorAll('.ai-msg-user').forEach(e=>e.remove()); true`);
    }
  }

  const real = errors.filter(e => !/Failed to fetch|ERR_|CORS|net::|NetworkError|Failed to load resource/i.test(e));
  check(real.length === 0, `Console không lỗi đỏ ${real.length ? JSON.stringify(real) : ''}`);
  console.log(pass ? '\nTẤT CẢ ĐẠT' : '\nCÓ LỖI');
  cleanup();
  process.exit(pass ? 0 : 1);
}
run().catch(e => { console.error(e); process.exit(1); });
