import os
import re
import json
import subprocess

def main():
    print("=== BUILDING YG MINIMALIST LUXURY EDITORIAL DASHBOARD ===")

    # 1. Read original backup
    with open("web/index.html.bak", "r", encoding="utf-8") as f:
        orig = f.read()

    # 2. Load required IDs
    with open("scratch/all_ids.json", "r", encoding="utf-8") as f:
        id_data = json.load(f)
    required_ids = id_data["html_ids"]
    js_ids = id_data["js_accessed_ids"]

    # 3. Extract original script
    script_start = orig.find("<script>")
    script_end = orig.rfind("</script>") + len("</script>")
    js_code = orig[script_start:script_end]

    # 4. Extract AI widget
    ai_widget_start = orig.find('<div class="ai-fab-container"', script_end)
    ai_widget_end = orig.find('</body>', ai_widget_start)
    ai_widget_html = orig[ai_widget_start:ai_widget_end].strip()

    # 5. Extract Modals
    # 5.1 walletModal
    wm_start = orig.find('<div class="modal-overlay" id="walletModal">')
    wm_end = orig.find('<!-- ============================================================ -->', wm_start)
    wallet_modal_html = orig[wm_start:wm_end].strip()

    # 5.2 announcementModal
    am_start = orig.find('<div class="modal-overlay" id="announcementModal">')
    am_end = orig.find('<!-- ============================================================ -->', am_start)
    ann_modal_html = orig[am_start:am_end].strip()

    # 5.3 rosterModal
    rm_start = orig.find('<div class="modal-overlay" id="rosterModal"')
    rm_end = orig.find('<!-- ============================================================ -->', rm_start)
    roster_modal_html = orig[rm_start:rm_end].strip()

    # 6. Extract Informational Sections
    def extract_section(tag_id):
        pattern = f'<section[^>]*id="{tag_id}"[^>]*>'
        match = re.search(pattern, orig)
        if not match:
            return ""
        s_start = match.start()
        s_end = orig.find('<!-- ============================================================ -->', s_start)
        return orig[s_start:s_end].strip()

    sec_about = extract_section("about")
    sec_workflow = extract_section("workflow")
    sec_governance = extract_section("governance")
    sec_economics = extract_section("economics")
    sec_blockchain = extract_section("blockchain")
    sec_faq = extract_section("faq")
    sec_transparency = extract_section("transparency")

    # 7. Extract Workspace Content Panels
    p_student_start = orig.find('<!-- TAB 1: SINH VIÊN')
    p_student_end = orig.find('<!-- TAB 2: BAN CÁN SỰ', p_student_start)
    panel_student_html = orig[p_student_start:p_student_end].strip()

    p_bcs_start = orig.find('<!-- TAB 2: BAN CÁN SỰ')
    p_bcs_end = orig.find('<!-- TAB 3: CỐ VẤN HỌC TẬP', p_bcs_start)
    panel_bcs_html = orig[p_bcs_start:p_bcs_end].strip()

    p_adv_start = orig.find('<!-- TAB 3: CỐ VẤN HỌC TẬP')
    p_adv_end = orig.find('<!-- TAB 4: LỊCH SỬ', p_adv_start)
    panel_adv_html = orig[p_adv_start:p_adv_end].strip()

    p_hist_start = orig.find('<!-- TAB 4: LỊCH SỬ')
    p_hist_end = orig.find('</section>', p_hist_start)
    panel_hist_html = orig[p_hist_start:p_hist_end].strip()

    # 8. Load CSS from yg_css.py
    from yg_css import generate_yg_css
    yg_css = generate_yg_css()

    # 9. Build Enhanced JS
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
      document.querySelectorAll(".sidebar-link, .nav-item-link").forEach(link => {
        link.addEventListener("click", () => {
          if (window.innerWidth <= 1024 && sidebarEl) {
            sidebarEl.classList.remove("show");
            if (backdropEl) backdropEl.classList.remove("show");
          }
        });
      });'''
    )

    # Sidebar profile sync
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
        if (sbRole) { sbRole.textContent = userAddress ? "Khách vãng lai" : "Chưa kết nối"; sbRole.className = "status-pill"; sbRole.style.background = ""; sbRole.style.color = ""; }
        if (sbAddr && userAddress) sbAddr.textContent = shortenAddress(userAddress);
        if (badge) {\n          badge.textContent = "Khách vãng lai";'''
    )

    # 10. Assemble the complete HTML
    doc = f"""<!DOCTYPE html>
<html lang="vi">

<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>KTS CLASS FUND — Cổng Thông Tin & Quản Lý Quỹ Lớp K57 Kinh Tế Số</title>
  <meta name="description"
    content="Cổng thông tin và hệ thống quản lý quỹ lớp minh bạch, ứng dụng công nghệ Smart Contract Ethereum Sepolia cho tập thể K57 ngành Kinh Tế Số.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link
    href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,400;1,600&family=Inter:wght@300;400;500;600;700;800;900&display=swap"
    rel="stylesheet">
  <!-- Ethers.js v6 CDN -->
  <script src="https://cdn.jsdelivr.net/npm/ethers@6.13.2/dist/ethers.umd.min.js"></script>
  <style>
{yg_css}
  </style>
</head>

<body>

  <!-- ============================================================ -->
  <!-- 1. TOPBAR HEADER (MINIMALIST LUXURY EDITORIAL)                -->
  <!-- ============================================================ -->
  <header class="app-topbar">
    <div class="topbar-container">
      <!-- Brand Logo & Identity -->
      <div class="brand-group">
        <a href="#dapp-workspace" class="brand-logo-mark" title="KTS Class Fund">
          K57
        </a>
        <div class="brand-titles">
          <span class="brand-main">KTS Class Fund</span>
          <span class="brand-sub">K57 Kinh Tế Số &bull; Sepolia Core</span>
        </div>
      </div>

      <!-- Main Desktop Navigation -->
      <nav class="topbar-nav" id="navLinks">
        <a href="#dapp-workspace" class="nav-item-link">01. Tổng quan</a>
        <a href="#classAnnouncementCard" class="nav-item-link">02. Thu quỹ</a>
        <a href="#dapp-workspace" onclick="switchRoleTab('student')" class="nav-item-link">03. Đóng góp</a>
        <a href="#dapp-workspace" onclick="switchRoleTab('bcs')" class="nav-item-link">04. Đề xuất chi</a>
        <a href="#dapp-workspace" onclick="switchRoleTab('advisor')" class="nav-item-link">05. Quản trị</a>
        <a href="#transparency" class="nav-item-link">06. Minh bạch</a>
        <button type="button" class="nav-roster-pill" onclick="openRosterModal()" title="Mở danh bạ lớp K57">
          👥 Danh bạ lớp <span class="badge" id="sidebarRosterBadge" style="background:var(--black-pure); color:#fff; border-radius:99px; padding:1px 6px; font-size:0.65rem;">5</span>
        </button>
      </nav>

      <!-- Actions & Wallet Buttons -->
      <div class="topbar-actions">
        <!-- Network status pill -->
        <div class="network-badge-minimal" id="networkBadge">
          <span class="network-dot-live" id="networkDot"></span>
          <span id="networkText">Sepolia Testnet</span>
        </div>

        <!-- Wallet connection CTAs -->
        <button type="button" class="btn-yg btn-yg-black" id="btnConnectWallet">
          <span>KẾT NỐI VÍ METAMASK</span>
        </button>
        <button type="button" class="btn-yg btn-yg-outline btn-sm-yg" id="btnSwitchWallet" style="display: none;">
          <span>ĐỔI VÍ</span>
        </button>
        <button type="button" class="btn-yg btn-yg-danger btn-sm-yg" id="btnDisconnectWallet" style="display: none;">
          <span>NGẮT KẾT NỐI</span>
        </button>

        <!-- Mobile Drawer Toggle -->
        <button type="button" class="btn-mobile-toggle" id="btnToggleNav" aria-label="Mở menu">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        </button>
      </div>
    </div>
  </header>

  <!-- ============================================================ -->
  <!-- 2. OFF-CANVAS MOBILE DRAWER & BACKDROP                       -->
  <!-- ============================================================ -->
  <aside class="app-sidebar" id="appSidebar">
    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:24px; padding-bottom:16px; border-bottom:var(--border-thin);">
      <div style="font-weight:800; font-size:1.1rem; text-transform:uppercase;">Menu Điều Hướng</div>
      <button type="button" onclick="document.getElementById('appSidebar').classList.remove('show'); document.getElementById('sidebarBackdrop').classList.remove('show');" style="background:none; border:none; font-size:1.4rem; cursor:pointer;">&times;</button>
    </div>

    <!-- User identity card in drawer -->
    <div style="background:var(--gray-50); border:var(--border-thin); border-radius:var(--radius-sm); padding:16px; margin-bottom:20px;">
      <div style="font-size:0.68rem; font-weight:700; text-transform:uppercase; color:var(--gray-500); margin-bottom:4px;">Tài khoản hiện hành</div>
      <div id="sidebarUserIdentity" style="font-weight:800; font-size:0.95rem; margin-bottom:4px;">Chưa kết nối ví</div>
      <div style="display:flex; align-items:center; gap:8px;">
        <span class="status-pill" id="sidebarRoleBadge" style="font-size:0.7rem;">Chưa xác thực</span>
        <span id="sidebarWalletShort" style="font-family:monospace; font-size:0.75rem; color:var(--gray-600);">--</span>
      </div>
    </div>

    <!-- Navigation links -->
    <div style="display:flex; flex-direction:column; gap:12px; margin-bottom:24px;">
      <a href="#dapp-workspace" class="sidebar-link" style="font-weight:700; font-size:0.9rem; text-transform:uppercase; padding:8px 0; border-bottom:1px solid var(--gray-100);">01. Tổng quan</a>
      <a href="#classAnnouncementCard" class="sidebar-link" style="font-weight:700; font-size:0.9rem; text-transform:uppercase; padding:8px 0; border-bottom:1px solid var(--gray-100);">02. Thu quỹ lớp</a>
      <a href="#dapp-workspace" onclick="switchRoleTab('student')" class="sidebar-link" style="font-weight:700; font-size:0.9rem; text-transform:uppercase; padding:8px 0; border-bottom:1px solid var(--gray-100);">03. Đóng góp & Hoàn tiền</a>
      <a href="#dapp-workspace" onclick="switchRoleTab('bcs')" class="sidebar-link" style="font-weight:700; font-size:0.9rem; text-transform:uppercase; padding:8px 0; border-bottom:1px solid var(--gray-100);">04. Đề xuất chi tiêu</a>
      <a href="#dapp-workspace" onclick="switchRoleTab('advisor')" class="sidebar-link" style="font-weight:700; font-size:0.9rem; text-transform:uppercase; padding:8px 0; border-bottom:1px solid var(--gray-100);">05. Quản trị CVHT</a>
      <a href="#transparency" class="sidebar-link" style="font-weight:700; font-size:0.9rem; text-transform:uppercase; padding:8px 0; border-bottom:1px solid var(--gray-100);">06. Minh bạch On-chain</a>
      <button type="button" onclick="openRosterModal()" style="text-align:left; background:none; border:none; font-weight:700; font-size:0.9rem; text-transform:uppercase; padding:8px 0; cursor:pointer; color:var(--accent-blue);">👥 Mở Danh bạ Lớp K57</button>
    </div>

    <div style="margin-top:auto; font-size:0.75rem; color:var(--gray-500); border-top:var(--border-thin); padding-top:16px;">
      Sepolia Contract: <a href="https://sepolia.etherscan.io/address/0xfe3ec1a75503Da9ddFd44aEBE18E461686376b52" target="_blank" style="color:var(--accent-blue);">0xfe3e...6b52</a>
    </div>
  </aside>
  <div class="sidebar-backdrop" id="sidebarBackdrop"></div>

  <!-- ============================================================ -->
  <!-- 3. MAIN APPLICATION CONTAINER                                -->
  <!-- ============================================================ -->
  <main class="app-main">

    <!-- ========================================================== -->
    <!-- SECTION A: HERO & QUICK CONTROL                            -->
    <!-- ========================================================== -->
    <section class="hero-editorial" id="dapp-workspace">
      <div class="hero-top-row">
        <div class="hero-header-text">
          <div class="editorial-tag">HỆ THỐNG QUẢN LÝ QUỸ LỚP PHI TẬP TRUNG &bull; ETHEREUM SEPOLIA</div>
          <h1 class="hero-title-giant">CỔNG THÔNG TIN &amp; QUẢN LÝ QUỸ LỚP K57</h1>
          <p class="hero-sub-editorial">
            Minh bạch hóa tài chính lớp K57 ngành Kinh Tế Số bằng Smart Contract bất biến. Toàn bộ dòng tiền được phân bổ tự động theo quy tắc 99% Quỹ lớp và 1% Phí vận hành, phê duyệt chi tiêu dân chủ qua cơ chế biểu quyết 51% của Ban cán sự.
          </p>
        </div>

        <!-- Verified Identity Card -->
        <div class="hero-user-badge-card">
          <div class="user-card-label">TRẠNG THÁI DANH TÍNH VÍ</div>
          <div class="user-card-name" id="studentIdentityName">Chưa kết nối ví</div>
          <div class="user-card-meta">
            <span class="status-pill" id="userRoleBadge">Khách vãng lai</span>
            <span class="user-card-address" id="userWalletAddress">0x0000...0000</span>
          </div>
        </div>
      </div>

      <!-- Quick Contract Address Strip -->
      <div class="quick-contract-strip">
        <div class="contract-label-group">
          <span style="font-size:0.75rem; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:var(--gray-600);">Hợp đồng (Sepolia):</span>
          <input type="text" class="contract-input-pill" id="quickContractAddress" value="0xfe3ec1a75503Da9ddFd44aEBE18E461686376b52" spellcheck="false" title="Địa chỉ Contract Sepolia">
        </div>
        <div class="contract-actions">
          <button type="button" class="btn-yg btn-yg-black btn-sm-yg" id="btnSaveQuickContract">Áp dụng</button>
          <button type="button" class="btn-yg btn-yg-outline btn-sm-yg" id="btnResetContract">Mặc định</button>
          <button type="button" class="btn-yg btn-yg-outline btn-sm-yg" id="btnCopyContract">Sao chép</button>
          <a href="https://sepolia.etherscan.io/address/0xfe3ec1a75503Da9ddFd44aEBE18E461686376b52" target="_blank" rel="noopener noreferrer" class="btn-yg btn-yg-outline btn-sm-yg" id="explorerLink" title="Xem trên Sepolia Etherscan">Etherscan &nearr;</a>
        </div>
      </div>

      <!-- Guest Warning Banner (Hidden when authorized) -->
      <div class="guest-warning-editorial" id="guestWarningBanner">
        <div style="display:flex; align-items:center; gap:10px;">
          <span style="font-size:1.1rem;">⚠️</span>
          <span><strong>Chế độ xem công khai:</strong> Bạn đang truy cập với tư cách Khách vãng lai. Hãy kết nối ví MetaMask đã đăng ký trong Danh bạ lớp K57 để nộp quỹ, tạo đề xuất hoặc tham gia biểu quyết.</span>
        </div>
        <button type="button" class="btn-yg btn-yg-black btn-sm-yg" onclick="connectWallet()">Kết nối ví</button>
      </div>
    </section>

    <!-- ========================================================== -->
    <!-- SECTION B: CLASS ANNOUNCEMENT BOX                          -->
    <!-- ========================================================== -->
    <section class="announcement-box-editorial" id="classAnnouncementCard">
      <div class="ann-header-row">
        <div>
          <div class="editorial-tag">THÔNG BÁO THU QUỸ ĐỊNH KỲ</div>
          <h2 class="ann-title-main" id="annTitle">Đợt thu quỹ học kỳ 1 — Năm học 2024-2025</h2>
        </div>
        <div style="display:flex; align-items:center; gap:10px;">
          <span class="status-pill status-ready" id="annStatusTag">ĐANG MỞ THU</span>
          <span style="font-size:0.8rem; color:var(--gray-500);" id="annStatusText">Hạn chót còn hiệu lực</span>
        </div>
      </div>

      <!-- Live metrics ribbon -->
      <div class="ann-stats-ribbon">
        <div class="ann-stat-item">
          <span class="ann-stat-lbl">Mức đóng quy định</span>
          <span class="ann-stat-val" id="annAmount">0.0500 ETH / SV</span>
        </div>
        <div class="ann-stat-item">
          <span class="ann-stat-lbl">Hạn chót nộp quỹ</span>
          <span class="ann-stat-val" id="annDeadline">--/--/----</span>
        </div>
        <div class="ann-stat-item">
          <span class="ann-stat-lbl">Sĩ số lớp K57</span>
          <span class="ann-stat-val" id="annClassSize">5 sinh viên</span>
        </div>
        <div class="ann-stat-item">
          <span class="ann-stat-lbl">Mục đích sử dụng</span>
          <span class="ann-stat-val" id="annPurpose" style="font-size:0.9rem; font-weight:600;">Chi hoạt động phong trào, in ấn tài liệu</span>
        </div>
      </div>

      <!-- Progress bar -->
      <div class="ann-progress-wrapper">
        <div class="ann-progress-labels">
          <span>Tiến độ nộp quỹ của lớp</span>
          <span id="annProgressText">Đang tải dữ liệu on-chain...</span>
        </div>
        <div class="ann-progress-track">
          <div class="ann-progress-fill" id="annProgressBar" style="width: 0%;"></div>
        </div>
      </div>

      <div style="display:flex; justify-content:flex-end;">
        <button type="button" class="btn-yg btn-yg-black" id="btnBannerQuickDeposit" onclick="switchRoleTab('student')">
          <span>NỘP QUỸ NGAY &rarr;</span>
        </button>
      </div>
    </section>

    <!-- ========================================================== -->
    <!-- SECTION C: OVERVIEW METRICS (EDITORIAL HIGH IMPACT)        -->
    <!-- ========================================================== -->
    <section>
      <div style="margin-bottom:16px;">
        <div class="editorial-tag">CHỈ SỐ TỔNG QUAN ON-CHAIN</div>
        <h2 style="font-size:1.6rem; font-weight:800; text-transform:uppercase; margin-top:4px;">TỔNG QUAN TÀI CHÍNH QUỸ LỚP</h2>
      </div>

      <div class="metrics-editorial-grid">
        <!-- 01. Tổng số dư hợp đồng -->
        <div class="metric-card-editorial">
          <div class="metric-header">
            <span class="metric-card-tag">01. Tổng số dư Hợp đồng</span>
            <span class="metric-card-icon">🏛️</span>
          </div>
          <div>
            <div class="metric-number-giant" id="metricContractBalance">--.----</div>
            <span class="metric-unit-text">ETH</span>
          </div>
          <div class="metric-sub-note">Tổng tài sản thực tế lưu ký tại địa chỉ Smart Contract</div>
        </div>

        <!-- 02. Quỹ lớp khả dụng -->
        <div class="metric-card-editorial">
          <div class="metric-header">
            <span class="metric-card-tag">02. Quỹ lớp khả dụng</span>
            <span class="metric-card-icon">💰</span>
          </div>
          <div>
            <div class="metric-number-giant" id="metricAvailableFund">--.----</div>
            <span class="metric-unit-text">ETH</span>
          </div>
          <div class="metric-sub-note">
            Số dư chính: <strong id="metricClassFund">--.---- ETH</strong> (trừ các khoản chi đang chờ)
          </div>
        </div>

        <!-- 03. Quỹ phí vận hành 1% -->
        <div class="metric-card-editorial">
          <div class="metric-header">
            <span class="metric-card-tag">03. Phí vận hành (1%)</span>
            <span class="metric-card-icon">⚡</span>
          </div>
          <div>
            <div class="metric-number-giant" id="metricAdminFee">--.----</div>
            <span class="metric-unit-text">ETH</span>
          </div>
          <div class="metric-sub-note">Quỹ phụ cấp Gas bù đắp cho Cố vấn học tập quản trị</div>
        </div>

        <!-- 04. Đề xuất chi đang chờ -->
        <div class="metric-card-editorial">
          <div class="metric-header">
            <span class="metric-card-tag">04. Đề xuất chi tiêu</span>
            <span class="metric-card-icon">📋</span>
          </div>
          <div>
            <div class="metric-number-giant" id="metricSpendCount">--</div>
            <span class="metric-unit-text">yêu cầu</span>
          </div>
          <div class="metric-sub-note">Các đề xuất chi đang chờ Ban cán sự biểu quyết</div>
        </div>

        <!-- 05. Yêu cầu hoàn tiền -->
        <div class="metric-card-editorial">
          <div class="metric-header">
            <span class="metric-card-tag">05. Yêu cầu hoàn tiền</span>
            <span class="metric-card-icon">🔄</span>
          </div>
          <div>
            <div class="metric-number-giant" id="metricRefundCount">--</div>
            <span class="metric-unit-text">yêu cầu</span>
          </div>
          <div class="metric-sub-note">Đơn xin rút tiền nộp nhầm/thừa đang được xem xét</div>
        </div>

        <!-- 06. Sĩ số lớp đồng bộ -->
        <div class="metric-card-editorial">
          <div class="metric-header">
            <span class="metric-card-tag">06. Sĩ số lớp K57</span>
            <span class="metric-card-icon">👥</span>
          </div>
          <div>
            <div class="metric-number-giant" id="metricTotalMembers">5</div>
            <span class="metric-unit-text">sinh viên</span>
          </div>
          <div class="metric-sub-note">Đồng bộ tự động theo Danh bạ sinh viên bảo mật</div>
        </div>
      </div>
    </section>

    <!-- ========================================================== -->
    <!-- SECTION D: WORKSPACE ROLES (TAB CONTROLS & CONTENT)        -->
    <!-- ========================================================== -->
    <section class="workspace-section">
      <!-- Tab Header Navigation -->
      <div class="workspace-tab-nav">
        <button type="button" class="workspace-tab-btn active" id="btnRoleStudent" onclick="switchRoleTab('student')">
          <span>🎓</span> <span>Sinh viên: Nộp &amp; Hoàn quỹ</span>
        </button>
        <button type="button" class="workspace-tab-btn" id="btnRoleBCS" onclick="switchRoleTab('bcs')">
          <span>👥</span> <span>Ban cán sự: Đề xuất &amp; Biểu quyết</span>
        </button>
        <button type="button" class="workspace-tab-btn" id="btnRoleAdvisor" onclick="switchRoleTab('advisor')">
          <span>🏛️</span> <span>Cố vấn: Quản trị &amp; Phí</span>
        </button>
        <button type="button" class="workspace-tab-btn" id="btnRoleHistory" onclick="switchRoleTab('history')">
          <span>📜</span> <span>Sổ cái &amp; Lịch sử On-chain</span>
        </button>
      </div>

      <!-- Panel Body Container -->
      <div class="workspace-panel-body">

        <!-- TAB 1: SINH VIÊN -->
        <div class="role-panel-content active" id="panelStudent">
{panel_student_html}
        </div>

        <!-- TAB 2: BAN CÁN SỰ -->
        <div class="role-panel-content" id="panelBCS">
{panel_bcs_html}
        </div>

        <!-- TAB 3: CỐ VẤN HỌC TẬP -->
        <div class="role-panel-content" id="panelAdvisor">
{panel_adv_html}
        </div>

        <!-- TAB 4: LỊCH SỬ & SỔ CÁI -->
        <div class="role-panel-content" id="panelHistory">
{panel_hist_html}
        </div>

      </div>
    </section>

    <!-- ========================================================== -->
    <!-- SECTION E: INFORMATIONAL & GOVERNANCE SECTIONS             -->
    <!-- ========================================================== -->
    <div style="display:flex; flex-direction:column; gap:40px;">
{sec_about}

{sec_workflow}

{sec_governance}

{sec_economics}

{sec_blockchain}

{sec_faq}

{sec_transparency}
    </div>

  </main>

  <!-- ============================================================ -->
  <!-- 4. SITE FOOTER                                               -->
  <!-- ============================================================ -->
  <footer class="site-footer-editorial">
    <div class="footer-container">
      <div class="footer-brand">
        <span class="footer-brand-title">KTS Class Fund — K57 Kinh Tế Số</span>
        <span class="footer-brand-copy">&copy; 2024-2025 Khoa Kinh Tế Số &bull; Hệ thống quản lý tài chính minh bạch trên Ethereum Sepolia</span>
      </div>
      <div style="display:flex; align-items:center; gap:16px; font-size:0.8rem; color:var(--gray-600);">
        <span>Contract: <code style="font-family:monospace; background:var(--gray-100); padding:2px 6px; border-radius:4px;">0xfe3ec1a75503Da9ddFd44aEBE18E461686376b52</code></span>
        <a href="https://sepolia.etherscan.io/address/0xfe3ec1a75503Da9ddFd44aEBE18E461686376b52" target="_blank" rel="noopener noreferrer" style="color:var(--accent-blue); font-weight:600;">Sepolia Explorer &nearr;</a>
      </div>
    </div>
  </footer>

  <!-- ============================================================ -->
  <!-- 5. MODALS PRESERVED VERBATIM                                 -->
  <!-- ============================================================ -->
{wallet_modal_html}

{ann_modal_html}

{roster_modal_html}

  <!-- ============================================================ -->
  <!-- 6. JAVASCRIPT LOGIC                                          -->
  <!-- ============================================================ -->
{enhanced_js}

  <!-- ============================================================ -->
  <!-- 7. FLOATING AI ASSISTANT CHAT WIDGET                         -->
  <!-- ============================================================ -->
{ai_widget_html}

</body>
</html>
"""

    # 11. Write output file
    target_path = "web/index.html"
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"Generated {target_path} successfully ({len(doc)} characters).")

    # 12. Verification: Check IDs
    with open(target_path, "r", encoding="utf-8") as f:
        new_content = f.read()

    new_html_ids = set(re.findall(r'id=["\']([a-zA-Z0-9_\-]+)["\']', new_content))
    missing_required = [rid for rid in required_ids if rid not in new_html_ids]
    print(f"Total HTML IDs in new file: {len(new_html_ids)}")
    print(f"Missing required IDs from original backup: {missing_required}")

    if missing_required:
        print("ERROR: Some required IDs are missing! Check carefully.")
    else:
        print("SUCCESS: 100% of required IDs are preserved!")

    return len(missing_required) == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
