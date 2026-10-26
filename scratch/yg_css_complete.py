import sys

def get_yg_editorial_css():
    return """
    /* ============================================================ */
    /* YG ENTERTAINMENT INSPIRED MINIMALIST LUXURY EDITORIAL CSS    */
    /* KTS CLASS FUND — K57 KINH TẾ SỐ                              */
    /* ============================================================ */

    :root {
      /* High-contrast Luxury Editorial Palette */
      --black-pure: #000000;
      --black-rich: #09090b;
      --black-surface: #18181b;
      --black-muted: #27272a;

      --white-pure: #ffffff;
      --white-subtle: #fcfcfc;

      --gray-50: #fafafa;
      --gray-100: #f4f4f5;
      --gray-200: #e4e4e7;
      --gray-300: #d4d4d8;
      --gray-400: #a1a1aa;
      --gray-500: #71717a;
      --gray-600: #52525b;
      --gray-700: #3f3f46;
      --gray-800: #27272a;

      /* Web3 Electric Cobalt Blue Accent */
      --brand-blue: #2563eb;
      --brand-blue-hover: #1d4ed8;
      --brand-blue-subtle: #eff6ff;
      --brand-blue-border: #bfdbfe;

      /* Role Semantics (Editorial Luxury Tint) */
      --student-color: #047857;
      --student-bg: #f0fdf4;
      --student-border: #bbf7d0;

      --bcs-color: #2563eb;
      --bcs-bg: #eff6ff;
      --bcs-border: #bfdbfe;

      --advisor-color: #6d28d9;
      --advisor-bg: #f5f3ff;
      --advisor-border: #ddd6fe;

      --warning-color: #b45309;
      --warning-bg: #fffbeb;
      --warning-border: #fde68a;

      --danger-color: #b91c1c;
      --danger-bg: #fef2f2;
      --danger-border: #fecaca;

      /* Layout & Architecture */
      --max-width: 1320px;
      --border-thin: 1px solid #e4e4e7;
      --border-black: 1px solid #09090b;

      --radius-xs: 2px;
      --radius-sm: 4px;
      --radius-md: 8px;
      --radius-lg: 12px;
      --radius-full: 9999px;

      --transition-fast: 0.16s cubic-bezier(0.16, 1, 0.3, 1);
      --transition-smooth: 0.24s cubic-bezier(0.16, 1, 0.3, 1);
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    html {
      scroll-behavior: smooth;
      font-size: 16px;
    }

    body {
      font-family: 'Inter', 'Be Vietnam Pro', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background-color: var(--gray-50);
      color: var(--black-rich);
      line-height: 1.6;
      -webkit-font-smoothing: antialiased;
      overflow-x: hidden;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    /* TYPOGRAPHY */
    h1, h2, h3, h4, h5, h6 {
      font-family: 'Be Vietnam Pro', 'Inter', sans-serif;
      font-weight: 800;
      color: var(--black-pure);
      letter-spacing: -0.03em;
      line-height: 1.15;
    }

    a {
      color: inherit;
      text-decoration: none;
      transition: color var(--transition-fast);
    }

    p {
      color: var(--gray-600);
      font-size: 0.95rem;
      line-height: 1.65;
    }

    /* TOPBAR NAVIGATION (EDITORIAL HEADER) */
    .topbar {
      position: sticky;
      top: 0;
      z-index: 1000;
      background: rgba(255, 255, 255, 0.96);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border-bottom: var(--border-thin);
      padding: 0 24px;
      height: 72px;
      display: flex;
      align-items: center;
    }

    .topbar-container {
      width: 100%;
      max-width: var(--max-width);
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
    }

    .brand-logo {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .brand-logo svg {
      width: 34px;
      height: 34px;
      fill: var(--black-pure);
    }

    .brand-title {
      font-size: 1.15rem;
      font-weight: 900;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--black-pure);
    }

    .brand-subtitle {
      font-size: 0.68rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--gray-500);
      display: block;
    }

    .nav-links {
      display: flex;
      align-items: center;
      gap: 24px;
      list-style: none;
    }

    .nav-link {
      font-size: 0.78rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--gray-600);
      padding: 6px 0;
      position: relative;
      transition: color var(--transition-fast);
    }

    .nav-link::after {
      content: "";
      position: absolute;
      bottom: 0;
      left: 0;
      width: 0%;
      height: 2px;
      background: var(--black-pure);
      transition: width var(--transition-smooth);
    }

    .nav-link:hover {
      color: var(--black-pure);
    }

    .nav-link:hover::after {
      width: 100%;
    }

    .topbar-actions {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .network-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      background: var(--white-pure);
      border: var(--border-thin);
      border-radius: var(--radius-full);
      font-size: 0.74rem;
      font-weight: 600;
      color: var(--gray-700);
    }

    .network-dot {
      width: 7px;
      height: 7px;
      background: #10b981;
      border-radius: 50%;
      box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
    }

    /* BUTTON SYSTEM (MINIMALIST LUXURY) */
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      font-family: inherit;
      font-size: 0.8rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      padding: 10px 22px;
      border-radius: var(--radius-sm);
      cursor: pointer;
      border: 1px solid transparent;
      transition: all var(--transition-fast);
      outline: none;
      white-space: nowrap;
    }

    .btn-primary {
      background: var(--black-pure);
      color: var(--white-pure);
      border-color: var(--black-pure);
    }

    .btn-primary:hover {
      background: var(--brand-blue);
      border-color: var(--brand-blue);
      color: var(--white-pure);
      transform: translateY(-1px);
    }

    .btn-secondary {
      background: var(--gray-100);
      color: var(--black-pure);
      border-color: var(--gray-200);
    }

    .btn-secondary:hover {
      background: var(--gray-200);
      color: var(--black-pure);
    }

    .btn-outline, .btn-outline-white, .btn-outline-light {
      background: transparent;
      color: var(--black-pure);
      border: 1px solid var(--gray-300);
    }

    .btn-outline:hover, .btn-outline-white:hover, .btn-outline-light:hover {
      border-color: var(--black-pure);
      background: var(--white-pure);
      color: var(--black-pure);
    }

    .btn-danger {
      background: var(--danger-bg);
      color: var(--danger-color);
      border-color: var(--danger-border);
    }

    .btn-danger:hover {
      background: var(--danger-color);
      color: var(--white-pure);
    }

    .btn-sm {
      padding: 6px 14px;
      font-size: 0.72rem;
    }

    /* HERO SECTION (EDITORIAL MAGAZINE COVER STYLE) */
    .hero-section {
      width: 100%;
      max-width: var(--max-width);
      margin: 32px auto 0 auto;
      padding: 0 24px;
      display: flex;
      flex-direction: column;
      gap: 28px;
    }

    .hero-banner {
      background: var(--white-pure);
      border: var(--border-thin);
      border-radius: var(--radius-md);
      padding: 44px 44px 36px 44px;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    .hero-title {
      font-size: clamp(2rem, 3.5vw, 3rem);
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: -0.035em;
      line-height: 1.1;
      color: var(--black-pure);
      margin-bottom: 8px;
    }

    .hero-desc {
      font-size: 1.05rem;
      color: var(--gray-600);
      max-width: 820px;
      line-height: 1.6;
    }

    /* QUICK CONTROL BAR (IDENTITY & WALLET BAR) */
    .quick-control-bar {
      background: var(--gray-50);
      border: var(--border-thin);
      border-radius: var(--radius-sm);
      padding: 18px 22px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .quick-status-group {
      display: flex;
      align-items: center;
      gap: 20px;
      flex-wrap: wrap;
    }

    .quick-status-item {
      display: flex;
      flex-direction: column;
      gap: 4px;
      min-width: 160px;
    }

    .quick-status-label {
      font-size: 0.68rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--gray-500);
    }

    .quick-status-val {
      font-size: 0.9rem;
      font-weight: 700;
      color: var(--black-pure);
    }

    /* CONTRACT INPUT STRIP */
    .contract-input-bar {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      padding-top: 14px;
      border-top: 1px solid var(--gray-200);
    }

    .contract-input-bar input {
      flex: 1;
      min-width: 320px;
      padding: 9px 14px;
      background: var(--white-pure);
      border: 1px solid var(--gray-300);
      border-radius: var(--radius-xs);
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.82rem;
      font-weight: 600;
      color: var(--black-rich);
      outline: none;
      transition: border-color var(--transition-fast);
    }

    .contract-input-bar input:focus {
      border-color: var(--black-pure);
    }

    /* GUEST WARNING BANNER */
    #guestWarningBanner {
      background: #fffbeb;
      border: 1px solid #fde68a;
      border-radius: var(--radius-sm);
      padding: 14px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      font-size: 0.85rem;
      color: #92400e;
    }

    /* ANNOUNCEMENT CARD (DYNAMIC CLASS SIZE 5 SV) */
    .class-announcement-card {
      background: var(--white-pure);
      border: var(--border-thin);
      border-radius: var(--radius-sm);
      padding: 32px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    .ann-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
    }

    .ann-tag-group {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .ann-badge-pill {
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--gray-500);
    }

    .ann-status-tag {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      padding: 4px 10px;
      border-radius: var(--radius-full);
      background: var(--student-bg);
      color: var(--student-color);
      border: 1px solid var(--student-border);
    }

    .ann-dot-pulse {
      width: 6px;
      height: 6px;
      background: #10b981;
      border-radius: 50%;
    }

    .ann-title {
      font-size: 1.35rem;
      font-weight: 800;
      color: var(--black-pure);
    }

    .ann-purpose {
      font-size: 0.9rem;
      color: var(--gray-600);
    }

    .ann-meta-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      background: var(--gray-50);
      border: var(--border-thin);
      border-radius: var(--radius-xs);
      padding: 16px 20px;
    }

    .ann-meta-item {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .ann-meta-label {
      font-size: 0.68rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--gray-500);
    }

    .ann-meta-val {
      font-size: 1.05rem;
      font-weight: 800;
      color: var(--black-pure);
    }

    .progress-bar-wrap {
      width: 100%;
      height: 6px;
      background: var(--gray-200);
      border-radius: var(--radius-full);
      overflow: hidden;
      margin: 8px 0;
    }

    .progress-bar-fill {
      height: 100%;
      background: var(--black-pure);
      border-radius: var(--radius-full);
      transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .ann-progress-desc {
      font-size: 0.78rem;
      font-weight: 600;
      color: var(--gray-600);
      display: flex;
      justify-content: space-between;
    }

    /* LIVE METRICS GRID (EDITORIAL STATS) */
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
    }

    .metric-card {
      background: var(--white-pure);
      border: var(--border-thin);
      border-radius: var(--radius-sm);
      padding: 24px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 16px;
      transition: border-color var(--transition-fast), transform var(--transition-fast);
    }

    .metric-card:hover {
      border-color: var(--black-pure);
      transform: translateY(-2px);
    }

    .metric-label {
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--gray-500);
    }

    .metric-val {
      font-size: clamp(1.8rem, 2.4vw, 2.2rem);
      font-weight: 800;
      font-feature-settings: "tnum";
      font-variant-numeric: tabular-nums;
      color: var(--black-pure);
      letter-spacing: -0.02em;
      line-height: 1.1;
    }

    .metric-sub {
      font-size: 0.76rem;
      color: var(--gray-500);
      border-top: 1px solid var(--gray-100);
      padding-top: 10px;
    }

    /* DAPP WORKSPACE (ROLES TABS & FORMS) */
    .dapp-hero-section {
      width: 100%;
      max-width: var(--max-width);
      margin: 36px auto 0 auto;
      padding: 0 24px;
    }

    .role-tabs-nav {
      display: flex;
      align-items: center;
      background: var(--white-pure);
      border: var(--border-thin);
      border-bottom: none;
      border-radius: var(--radius-sm) var(--radius-sm) 0 0;
      overflow-x: auto;
    }

    .role-tab-btn {
      flex: 1;
      padding: 18px 24px;
      background: transparent;
      border: none;
      border-right: var(--border-thin);
      border-bottom: 2px solid transparent;
      font-family: inherit;
      font-size: 0.8rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--gray-500);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      transition: all var(--transition-fast);
      white-space: nowrap;
    }

    .role-tab-btn:hover {
      color: var(--black-pure);
      background: var(--gray-50);
    }

    .role-tab-btn.active {
      color: var(--black-pure);
      border-bottom-color: var(--black-pure);
      background: var(--white-pure);
    }

    .role-detail-container {
      background: var(--white-pure);
      border: var(--border-thin);
      border-radius: 0 0 var(--radius-sm) var(--radius-sm);
      padding: 36px;
    }

    .role-panel {
      display: none;
      flex-direction: column;
      gap: 32px;
    }

    .role-panel.active {
      display: flex;
    }

    /* FORMS & INPUTS */
    .form-group {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 16px;
    }

    .form-group label {
      font-size: 0.74rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--black-pure);
    }

    .form-control {
      width: 100%;
      padding: 10px 16px;
      background: var(--white-pure);
      border: 1px solid var(--gray-300);
      border-radius: var(--radius-xs);
      font-family: inherit;
      font-size: 0.88rem;
      color: var(--black-pure);
      outline: none;
      transition: border-color var(--transition-fast);
    }

    .form-control:focus {
      border-color: var(--black-pure);
    }

    .form-text, .form-hint {
      font-size: 0.74rem;
      color: var(--gray-500);
    }

    /* DATA TABLES */
    .table-responsive {
      width: 100%;
      overflow-x: auto;
      border: var(--border-thin);
      border-radius: var(--radius-xs);
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.84rem;
      text-align: left;
    }

    th {
      background: var(--gray-50);
      padding: 12px 18px;
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--gray-600);
      border-bottom: var(--border-thin);
      white-space: nowrap;
    }

    td {
      padding: 14px 18px;
      border-bottom: 1px solid var(--gray-100);
      color: var(--black-rich);
      vertical-align: middle;
    }

    tr:last-child td {
      border-bottom: none;
    }

    tr:hover td {
      background: var(--gray-50);
    }

    /* STATUS PILLS */
    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 0.7rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      padding: 4px 10px;
      border-radius: var(--radius-full);
      border: 1px solid var(--gray-300);
      background: var(--gray-50);
      color: var(--black-pure);
    }

    .status-pill.status-pending {
      background: var(--warning-bg);
      color: var(--warning-color);
      border-color: var(--warning-border);
    }

    .status-pill.status-ready {
      background: var(--brand-blue-subtle);
      color: var(--brand-blue);
      border-color: var(--brand-blue-border);
    }

    .status-pill.status-executed, .status-pill.status-approved {
      background: var(--student-bg);
      color: var(--student-color);
      border-color: var(--student-border);
    }

    .status-pill.status-rejected, .status-pill.status-expired {
      background: var(--danger-bg);
      color: var(--danger-color);
      border-color: var(--danger-border);
    }

    /* CONTENT SECTIONS (ABOUT, WORKFLOW, GOVERNANCE, ETC.) */
    .site-section {
      width: 100%;
      max-width: var(--max-width);
      margin: 48px auto 0 auto;
      padding: 0 24px;
    }

    .section-header {
      margin-bottom: 24px;
    }

    .section-tag {
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: var(--gray-500);
      display: inline-block;
      margin-bottom: 6px;
    }

    .section-title {
      font-size: 1.7rem;
      font-weight: 900;
      text-transform: uppercase;
      color: var(--black-pure);
      letter-spacing: -0.025em;
    }

    .section-desc {
      font-size: 0.95rem;
      color: var(--gray-600);
      margin-top: 4px;
    }

    .card {
      background: var(--white-pure);
      border: var(--border-thin);
      border-radius: var(--radius-sm);
      padding: 28px;
    }

    /* TERMINAL WINDOW (TRANSPARENCY LOG) */
    .terminal-window {
      background: var(--black-pure);
      border-radius: var(--radius-sm);
      padding: 20px 24px;
      color: #e4e4e7;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.8rem;
    }

    .terminal-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--black-muted);
      padding-bottom: 12px;
      margin-bottom: 14px;
      font-size: 0.75rem;
      color: var(--gray-400);
    }

    .terminal-body {
      max-height: 240px;
      overflow-y: auto;
      line-height: 1.6;
      word-break: break-all;
    }

    /* SITE FOOTER */
    .site-footer {
      background: var(--white-pure);
      border-top: var(--border-thin);
      padding: 48px 24px;
      margin-top: 60px;
    }

    .footer-container {
      max-width: var(--max-width);
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      flex-wrap: wrap;
    }

    .footer-brand h4 {
      font-size: 0.95rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .footer-brand p {
      font-size: 0.78rem;
      color: var(--gray-500);
    }

    /* MODAL WINDOWS */
    .modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(0, 0, 0, 0.6);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9999;
      opacity: 0;
      pointer-events: none;
      transition: opacity var(--transition-fast);
      padding: 20px;
    }

    .modal-overlay.open, .modal-overlay.show {
      opacity: 1;
      pointer-events: auto;
    }

    .modal-card {
      background: var(--white-pure);
      border: var(--border-thin);
      border-radius: var(--radius-sm);
      max-width: 620px;
      width: 100%;
      max-height: 90vh;
      display: flex;
      flex-direction: column;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.16);
    }

    .modal-card.modal-lg {
      max-width: 880px;
    }

    .modal-header {
      padding: 20px 24px;
      border-bottom: var(--border-thin);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .modal-title {
      font-size: 1.15rem;
      font-weight: 800;
      color: var(--black-pure);
    }

    .modal-body {
      padding: 24px;
      overflow-y: auto;
      flex: 1;
    }

    .modal-footer {
      padding: 16px 24px;
      border-top: var(--border-thin);
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 12px;
      background: var(--gray-50);
    }

    /* AI ASSISTANT CHATBOT */
    .ai-fab-container {
      position: fixed;
      bottom: 28px;
      right: 28px;
      z-index: 10000;
    }

    .ai-fab-btn {
      background: var(--black-pure);
      color: var(--white-pure);
      border: 1px solid var(--black-pure);
      border-radius: var(--radius-full);
      padding: 12px 22px;
      font-family: inherit;
      font-size: 0.84rem;
      font-weight: 700;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 10px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.16);
      transition: all var(--transition-fast);
    }

    .ai-fab-btn:hover {
      background: var(--brand-blue);
      border-color: var(--brand-blue);
      transform: translateY(-2px);
    }

    .ai-chat-drawer {
      position: fixed;
      bottom: 84px;
      right: 28px;
      width: 420px;
      height: 580px;
      max-height: calc(100vh - 120px);
      background: var(--white-pure);
      border: var(--border-thin);
      border-radius: var(--radius-md);
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.18);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      transform: translateY(20px) scale(0.96);
      opacity: 0;
      pointer-events: none;
      transition: all var(--transition-smooth);
    }

    .ai-chat-drawer.open {
      transform: translateY(0) scale(1);
      opacity: 1;
      pointer-events: auto;
    }

    .ai-chat-header {
      padding: 16px 20px;
      background: var(--black-pure);
      color: var(--white-pure);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .ai-header-title {
      font-size: 0.95rem;
      font-weight: 800;
    }

    .ai-header-status {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.72rem;
      color: var(--gray-400);
    }

    .ai-status-indicator {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #10b981;
    }

    .ai-header-close {
      background: transparent;
      border: none;
      color: var(--gray-400);
      font-size: 1.3rem;
      cursor: pointer;
    }

    .ai-chat-body {
      flex: 1;
      overflow-y: auto;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      background: var(--gray-50);
      font-size: 0.85rem;
    }

    .ai-msg {
      padding: 12px 16px;
      border-radius: var(--radius-sm);
      max-width: 85%;
      line-height: 1.5;
    }

    .ai-msg-bot {
      background: var(--white-pure);
      border: var(--border-thin);
      color: var(--black-rich);
      align-self: flex-start;
    }

    .ai-msg-user {
      background: var(--black-pure);
      color: var(--white-pure);
      align-self: flex-end;
    }

    .ai-prompt-chip {
      background: var(--gray-100);
      border: var(--border-thin);
      border-radius: var(--radius-xs);
      padding: 6px 10px;
      font-size: 0.75rem;
      font-weight: 600;
      text-align: left;
      cursor: pointer;
      color: var(--black-rich);
      margin-top: 4px;
      display: block;
      width: 100%;
    }

    .ai-prompt-chip:hover {
      background: var(--white-pure);
      border-color: var(--black-pure);
    }

    .ai-chat-footer {
      padding: 14px 20px;
      background: var(--white-pure);
      border-top: var(--border-thin);
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .ai-input-row {
      display: flex;
      gap: 8px;
    }

    .ai-input {
      flex: 1;
      padding: 8px 12px;
      border: 1px solid var(--gray-300);
      border-radius: var(--radius-xs);
      font-family: inherit;
      font-size: 0.85rem;
      outline: none;
    }

    .ai-send-btn {
      padding: 8px 16px;
      background: var(--black-pure);
      color: var(--white-pure);
      border: none;
      border-radius: var(--radius-xs);
      font-weight: 700;
      cursor: pointer;
    }

    .ai-send-btn:hover {
      background: var(--brand-blue);
    }

    /* RESPONSIVE DESIGN */
    @media (max-width: 1024px) {
      .nav-links {
        display: none;
      }
      .hero-banner {
        padding: 32px 24px;
      }
      .role-detail-container {
        padding: 24px;
      }
    }

    @media (max-width: 640px) {
      .hero-title {
        font-size: 1.85rem;
      }
      .network-badge {
        display: none;
      }
      .ai-chat-drawer {
        width: calc(100vw - 32px);
        right: 16px;
        bottom: 80px;
      }
      .ai-fab-container {
        bottom: 16px;
        right: 16px;
      }
    }
    """

if __name__ == "__main__":
    css = get_yg_editorial_css()
    print(f"YG CSS generated: {len(css)} characters")
