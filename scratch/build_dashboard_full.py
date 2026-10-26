import os
import re
import json

def main():
    with open("web/index.html.bak", "r", encoding="utf-8") as f:
        orig = f.read()

    # Load required IDs
    with open("scratch/all_ids.json", "r", encoding="utf-8") as f:
        id_data = json.load(f)
    required_ids = id_data["html_ids"]
    js_ids = id_data["js_accessed_ids"]

    # Extract original script
    script_start = orig.find("<script>")
    script_end = orig.rfind("</script>") + len("</script>")
    js_code = orig[script_start:script_end]

    # Extract AI widget
    ai_widget_start = orig.find('<div class="ai-fab-container"', script_end)
    ai_widget_end = orig.find('</body>', ai_widget_start)
    ai_widget_html = orig[ai_widget_start:ai_widget_end].strip()

    # Extract modal HTMLs from original HTML
    # 1. walletModal
    wm_start = orig.find('<div class="modal-overlay" id="walletModal">')
    wm_end = orig.find('<!-- ============================================================ -->', wm_start)
    wallet_modal_html = orig[wm_start:wm_end].strip()

    # 2. announcementModal
    am_start = orig.find('<div class="modal-overlay" id="announcementModal">')
    am_end = orig.find('<!-- ============================================================ -->', am_start)
    ann_modal_html = orig[am_start:am_end].strip()

    # 3. rosterModal
    rm_start = orig.find('<div class="modal-overlay" id="rosterModal"')
    rm_end = orig.find('<!-- ============================================================ -->', rm_start)
    roster_modal_html = orig[rm_start:rm_end].strip()

    # Extract sections from original HTML
    # Section: about
    sec_about_start = orig.find('<section id="about">')
    sec_about_end = orig.find('<!-- ============================================================ -->', sec_about_start)
    sec_about = orig[sec_about_start:sec_about_end].strip()

    # Section: workflow
    sec_workflow_start = orig.find('<section id="workflow"')
    sec_workflow_end = orig.find('<!-- ============================================================ -->', sec_workflow_start)
    sec_workflow = orig[sec_workflow_start:sec_workflow_end].strip()

    # Section: governance
    sec_gov_start = orig.find('<section id="governance">')
    sec_gov_end = orig.find('<!-- ============================================================ -->', sec_gov_start)
    sec_gov = orig[sec_gov_start:sec_gov_end].strip()

    # Section: economics
    sec_eco_start = orig.find('<section id="economics"')
    sec_eco_end = orig.find('<!-- ============================================================ -->', sec_eco_start)
    sec_eco = orig[sec_eco_start:sec_eco_end].strip()

    # Section: blockchain
    sec_bc_start = orig.find('<section id="blockchain">')
    sec_bc_end = orig.find('<!-- ============================================================ -->', sec_bc_start)
    sec_bc = orig[sec_bc_start:sec_bc_end].strip()

    # Section: faq
    sec_faq_start = orig.find('<section id="faq"')
    sec_faq_end = orig.find('<!-- ============================================================ -->', sec_faq_start)
    sec_faq = orig[sec_faq_start:sec_faq_end].strip()

    # Section: transparency
    sec_trans_start = orig.find('<section id="transparency"')
    sec_trans_end = orig.find('<!-- ============================================================ -->', sec_trans_start)
    sec_trans = orig[sec_trans_start:sec_trans_end].strip()

    # Section: dapp-workspace
    sec_ws_start = orig.find('<section class="dapp-hero-section" id="dapp-workspace">')
    sec_ws_end = orig.find('<!-- ============================================================ -->', sec_ws_start)
    sec_ws = orig[sec_ws_start:sec_ws_end].strip()

    # Hero content pieces
    # quick-control-bar
    qcb_start = orig.find('<div class="quick-control-bar">')
    qcb_end = orig.find('<!-- CẢNH BÁO KHÁCH VÃNG LAI', qcb_start)
    qcb = orig[qcb_start:qcb_end].strip()

    # guestWarningBanner
    gwb_start = orig.find('<div id="guestWarningBanner"')
    gwb_end = orig.find('<!-- BẢNG THÔNG BÁO THU QUỸ', gwb_start)
    gwb = orig[gwb_start:gwb_end].strip()

    # class-announcement-card
    cac_start = orig.find('<div class="class-announcement-card" id="classAnnouncementCard">')
    cac_end = orig.find('<!-- Live metrics ribbon -->', cac_start)
    cac = orig[cac_start:cac_end].strip()

    # metrics-grid
    mg_start = orig.find('<div class="metrics-grid">')
    mg_end = orig.find('</div>\n    </div>\n  </section>', mg_start) + len('</div>')
    mg = orig[mg_start:mg_end].strip()

    # Footer
    ft_start = orig.find('<footer class="site-footer">')
    ft_end = orig.find('<!-- ============================================================ -->', ft_start)
    ft = orig[ft_start:ft_end].strip()

    print("All core HTML blocks extracted successfully.")

    # Read CSS from test_css_builder
    from test_css_builder import build as get_css
    # We can import css_code
    with open("scratch/test_css_builder.py", "r", encoding="utf-8") as f:
        tcb_content = f.read()
    css_start = tcb_content.find('css_code = """') + len('css_code = """')
    css_end = tcb_content.find('"""\n\n    print("CSS built', css_start)
    modern_css = tcb_content[css_start:css_end]

    # Additional JS helpers to smoothly integrate sidebar with mobile toggle & role display updates
    enhanced_js = js_code.replace(
        'const btnToggle = document.getElementById("btnToggleNav");\n      const navLinks = document.getElementById("navLinks");\n      if (btnToggle && navLinks) {\n        btnToggle.addEventListener("click", () => {\n          navLinks.classList.toggle("show");\n        });\n      }',
        '''// Mobile & Sidebar navigation toggle
      const btnToggle = document.getElementById("btnToggleNav");
      const sidebarEl = document.getElementById("appSidebar");
      const backdropEl = document.getElementById("sidebarBackdrop");
      if (btnToggle && sidebarEl) {
        btnToggle.addEventListener("click", () => {
          sidebarEl.classList.toggle("show");
          if (backdropEl) backdropEl.classList.toggle("show");
        });
      }
      if (backdropEl && sidebarEl) {
        backdropEl.addEventListener("click", () => {
          sidebarEl.classList.remove("show");
          backdropEl.classList.remove("show");
        });
      }
      // Close sidebar when clicking links on mobile
      document.querySelectorAll(".sidebar-link").forEach(link => {
        link.addEventListener("click", () => {
          if (window.innerWidth <= 1024 && sidebarEl) {
            sidebarEl.classList.remove("show");
            if (backdropEl) backdropEl.classList.remove("show");
          }
        });
      });'''
    )

    # In updateRoleDisplay, also update sidebar profile card if present
    enhanced_js = enhanced_js.replace(
        'if (badge) {\n          badge.textContent = "🏛️ Cố vấn học tập";',
        '''const sbId = document.getElementById("sidebarUserIdentity");
        const sbRole = document.getElementById("sidebarRoleBadge");
        const sbAddr = document.getElementById("sidebarWalletShort");
        if (sbId) sbId.textContent = "Giảng viên phụ trách K57";
        if (sbRole) { sbRole.textContent = "🏛️ Cố vấn"; sbRole.className = "status-pill"; sbRole.style.background = "var(--advisor-bg)"; sbRole.style.color = "var(--advisor-color)"; }
        if (sbAddr && userAddress) sbAddr.textContent = shortenAddress(userAddress);
        if (badge) {\n          badge.textContent = "🏛️ Cố vấn học tập";'''
    )

    enhanced_js = enhanced_js.replace(
        'if (badge) {\n          badge.textContent = "👥 Ban cán sự";',
        '''const sbId = document.getElementById("sidebarUserIdentity");
        const sbRole = document.getElementById("sidebarRoleBadge");
        const sbAddr = document.getElementById("sidebarWalletShort");
        if (sbId) sbId.textContent = studentObj ? `${studentObj.name} (${studentObj.mssv})` : "Ban cán sự K57";
        if (sbRole) { sbRole.textContent = "👥 Ban cán sự"; sbRole.className = "status-pill"; sbRole.style.background = "var(--bcs-bg)"; sbRole.style.color = "var(--bcs-color)"; }
        if (sbAddr && userAddress) sbAddr.textContent = shortenAddress(userAddress);
        if (badge) {\n          badge.textContent = "👥 Ban cán sự";'''
    )

    enhanced_js = enhanced_js.replace(
        'if (badge) {\n          badge.textContent = "🎓 Sinh viên";',
        '''const sbId = document.getElementById("sidebarUserIdentity");
        const sbRole = document.getElementById("sidebarRoleBadge");
        const sbAddr = document.getElementById("sidebarWalletShort");
        if (sbId) sbId.textContent = studentObj ? `${studentObj.name} (${studentObj.mssv})` : "Sinh viên K57";
        if (sbRole) { sbRole.textContent = "🎓 Sinh viên"; sbRole.className = "status-pill"; sbRole.style.background = "var(--student-bg)"; sbRole.style.color = "var(--student-color)"; }
        if (sbAddr && userAddress) sbAddr.textContent = shortenAddress(userAddress);
        if (badge) {\n          badge.textContent = "🎓 Sinh viên";'''
    )

    enhanced_js = enhanced_js.replace(
        'if (badge) {\n          badge.textContent = "Khách vãng lai";',
        '''const sbId = document.getElementById("sidebarUserIdentity");
        const sbRole = document.getElementById("sidebarRoleBadge");
        const sbAddr = document.getElementById("sidebarWalletShort");
        if (sbId) sbId.textContent = userAddress ? shortenAddress(userAddress) : "Chưa kết nối ví";
        if (sbRole) { sbRole.textContent = userAddress ? "Khách vãng lai" : "Chưa kết nối"; sbRole.className = "status-pill status-ready"; sbRole.style.background = ""; sbRole.style.color = ""; }
        if (sbAddr && userAddress) sbAddr.textContent = shortenAddress(userAddress);
        if (badge) {\n          badge.textContent = "Khách vãng lai";'''
    )

    # In disconnectWallet, reset sidebar user card
    enhanced_js = enhanced_js.replace(
        'updateRoleDisplay("guest", null);',
        '''updateRoleDisplay("guest", null);
      const sbId = document.getElementById("sidebarUserIdentity");
      const sbRole = document.getElementById("sidebarRoleBadge");
      const sbAddr = document.getElementById("sidebarWalletShort");
      if (sbId) sbId.textContent = "Chưa kết nối ví";
      if (sbRole) { sbRole.textContent = "Chưa kết nối"; sbRole.className = "status-pill status-ready"; sbRole.style.background = ""; sbRole.style.color = ""; }
      if (sbAddr) sbAddr.textContent = "--";'''
    )

    # Build the full page HTML
    page_html = f"""<!DOCTYPE html>
<html lang="vi">

<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>KTS CLASS FUND — Cổng Thông Tin & Quản Lý Quỹ Lớp (K57 Kinh Tế Số)</title>
  <meta name="description"
    content="Cổng thông tin và hệ thống quản lý quỹ lớp minh bạch bằng công nghệ Blockchain Ethereum Sepolia cho tập thể sinh viên lớp K57 KTS.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link
    href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,400;1,600&family=Inter:wght@300;400;500;600;700;800&display=swap"
    rel="stylesheet">
  <!-- Ethers.js v6 via jsDelivr CDN -->
  <script src="https://cdn.jsdelivr.net/npm/ethers@6.13.2/dist/ethers.umd.min.js"></script>
  <style>
{modern_css}
  </style>
</head>

<body>
  <!-- ============================================================ -->
  <!-- SIDEBAR NAVIGATION (MODERN SAAS DASHBOARD)                   -->
  <!-- ============================================================ -->
  <aside class="app-sidebar" id="appSidebar">
    <div class="sidebar-header">
      <div class="sidebar-logo-icon">
        <svg viewBox="0 0 24 24">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
        </svg>
      </div>
      <div>
        <div class="sidebar-brand-title">KTS CLASS FUND</div>
        <div class="sidebar-brand-sub">K57 Kinh Tế Số &bull; ECO2432</div>
      </div>
    </div>

    <!-- User Identity Profile in Sidebar -->
    <div class="sidebar-user-card">
      <div class="sidebar-user-header">
        <span class="sidebar-user-label">Tài khoản ví Web3</span>
        <span class="status-pill status-ready" id="sidebarRoleBadge" style="font-size: 0.7rem; padding: 2px 7px;">Chưa kết nối</span>
      </div>
      <div class="sidebar-user-identity" id="sidebarUserIdentity">
        Chưa kết nối ví
      </div>
      <div style="display: flex; align-items: center; justify-content: space-between; font-size: 0.74rem; color: #94a3b8;">
        <span id="sidebarWalletShort" style="font-family: monospace;">--</span>
        <span style="font-size: 0.7rem; color: #64748b;">Sepolia Testnet</span>
      </div>
    </div>

    <!-- Navigation Menu (Contains id="navLinks" for backward compatibility) -->
    <ul class="sidebar-menu" id="navLinks">
      <li class="sidebar-group-label">Bảng Điều Khiển</li>
      <li class="sidebar-link-item">
        <a href="#hero" class="sidebar-link active">
          <span class="sidebar-link-icon">📊</span>
          <span>Tổng quan &amp; Chỉ số</span>
        </a>
      </li>
      <li class="sidebar-link-item">
        <a href="#classAnnouncementCard" class="sidebar-link">
          <span class="sidebar-link-icon">📢</span>
          <span>Thông báo nộp quỹ</span>
        </a>
      </li>

      <li class="sidebar-group-label">Không Gian Thao Tác</li>
      <li class="sidebar-link-item">
        <a href="#dapp-workspace" onclick="selectRoleView('student')" class="sidebar-link">
          <span class="sidebar-link-icon">🎓</span>
          <span>Sinh viên K57</span>
        </a>
      </li>
      <li class="sidebar-link-item">
        <a href="#dapp-workspace" onclick="selectRoleView('bcs')" class="sidebar-link">
          <span class="sidebar-link-icon">👥</span>
          <span>Ban cán sự</span>
        </a>
      </li>
      <li class="sidebar-link-item">
        <a href="#dapp-workspace" onclick="selectRoleView('advisor')" class="sidebar-link">
          <span class="sidebar-link-icon">🛡️</span>
          <span>Cố vấn học tập</span>
        </a>
      </li>
      <li class="sidebar-link-item">
        <a href="#dapp-workspace" onclick="selectRoleView('history')" class="sidebar-link">
          <span class="sidebar-link-icon">📈</span>
          <span>Sổ nhật ký dòng tiền</span>
        </a>
      </li>

      <li class="sidebar-group-label">Quản Trị &amp; Dữ Liệu</li>
      <li class="sidebar-link-item">
        <a href="javascript:void(0)" onclick="openRosterModal()" class="sidebar-link">
          <span class="sidebar-link-icon">📋</span>
          <span>Danh bạ lớp K57</span>
          <span class="sidebar-badge" id="sidebarRosterBadge">5</span>
        </a>
      </li>
      <li class="sidebar-link-item">
        <a href="#transparency" class="sidebar-link">
          <span class="sidebar-link-icon">⚙️</span>
          <span>Cấu hình &amp; Terminal</span>
        </a>
      </li>

      <li class="sidebar-group-label">Hướng Dẫn &amp; Quy Chế</li>
      <li class="sidebar-link-item">
        <a href="#workflow" class="sidebar-link">
          <span class="sidebar-link-icon">🔄</span>
          <span>Quy trình thu chi</span>
        </a>
      </li>
      <li class="sidebar-link-item">
        <a href="#governance" class="sidebar-link">
          <span class="sidebar-link-icon">⚖️</span>
          <span>Biểu quyết 51%</span>
        </a>
      </li>
      <li class="sidebar-link-item">
        <a href="#economics" class="sidebar-link">
          <span class="sidebar-link-icon">💰</span>
          <span>Phân bổ 99/1 &amp; Gas</span>
        </a>
      </li>
      <li class="sidebar-link-item">
        <a href="#blockchain" class="sidebar-link">
          <span class="sidebar-link-icon">💡</span>
          <span>Cẩm nang 101</span>
        </a>
      </li>
      <li class="sidebar-link-item">
        <a href="#faq" class="sidebar-link">
          <span class="sidebar-link-icon">❓</span>
          <span>Câu hỏi thường gặp</span>
        </a>
      </li>
    </ul>

    <!-- Sidebar Footer -->
    <div class="sidebar-footer">
      <div class="sidebar-footer-row">
        <span>Mạng:</span>
        <strong style="color: #e2e8f0;">Ethereum Sepolia</strong>
      </div>
      <div class="sidebar-footer-row">
        <span>Smart Contract:</span>
        <a href="https://sepolia.etherscan.io/address/0xfe3ec1a75503Da9ddFd44aEBE18E461686376b52" target="_blank" style="color: #38bdf8; font-family: monospace; font-size: 0.72rem;">0xfe3e...6b52 ↗</a>
      </div>
    </div>
  </aside>

  <!-- Mobile Backdrop Overlay -->
  <div class="sidebar-backdrop" id="sidebarBackdrop"></div>

  <!-- ============================================================ -->
  <!-- MAIN APPLICATION WRAPPER                                     -->
  <!-- ============================================================ -->
  <div class="app-main">
    <!-- Top Bar -->
    <header class="app-topbar">
      <div class="topbar-left">
        <button class="menu-toggle" id="btnToggleNav" aria-label="Mở menu điều hướng">☰</button>
        <div class="topbar-breadcrumbs">
          <span>🏠 KTS Class Fund</span>
          <span>/</span>
          <strong>Dashboard Quản Trị Quỹ Lớp K57</strong>
        </div>
      </div>

      <div class="topbar-right">
        <div class="badge-network" id="networkBadge">
          <span class="badge-dot" id="networkDot"></span>
          <span id="networkText">Chưa kết nối ví</span>
        </div>
        <button class="btn btn-primary btn-sm" id="btnConnectWallet" title="Bấm để kết nối hoặc đổi tài khoản">
          <svg style="width:16px;height:16px;fill:currentColor;" viewBox="0 0 24 24">
            <path
              d="M21 7.28V5c0-1.1-.9-2-2-2H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2v-2.28c.59-.35 1-.98 1-1.72V9c0-.74-.41-1.37-1-1.72zM20 9v6h-7V9h7zM5 19V5h14v2h-6c-1.1 0-2 .9-2 2v6c0 1.1.9 2 2 2h6v2H5z" />
          </svg>
          <span id="walletBtnText">Kết nối MetaMask</span>
        </button>
        <button class="btn btn-outline btn-sm" id="btnSwitchWallet"
          style="display:none;" title="Đổi sang tài khoản ví khác"
          onclick="switchAccount()">
          🔄 Đổi ví
        </button>
        <button class="btn btn-danger btn-sm" id="btnDisconnectWallet" style="display:none; padding:6px 10px;"
          title="Ngắt kết nối ví" onclick="disconnectWallet()">
          ✕
        </button>
      </div>
    </header>

    <!-- Main Content -->
    <main class="app-content">
      <!-- HERO & DASHBOARD OVERVIEW -->
      <section class="hero-section" id="hero">
        <div class="hero-banner-card">
          <div class="hero-tag">
            <span>●</span> Cổng Thông Tin &amp; Quản Lý Quỹ Lớp Blockchain Chuẩn Mực ECO2432
          </div>
          <h1 class="hero-title">KTS CLASS FUND — Minh bạch hóa quản lý quỹ lớp bằng Blockchain</h1>
          <p class="hero-desc">
            Hệ thống quản lý đóng góp, giải ngân chi tiêu và đối soát giao dịch thời gian thực thông qua hợp đồng thông minh Ethereum Sepolia, giúp toàn thể sinh viên K57 giám sát dòng tiền minh bạch.
          </p>
        </div>

        <!-- Quick Control Bar (Address, Role, Student Identity, Contract Config) -->
{qcb}

        <!-- CẢNH BÁO KHÁCH VÃNG LAI (GUEST WARNING BANNER) -->
{gwb}

        <!-- BẢNG THÔNG BÁO THU QUỸ LỚP (CLASS ANNOUNCEMENT BANNER) -->
{cac}

        <!-- Live metrics ribbon -->
{mg}
      </section>

      <!-- 3 Ô GIAO DIỆN THEO 3 VAI TRÒ -->
{sec_ws}

      <!-- BỐI CẢNH, VẤN ĐỀ & MỤC TIÊU DỰ ÁN -->
{sec_about}

      <!-- QUY TRÌNH HOẠT ĐỘNG CHUẨN HÓA -->
{sec_workflow}

      <!-- QUY CHẾ BIỂU QUYẾT 51% -->
{sec_gov}

      <!-- PHÂN BỔ TÀI CHÍNH 99% / 1% -->
{sec_eco}

      <!-- CẨM NANG BLOCKCHAIN 101 CHO SINH VIÊN -->
{sec_bc}

      <!-- CÂU HỎI THƯỜNG GẶP (FAQ ACCORDION) -->
{sec_faq}

      <!-- MINH BẠCH VÀ CẤU HÌNH HỢP ĐỒNG -->
{sec_trans}
    </main>

    <!-- FOOTER -->
{ft}
  </div>

  <!-- ============================================================ -->
  <!-- MODAL HƯỚNG DẪN / CẤU HÌNH                                   -->
  <!-- ============================================================ -->
{wallet_modal_html}

  <!-- ============================================================ -->
  <!-- MODAL QUẢN TRỊ THÔNG BÁO LỚP (BCS & CỐ VẤN)                 -->
  <!-- ============================================================ -->
{ann_modal_html}

  <!-- ============================================================ -->
  <!-- MODAL DANH BẠ SINH VIÊN K57 & XÁC THỰC VÍ                    -->
  <!-- ============================================================ -->
{roster_modal_html}

  <!-- ============================================================ -->
  <!-- JAVASCRIPT LOGIC                                             -->
  <!-- ============================================================ -->
{enhanced_js}

  <!-- ============================================================ -->
  <!-- AI ASSISTANT FLOATING CHAT WIDGET                            -->
  <!-- ============================================================ -->
{ai_widget_html}
</body>

</html>
"""

    # Check that all required IDs are present in page_html
    missing_ids = []
    for rid in required_ids:
        # Check if id="{rid}" or id='{rid}' is in page_html
        if f'id="{rid}"' not in page_html and f"id='{rid}'" not in page_html:
            missing_ids.append(rid)

    print(f"Total required IDs checked: {len(required_ids)}")
    if missing_ids:
        print(f"ERROR: Missing {len(missing_ids)} IDs: {missing_ids}")
        return False
    else:
        print("PERFECT: 100% of required HTML IDs are present in the new dashboard!")

    # Write out to web/index.html
    with open("web/index.html", "w", encoding="utf-8") as out:
        out.write(page_html)

    print("Successfully compiled and written to web/index.html!")
    return True

if __name__ == "__main__":
    main()
