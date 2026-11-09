import re

# 1. Update web/styles.css
css_path = r'web/styles.css'
with open(css_path, 'r', encoding='utf-8') as f:
    css = f.read()

modal_css = """
/* ==========================================================================
   FOCUSED ACTION MODAL SYSTEM (MoMo-Style Direct Action Popups)
   ========================================================================== */

#dapp-workspace.modal-overlay {
  position: fixed !important;
  inset: 0 !important;
  background: rgba(0, 0, 0, 0.65) !important;
  backdrop-filter: blur(5px) !important;
  -webkit-backdrop-filter: blur(5px) !important;
  z-index: 1100 !important;
  display: none;
  align-items: center;
  justify-content: center;
  padding: 20px !important;
  overflow-y: auto !important;
}

#dapp-workspace.modal-overlay.show {
  display: flex !important;
}

#dapp-workspace .workspace-modal-box {
  background: #ffffff;
  border-radius: 20px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.3);
  width: 100%;
  max-width: 620px;
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: modalScaleIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  padding: 0;
  border: 1px solid var(--border-color);
  margin: auto;
}

#dapp-workspace .workspace-modal-header {
  padding: 16px 22px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
  flex-shrink: 0;
}

#dapp-workspace .workspace-modal-title-box {
  display: flex;
  align-items: center;
  gap: 10px;
}

#dapp-workspace .workspace-modal-title {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--text-main);
}

#dapp-workspace .workspace-modal-sub {
  font-size: 0.76rem;
  color: var(--text-muted);
}

#dapp-workspace .workspace-modal-body {
  padding: 20px 24px;
  overflow-y: auto;
  flex: 1;
}

#dapp-workspace .role-panel {
  box-shadow: none !important;
  border: none !important;
  padding: 0 !important;
  margin: 0 !important;
  background: transparent !important;
}

#dapp-workspace .role-panel > .panel-header {
  display: none !important;
}

/* Dark mode for workspace modal */
body.dark-theme #dapp-workspace .workspace-modal-box {
  background: #1e293b !important;
  color: #f8fafc !important;
  border-color: #334155 !important;
}
body.dark-theme #dapp-workspace .workspace-modal-header {
  background: #0f172a !important;
  border-color: #334155 !important;
}
body.dark-theme #dapp-workspace .workspace-modal-title {
  color: #f8fafc !important;
}
"""

if "FOCUSED ACTION MODAL SYSTEM" not in css:
    with open(css_path, 'a', encoding='utf-8') as f:
        f.write(modal_css)
    print("Added modal_css to web/styles.css")
else:
    print("modal_css already in web/styles.css")

# 2. Update web/index.html
html_path = r'web/index.html'
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Replace the opening of dapp-workspace and top-bar up to roleDetailContainer
old_ws_header = """      <!-- KHÔNG GIAN THAO TÁC (ẨN MẶC ĐỊNH, MỞ QUA CÁC NÚT BẤM DỊCH VỤ / HÀNH ĐỘNG) -->
      <section class="dapp-hero-section" id="dapp-workspace" style="display: none;">
        <div class="container">
          <!-- Thanh điều hướng thu gọn Không gian thao tác -->
          <div class="workspace-top-bar" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:18px; padding-bottom:12px; border-bottom:1px dashed var(--border-color);">
            <button class="btn btn-secondary" type="button" onclick="closeWorkspaceView()" style="display:inline-flex; align-items:center; gap:8px; font-weight:600; padding:8px 16px; border-radius:10px;">
              <svg style="width:18px;height:18px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
              <span>Quay lại Trang chủ</span>
            </button>
            <button class="btn btn-outline" type="button" onclick="closeWorkspaceView()" style="display:inline-flex; align-items:center; gap:6px; font-size:0.85rem; padding:8px 14px; border-radius:10px;">
              ✕ Đóng không gian thao tác
            </button>
          </div>
          <div class="workspace-role-header" style="text-align: center; max-width: 760px; margin: 0 auto 16px auto;">
            <span class="section-badge" style="background:#e0e7ff; color:var(--brand-blue); font-weight:700;">Không Gian
              Thao Tác</span>
            <h2 style="font-size: 2rem; color: var(--primary-navy); margin: 8px 0 6px 0;">
              Chọn Vai Trò Để Thao Tác
            </h2>
            <p style="font-size: 0.95rem; color: var(--text-muted);">
              Bấm chọn vai trò hoặc xem toàn bộ luồng dòng tiền để mở ô chi tiết:
            </p>

            <!-- 3 NÚT BẤM TRANG CHỦ THEO YÊU CẦU -->
            <div class="role-buttons-group">
              <button class="role-btn-item role-btn-student" id="btnRoleStudent" onclick="selectRoleView('student')">
                <span class="role-btn-icon">🎓</span>
                <span class="role-btn-label">Sinh viên</span>
              </button>
              <button class="role-btn-item role-btn-bcs" id="btnRoleBCS" onclick="selectRoleView('bcs')">
                <span class="role-btn-icon">👥</span>
                <span class="role-btn-label">Ban cán sự</span>
              </button>
              <button class="role-btn-item role-btn-advisor" id="btnRoleAdvisor" onclick="selectRoleView('advisor')">
                <span class="role-btn-icon">🛡️</span>
                <span class="role-btn-label">Cố vấn học tập</span>
              </button>
              <button class="role-btn-item role-btn-history" id="btnRoleHistory" onclick="selectRoleView('history')">
                <span class="role-btn-icon">📊</span>
                <span class="role-btn-label">Lịch sử dòng tiền</span>
              </button>
            </div>
          </div>"""

new_ws_header = """      <!-- MODAL THAO TÁC TẬP TRUNG (FOCUSED ACTION MODAL - MOMO STYLE) -->
      <section class="dapp-hero-section modal-overlay" id="dapp-workspace" style="display: none;" onclick="if(event.target === this) closeActionModal()">
        <div class="modal-box workspace-modal-box" id="workspaceModalBox">
          <!-- Modal Header -->
          <div class="workspace-modal-header">
            <div class="workspace-modal-title-box">
              <span id="actionModalIcon" style="font-size: 1.35rem;">⚡</span>
              <div>
                <h3 class="workspace-modal-title" id="actionModalTitle">Nạp Quỹ Lớp K57</h3>
                <span class="workspace-modal-sub" id="actionModalSub">Hợp đồng thông minh Ethereum Sepolia</span>
              </div>
            </div>
            <button class="modal-close" type="button" onclick="closeActionModal()" aria-label="Đóng">&times;</button>
          </div>

          <!-- Modal Body -->
          <div class="workspace-modal-body">
            <!-- Giữ nguyên các ID cho test suite nhưng ẩn thanh chọn vai trò khỏi giao diện popup -->
            <div class="workspace-role-header" style="display: none !important;" aria-hidden="true">
              <div class="role-buttons-group">
                <button class="role-btn-item role-btn-student" id="btnRoleStudent" onclick="selectRoleView('student')"><span class="role-btn-icon">🎓</span><span class="role-btn-label">Sinh viên</span></button>
                <button class="role-btn-item role-btn-bcs" id="btnRoleBCS" onclick="selectRoleView('bcs')"><span class="role-btn-icon">👥</span><span class="role-btn-label">Ban cán sự</span></button>
                <button class="role-btn-item role-btn-advisor" id="btnRoleAdvisor" onclick="selectRoleView('advisor')"><span class="role-btn-icon">🛡️</span><span class="role-btn-label">Cố vấn học tập</span></button>
                <button class="role-btn-item role-btn-history" id="btnRoleHistory" onclick="selectRoleView('history')"><span class="role-btn-icon">📊</span><span class="role-btn-label">Lịch sử dòng tiền</span></button>
              </div>
            </div>"""

if old_ws_header in html:
    html = html.replace(old_ws_header, new_ws_header)
    print("Replaced old_ws_header successfully!")
else:
    print("old_ws_header not found exactly, check variations!")

# Check closing tag of dapp-workspace
# In old html:
#                   <a id="flowLinkEtherscan" href="https://sepolia.etherscan.io" target="_blank"
#                     class="btn btn-sm btn-outline" style="font-size: 0.85rem;">
#                     Tra cứu chi tiết trên Sepolia Etherscan &rarr;
#                   </a>
#                 </div>
#               </div>
#             </div>
#           </div>
#
#         </div>
#       </div>
#     </section>

old_ws_footer = """                  <a id="flowLinkEtherscan" href="https://sepolia.etherscan.io" target="_blank"
                      class="btn btn-sm btn-outline" style="font-size: 0.85rem;">
                      Tra cứu chi tiết trên Sepolia Etherscan &rarr;
                    </a>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>
      </section>"""

new_ws_footer = """                  <a id="flowLinkEtherscan" href="https://sepolia.etherscan.io" target="_blank"
                      class="btn btn-sm btn-outline" style="font-size: 0.85rem;">
                      Tra cứu chi tiết trên Sepolia Etherscan &rarr;
                    </a>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>
          </div>
        </div>
      </section>"""

if old_ws_footer in html:
    html = html.replace(old_ws_footer, new_ws_footer)
    print("Replaced old_ws_footer successfully!")
else:
    print("old_ws_footer not found exactly, checking...")

# 3. Add JS functions openActionModal and closeActionModal, update handleQuickAction
js_functions = """
    // =========================================================================
    // FOCUSED ACTION MODAL CONTROLLER (MoMo-Style Direct Action Interface)
    // =========================================================================

    function openActionModal(action) {
      if (typeof closeAllNavDropdowns === "function") closeAllNavDropdowns();
      if (typeof closeAllMobileSheets === "function") closeAllMobileSheets();

      const ws = document.getElementById("dapp-workspace");
      const modalBox = document.getElementById("workspaceModalBox");
      const iconEl = document.getElementById("actionModalIcon");
      const titleEl = document.getElementById("actionModalTitle");
      const subEl = document.getElementById("actionModalSub");

      if (!ws) return;

      const pStudent = document.getElementById("panelStudent");
      const pBCS = document.getElementById("panelBCS");
      const pAdvisor = document.getElementById("panelAdvisor");
      const pHistory = document.getElementById("panelHistory");

      const secDeposit = document.getElementById("sectionDepositForm");
      const secRefund = document.getElementById("sectionRefundForm");
      const secSpendCreate = document.getElementById("sectionBcsCreateSpend");
      const secBcsCol = document.getElementById("sectionBcsManageCollection");
      const secAdvBcs = document.getElementById("sectionAdvisorManageBcs");
      const secAdvFee = document.getElementById("sectionAdvisorWithdrawFee");
      const secAdvMon = document.getElementById("sectionAdvisorStudentMonitor");

      // Hide all panels
      [pStudent, pBCS, pAdvisor, pHistory].forEach(p => { if (p) p.style.display = "none"; });

      // Default hide all inner forms
      if (secDeposit) secDeposit.style.display = "none";
      if (secRefund) secRefund.style.display = "none";
      if (secSpendCreate) secSpendCreate.style.display = "none";
      if (secBcsCol) secBcsCol.style.display = "none";
      if (secAdvBcs) secAdvBcs.style.display = "none";
      if (secAdvFee) secAdvFee.style.display = "none";
      if (secAdvMon) secAdvMon.style.display = "none";

      const roleDetailContainer = document.getElementById("roleDetailContainer");
      if (roleDetailContainer) roleDetailContainer.style.display = "block";

      const verifiedRole = window.currentVerifiedRole || "none";

      if (action === "deposit") {
        if (modalBox) modalBox.style.maxWidth = "560px";
        if (iconEl) iconEl.textContent = "⚡";
        if (titleEl) titleEl.textContent = "Nạp Quỹ Lớp K57";
        if (subEl) subEl.textContent = "Ethereum Sepolia • Net 99% ngân sách lớp, 1% quỹ vận hành";
        if (pStudent) pStudent.style.display = "block";
        if (secDeposit) secDeposit.style.display = "block";
        const inp = document.getElementById("inputDepositAmount");
        if (inp) setTimeout(() => inp.focus(), 150);
      } else if (action === "refund") {
        if (modalBox) modalBox.style.maxWidth = "680px";
        if (iconEl) iconEl.textContent = "💸";
        if (titleEl) titleEl.textContent = "Yêu Cầu Hoàn Tiền";
        if (subEl) subEl.textContent = "Hạn mức tối đa 99% số tiền ròng bạn đã đóng góp vào Quỹ";
        if (pStudent) pStudent.style.display = "block";
        if (secRefund) secRefund.style.display = "block";
        const inp = document.getElementById("inputRefundAmount");
        if (inp) setTimeout(() => inp.focus(), 150);
      } else if (action === "spend") {
        if (modalBox) modalBox.style.maxWidth = "640px";
        if (iconEl) iconEl.textContent = "📝";
        if (titleEl) titleEl.textContent = "Tạo Đề Xuất Chi Tiêu Lớp";
        if (subEl) subEl.textContent = "Dành riêng cho Ban cán sự • Cần tối thiểu 51% biểu quyết tán thành trong 7 ngày";
        if (pBCS) pBCS.style.display = "block";
        if (secSpendCreate) secSpendCreate.style.display = "block";
        const inp = document.getElementById("inputSpendRecipient");
        if (inp) setTimeout(() => inp.focus(), 150);
      } else if (action === "vote" || action === "disburse") {
        if (modalBox) modalBox.style.maxWidth = "980px";
        if (iconEl) iconEl.textContent = "⚖️";
        if (titleEl) titleEl.textContent = "Biểu Quyết & Giải Ngân (BCS)";
        if (subEl) subEl.textContent = "Danh sách các khoản chi và yêu cầu hoàn tiền đang chờ Ban cán sự biểu quyết";
        if (pBCS) pBCS.style.display = "block";
        const bcsSpendTable = document.getElementById("bcsSpendTableBody");
        if (bcsSpendTable) {
          const wrap = bcsSpendTable.closest(".data-table-container") || bcsSpendTable.parentElement;
          if (wrap) wrap.style.display = "block";
        }
      } else if (action === "ledger" || action === "history") {
        if (modalBox) modalBox.style.maxWidth = "1040px";
        if (iconEl) iconEl.textContent = "📊";
        if (titleEl) titleEl.textContent = "Sổ Nhật Ký Dòng Tiền On-Chain";
        if (subEl) subEl.textContent = "Minh bạch 100% toàn bộ giao dịch trên sổ cái Ethereum Sepolia";
        if (pHistory) {
          pHistory.style.display = "block";
          if (typeof renderFlowLedgerTable === "function" && Array.isArray(allFlowItems)) {
            renderFlowLedgerTable(allFlowItems);
          }
        }
      } else if (action === "manage-bcs" || action === "bcs-manage") {
        if (modalBox) modalBox.style.maxWidth = "660px";
        if (iconEl) iconEl.textContent = "🛡️";
        if (titleEl) titleEl.textContent = "Quản Lý Ban Cán Sự (Cố Vấn)";
        if (subEl) subEl.textContent = "Bổ nhiệm hoặc bãi nhiệm thành viên Ban cán sự lớp K57";
        if (pAdvisor) pAdvisor.style.display = "block";
        if (secAdvBcs) secAdvBcs.style.display = "block";
      } else if (action === "withdraw-fee") {
        if (modalBox) modalBox.style.maxWidth = "660px";
        if (iconEl) iconEl.textContent = "💰";
        if (titleEl) titleEl.textContent = "Rút Quỹ Vận Hành 1% (Cố Vấn)";
        if (subEl) subEl.textContent = "Thu hồi adminFeePool để bù đắp chi phí gas giao dịch";
        if (pAdvisor) pAdvisor.style.display = "block";
        if (secAdvFee) secAdvFee.style.display = "block";
      }

      // Sync role permissions
      syncRolePermissionsUI(verifiedRole);

      // Open Modal Overlay
      ws.classList.add("modal-overlay", "show");
      ws.style.display = "flex";
    }

    function closeActionModal() {
      const ws = document.getElementById("dapp-workspace");
      if (ws) {
        ws.classList.remove("show");
        ws.style.display = "none";
      }
    }

    function closeWorkspaceView() {
      closeActionModal();
    }
"""

# Replace handleQuickAction implementation
pattern_quick_action = r'function handleQuickAction\(action\)\s*\{[\s\S]*?\n    \}'
html = re.sub(
    pattern_quick_action,
    """function handleQuickAction(action) {
      openActionModal(action);
    }""",
    html
)

# Append js_functions before </script>
idx_script_end = html.rfind('</script>')
if idx_script_end != -1:
    html = html[:idx_script_end] + js_functions + "\n  " + html[idx_script_end:]
    print("Added action modal JS controller!")

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print("Finished applying focused action modals!")

