import re

with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

pattern = r'function openActionModal\(action\)\s*\{[\s\S]*?\n    \}'

replacement = """function openActionModal(action) {
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
      [pStudent, pBCS, pAdvisor, pHistory].forEach(p => { if (p) p.style.display = "none"; });

      const roleDetailContainer = document.getElementById("roleDetailContainer");
      if (roleDetailContainer) roleDetailContainer.style.display = "block";

      if (action === "deposit") {
        if (modalBox) modalBox.style.maxWidth = "560px";
        if (iconEl) iconEl.textContent = "⚡";
        if (titleEl) titleEl.textContent = "Nạp Quỹ Lớp K57";
        if (subEl) subEl.textContent = "Ethereum Sepolia • Net 99% ngân sách lớp, 1% quỹ vận hành";
        if (pStudent) pStudent.style.display = "block";
        if (secRefund) secRefund.style.display = "none";
        if (verifiedRole === "student" || verifiedRole === "bcs") {
          if (secDeposit) secDeposit.style.display = "block";
        }
        const inp = document.getElementById("inputDepositAmount");
        if (inp) setTimeout(() => inp.focus(), 150);
      } else if (action === "refund") {
        if (modalBox) modalBox.style.maxWidth = "680px";
        if (iconEl) iconEl.textContent = "💸";
        if (titleEl) titleEl.textContent = "Yêu Cầu Hoàn Tiền";
        if (subEl) subEl.textContent = "Hạn mức tối đa 99% số tiền ròng bạn đã đóng góp vào Quỹ";
        if (pStudent) pStudent.style.display = "block";
        if (secDeposit) secDeposit.style.display = "none";
        if (verifiedRole === "student" || verifiedRole === "bcs") {
          if (secRefund) secRefund.style.display = "block";
        }
        const inp = document.getElementById("inputRefundAmount");
        if (inp) setTimeout(() => inp.focus(), 150);
      } else if (action === "spend") {
        if (modalBox) modalBox.style.maxWidth = "640px";
        if (iconEl) iconEl.textContent = "📝";
        if (titleEl) titleEl.textContent = "Tạo Đề Xuất Chi Tiêu Lớp";
        if (subEl) subEl.textContent = "Dành riêng cho Ban cán sự • Cần tối thiểu 51% biểu quyết tán thành trong 7 ngày";
        if (pBCS) pBCS.style.display = "block";
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
        if (modalBox) modalBox.style.maxWidth = "980px";
        if (iconEl) iconEl.textContent = "⚖️";
        if (titleEl) titleEl.textContent = "Biểu Quyết & Giải Ngân (BCS)";
        if (subEl) subEl.textContent = "Danh sách các khoản chi và yêu cầu hoàn tiền đang chờ Ban cán sự biểu quyết";
        if (pBCS) pBCS.style.display = "block";
        if (secSpendCreate) secSpendCreate.style.display = "none";
        if (secBcsCol) secBcsCol.style.display = "none";
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
        if (secAdvFee) secAdvFee.style.display = "none";
        if (secAdvMon) secAdvMon.style.display = "none";
        if (verifiedRole === "advisor") {
          if (secAdvBcs) secAdvBcs.style.display = "block";
        }
      } else if (action === "withdraw-fee") {
        if (modalBox) modalBox.style.maxWidth = "660px";
        if (iconEl) iconEl.textContent = "💰";
        if (titleEl) titleEl.textContent = "Rút Quỹ Vận Hành 1% (Cố Vấn)";
        if (subEl) subEl.textContent = "Thu hồi adminFeePool để bù đắp chi phí gas giao dịch";
        if (pAdvisor) pAdvisor.style.display = "block";
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

if re.search(pattern, html):
    html = re.sub(pattern, replacement, html, count=1)
    with open('web/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Updated openActionModal successfully!")
else:
    print("Could not match openActionModal pattern!")

