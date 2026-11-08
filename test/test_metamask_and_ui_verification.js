/**
 * Comprehensive Verification Test: MetaMask Connection, Syntax & Detail Modal
 * KTS-Class-Fund-K57
 */
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

(async () => {
  console.log("=== BẮT ĐẦU KIỂM TRA BẮT BUỘC SAU KHI SỬA LỖI SYNTAXERROR ===");

  // -------------------------------------------------------------
  // PHẦN A: KIỂM TRA CÚ PHÁP TOÀN BỘ SCRIPT TRONG web/index.html
  // -------------------------------------------------------------
  console.log("\n--- [A. KIỂM TRA CÚ PHÁP TẤT CẢ SCRIPT] ---");
  const html = fs.readFileSync('web/index.html', 'utf8');
  const scriptRegex = /<script\b[^>]*>([\s\S]*?)<\/script>/gi;
  let match;
  let scriptIdx = 0;
  let syntaxErrors = [];

  while ((match = scriptRegex.exec(html)) !== null) {
    scriptIdx++;
    const code = match[1];
    if (!code.trim()) continue;
    try {
      new vm.Script(code);
      console.log(`  ✓ Script ${scriptIdx}: SYNTAX OK (${code.length} bytes)`);
    } catch (err) {
      syntaxErrors.push({ scriptIdx, err });
      console.error(`  ✗ Script ${scriptIdx}: LỖI CÚ PHÁP ->`, err.message);
    }
  }

  assert.strictEqual(syntaxErrors.length, 0, "Không được có bất kỳ lỗi cú pháp nào trong các thẻ <script>!");
  console.log("  ==> KẾT QUẢ PHẦN A: 100% CÁC SCRIPT ĐẠT CHUẨN CÚ PHÁP JAVASCRIPT (PASS)");

  // -------------------------------------------------------------
  // PHẦN B: KIỂM TRA KẾT NỐI VÍ & KHỞI TẠO DOMCONTENTLOADED
  // -------------------------------------------------------------
  console.log("\n--- [B. KIỂM TRA KHỞI TẠO & SỰ KIỆN KẾT NỐI VÍ] ---");

  class FakeElement {
    constructor(id, tagName = 'div') {
      this.id = id;
      this.tagName = tagName;
      this.style = { display: '' };
      this.classList = {
        classes: new Set(),
        add: function(c) { this.classes.add(c); },
        remove: function(c) { this.classes.delete(c); },
        contains: function(c) { return this.classes.has(c); },
        toggle: function(c, force) {
          if (force === undefined) {
            if (this.classes.has(c)) this.classes.delete(c); else this.classes.add(c);
          } else if (force) this.classes.add(c); else this.classes.delete(c);
        }
      };
      this.textContent = '';
      this.innerHTML = '';
      this.value = '';
      this.eventListeners = {};
    }
    appendChild(c) {}
    addEventListener(event, handler) {
      if (!this.eventListeners[event]) this.eventListeners[event] = [];
      this.eventListeners[event].push(handler);
    }
    click() {
      if (this.eventListeners['click']) {
        for (const h of this.eventListeners['click']) {
          h({ target: this, preventDefault: () => {} });
        }
      }
    }
  }

  const domElements = {};
  function getEl(id) {
    if (!domElements[id]) {
      domElements[id] = new FakeElement(id);
    }
    return domElements[id];
  }

  const windowListeners = {};
  let ethereumListeners = {};

  const mockEthereum = {
    isMetaMask: true,
    request: async ({ method, params }) => {
      if (method === 'eth_accounts') return ['0x85ac8f0ca75f2e3fda073bc566659c011208da74'];
      if (method === 'eth_requestAccounts') return ['0x85ac8f0ca75f2e3fda073bc566659c011208da74'];
      return null;
    },
    on: (event, handler) => {
      ethereumListeners[event] = handler;
    }
  };

  const fakeWindow = {
    ethereum: mockEthereum,
    location: { protocol: 'http:', reload: () => {} },
    innerWidth: 1200,
    addEventListener: (event, handler) => {
      if (!windowListeners[event]) windowListeners[event] = [];
      windowListeners[event].push(handler);
    }
  };

  const fakeDocument = {
    getElementById: getEl,
    createElement: (tag) => new FakeElement("elem-" + Date.now(), tag),
    querySelectorAll: () => [],
    addEventListener: (event, handler) => {
      if (!windowListeners[event]) windowListeners[event] = [];
      windowListeners[event].push(handler);
    }
  };

  // Fake ethers
  const fakeEthers = {
    isAddress: (a) => typeof a === 'string' && a.startsWith('0x') && a.length === 42,
    BrowserProvider: class {
      constructor(eth) { this.eth = eth; }
      send(method, params) { return this.eth.request({ method, params }); }
      getSigner() { return Promise.resolve({ getAddress: () => '0x85ac8f0ca75f2e3fda073bc566659c011208da74' }); }
      getNetwork() { return Promise.resolve({ chainId: 11155111n }); }
    },
    JsonRpcProvider: class {
      constructor(url) {}
    }
  };

  // Set up sandbox context
  const sandbox = {
    window: fakeWindow,
    document: fakeDocument,
    localStorage: {
      data: {},
      getItem: (k) => sandbox.localStorage.data[k] || null,
      setItem: (k, v) => { sandbox.localStorage.data[k] = String(v); },
      removeItem: (k) => { delete sandbox.localStorage.data[k]; }
    },
    ethers: fakeEthers,
    console: console,
    setTimeout: setTimeout,
    clearTimeout: clearTimeout,
    fetch: async () => ({ ok: true, json: async () => ({ success: true }) }),
    alert: (msg) => {},
    escapeHtml: (s) => s || '',
    logToTerminal: () => {}
  };
  sandbox.global = sandbox;
  sandbox.window.window = sandbox.window;
  sandbox.window.document = fakeDocument;

  const ctx = vm.createContext(sandbox);

  // Execute the main script (Script 2)
  let mainScriptMatch = html.match(/<script\b[^>]*>([\s\S]*?)<\/script>/gi);
  let mainScriptCode = mainScriptMatch[1].replace(/<\/?script\b[^>]*>/gi, '');

  vm.runInContext(mainScriptCode, ctx);

  console.log("  ✓ Main script nạp vào context VM thành công không lỗi.");

  // 1. Kiểm tra DOMContentLoaded listener đã đăng ký
  assert.ok(windowListeners['DOMContentLoaded'] && windowListeners['DOMContentLoaded'].length > 0, "Phải có listener cho DOMContentLoaded");
  console.log("  ✓ window.addEventListener('DOMContentLoaded') đã được đăng ký thành công.");

  // 2. Kích hoạt DOMContentLoaded
  console.log("  -> Kích hoạt sự kiện DOMContentLoaded...");
  for (const handler of windowListeners['DOMContentLoaded']) {
    handler();
  }

  // Chờ initWeb3() hoàn thành
  await ctx.initWeb3();

  // 3. Kiểm tra nút btnConnectWallet đã có click handler
  const btnConnect = domElements['btnConnectWallet'];
  assert.ok(btnConnect, "Nút #btnConnectWallet phải tồn tại trong DOM");
  assert.ok(btnConnect.eventListeners['click'] && btnConnect.eventListeners['click'].length > 0, "Nút #btnConnectWallet PHẢI có click event listener");
  console.log("  ✓ Nút #btnConnectWallet đã được gán sự kiện click thành công!");

  // 4. Kiểm tra initWeb3 đã được thực thi và gán listener vào window.ethereum
  assert.ok(ethereumListeners['accountsChanged'], "window.ethereum.on('accountsChanged') phải được đăng ký");
  assert.ok(ethereumListeners['chainChanged'], "window.ethereum.on('chainChanged') phải được đăng ký");
  console.log("  ✓ initWeb3() đã chạy và đăng ký thành công listener accountsChanged & chainChanged trên window.ethereum.");

  // 5. Kiểm tra hàm connectWallet được gắn trực tiếp vào sự kiện click của nút
  const clickHandler = btnConnect.eventListeners['click'][0];
  assert.ok(clickHandler, "Phải có hàm xử lý sự kiện click");
  assert.strictEqual(clickHandler.name, "connectWallet", "Sự kiện click phải liên kết chính xác với hàm connectWallet");
  console.log("  ✓ Sự kiện click của nút #btnConnectWallet đã liên kết đúng 100% với hàm connectWallet.");
  console.log("  ==> KẾT QUẢ PHẦN B: KẾT NỐI VÍ HOÀN TOÀN ĐƯỢC PHỤC HỒI (PASS)");

  // -------------------------------------------------------------
  // PHẦN C: KIỂM TRA HÀM viewAnnouncementDetail(id)
  // -------------------------------------------------------------
  console.log("\n--- [C. KIỂM TRA HÀM viewAnnouncementDetail] ---");
  let lastAlertMessage = null;
  ctx.alert = (msg) => { lastAlertMessage = msg; };

  // Case C1: Thông báo đang active với dữ liệu progress
  console.log("  [C1] Tra cứu thông báo Active có tiến độ:");
  ctx.getActiveNotifications = () => [
    {
      id: "ann-active-test",
      title: "Đợt thu học phần Tin học",
      status: "active",
      targetAmountEth: "0.0150",
      classSize: 7,
      deadline: "23:59 ngày 30/12/2026",
      createdAt: "2026-11-04T10:00:00+07:00",
      endedAt: null,
      endReason: null,
      progress: {
        contributingWalletsCount: 3,
        classSize: 7,
        headcountPercent: 43,
        raisedEth: "0.0045"
      },
      updatedBy: "0x85ac8f0ca75f2e3fda073bc566659c011208da74",
      updatedAt: "2026-11-04T10:00:00+07:00",
      purpose: "Mua tài liệu thực hành"
    }
  ];

  await ctx.viewAnnouncementDetail("ann-active-test");
  assert.ok(lastAlertMessage, "Alert phải hiển thị nội dung chi tiết");
  assert.ok(lastAlertMessage.includes("Đợt thu học phần Tin học"), "Phải có tiêu đề");
  assert.ok(lastAlertMessage.includes("Tiến độ đợt thu: 3/7 ví (43%) • Thu: 0.0045 ETH"), "Phải hiển thị tiến độ đợt thu dạng plain text");
  assert.ok(!lastAlertMessage.includes("<div") && !lastAlertMessage.includes("</div>"), "Tuyệt đối không có mã HTML vỡ trong alert");
  console.log("    ✓ C1 PASS: Alert hiển thị đúng thông tin đợt thu active và tiến độ plain text.");

  // Case C2: Thông báo đã kết thúc có finalProgress
  console.log("  [C2] Tra cứu thông báo đã kết thúc có snapshot finalProgress:");
  ctx.getActiveNotifications = () => [];
  ctx.getAnnouncementHistory = () => [
    {
      id: "ann-closed-test",
      title: "Đợt thu quỹ đầu năm",
      status: "completed",
      targetAmountEth: "0.0100",
      classSize: 7,
      deadline: "23:59 ngày 01/10/2026",
      createdAt: "2026-09-01T08:00:00+07:00",
      endedAt: "2026-10-01T23:59:00+07:00",
      endReason: "Đã hoàn thành 100%",
      progress: {
        finalProgress: {
          contributingWalletsCount: 7,
          classSize: 7,
          headcountPercent: 100,
          raisedEth: "0.0100"
        }
      },
      updatedBy: "0x85ac8f0ca75f2e3fda073bc566659c011208da74",
      updatedAt: "2026-10-01T23:59:00+07:00",
      purpose: "Quỹ thường niên"
    }
  ];

  await ctx.viewAnnouncementDetail("ann-closed-test");
  assert.ok(lastAlertMessage.includes("Đợt thu quỹ đầu năm"), "Phải có tiêu đề");
  assert.ok(lastAlertMessage.includes("Tiến độ đợt thu: 7/7 ví (100%) • Thu: 0.0100 ETH"), "Phải trích xuất đúng snapshot finalProgress dạng plain text");
  assert.ok(lastAlertMessage.includes("Đã hoàn thành 100%"), "Phải có lý do kết thúc");
  console.log("    ✓ C2 PASS: Alert hiển thị chính xác snapshot finalProgress.");

  // Case C3: Thông báo không có dữ liệu progress (progress = null/undefined)
  console.log("  [C3] Tra cứu thông báo không có dữ liệu progress:");
  ctx.getAnnouncementHistory = () => [
    {
      id: "ann-no-progress-test",
      title: "Đợt thu không có dữ liệu tiến độ",
      status: "archived",
      targetAmountEth: "0.0050",
      classSize: 7,
      deadline: "Không có",
      createdAt: "2026-08-01T08:00:00+07:00",
      endedAt: "2026-08-15T00:00:00+07:00",
      endReason: "Hết hạn",
      progress: null,
      updatedBy: "0x85ac8f0ca75f2e3fda073bc566659c011208da74",
      updatedAt: "2026-08-15T00:00:00+07:00",
      purpose: "Lưu trữ cũ"
    }
  ];

  await ctx.viewAnnouncementDetail("ann-no-progress-test");
  assert.ok(lastAlertMessage.includes("Đợt thu không có dữ liệu tiến độ"));
  assert.ok(!lastAlertMessage.includes("Tiến độ đợt thu:"), "Không có tiến độ thì không hiển thị dòng tiến độ");
  console.log("    ✓ C3 PASS: Alert xử lý an toàn khi progress là null mà không ném ngoại lệ.");
  console.log("  ==> KẾT QUẢ PHẦN C: HÀM viewAnnouncementDetail HOẠT ĐỘNG HOÀN HẢO (PASS)");

  // -------------------------------------------------------------
  // PHẦN D: KIỂM TRA HỒI QUY CÁC CHỨC NĂNG CỐT LÕI
  // -------------------------------------------------------------
  console.log("\n--- [D. KIỂM TRA HỒI QUY CÁC TÍNH NĂNG CỐT LÕI] ---");
  const coreFunctions = [
    'doDeposit',
    'doCreateRefund',
    'doCreateSpend',
    'doSetBCS',
    'doWithdrawFee',
    'connectWallet',
    'disconnectWallet',
    'switchAccount',
    'initWeb3',
    'authenticateWalletSession',
    'renderMultipleProgressCards',
    'renderAnnouncementHistoryUI'
  ];

  for (const fnName of coreFunctions) {
    assert.strictEqual(typeof ctx[fnName], 'function', `Hàm cốt lõi ${fnName} PHẢI tồn tại và là function!`);
    console.log(`  ✓ Hàm ${fnName}: Đã định nghĩa và nguyên vẹn.`);
  }

  console.log("  ==> KẾT QUẢ PHẦN D: TẤT CẢ TÍNH NĂNG CỐT LÕI ĐƯỢC BẢO TOÀN NGUYÊN VẸN (PASS)");
  console.log("\n🎉 TOÀN BỘ 4 MỤC KIỂM THỬ ĐỀU ĐẠT CHUẨN (100% PASS)!");
})().catch(err => {
  console.error("LỖI KIỂM THỬ:", err);
  process.exit(1);
});
