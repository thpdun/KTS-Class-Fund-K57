import re

# 1. Update web/styles.css
css_path = 'web/styles.css'
with open(css_path, 'r', encoding='utf-8') as f:
    css = f.read()

# Replace or update modal system in styles.css
old_modal_pattern = r'/\* ==========================================================================\s*FOCUSED ACTION MODAL SYSTEM[\s\S]*?(?=(/\*|$))'

new_modal_styles = """/* ==========================================================================
   FOCUSED ACTION MODAL SYSTEM (MoMo-Style Direct Action Popups - Spacious & Clean)
   ========================================================================== */

#dapp-workspace.modal-overlay {
  position: fixed !important;
  inset: 0 !important;
  background: rgba(0, 0, 0, 0.65) !important;
  backdrop-filter: blur(6px) !important;
  -webkit-backdrop-filter: blur(6px) !important;
  z-index: 1100 !important;
  display: none;
  align-items: center;
  justify-content: center;
  padding: 24px !important;
  overflow-y: auto !important;
}

#dapp-workspace.modal-overlay.show {
  display: flex !important;
}

#dapp-workspace .workspace-modal-box {
  background: #ffffff;
  border-radius: 24px !important;
  box-shadow: 0 28px 72px rgba(0, 0, 0, 0.35) !important;
  width: 95% !important;
  max-width: 900px !important; /* To hơn, rộng rãi, chữ không bị chen chúc */
  max-height: 88vh !important;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: modalScaleIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  padding: 0;
  border: 1px solid var(--border-color);
  margin: auto;
}

#dapp-workspace .workspace-modal-header {
  padding: 20px 28px !important;
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
  gap: 12px;
}

#dapp-workspace .workspace-modal-title {
  margin: 0;
  font-size: 1.25rem !important;
  font-weight: 700;
  color: var(--text-main);
}

#dapp-workspace .workspace-modal-sub {
  font-size: 0.82rem !important;
  color: var(--text-muted);
}

#dapp-workspace .workspace-modal-body {
  padding: 26px 30px !important;
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

/* Responsive grid for flow steps - rộng rãi, minmax 260px không ép 4 cột hẹp */
.flow-steps-grid {
  display: grid !important;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)) !important;
  gap: 20px !important;
  align-items: stretch !important;
}

.flow-step-box {
  background: #f8fafc !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 16px !important;
  padding: 20px 18px !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 8px !important;
  box-sizing: border-box !important;
}

.flow-step-box h5 {
  font-size: 1rem !important;
  font-weight: 700 !important;
  margin: 6px 0 !important;
}

.flow-step-box p {
  font-size: 0.86rem !important;
  line-height: 1.6 !important;
  color: var(--text-muted) !important;
}

/* ==========================================================================
   SITE FOOTER - DẢI NGANG TRỌN VẸN Ở DƯỚI (FULL-WIDTH HORIZONTAL STRIP)
   ========================================================================== */
footer.site-footer,
.site-footer {
  width: 100% !important;
  max-width: 100vw !important;
  background: #0f172a !important;
  color: #94a3b8 !important;
  padding: 56px 0 calc(96px + env(safe-area-inset-bottom, 0px)) 0 !important;
  border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
  margin-top: 60px !important;
  position: relative !important;
  z-index: 10 !important;
  clear: both !important;
  box-sizing: border-box !important;
  display: block !important;
}

.site-footer .container {
  width: 100% !important;
  max-width: 1280px !important;
  margin: 0 auto !important;
  padding: 0 32px !important;
  box-sizing: border-box !important;
}

.site-footer .footer-grid {
  display: grid !important;
  grid-template-columns: 2fr 1fr 1fr !important;
  gap: 48px !important;
  margin-bottom: 36px !important;
}

@media (max-width: 900px) {
  .site-footer .footer-grid {
    grid-template-columns: 1fr !important;
    gap: 28px !important;
  }
}

.site-footer .footer-bottom {
  border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
  padding-top: 24px !important;
  display: flex !important;
  justify-content: space-between !important;
  align-items: center !important;
  font-size: 0.85rem !important;
  flex-wrap: wrap !important;
  gap: 16px !important;
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

if re.search(old_modal_pattern, css):
    css = re.sub(old_modal_pattern, new_modal_styles, css)
    print("Updated FOCUSED ACTION MODAL SYSTEM in styles.css!")
else:
    css += "\n" + new_modal_styles
    print("Appended new modal and footer styles to styles.css!")

with open(css_path, 'w', encoding='utf-8') as f:
    f.write(css)

# 2. Update openActionModal in web/index.html to give spacious dimensions to modals
html_path = 'web/index.html'
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Update openActionModal dimensions and strict panel hiding
old_fn = r'function openActionModal\(action\)\s*\{[\s\S]*?\n    \}'

new_fn = """function openActionModal(action) {
      if (typeof closeAllNavDropdowns === "function") closeAllNavDropdowns();
      if (typeof closeAllMobileSheets === "function") closeAllMobileSheets();

      const ws = document.getElementById("dapp-workspace");
      const modalBox = document.getElementById("workspaceModalBox");
      const iconEl = document.getElementById("actionModalIcon");
      const titleEl = document.getElementById("actionModalTitle");
      const subEl = document.getElementById("actionModalSub");

      if (!ws) return;

      const verifiedRole = window.currentVerifiedRole || "none";

      // First sync role permissions to set basic access & notices
      syncRolePermissionsUI(verifiedRole);

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

      // Hide all panels initially
      [pStudent, pBCS, pAdvisor, pHistory].forEach(p => { 
        if (p) p.style.setProperty('display', 'none', 'important'); 
      });

      const roleDetailContainer = document.getElementById("roleDetailContainer");
      if (roleDetailContainer) roleDetailContainer.style.display = "block";

      if (action === "deposit") {
        if (modalBox) modalBox.style.maxWidth = "700px";
        if (iconEl) iconEl.textContent = "⚡";
        if (titleEl) titleEl.textContent = "Nạp Quỹ Lớp K57";
        if (subEl) subEl.textContent = "Ethereum Sepolia • Net 99% ngân sách lớp, 1% quỹ vận hành";
        if (pStudent) pStudent.style.setProperty('display', 'block', 'important');
        if (secRefund) secRefund.style.display = "none";
        if (verifiedRole === "student" || verifiedRole === "bcs") {
          if (secDeposit) secDeposit.style.display = "block";
        }
        const inp = document.getElementById("inputDepositAmount");
        if (inp) setTimeout(() => inp.focus(), 150);
      } else if (action === "refund") {
        if (modalBox) modalBox.style.maxWidth = "760px";
        if (iconEl) iconEl.textContent = "💸";
        if (titleEl) titleEl.textContent = "Yêu Cầu Hoàn Tiền";
        if (subEl) subEl.textContent = "Hạn mức tối đa 99% số tiền ròng bạn đã đóng góp vào Quỹ";
        if (pStudent) pStudent.style.setProperty('display', 'block', 'important');
        if (secDeposit) secDeposit.style.display = "none";
        if (verifiedRole === "student" || verifiedRole === "bcs") {
          if (secRefund) secRefund.style.display = "block";
        }
        const inp = document.getElementById("inputRefundAmount");
        if (inp) setTimeout(() => inp.focus(), 150);
      } else if (action === "spend") {
        if (modalBox) modalBox.style.maxWidth = "840px";
        if (iconEl) iconEl.textContent = "📝";
        if (titleEl) titleEl.textContent = "Tạo Đề Xuất Chi Tiêu Lớp";
        if (subEl) subEl.textContent = "Dành riêng cho Ban cán sự • Cần tối thiểu 51% biểu quyết tán thành trong 7 ngày";
        if (pBCS) pBCS.style.setProperty('display', 'block', 'important');
        if (secBcsCol) secBcsCol.style.display = "none";
        const bcsSpendTable = document.getElementById("bcsSpendTableBody");
        if (bcsSpendTable) {
          const wrap = bcsSpendTable.closest(".data-table-container") || bcsSpendTable.parentElement;
          if (wrap) wrap.style.display = "none";
        }
        if (verifiedRole === "bcs") {
          if (secSpendCreate) secSpendCreate.style.display = "block";
        }
        const inp = document.getElementById("inputSpendRecipient");
        if (inp) setTimeout(() => inp.focus(), 150);
      } else if (action === "vote" || action === "disburse") {
        if (modalBox) modalBox.style.maxWidth = "1140px";
        if (iconEl) iconEl.textContent = "⚖️";
        if (titleEl) titleEl.textContent = "Biểu Quyết & Giải Ngân (BCS)";
        if (subEl) subEl.textContent = "Danh sách các khoản chi và yêu cầu hoàn tiền đang chờ Ban cán sự biểu quyết";
        if (pBCS) pBCS.style.setProperty('display', 'block', 'important');
        if (secSpendCreate) secSpendCreate.style.display = "none";
        if (secBcsCol) secBcsCol.style.display = "none";
        const bcsSpendTable = document.getElementById("bcsSpendTableBody");
        if (bcsSpendTable) {
          const wrap = bcsSpendTable.closest(".data-table-container") || bcsSpendTable.parentElement;
          if (wrap) wrap.style.display = "block";
        }
      } else if (action === "ledger" || action === "history") {
        if (modalBox) modalBox.style.maxWidth = "1180px";
        if (iconEl) iconEl.textContent = "📊";
        if (titleEl) titleEl.textContent = "Sổ Nhật Ký Dòng Tiền On-Chain";
        if (subEl) subEl.textContent = "Minh bạch 100% toàn bộ giao dịch trên sổ cái Ethereum Sepolia";
        if (pHistory) {
          pHistory.style.setProperty('display', 'block', 'important');
          if (typeof renderFlowLedgerTable === "function" && Array.isArray(allFlowItems)) {
            renderFlowLedgerTable(allFlowItems);
          }
        }
      } else if (action === "manage-bcs" || action === "bcs-manage") {
        if (modalBox) modalBox.style.maxWidth = "800px";
        if (iconEl) iconEl.textContent = "🛡️";
        if (titleEl) titleEl.textContent = "Quản Lý Ban Cán Sự (Cố Vấn)";
        if (subEl) subEl.textContent = "Bổ nhiệm hoặc bãi nhiệm thành viên Ban cán sự lớp K57";
        if (pAdvisor) pAdvisor.style.setProperty('display', 'block', 'important');
        if (secAdvFee) secAdvFee.style.display = "none";
        if (secAdvMon) secAdvMon.style.display = "none";
        if (verifiedRole === "advisor") {
          if (secAdvBcs) secAdvBcs.style.display = "block";
        }
      } else if (action === "withdraw-fee") {
        if (modalBox) modalBox.style.maxWidth = "760px";
        if (iconEl) iconEl.textContent = "💰";
        if (titleEl) titleEl.textContent = "Rút Quỹ Vận Hành 1% (Cố Vấn)";
        if (subEl) subEl.textContent = "Thu hồi adminFeePool để bù đắp chi phí gas giao dịch";
        if (pAdvisor) pAdvisor.style.setProperty('display', 'block', 'important');
        if (secAdvBcs) secAdvBcs.style.display = "none";
        if (secAdvMon) secAdvMon.style.display = "none";
        if (verifiedRole === "advisor") {
          if (secAdvFee) secAdvFee.style.display = "block";
        }
      }

      // Open Modal Overlay
      ws.classList.add("modal-overlay", "show");
      ws.style.display = "flex";
    }"""

if re.search(old_fn, html):
    html = re.sub(old_fn, new_fn, html, count=1)
    print("Updated openActionModal with spacious widths & strict panel hiding!")
else:
    print("Pattern for openActionModal not matched!")

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

