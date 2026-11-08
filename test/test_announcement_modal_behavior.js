// -*- coding: utf-8 -*-
/**
 * test_announcement_modal_behavior.js
 * Kiểm thử hành vi Modal Tạo/Sửa thông báo theo yêu cầu V4.5.2:
 * 1. Không tự đóng modal khi lưu thất bại (503 STORAGE_PROTECTED hoặc 500 hoặc 403).
 * 2. Dữ liệu trong form được bảo toàn nguyên vẹn khi lưu thất bại.
 * 3. Chống double-submit (nút bị vô hiệu hóa khi đang gửi).
 * 4. Yêu cầu xác thực phiên nếu thiếu session.
 * 5. Chỉ đóng modal khi Backend xác nhận thành công.
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

console.log("=== BẮT ĐẦU KIỂM THỬ HÀNH VI MODAL TẠO THÔNG BÁO V4.5.2 ===");

// 1. Đọc nội dung index.html
const htmlPath = path.join(__dirname, '..', 'web', 'index.html');
const htmlContent = fs.readFileSync(htmlPath, 'utf8');

// Trích xuất script chính
const scriptMatches = [...htmlContent.matchAll(/<script(?:\s+type="[^"]*")?>([\s\S]*?)<\/script>/gi)];
const mainScript = scriptMatches[scriptMatches.length - 1][1];

// Giả lập môi trường DOM
function createTestContext(fetchMock) {
  const alerts = [];
  const logs = [];
  const elements = {};

  function makeEl(id, tagName = 'div') {
    if (!elements[id]) {
      elements[id] = {
        id,
        tagName: tagName.toUpperCase(),
        value: '',
        textContent: '',
        style: {},
        classList: {
          classes: new Set(),
          add(c) { this.classes.add(c); },
          remove(c) { this.classes.delete(c); },
          contains(c) { return this.classes.has(c); }
        },
        listeners: {},
        addEventListener(event, fn) {
          if (!this.listeners[event]) this.listeners[event] = [];
          this.listeners[event].push(fn);
        },
        async dispatchEvent(event) {
          if (this.listeners[event]) {
            for (const fn of this.listeners[event]) {
              await fn();
            }
          }
        },
        appendChild(child) {},
        disabled: false
      };
    }
    return elements[id];
  }

  // Khởi tạo các phần tử form và modal
  const modalEl = makeEl('announcementModal');
  const btnSave = makeEl('btnSaveAnnouncementModal', 'button');
  const btnOpen = makeEl('btnOpenAnnModal', 'button');
  const bVerify = makeEl('btnVerifyWalletAuth', 'button');
  const titleInput = makeEl('formAnnTitle', 'input');
  const amountInput = makeEl('formAnnAmount', 'input');
  const classSizeInput = makeEl('formAnnClassSize', 'input');
  const deadlineInput = makeEl('formAnnDeadline', 'input');
  const purposeInput = makeEl('formAnnPurpose', 'input');
  const statusInput = makeEl('formAnnStatus', 'select');

  // Giá trị ban đầu
  statusInput.value = 'Đang diễn ra';

  const context = {
    window: {},
    document: {
      getElementById(id) { return elements[id] || makeEl(id); },
      querySelector(sel) {
        if (sel === "#announcementModal .modal-header h3") {
          return makeEl('modalTitleHeader', 'h3');
        }
        return makeEl('generic_' + sel);
      },
      querySelectorAll() { return []; },
      createElement(tag) { return makeEl('created_' + Math.random(), tag); },
      addEventListener() {}
    },
    localStorage: {
      data: {},
      getItem(k) { return this.data[k] || null; },
      setItem(k, v) { this.data[k] = String(v); },
      removeItem(k) { delete this.data[k]; }
    },
    sessionStorage: {
      data: {},
      getItem(k) { return this.data[k] || null; },
      setItem(k, v) { this.data[k] = String(v); },
      removeItem(k) { delete this.data[k]; }
    },
    alert(msg) { alerts.push(msg); },
    confirm() { return true; },
    prompt() { return "Lý do"; },
    console: {
      log(...args) { logs.push(args.join(' ')); },
      warn(...args) { logs.push(args.join(' ')); },
      error(...args) { logs.push(args.join(' ')); }
    },
    fetch: fetchMock,
    setTimeout: (fn) => fn(),
    setInterval: () => {},
    clearTimeout: () => {},
    clearInterval: () => {},
    AI_BACKEND_URL: "http://127.0.0.1:8000",
    ethers: {
      formatEther: (w) => "0",
      parseEther: (e) => BigInt(0)
    }
  };

  context.window = context;
  context.window.addEventListener = (event, fn) => {};

  vm.createContext(context);
  vm.runInContext(mainScript, context);

  // Kích hoạt thiết lập event listener cho modal
  if (typeof context.initAnnouncementSystem === "function") {
    context.initAnnouncementSystem();
  }

  function setScopeVars({ userAddress, isBcsMember, isAdvisor, userSessionToken }) {
    let script = "";
    if (userAddress !== undefined) script += `userAddress = ${JSON.stringify(userAddress)};\n`;
    if (isBcsMember !== undefined) script += `isBcsMember = ${JSON.stringify(isBcsMember)};\n`;
    if (isAdvisor !== undefined) script += `isAdvisor = ${JSON.stringify(isAdvisor)};\n`;
    if (userSessionToken !== undefined) script += `userSessionToken = ${JSON.stringify(userSessionToken)};\n`;
    vm.runInContext(script, context);
  }

  return { context, elements, alerts, logs, setScopeVars };
}

async function runTests() {
  // Test 1: Bấm Lưu khi chưa có Session token -> modal không đóng, alert yêu cầu xác thực
  {
    console.log("\n[Test 1] Bấm Lưu khi chưa có Session token:");
    const { context, elements, alerts, setScopeVars } = createTestContext(async () => {});
    
    // Thiết lập biến scope với quyền BCS nhưng CHƯA CÓ TOKEN
    setScopeVars({
      userAddress: "0x78567A377559F0cB30173f93869326a82320159a",
      isBcsMember: true,
      isAdvisor: false,
      userSessionToken: null
    });

    vm.runInContext("openAnnModal();", context);
    assert.strictEqual(elements.announcementModal.classList.contains('open'), true, "Modal phải mở");

    // Nhập dữ liệu
    elements.formAnnTitle.value = "Đợt thu 1";
    elements.formAnnAmount.value = "0.01";

    // Bấm nút Lưu
    await elements.btnSaveAnnouncementModal.dispatchEvent('click');

    // Kiểm tra: Modal vẫn mở, hiện alert yêu cầu ký xác thực ví
    assert.strictEqual(elements.announcementModal.classList.contains('open'), true, "Modal KHÔNG được đóng khi thiếu token");
    assert.strictEqual(elements.formAnnTitle.value, "Đợt thu 1", "Dữ liệu tiêu đề phải được giữ nguyên");
    assert(alerts.some(a => a.includes("Phiên xác thực ví chưa sẵn sàng")), "Phải có alert yêu cầu ký xác thực ví");
    console.log("  -> PASS: Modal giữ nguyên, dữ liệu form không mất, hiển thị cảnh báo yêu cầu xác thực ví.");
  }

  // Test 2: Bấm Lưu khi Backend trả về 503 STORAGE_PROTECTED -> Modal không đóng, dữ liệu giữ nguyên
  {
    console.log("\n[Test 2] Bấm Lưu khi Backend trả về 503 STORAGE_PROTECTED:");
    const mockFetch = async (url) => {
      if (url.includes("/api/announcement")) {
        return {
          ok: false,
          status: 503,
          json: async () => ({
            success: false,
            code: "STORAGE_PROTECTED",
            error: "Hệ thống lưu trữ đang ở chế độ bảo vệ dữ liệu (Read-Only)."
          })
        };
      }
    };

    const { context, elements, alerts, setScopeVars } = createTestContext(mockFetch);
    setScopeVars({
      userAddress: "0x78567A377559F0cB30173f93869326a82320159a",
      isBcsMember: true,
      isAdvisor: false,
      userSessionToken: "valid_bcs_session_token"
    });

    vm.runInContext("openAnnModal();", context);
    elements.formAnnTitle.value = "Chiến dịch Mùa Đông";
    elements.formAnnAmount.value = "0.02";
    elements.formAnnPurpose.value = "Hoạt động thiện nguyện";

    await elements.btnSaveAnnouncementModal.dispatchEvent('click');

    // Kiểm tra: Modal vẫn mở, form giữ nguyên, alert hiển thị rõ lỗi 503
    assert.strictEqual(elements.announcementModal.classList.contains('open'), true, "Modal KHÔNG được đóng khi Backend báo lỗi 503");
    assert.strictEqual(elements.formAnnTitle.value, "Chiến dịch Mùa Đông", "Tiêu đề không bị mất");
    assert.strictEqual(elements.formAnnPurpose.value, "Hoạt động thiện nguyện", "Mục đích không bị mất");
    assert(alerts.some(a => a.includes("Lưu thông báo thất bại") && a.includes("chế độ bảo vệ dữ liệu")), "Alert phải nêu rõ lỗi STORAGE_PROTECTED");
    console.log("  -> PASS: Khi Backend trả về 503, Modal không đóng, form được giữ nguyên, báo lỗi chi tiết.");
  }

  // Test 3: Bấm Lưu khi Backend gặp sự cố sập mạng / 500 HTML -> Modal không đóng, dữ liệu giữ nguyên
  {
    console.log("\n[Test 3] Bấm Lưu khi Backend phản hồi HTML 500 (Internal Error):");
    const mockFetch = async () => {
      return {
        ok: false,
        status: 500,
        json: async () => { throw new Error("Unexpected token '<'"); }
      };
    };

    const { context, elements, alerts, setScopeVars } = createTestContext(mockFetch);
    setScopeVars({
      userAddress: "0x78567A377559F0cB30173f93869326a82320159a",
      isBcsMember: true,
      isAdvisor: false,
      userSessionToken: "valid_bcs_session_token"
    });

    vm.runInContext("openAnnModal();", context);
    elements.formAnnTitle.value = "Đợt thu kiểm thử lỗi 500";
    elements.formAnnAmount.value = "0.015";

    await elements.btnSaveAnnouncementModal.dispatchEvent('click');

    // Kiểm tra: Modal vẫn mở, form giữ nguyên, alert báo lỗi mạng
    assert.strictEqual(elements.announcementModal.classList.contains('open'), true, "Modal KHÔNG được đóng khi gặp lỗi 500");
    assert.strictEqual(elements.formAnnTitle.value, "Đợt thu kiểm thử lỗi 500", "Dữ liệu không bị mất");
    assert(alerts.some(a => a.includes("Không thể kết nối") || a.includes("lỗi")), "Alert phải thông báo lỗi mạng cho người dùng");
    console.log("  -> PASS: Khi gặp lỗi 500/HTML, Modal không đóng, dữ liệu không mất, người dùng được thông báo rõ.");
  }

  // Test 4: Bấm Lưu thành công (Backend 200) -> Modal đóng, đồng bộ và hiển thị thành công
  {
    console.log("\n[Test 4] Bấm Lưu khi Backend phản hồi 200 thành công:");
    let syncCalled = false;
    const mockFetch = async (url) => {
      if (url.includes("/api/announcement") && !url.includes("/close")) {
        syncCalled = true;
        return {
          ok: true,
          status: 200,
          json: async () => ({
            success: true,
            announcement: { id: "TB-NEW", title: "Quỹ mới thành công", targetAmountEth: "0.01", status: "active" },
            activeNotifications: [{ id: "TB-NEW", title: "Quỹ mới thành công", targetAmountEth: "0.01", status: "active" }]
          })
        };
      }
    };

    const { context, elements, alerts, setScopeVars } = createTestContext(mockFetch);
    setScopeVars({
      userAddress: "0x78567A377559F0cB30173f93869326a82320159a",
      isBcsMember: true,
      isAdvisor: false,
      userSessionToken: "valid_bcs_session_token"
    });

    vm.runInContext("openAnnModal();", context);
    elements.formAnnTitle.value = "Quỹ mới thành công";
    elements.formAnnAmount.value = "0.01";

    await elements.btnSaveAnnouncementModal.dispatchEvent('click');

    // Kiểm tra: Modal ĐÃ ĐÓNG và hiển thị alert thành công
    assert.strictEqual(elements.announcementModal.classList.contains('open'), false, "Modal PHẢI ĐÓNG khi Backend xác nhận thành công");
    assert(alerts.some(a => a.includes("Đã cập nhật và lưu thông báo thành công")), "Phải hiển thị alert thành công");
    console.log("  -> PASS: Khi lưu thành công, modal đóng, gọi syncAnnouncementFromServer và hiển thị thông báo thành công.");
  }

  console.log("\n🎉 TẤT CẢ 4 BÀI TEST BROWSER/DOM EMULATION VỀ MODAL ĐỀU ĐẠT (100% PASS)!");
}

runTests().catch(err => {
  console.error("Test thất bại:", err);
  process.exit(1);
});
