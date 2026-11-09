import re

with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

with open('scratch/js_ids.txt', 'r', encoding='utf-8') as f:
    js_ids = [line.strip() for line in f if line.strip()]

topbar_start = html.find('    <header class="app-topbar">')
workspace_start = html.find('      <!-- 3 Ô GIAO DIỆN THEO 3 VAI TRÒ -->')

assert topbar_start != -1, "topbar_start not found"
assert workspace_start != -1, "workspace_start not found"

new_section = """    <!-- TOPBAR MỚI (THANH TRÊN CÙNG SÁNG, CAO 68PX) -->
    <header class="app-topbar app-topbar-modern" id="appTopbarModern">
      <div class="topbar-brand">
        <!-- Nút toggle sidebar cũ được giữ trong DOM nhưng ẩn bằng CSS -->
        <button class="menu-toggle" id="btnToggleNav" style="display:none;" aria-label="Mở menu">☰</button>
        <img src="logo1.png" alt="Logo KTS Class Fund" class="topbar-brand-logo">
        <div class="topbar-brand-text">
          <div class="topbar-brand-title">KTS CLASS FUND</div>
          <div class="topbar-brand-sub">Lớp K57 Kinh Tế Số &bull; ECO2432</div>
        </div>
      </div>

      <!-- Menu giữa: Trang chủ · Đề xuất · Sổ quỹ · Thành viên · Hướng dẫn -->
      <nav class="topbar-center-nav" id="topbarNav">
        <a href="#hero" class="nav-pill-item active">
          <svg style="width:16px;height:16px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>
          <span>Trang chủ</span>
        </a>
        <a href="#dapp-workspace" onclick="selectRoleView('bcs')" class="nav-pill-item">
          <svg style="width:16px;height:16px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
          <span>Đề xuất</span>
        </a>
        <a href="#dapp-workspace" onclick="selectRoleView('history')" class="nav-pill-item">
          <svg style="width:16px;height:16px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><line x1="12" y1="20" x2="12" y2="10"></line><line x1="18" y1="20" x2="18" y2="4"></line><line x1="6" y1="20" x2="6" y2="16"></line></svg>
          <span>Sổ quỹ</span>
        </a>
        <a href="javascript:void(0)" onclick="openRosterModal()" class="nav-pill-item">
          <svg style="width:16px;height:16px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
          <span>Thành viên</span>
        </a>
        <a href="#faq" class="nav-pill-item">
          <svg style="width:16px;height:16px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
          <span>Hướng dẫn</span>
        </a>
      </nav>

      <!-- Bên phải: Chip mạng Sepolia + MỘT Chip ví duy nhất -->
      <div class="topbar-right-controls">
        <div class="chip-network-sepolia" id="networkBadge">
          <span class="chip-network-dot" id="networkDot"></span>
          <span id="networkText">Sepolia</span>
        </div>

        <div class="unified-wallet-container" id="unifiedWalletContainer" style="position: relative;">
          <!-- Nút kết nối ban đầu -->
          <button class="btn btn-primary btn-sm" id="btnConnectWallet" title="Bấm để kết nối hoặc đổi tài khoản">
            <svg style="width:16px;height:16px;fill:currentColor;" viewBox="0 0 24 24">
              <path d="M21 7.28V5c0-1.1-.9-2-2-2H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2v-2.28c.59-.35 1-.98 1-1.72V9c0-.74-.41-1.37-1-1.72zM20 9v6h-7V9h7zM5 19V5h14v2h-6c-1.1 0-2 .9-2 2v6c0 1.1.9 2 2 2h6v2H5z" />
            </svg>
            <span id="walletBtnText">Kết nối MetaMask</span>
          </button>

          <!-- Chip ví duy nhất (Avatar chữ cái + Vai trò + Địa chỉ rút gọn) -->
          <div class="unified-wallet-chip" id="unifiedWalletChip" style="display: none;" onclick="toggleWalletDropdown(event)">
            <div class="wallet-avatar-circle" id="walletAvatarLetter">K</div>
            <div class="wallet-chip-info">
              <span class="wallet-chip-role" id="walletChipRoleTitle">Sinh viên K57</span>
              <span class="wallet-chip-address" id="walletChipAddressShort">0x0000...0000</span>
            </div>
            <span class="wallet-chip-caret">▾</span>
          </div>

          <!-- Menu thả xuống của chip ví -->
          <div class="wallet-dropdown-menu" id="walletDropdownMenu">
            <div class="wallet-dropdown-header">
              <div class="wallet-dropdown-header-title">Tài khoản ví Web3</div>
              <div class="wallet-dropdown-header-name" id="walletDropdownUserName">Chưa kết nối</div>
              <span class="badge-topbar-role" id="topbarRoleBadge" style="display:none;"></span>
            </div>
            <button class="wallet-dropdown-item" id="btnSwitchWallet" type="button" onclick="switchAccount()">
              <svg style="width:16px;height:16px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path><path d="m9 11 3 3L22 4"></path></svg>
              <span>Đổi ví</span>
            </button>
            <button class="wallet-dropdown-item" id="btnVerifyWalletAuth" type="button" style="display:none;" onclick="authenticateWalletSession(true)">
              <svg style="width:16px;height:16px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
              <span>Ký xác thực</span>
            </button>
            <button class="wallet-dropdown-item danger" id="btnDisconnectWallet" type="button" onclick="disconnectWallet()">
              <svg style="width:16px;height:16px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>
              <span>Đăng xuất</span>
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="app-content">
      <!-- 2.a LỜI CHÀO LỚN -->
      <div class="home-welcome-section">
        <div class="welcome-greeting-title" id="welcomeGreetingTitle">
          Chào mừng trở lại, <span id="welcomeRoleDisplay">Bạn</span>
        </div>
        <div class="welcome-greeting-sub">
          Hệ thống Quỹ Lớp K57 Kinh Tế Số &bull; ECO2432 &bull; <span id="welcomeIdentityDisplay">Chưa kết nối ví</span>
        </div>
      </div>

      <!-- 2.b KHỐI HERO HOÀNH TRÁNG -->
      <section class="grand-hero-container" id="hero">
        <div class="grand-hero-card">
          <div class="hero-balance-label">
            <svg style="width:18px;height:18px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>
            <span>Quỹ Lớp Hiện Có</span>
          </div>
          <div class="hero-balance-display">
            <span class="hero-balance-number" id="metricClassFund">- ETH</span>
          </div>

          <!-- 3 thẻ kính mờ trong Hero -->
          <div class="hero-glass-row">
            <div class="hero-glass-card">
              <div class="hero-glass-title">Khả dụng (Net 99%)</div>
              <div class="hero-glass-val" id="heroGlassAvailable">0.0000 ETH</div>
              <div class="hero-glass-sub" id="metricClassFundNote">Sẵn sàng phục vụ lớp</div>
            </div>
            <div class="hero-glass-card">
              <div class="hero-glass-title">Đang giữ chỗ</div>
              <div class="hero-glass-val" id="heroGlassReserved">0.0000 ETH</div>
              <div class="hero-glass-sub">Khóa cho chi / hoàn</div>
            </div>
            <div class="hero-glass-card">
              <div class="hero-glass-title">Quỹ vận hành (1%)</div>
              <div class="hero-glass-val" id="metricAdminFee">- ETH</div>
              <div class="hero-glass-sub" id="metricAdminFeeNote">Hoàn gas tự động EIP-1559</div>
            </div>
          </div>

          <!-- 2 nút hành động trên Hero -->
          <div class="hero-action-buttons">
            <button class="btn btn-hero-deposit" id="btnHeroDeposit" type="button" onclick="handleQuickAction('deposit')">
              <svg style="width:18px;height:18px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 8 12 12 14 14"></polyline></svg>
              <span>Nạp quỹ ngay</span>
            </button>
            <button class="btn btn-hero-spend" id="btnHeroSpend" type="button" onclick="handleQuickAction('spend')">
              <svg style="width:18px;height:18px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
              <span>Đề xuất chi</span>
            </button>
          </div>
        </div>
      </section>

      <!-- 2-COLUMN LAYOUT (MAIN LEFT + 360PX RIGHT RAIL) -->
      <div class="home-layout-grid">
        <!-- CỘT TRÁI (MAIN) -->
        <div class="home-left-col">
          <!-- 2.c LƯỚI "BẠN MUỐN LÀM GÌ?" (6 Ô LỚN CÓ ICON) -->
          <div class="action-service-section">
            <div class="section-headline-title">
              <svg style="width:20px;height:20px;color:var(--primary);" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
              <span>Bạn muốn làm gì?</span>
            </div>
            <div class="action-service-grid">
              <!-- Ô 1: Nạp quỹ -->
              <div class="action-service-card" id="cardActionDeposit" onclick="handleQuickAction('deposit')">
                <div class="action-service-icon-box">
                  <svg style="width:22px;height:22px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect><line x1="1" y1="10" x2="23" y2="10"></line></svg>
                </div>
                <div class="action-service-title">Nạp quỹ</div>
                <div class="action-service-desc">Đóng góp ETH vào Quỹ lớp K57 (Net 99%)</div>
              </div>

              <!-- Ô 2: Xin hoàn tiền -->
              <div class="action-service-card" id="cardActionRefund" onclick="handleQuickAction('refund')">
                <div class="action-service-icon-box">
                  <svg style="width:22px;height:22px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path><path d="M3 3v5h5"></path></svg>
                </div>
                <div class="action-service-title">Xin hoàn tiền</div>
                <div class="action-service-desc">Rút lại tiền khi nạp nhầm trong hạn mức Net</div>
              </div>

              <!-- Ô 3: Đề xuất chi (BCS) -->
              <div class="action-service-card" id="cardActionSpend" onclick="handleQuickAction('spend')">
                <div class="action-service-icon-box">
                  <svg style="width:22px;height:22px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                </div>
                <div class="action-service-title">Đề xuất chi</div>
                <div class="action-service-desc">Khởi tạo khoản chi tập thể lớp để BCS biểu quyết</div>
              </div>

              <!-- Ô 4: Biểu quyết (BCS & CVHT) -->
              <div class="action-service-card" id="cardActionVote" onclick="handleQuickAction('vote')">
                <div class="action-service-icon-box">
                  <svg style="width:22px;height:22px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><polyline points="9 11 12 14 22 4"></polyline><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path></svg>
                </div>
                <div class="action-service-title">Biểu quyết</div>
                <div class="action-service-desc">Tham gia bỏ phiếu duyệt chi / hoàn tiền (&ge; 51%)</div>
              </div>

              <!-- Ô 5: Sổ dòng tiền -->
              <div class="action-service-card" id="cardActionLedger" onclick="selectRoleView('history')">
                <div class="action-service-icon-box">
                  <svg style="width:22px;height:22px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>
                </div>
                <div class="action-service-title">Sổ dòng tiền</div>
                <div class="action-service-desc">Nhật ký 4 luồng thu chi minh bạch trên blockchain</div>
              </div>

              <!-- Ô 6: Thành viên -->
              <div class="action-service-card" id="cardActionMembers" onclick="openRosterModal()">
                <div class="action-service-icon-box">
                  <svg style="width:22px;height:22px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="8.5" cy="7" r="4"></circle><line x1="20" y1="8" x2="20" y2="14"></line><line x1="23" y1="11" x2="17" y2="11"></line></svg>
                </div>
                <div class="action-service-title">Thành viên</div>
                <div class="action-service-desc">Tra cứu danh bạ lớp K57 &amp; tiến độ nộp quỹ</div>
              </div>

              <!-- Ô 7: Quản trị (Dành riêng cho CVHT) -->
              <div class="action-service-card" id="cardActionGovernance" style="display:none;" onclick="selectRoleView('advisor')">
                <div class="action-service-icon-box" style="background:#f5f3ff; color:#6d28d9;">
                  <svg style="width:22px;height:22px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
                </div>
                <div class="action-service-title">Quản trị CVHT</div>
                <div class="action-service-desc">Bổ nhiệm BCS, điều chuyển phí &amp; danh bạ on-chain</div>
              </div>
            </div>
          </div>

          <!-- 2.d "VIỆC CẦN BẠN XỬ LÝ" -->
          <section class="pending-actions-section" id="pendingActionsSection">
            <div class="pending-actions-card">
              <div class="pending-actions-header">
                <div class="pending-header-title">
                  <svg style="width:20px;height:20px;color:var(--primary);" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                  <div>
                    <h3 class="pending-title">Việc cần bạn xử lý</h3>
                    <p class="pending-subtitle">Tác vụ theo thời gian thực dựa trên trạng thái hợp đồng thông minh và vai trò</p>
                  </div>
                </div>
                <div class="pending-header-actions">
                  <span class="pending-count-badge all-clear" id="pendingCountBadge">0 việc cần xử lý</span>
                  <button class="btn btn-sm btn-outline" type="button" onclick="refreshContractData()" title="Làm mới tác vụ on-chain">🔄 Cập nhật</button>
                </div>
              </div>
              <div class="pending-actions-list" id="pendingActionsList">
                <div class="pending-all-clear">
                  <div class="all-clear-icon">✨</div>
                  <div class="all-clear-content">
                    <h4>Đang tải dữ liệu tác vụ on-chain...</h4>
                    <p>Hệ thống đang đồng bộ dữ liệu để kiểm tra các việc cần xử lý theo vai trò của bạn.</p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <!-- KHU VỰC CÀI ĐẶT NÂNG CAO CHO CỐ VẤN (COLLAPSIBLE ACCORDION) -->
          <div id="sectionAdvancedSettings" class="advanced-accordion-wrapper" style="display: none;">
            <details class="advanced-details-box" style="background:#fff; border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:16px 20px; box-shadow:var(--shadow-card);">
              <summary class="advanced-summary-btn" style="list-style:none; display:flex; justify-content:space-between; align-items:center; cursor:pointer;">
                <span style="display:flex; align-items:center; gap:8px; font-weight:700; color:var(--text-main);">
                  <svg style="width:18px;height:18px;color:var(--primary);" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
                  <span>Cài đặt &amp; Quản trị kỹ thuật nâng cao (Dành riêng cho Cố vấn)</span>
                </span>
                <span class="advanced-caret" style="color:var(--text-muted); font-size:0.85rem;">Chi tiết ▾</span>
              </summary>
              <div style="margin-top:14px; padding-top:14px; border-top:1px dashed var(--border-color);">
                <div class="contract-toolbar-row" style="margin-bottom:12px;">
                  <div class="contract-input-bar">
                    <input type="text" id="quickContractAddress" placeholder="Dán địa chỉ Hợp đồng (0x...)">
                  </div>
                  <button class="btn btn-sm btn-primary" id="btnSaveQuickContract" type="button" title="Lưu và tải hợp đồng">Lưu &amp; Tải</button>
                  <button class="btn btn-sm btn-outline" id="btnResetQuickContract" type="button" onclick="resetToDefaultContract()" title="Khôi phục mặc định">🔄 Đặt lại</button>
                  <div class="quick-status-item-btn" id="itemRosterModalBtn" style="display: none; margin-left: auto;">
                    <button class="btn btn-sm btn-outline" id="btnOpenRosterModal" type="button" onclick="openRosterModal()">
                      <span>📋</span> Quản lý Danh bạ K57 (<span id="rosterCountBadge">--</span>)
                    </button>
                  </div>
                </div>
              </div>
            </details>
          </div>

          <!-- HIDDEN LEGACY ANCHOR CONTAINER: BẢO VỆ 100% ID CŨ CHO JAVASCRIPT -->
          <div id="legacyDomAnchorWrapper" style="display:none !important;" aria-hidden="true">
            <span id="quickWalletAccount">Chưa kết nối</span>
            <span id="quickRoleBadge">Chưa kết nối</span>
            <span id="quickStudentIdentity">--</span>
            <span id="quickNetworkStatus"></span>
            <button id="btnQuickSwitch" onclick="switchAccount()"></button>
            <button id="btnQuickDisconnect" onclick="disconnectWallet()"></button>
            <div id="guestWarningBanner"></div>
            <span id="metricDepositorsCount">-</span>
            <span id="metricDepositorsNote"></span>
            <span id="metricSpendCount">-</span>
            <span id="metricRefundCount">-</span>
            <span id="metricActiveBCS">-</span>
            <span id="metricActiveBCSNote"></span>
          </div>
        </div>

        <!-- CỘT PHẢI (RIGHT RAIL 360PX) -->
        <div class="home-right-rail">
          <!-- THẺ 1: ĐỢT THU ĐANG MỞ -->
          <div class="rail-card class-announcement-card" id="classAnnouncementCard">
            <div class="rail-card-title">
              <span style="display:flex; align-items:center; gap:7px;">
                <svg style="width:17px;height:17px;color:var(--primary);" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
                <span>Đợt thu đang mở</span>
              </span>
              <span class="ann-status-tag" id="annStatusTag"><span class="ann-dot-pulse"></span> <span id="annStatusText">Chưa có đợt thu</span></span>
            </div>

            <!-- CONTAINER TIẾN ĐỘ ĐA THÔNG BÁO -->
            <div id="activeProgressCardsContainer" style="display: flex; flex-direction: column; gap: 12px; margin-bottom: 14px;">
              <!-- Được render động bởi renderMultipleProgressCards() -->
            </div>

            <!-- Trạng thái cá nhân -->
            <div class="ann-personal-status-box" id="annPersonalStatusBox"
              style="padding: 10px 12px; background: var(--bg-page); border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); display: flex; flex-direction:column; gap: 6px;">
              <div style="font-size: 0.82rem; display: flex; align-items: center; justify-content:space-between;">
                <span style="font-weight: 700; color: var(--text-main);">Trạng thái của bạn:</span>
                <span id="annPersonalStatusBadge" class="task-badge status-unverified">Chưa kết nối</span>
              </div>
              <span id="annPersonalStatusDesc" style="font-size: 0.76rem; color: var(--text-muted);">Kết nối ví MetaMask để kiểm tra trạng thái</span>
            </div>

            <div style="display:flex; gap:8px; margin-top:14px; flex-wrap:wrap;">
              <button class="btn btn-sm btn-primary" id="btnBannerQuickDeposit" style="display:none; width:100%;">
                ⚡ Nộp quỹ cho đợt này
              </button>
              <button class="btn btn-sm btn-outline" id="btnToggleAnnHistory" type="button" style="width:100%; font-size:0.8rem;" title="Xem lịch sử">
                📜 Lịch sử đợt thu (<span id="annHistoryCountBadge">0</span>)
              </button>
              <button class="btn btn-sm btn-purple" id="btnOpenAnnModal" type="button" style="display:none; width:100%; font-size:0.8rem;">
                ➕ Tạo đợt thu mới (BCS)
              </button>
            </div>
          </div>

          <!-- MỤC LỊCH SỬ THÔNG BÁO THU QUỸ ĐÃ HOÀN THÀNH -->
          <div class="rail-card" id="annHistoryCard" style="display:none;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid var(--border-color);">
              <strong style="font-size:0.88rem; color:var(--text-main);">📁 Lịch sử kêu gọi nộp quỹ</strong>
              <button class="btn btn-sm btn-secondary" id="btnCloseAnnHistory" type="button" style="padding:2px 8px; font-size:0.75rem;">✕</button>
            </div>
            <div id="annHistoryListContainer" style="display: flex; flex-direction: column; gap: 10px;"></div>
          </div>

          <!-- THẺ 2: HOẠT ĐỘNG GẦN ĐÂY -->
          <div class="rail-card" id="cardRecentActivitiesRail">
            <div class="rail-card-title">
              <span style="display:flex; align-items:center; gap:7px;">
                <svg style="width:17px;height:17px;color:var(--primary);" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
                <span>Hoạt động gần đây</span>
              </span>
              <a href="javascript:void(0)" onclick="selectRoleView('history')" style="font-size:0.78rem; font-weight:600; color:var(--primary); text-decoration:none;">Xem tất cả &rarr;</a>
            </div>
            <div class="rail-activity-list" id="railRecentActivityList">
              <div style="font-size:0.82rem; color:var(--text-muted); text-align:center; padding:12px 0;">Đang tải dữ liệu on-chain...</div>
            </div>
          </div>

          <!-- THẺ 3: TRỢ LÝ AI QUỸ LỚP -->
          <div class="rail-card rail-ai-promo-card" id="cardAiAssistantRail">
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
              <div style="width:36px; height:36px; border-radius:10px; background:#0B6B57; color:#fff; display:flex; align-items:center; justify-content:center;">
                <svg style="width:20px;height:20px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"></path></svg>
              </div>
              <div>
                <div style="font-weight:700; color:var(--primary-dark); font-size:0.95rem;">Trợ lý AI Quỹ Lớp</div>
                <div style="font-size:0.75rem; color:var(--text-muted);">Tư vấn quy chế &amp; đối soát số dư</div>
              </div>
            </div>
            <p style="font-size:0.8rem; color:var(--text-muted); line-height:1.5; margin-bottom:14px;">
              Hỏi đáp tức thì về quy trình hoàn tiền Net 99%, ngưỡng biểu quyết 51% và số dư on-chain thời gian thực.
            </p>
            <button class="btn btn-primary" type="button" style="width:100%; font-size:0.85rem;" onclick="document.getElementById('aiFabToggle').click()">
              ✨ Hỏi Trợ lý AI ngay
            </button>
          </div>
        </div>
      </div>
"""

# Perform replacement
modified_html = html[:topbar_start] + new_section + html[workspace_start:]

# Check missing IDs
missing = [i for i in js_ids if f'id="{i}"' not in modified_html and f"id='{i}'" not in modified_html]
print(f"Missing IDs after replacement: {len(missing)}")
if missing:
    print("Missing IDs:", missing)

with open('web/index.html', 'w', encoding='utf-8') as f:
    f.write(modified_html)

print("Applied Stage 2 replacement successfully!")

