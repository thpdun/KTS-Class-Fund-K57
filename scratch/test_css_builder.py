import re
import json

def build():
    with open("web/index.html.bak", "r", encoding="utf-8") as f:
        orig = f.read()

    # Extract script
    script_start = orig.find("<script>")
    script_end = orig.rfind("</script>") + len("</script>")
    js_code = orig[script_start:script_end]

    # Extract AI widget
    ai_widget_start = orig.find('<div class="ai-fab-container"', script_end)
    ai_widget_end = orig.find('</body>', ai_widget_start)
    ai_widget_html = orig[ai_widget_start:ai_widget_end].strip()

    # Build the modern CSS
    css_code = """
    :root {
      /* Brand Color Palette */
      --primary-navy: #0f172a;
      --secondary-navy: #1e293b;
      --navy-light: #334155;
      --brand-blue: #2563eb;
      --brand-blue-hover: #1d4ed8;
      --brand-blue-light: #eff6ff;
      --brand-cyan: #0284c7;
      
      /* Backgrounds & Surfaces */
      --bg-slate: #f8fafc;
      --bg-page: #f1f5f9;
      --card-bg: #ffffff;
      --card-hover: #fafafa;
      --border-color: #e2e8f0;
      --border-focus: #3b82f6;

      /* Typography */
      --text-main: #0f172a;
      --text-muted: #64748b;
      --text-light: #94a3b8;

      /* Role & Semantic Colors */
      --student-color: #059669;
      --student-bg: #ecfdf5;
      --student-border: #a7f3d0;

      --bcs-color: #2563eb;
      --bcs-bg: #eff6ff;
      --bcs-border: #bfdbfe;

      --advisor-color: #7c3aed;
      --advisor-bg: #f5f3ff;
      --advisor-border: #ddd6fe;

      --success: #059669;
      --success-bg: #ecfdf5;
      --warning: #d97706;
      --warning-bg: #fffbeb;
      --danger: #dc2626;
      --danger-bg: #fef2f2;
      --info-bg: #eff6ff;
      
      /* Elevation & Radii */
      --shadow-xs: 0 1px 2px rgba(15, 23, 42, 0.04);
      --shadow-sm: 0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04);
      --shadow-md: 0 4px 6px -1px rgba(15, 23, 42, 0.07), 0 2px 4px -2px rgba(15, 23, 42, 0.05);
      --shadow-lg: 0 10px 15px -3px rgba(15, 23, 42, 0.08), 0 4px 6px -4px rgba(15, 23, 42, 0.04);
      --shadow-xl: 0 20px 25px -5px rgba(15, 23, 42, 0.1), 0 8px 10px -6px rgba(15, 23, 42, 0.05);
      
      --radius-sm: 6px;
      --radius-md: 10px;
      --radius-lg: 14px;
      --radius-xl: 18px;
      --radius-full: 9999px;

      /* Sidebar & Layout */
      --sidebar-width: 270px;
      --topbar-height: 68px;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    html {
      scroll-behavior: smooth;
    }

    body {
      font-family: 'Be Vietnam Pro', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background-color: var(--bg-slate);
      color: var(--text-main);
      line-height: 1.6;
      -webkit-font-smoothing: antialiased;
      overflow-x: hidden;
      display: flex;
      min-height: 100vh;
    }

    h1, h2, h3, h4, h5, h6 {
      font-family: 'Be Vietnam Pro', 'Inter', sans-serif;
      font-weight: 700;
      color: var(--primary-navy);
      letter-spacing: -0.02em;
    }

    a {
      color: var(--brand-blue);
      text-decoration: none;
      transition: color 0.15s ease;
    }

    a:hover {
      color: var(--brand-blue-hover);
    }

    section {
      scroll-margin-top: calc(var(--topbar-height) + 20px);
    }

    /* ============================================================ */
    /* 1. APP SHELL & SIDEBAR NAVIGATION                            */
    /* ============================================================ */
    .app-sidebar {
      position: fixed;
      top: 0;
      left: 0;
      width: var(--sidebar-width);
      height: 100vh;
      background: var(--primary-navy);
      color: #f8fafc;
      display: flex;
      flex-direction: column;
      z-index: 1000;
      border-right: 1px solid rgba(255, 255, 255, 0.08);
      transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .sidebar-header {
      padding: 20px 20px 16px 20px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .sidebar-logo-icon {
      width: 38px;
      height: 38px;
      border-radius: 10px;
      background: linear-gradient(135deg, #2563eb 0%, #38bdf8 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
      flex-shrink: 0;
    }

    .sidebar-logo-icon svg {
      width: 22px;
      height: 22px;
      fill: #ffffff;
    }

    .sidebar-brand-title {
      font-size: 1.1rem;
      font-weight: 800;
      color: #ffffff;
      letter-spacing: -0.02em;
      line-height: 1.2;
    }

    .sidebar-brand-sub {
      font-size: 0.68rem;
      color: #94a3b8;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    /* Sidebar User Card */
    .sidebar-user-card {
      margin: 14px 16px;
      padding: 12px 14px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: var(--radius-md);
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .sidebar-user-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .sidebar-user-label {
      font-size: 0.7rem;
      color: #94a3b8;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .sidebar-user-identity {
      font-size: 0.85rem;
      font-weight: 700;
      color: #38bdf8;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    /* Sidebar Nav Menu */
    .sidebar-menu {
      flex: 1;
      overflow-y: auto;
      padding: 10px 14px 20px 14px;
      list-style: none;
    }

    .sidebar-group-label {
      font-size: 0.68rem;
      font-weight: 700;
      text-transform: uppercase;
      color: #64748b;
      letter-spacing: 0.08em;
      margin: 18px 8px 6px 8px;
    }

    .sidebar-group-label:first-child {
      margin-top: 4px;
    }

    .sidebar-link-item {
      margin-bottom: 2px;
    }

    .sidebar-link {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 9px 12px;
      border-radius: 8px;
      color: #cbd5e1;
      font-size: 0.88rem;
      font-weight: 500;
      transition: all 0.15s ease;
      cursor: pointer;
      text-decoration: none;
      border: 1px solid transparent;
    }

    .sidebar-link:hover {
      background: rgba(255, 255, 255, 0.07);
      color: #ffffff;
      border-color: rgba(255, 255, 255, 0.04);
    }

    .sidebar-link.active {
      background: rgba(37, 99, 235, 0.2);
      color: #60a5fa;
      border-color: rgba(37, 99, 235, 0.4);
      font-weight: 600;
    }

    .sidebar-link-icon {
      font-size: 1rem;
      width: 20px;
      text-align: center;
      flex-shrink: 0;
    }

    .sidebar-badge {
      margin-left: auto;
      font-size: 0.7rem;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 12px;
      background: rgba(37, 99, 235, 0.3);
      color: #93c5fd;
      border: 1px solid rgba(147, 197, 253, 0.3);
    }

    /* Sidebar Footer */
    .sidebar-footer {
      padding: 14px 16px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      background: rgba(15, 23, 42, 0.7);
      font-size: 0.75rem;
      color: #94a3b8;
    }

    .sidebar-footer-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 6px;
    }

    .sidebar-footer-row:last-child {
      margin-bottom: 0;
    }

    .sidebar-backdrop {
      display: none;
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(15, 23, 42, 0.6);
      backdrop-filter: blur(4px);
      z-index: 990;
    }

    /* ============================================================ */
    /* 2. APP MAIN & TOPBAR                                         */
    /* ============================================================ */
    .app-main {
      margin-left: var(--sidebar-width);
      width: calc(100% - var(--sidebar-width));
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      transition: margin 0.25s ease, width 0.25s ease;
    }

    .app-topbar {
      position: sticky;
      top: 0;
      height: var(--topbar-height);
      background: rgba(255, 255, 255, 0.95);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border-color);
      z-index: 900;
      padding: 0 32px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .topbar-left {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .menu-toggle {
      display: none;
      background: transparent;
      border: 1px solid var(--border-color);
      color: var(--primary-navy);
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 1.1rem;
      cursor: pointer;
      line-height: 1;
    }

    .menu-toggle:hover {
      background: #f1f5f9;
    }

    .topbar-breadcrumbs {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.9rem;
      color: var(--text-muted);
    }

    .topbar-breadcrumbs strong {
      color: var(--primary-navy);
      font-weight: 700;
    }

    .topbar-right {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }

    /* Network Badge */
    .badge-network {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      border-radius: var(--radius-full);
      font-size: 0.78rem;
      font-weight: 600;
      background: #f8fafc;
      border: 1px solid var(--border-color);
      color: var(--text-main);
    }

    .badge-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #94a3b8;
    }

    .badge-dot.connected {
      background: var(--success);
      box-shadow: 0 0 0 3px rgba(5, 150, 105, 0.2);
    }

    .badge-dot.error {
      background: var(--danger);
      box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.2);
    }

    /* Buttons */
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 9px 16px;
      border-radius: var(--radius-md);
      font-weight: 600;
      font-size: 0.88rem;
      cursor: pointer;
      border: 1px solid transparent;
      transition: all 0.18s ease;
      text-decoration: none;
      line-height: 1.35;
      white-space: nowrap;
    }

    .btn-sm {
      padding: 6px 12px;
      font-size: 0.8rem;
      border-radius: 8px;
    }

    .btn-primary {
      background: var(--brand-blue);
      color: #ffffff;
      box-shadow: 0 1px 2px rgba(37, 99, 235, 0.2);
    }

    .btn-primary:hover {
      background: var(--brand-blue-hover);
      color: #ffffff;
      box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
    }

    .btn-success {
      background: var(--success);
      color: #ffffff;
    }

    .btn-success:hover {
      background: #047857;
      color: #ffffff;
    }

    .btn-purple {
      background: var(--advisor-color);
      color: #ffffff;
    }

    .btn-purple:hover {
      background: #6d28d9;
      color: #ffffff;
    }

    .btn-danger {
      background: var(--danger);
      color: #ffffff;
    }

    .btn-danger:hover {
      background: #b91c1c;
    }

    .btn-secondary {
      background: #e2e8f0;
      color: #334155;
    }

    .btn-secondary:hover {
      background: #cbd5e1;
    }

    .btn-outline {
      background: #ffffff;
      border: 1px solid var(--border-color);
      color: var(--text-main);
    }

    .btn-outline:hover {
      background: #f8fafc;
      border-color: #cbd5e1;
    }

    .btn-outline-white {
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.2);
      color: #ffffff;
    }

    .btn-outline-white:hover {
      background: rgba(255, 255, 255, 0.2);
      border-color: rgba(255, 255, 255, 0.35);
    }

    .btn-outline-light {
      background: transparent;
      border: 1px solid var(--border-color);
      color: var(--text-muted);
    }

    .btn-outline-light:hover {
      background: #f1f5f9;
      color: var(--text-main);
    }

    /* Content Area */
    .app-content {
      padding: 28px 32px 64px 32px;
      max-width: 1400px;
      width: 100%;
      margin: 0 auto;
    }

    .container {
      width: 100%;
      max-width: 1300px;
      margin: 0 auto;
    }

    /* ============================================================ */
    /* 3. HERO & QUICK CONTROL TOOLBAR                              */
    /* ============================================================ */
    .hero-section {
      margin-bottom: 24px;
    }

    .hero-banner-card {
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-lg);
      padding: 24px 28px;
      box-shadow: var(--shadow-sm);
      margin-bottom: 20px;
      position: relative;
      overflow: hidden;
    }

    .hero-banner-card::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 4px;
      height: 100%;
      background: linear-gradient(180deg, var(--brand-blue) 0%, var(--brand-cyan) 100%);
    }

    .hero-tag {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      background: var(--brand-blue-light);
      border: 1px solid var(--bcs-border);
      border-radius: var(--radius-full);
      font-size: 0.75rem;
      font-weight: 700;
      color: var(--brand-blue);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 10px;
    }

    .hero-tag span {
      font-size: 0.65rem;
    }

    .hero-title {
      font-size: 1.65rem;
      color: var(--primary-navy);
      margin-bottom: 6px;
      font-weight: 800;
      line-height: 1.3;
    }

    .hero-desc {
      font-size: 0.92rem;
      color: var(--text-muted);
      line-height: 1.6;
      max-width: 900px;
    }

    /* Quick Control Bar */
    .quick-control-bar {
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-lg);
      padding: 16px 20px;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      gap: 14px;
      margin-bottom: 20px;
    }

    .quick-status-group {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 14px;
    }

    .quick-status-item {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .quick-status-label {
      font-size: 0.72rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
    }

    .quick-status-val {
      font-size: 0.88rem;
      font-weight: 700;
      color: var(--primary-navy);
      word-break: break-all;
    }

    .contract-input-bar {
      display: flex;
      align-items: center;
      gap: 8px;
      background: #f8fafc;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 6px 12px;
      flex: 1;
      min-width: 280px;
    }

    .contract-input-bar input {
      border: none;
      background: transparent;
      outline: none;
      font-family: monospace;
      font-size: 0.84rem;
      color: var(--text-main);
      width: 100%;
    }

    /* Guest Warning */
    #guestWarningBanner {
      border-radius: var(--radius-md);
      box-shadow: var(--shadow-xs);
    }

    /* ============================================================ */
    /* 4. CLASS ANNOUNCEMENT CARD                                   */
    /* ============================================================ */
    .class-announcement-card {
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-lg);
      padding: 22px 24px;
      box-shadow: var(--shadow-sm);
      margin-bottom: 24px;
      position: relative;
      overflow: hidden;
      border-left: 5px solid var(--brand-blue);
    }

    .ann-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      flex-wrap: wrap;
      gap: 10px;
    }

    .ann-tag-group {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .ann-badge-pill {
      font-size: 0.74rem;
      font-weight: 700;
      padding: 3px 9px;
      border-radius: 6px;
      background: #eff6ff;
      color: #1d4ed8;
      border: 1px solid #bfdbfe;
    }

    .ann-status-tag {
      font-size: 0.74rem;
      font-weight: 600;
      padding: 3px 9px;
      border-radius: 6px;
      background: #fef2f2;
      color: #b91c1c;
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }

    .ann-dot-pulse {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #ef4444;
      animation: pulse 1.5s infinite;
    }

    @keyframes pulse {
      0% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(1.2); }
      100% { opacity: 1; transform: scale(1); }
    }

    .ann-title {
      font-size: 1.3rem;
      color: var(--primary-navy);
      margin-bottom: 6px;
      font-weight: 700;
    }

    .ann-purpose {
      font-size: 0.88rem;
      color: var(--text-muted);
      margin-bottom: 14px;
      line-height: 1.5;
    }

    .ann-meta-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      background: #f8fafc;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 12px 16px;
      margin-bottom: 16px;
    }

    .ann-meta-item {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .ann-meta-label {
      font-size: 0.74rem;
      color: var(--text-muted);
      font-weight: 600;
    }

    .ann-meta-val {
      font-size: 0.92rem;
      font-weight: 700;
      color: var(--primary-navy);
    }

    .ann-progress-section {
      margin-bottom: 16px;
    }

    .ann-progress-header {
      display: flex;
      justify-content: space-between;
      font-size: 0.84rem;
      color: var(--text-muted);
      margin-bottom: 6px;
    }

    .ann-progress-header strong {
      color: var(--primary-navy);
      font-weight: 700;
    }

    .ann-progress-track {
      height: 9px;
      background: #e2e8f0;
      border-radius: 10px;
      overflow: hidden;
    }

    .ann-progress-fill {
      height: 100%;
      background: linear-gradient(90deg, #2563eb, #38bdf8);
      border-radius: 10px;
      transition: width 0.4s ease;
    }

    .ann-footer {
      display: flex;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
    }

    .ann-tip {
      font-size: 0.8rem;
      color: var(--text-muted);
    }

    /* ============================================================ */
    /* 5. LIVE METRICS GRID                                         */
    /* ============================================================ */
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 16px;
      margin-bottom: 28px;
    }

    .metric-card {
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-lg);
      padding: 18px 20px;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      gap: 6px;
      transition: transform 0.15s ease, box-shadow 0.15s ease;
    }

    .metric-card:hover {
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
      border-color: #cbd5e1;
    }

    .metric-title {
      font-size: 0.76rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
    }

    .metric-num {
      font-size: 1.6rem;
      font-weight: 800;
      color: var(--primary-navy);
      letter-spacing: -0.02em;
      line-height: 1.2;
    }

    .metric-note {
      font-size: 0.74rem;
      color: var(--text-light);
      margin-top: 2px;
    }

    /* ============================================================ */
    /* 6. WORKSPACE & ROLE TABS                                     */
    /* ============================================================ */
    .dapp-hero-section {
      margin-bottom: 36px;
    }

    .workspace-role-header {
      text-align: center;
      max-width: 760px;
      margin: 0 auto 18px auto;
    }

    .section-badge {
      display: inline-block;
      padding: 4px 12px;
      background: #e0e7ff;
      color: var(--brand-blue);
      border-radius: var(--radius-full);
      font-size: 0.74rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 8px;
    }

    .section-title {
      font-size: 1.6rem;
      color: var(--primary-navy);
      margin-bottom: 8px;
      font-weight: 800;
    }

    .section-desc {
      font-size: 0.9rem;
      color: var(--text-muted);
      line-height: 1.6;
    }

    .role-buttons-group {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-top: 16px;
    }

    .role-btn-item {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      padding: 14px 18px;
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      cursor: pointer;
      font-weight: 700;
      font-size: 0.92rem;
      color: var(--primary-navy);
      transition: all 0.18s ease;
      box-shadow: var(--shadow-xs);
    }

    .role-btn-item:hover {
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
    }

    .role-btn-student.active {
      background: var(--student-bg);
      border-color: var(--student-color);
      color: var(--student-color);
      box-shadow: 0 0 0 2px rgba(5, 150, 105, 0.2);
    }

    .role-btn-bcs.active {
      background: var(--bcs-bg);
      border-color: var(--bcs-color);
      color: var(--bcs-color);
      box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2);
    }

    .role-btn-advisor.active {
      background: var(--advisor-bg);
      border-color: var(--advisor-color);
      color: var(--advisor-color);
      box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.2);
    }

    .role-btn-history.active {
      background: #ffedd5;
      border-color: #ea580c;
      color: #ea580c;
      box-shadow: 0 0 0 2px rgba(234, 88, 12, 0.2);
    }

    .role-btn-icon {
      font-size: 1.25rem;
    }

    /* Role Detail Panels */
    .role-detail-container {
      margin-top: 20px;
    }

    .role-panel {
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-lg);
      padding: 24px;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    .panel-student { border-top: 4px solid var(--student-color); }
    .panel-bcs { border-top: 4px solid var(--bcs-color); }
    .panel-advisor { border-top: 4px solid var(--advisor-color); }
    .panel-history { border-top: 4px solid #ea580c; }

    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--border-color);
    }

    .panel-title {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 1.15rem;
      font-weight: 700;
    }

    .panel-badge {
      font-size: 0.72rem;
      font-weight: 700;
      padding: 3px 10px;
      border-radius: var(--radius-full);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .badge-student-role { background: var(--student-bg); color: var(--student-color); border: 1px solid var(--student-border); }
    .badge-bcs-role { background: var(--bcs-bg); color: var(--bcs-color); border: 1px solid var(--bcs-border); }
    .badge-advisor-role { background: var(--advisor-bg); color: var(--advisor-color); border: 1px solid var(--advisor-border); }

    .panel-body {
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    /* Forms */
    .form-group {
      margin-bottom: 14px;
    }

    .form-group label {
      display: block;
      font-size: 0.84rem;
      font-weight: 600;
      color: var(--text-main);
      margin-bottom: 6px;
    }

    .form-control {
      width: 100%;
      padding: 9px 12px;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      font-size: 0.88rem;
      color: var(--text-main);
      background: #ffffff;
      outline: none;
      transition: border-color 0.15s, box-shadow 0.15s;
    }

    .form-control:focus {
      border-color: var(--border-focus);
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
    }

    /* Data Tables */
    .data-table-container {
      width: 100%;
      overflow-x: auto;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      background: #ffffff;
    }

    .data-table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 0.86rem;
    }

    .data-table thead {
      background: #f8fafc;
      border-bottom: 1px solid var(--border-color);
    }

    .data-table th {
      padding: 12px 14px;
      font-weight: 700;
      color: var(--text-muted);
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .data-table td {
      padding: 12px 14px;
      border-bottom: 1px solid #f1f5f9;
      color: var(--text-main);
      vertical-align: middle;
    }

    .data-table tbody tr:hover {
      background: #f8fafc;
    }

    .data-table tbody tr:last-child td {
      border-bottom: none;
    }

    /* Status Pills */
    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 3px 8px;
      border-radius: var(--radius-full);
      font-size: 0.74rem;
      font-weight: 600;
      white-space: nowrap;
    }

    .status-ready { background: var(--success-bg); color: #047857; border: 1px solid #a7f3d0; }
    .status-pending { background: var(--warning-bg); color: #b45309; border: 1px solid #fde68a; }
    .status-executed { background: var(--info-bg); color: #1d4ed8; border: 1px solid #bfdbfe; }
    .status-expired { background: var(--danger-bg); color: #b91c1c; border: 1px solid #fecaca; }

    /* Flow History Cards */
    .flow-balance-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 14px;
      margin-bottom: 20px;
    }

    .flow-balance-card {
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 14px 16px;
      box-shadow: var(--shadow-xs);
    }

    .flow-balance-title {
      font-size: 0.74rem;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .flow-balance-val {
      font-size: 1.35rem;
      font-weight: 800;
      margin: 4px 0 2px 0;
    }

    .flow-steps-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
    }

    .flow-step-box {
      background: #f8fafc;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 14px 16px;
    }

    .flow-step-badge {
      display: inline-block;
      font-size: 0.68rem;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      margin-bottom: 8px;
    }

    .flow-badge-inflow { background: #d1fae5; color: #065f46; }
    .flow-badge-spend { background: #dbeafe; color: #1e40af; }
    .flow-badge-refund { background: #ffedd5; color: #9a3412; }
    .flow-badge-gas { background: #ede9fe; color: #5b21b6; }

    .flow-filter-group {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }

    .flow-filter-btn {
      padding: 5px 12px;
      border-radius: 6px;
      border: 1px solid var(--border-color);
      background: #ffffff;
      color: var(--text-muted);
      font-size: 0.78rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .flow-filter-btn:hover {
      background: #f1f5f9;
      color: var(--text-main);
    }

    .flow-filter-btn.active {
      background: var(--brand-blue);
      color: #ffffff;
      border-color: var(--brand-blue);
    }

    /* ============================================================ */
    /* 7. KNOWLEDGE & GUIDANCE CARDS                                */
    /* ============================================================ */
    .grid-2 {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 20px;
    }

    .grid-3 {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 20px;
    }

    .card {
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-lg);
      padding: 22px 24px;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .card-icon {
      width: 42px;
      height: 42px;
      border-radius: 10px;
      background: var(--brand-blue-light);
      color: var(--brand-blue);
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 4px;
    }

    .card-icon svg {
      width: 22px;
      height: 22px;
    }

    .card-title {
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--primary-navy);
    }

    .card-desc {
      font-size: 0.88rem;
      color: var(--text-muted);
      line-height: 1.6;
    }

    /* Timeline Workflow */
    .timeline {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .timeline-step {
      display: flex;
      gap: 16px;
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 18px 20px;
      box-shadow: var(--shadow-xs);
    }

    .step-badge {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: var(--brand-blue);
      color: #ffffff;
      font-weight: 700;
      font-size: 0.9rem;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .step-content {
      flex: 1;
    }

    .step-content h4 {
      font-size: 1rem;
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 8px;
    }

    .step-meta {
      display: flex;
      gap: 14px;
      margin-bottom: 8px;
      flex-wrap: wrap;
    }

    .meta-tag {
      font-size: 0.78rem;
      color: var(--text-muted);
    }

    .meta-tag strong {
      color: var(--primary-navy);
    }

    /* Calculator Box */
    .calc-box {
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-lg);
      padding: 24px;
      box-shadow: var(--shadow-sm);
    }

    /* FAQ */
    .faq-search-box {
      display: flex;
      align-items: center;
      gap: 10px;
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-full);
      padding: 10px 18px;
      max-width: 640px;
      margin: 0 auto 24px auto;
      box-shadow: var(--shadow-sm);
    }

    .faq-search-icon {
      color: var(--text-light);
    }

    .faq-search-input {
      border: none;
      outline: none;
      background: transparent;
      width: 100%;
      font-size: 0.92rem;
      color: var(--text-main);
    }

    .accordion-item {
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      margin-bottom: 10px;
      overflow: hidden;
      box-shadow: var(--shadow-xs);
    }

    .accordion-header {
      padding: 14px 18px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      cursor: pointer;
      font-weight: 600;
      color: var(--primary-navy);
      font-size: 0.94rem;
      transition: background 0.15s ease;
    }

    .accordion-header:hover {
      background: #f8fafc;
    }

    .accordion-content {
      padding: 0 18px 14px 18px;
      color: var(--text-muted);
      font-size: 0.88rem;
      line-height: 1.6;
      display: none;
    }

    .accordion-item.open .accordion-content {
      display: block;
    }

    .accordion-icon {
      transition: transform 0.2s ease;
      color: var(--text-light);
    }

    .accordion-item.open .accordion-icon {
      transform: rotate(180deg);
      color: var(--brand-blue);
    }

    /* Terminal Console */
    .log-terminal {
      background: #0f172a;
      color: #38bdf8;
      font-family: 'Consolas', 'Monaco', monospace;
      font-size: 0.8rem;
      padding: 14px 16px;
      border-radius: 8px;
      height: 180px;
      overflow-y: auto;
      line-height: 1.5;
      border: 1px solid rgba(255, 255, 255, 0.1);
    }

    /* ============================================================ */
    /* 8. MODALS & ROSTER DIALOG                                    */
    /* ============================================================ */
    .modal-overlay {
      display: none;
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(15, 23, 42, 0.65);
      backdrop-filter: blur(6px);
      z-index: 1100;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }

    .modal-overlay.open,
    .modal-overlay.show {
      display: flex;
    }

    .modal-box {
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-xl);
      padding: 24px;
      box-shadow: var(--shadow-xl);
      max-width: 600px;
      width: 100%;
      max-height: 90vh;
      display: flex;
      flex-direction: column;
    }

    #rosterModal .modal-box {
      max-width: 1050px;
      width: 95%;
    }

    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
    }

    .modal-close {
      background: transparent;
      border: none;
      font-size: 1.4rem;
      color: var(--text-light);
      cursor: pointer;
      line-height: 1;
    }

    .modal-close:hover {
      color: var(--danger);
    }

    /* Roster Modal Styles */
    .roster-header-badge {
      font-size: 0.72rem;
      font-weight: 700;
      padding: 2px 8px;
      background: #eff6ff;
      color: var(--brand-blue);
      border-radius: var(--radius-full);
      border: 1px solid #bfdbfe;
    }

    .roster-stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }

    .roster-stat-card {
      background: #f8fafc;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 12px 14px;
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .roster-stat-icon {
      width: 36px;
      height: 36px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.1rem;
      flex-shrink: 0;
    }

    .roster-stat-value {
      font-size: 1.25rem;
      font-weight: 800;
      color: var(--primary-navy);
      line-height: 1.1;
    }

    .roster-stat-label {
      font-size: 0.72rem;
      color: var(--text-muted);
      font-weight: 600;
    }

    .roster-toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 14px;
      flex-wrap: wrap;
    }

    .roster-search-wrapper {
      display: flex;
      align-items: center;
      gap: 8px;
      background: #f8fafc;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 6px 12px;
      flex: 1;
      min-width: 260px;
    }

    .roster-search-input {
      border: none;
      background: transparent;
      outline: none;
      width: 100%;
      font-size: 0.85rem;
      color: var(--text-main);
    }

    .roster-filter-pills {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }

    .roster-filter-btn {
      padding: 6px 12px;
      border-radius: var(--radius-full);
      border: 1px solid var(--border-color);
      background: #ffffff;
      color: var(--text-muted);
      font-size: 0.78rem;
      font-weight: 600;
      cursor: pointer;
    }

    .roster-filter-btn.active {
      background: var(--brand-blue);
      color: #ffffff;
      border-color: var(--brand-blue);
    }

    .roster-table-wrapper {
      overflow-x: auto;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      margin-bottom: 14px;
    }

    .roster-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.85rem;
    }

    .roster-table th {
      background: #f8fafc;
      padding: 10px 14px;
      font-weight: 700;
      color: var(--text-muted);
      font-size: 0.74rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      border-bottom: 1px solid var(--border-color);
    }

    .roster-table td {
      padding: 10px 14px;
      border-bottom: 1px solid #f1f5f9;
      vertical-align: middle;
    }

    .roster-student-info {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .roster-avatar {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      color: #ffffff;
      font-weight: 700;
      font-size: 0.75rem;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .roster-student-name {
      font-weight: 600;
      color: var(--primary-navy);
    }

    .roster-mssv-badge {
      font-family: monospace;
      font-size: 0.78rem;
      font-weight: 600;
      background: #f1f5f9;
      padding: 2px 6px;
      border-radius: 4px;
      color: #475569;
    }

    .roster-wallet-box {
      display: flex;
      align-items: center;
      gap: 6px;
      font-family: monospace;
      font-size: 0.8rem;
    }

    .roster-copy-btn, .roster-explorer-link {
      background: transparent;
      border: 1px solid var(--border-color);
      border-radius: 4px;
      padding: 2px 6px;
      cursor: pointer;
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    /* ============================================================ */
    /* 9. AI CHAT FLOATING WIDGET                                   */
    /* ============================================================ */
    .ai-fab-container {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 1050;
    }

    .ai-fab-btn {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 20px;
      background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%);
      color: #ffffff;
      border: none;
      border-radius: var(--radius-full);
      font-weight: 700;
      font-size: 0.9rem;
      cursor: pointer;
      box-shadow: 0 8px 20px rgba(37, 99, 235, 0.4);
      transition: all 0.2s ease;
    }

    .ai-fab-btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 12px 24px rgba(37, 99, 235, 0.5);
    }

    .ai-fab-badge {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #22c55e;
      box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.5);
    }

    .ai-chat-drawer {
      display: none;
      position: absolute;
      bottom: 60px;
      right: 0;
      width: 380px;
      max-width: calc(100vw - 32px);
      height: 540px;
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-lg);
      box-shadow: var(--shadow-xl);
      flex-direction: column;
      overflow: hidden;
    }

    .ai-chat-drawer.open {
      display: flex;
    }

    .ai-chat-header {
      padding: 14px 18px;
      background: var(--primary-navy);
      color: #ffffff;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .ai-header-title {
      font-size: 0.95rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .ai-header-status {
      font-size: 0.72rem;
      color: #94a3b8;
      display: flex;
      align-items: center;
      gap: 5px;
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
      color: #94a3b8;
      font-size: 1.25rem;
      cursor: pointer;
    }

    .ai-header-close:hover {
      color: #ffffff;
    }

    .ai-chat-body {
      flex: 1;
      padding: 16px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background: #f8fafc;
    }

    .ai-msg {
      max-width: 85%;
      padding: 10px 14px;
      border-radius: 12px;
      font-size: 0.84rem;
      line-height: 1.5;
    }

    .ai-msg-bot {
      background: #ffffff;
      border: 1px solid var(--border-color);
      color: var(--text-main);
      align-self: flex-start;
      border-bottom-left-radius: 2px;
    }

    .ai-msg-user {
      background: var(--brand-blue);
      color: #ffffff;
      align-self: flex-end;
      border-bottom-right-radius: 2px;
    }

    .ai-quick-prompts {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-top: 10px;
    }

    .ai-prompt-chip {
      background: #f1f5f9;
      border: 1px solid #cbd5e1;
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 0.78rem;
      color: #334155;
      text-align: left;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .ai-prompt-chip:hover {
      background: #e2e8f0;
      color: #0f172a;
    }

    .ai-chat-footer {
      padding: 12px 14px;
      border-top: 1px solid var(--border-color);
      background: #ffffff;
    }

    .ai-input-row {
      display: flex;
      gap: 8px;
    }

    .ai-input {
      flex: 1;
      padding: 8px 12px;
      border: 1px solid var(--border-color);
      border-radius: 6px;
      font-size: 0.84rem;
      outline: none;
    }

    .ai-input:focus {
      border-color: var(--brand-blue);
    }

    .ai-send-btn {
      padding: 8px 14px;
      background: var(--brand-blue);
      color: #ffffff;
      border: none;
      border-radius: 6px;
      font-weight: 600;
      font-size: 0.84rem;
      cursor: pointer;
    }

    .ai-footer-note {
      font-size: 0.68rem;
      color: var(--text-light);
      margin-top: 6px;
      text-align: center;
    }

    /* Footer */
    .site-footer {
      background: #0f172a;
      color: #94a3b8;
      padding: 40px 0 24px 0;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      margin-top: auto;
    }

    .footer-grid {
      display: grid;
      grid-template-columns: 2fr 1fr 1fr;
      gap: 32px;
      margin-bottom: 32px;
    }

    .footer-brand h3 {
      color: #ffffff;
      font-size: 1.15rem;
      margin-bottom: 8px;
    }

    .footer-links h4 {
      color: #ffffff;
      font-size: 0.88rem;
      margin-bottom: 12px;
    }

    .footer-links ul {
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 8px;
      font-size: 0.84rem;
    }

    .footer-links a {
      color: #94a3b8;
    }

    .footer-links a:hover {
      color: #ffffff;
    }

    .footer-bottom {
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      padding-top: 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.78rem;
      flex-wrap: wrap;
      gap: 10px;
    }

    /* ============================================================ */
    /* 10. RESPONSIVE BREAKPOINTS                                   */
    /* ============================================================ */
    @media (max-width: 1024px) {
      .app-sidebar {
        transform: translateX(-100%);
      }

      .app-sidebar.show {
        transform: translateX(0);
      }

      .sidebar-backdrop.show {
        display: block;
      }

      .app-main {
        margin-left: 0;
        width: 100%;
      }

      .menu-toggle {
        display: block;
      }

      .app-content {
        padding: 20px 16px 40px 16px;
      }

      .app-topbar {
        padding: 0 16px;
      }

      .footer-grid {
        grid-template-columns: 1fr;
        gap: 24px;
      }
    }

    @media (max-width: 640px) {
      .hero-title {
        font-size: 1.35rem;
      }

      .quick-status-group {
        grid-template-columns: 1fr;
      }

      .role-buttons-group {
        grid-template-columns: 1fr 1fr;
      }

      .metrics-grid {
        grid-template-columns: 1fr 1fr;
      }

      .contract-input-bar {
        min-width: 100%;
      }
    }
    """

    print("CSS built successfully.")

if __name__ == "__main__":
    build()
