import os
import re
import json

def generate_yg_css():
    return """
    /* ============================================================ */
    /* MINIMALIST LUXURY EDITORIAL (YG ENTERTAINMENT INSPIRED) CSS    */
    /* ============================================================ */
    :root {
      /* Editorial Palette */
      --bg-primary: #ffffff;
      --bg-secondary: #f8fafc;
      --bg-tertiary: #f1f5f9;
      --bg-card: #ffffff;
      --bg-card-hover: #fafafa;

      /* High-contrast Monochrome */
      --black-pure: #000000;
      --black-rich: #09090b;
      --black-subtle: #18181b;
      --black-surface: #27272a;

      --white-pure: #ffffff;
      --white-off: #fbfbfb;

      --gray-50: #fafafa;
      --gray-100: #f4f4f5;
      --gray-200: #e4e4e7;
      --gray-300: #d4d4d8;
      --gray-400: #a1a1aa;
      --gray-500: #71717a;
      --gray-600: #52525b;
      --gray-700: #3f3f46;
      --gray-800: #27272a;
      --gray-900: #18181b;

      /* Web3 Electric Blue Accent */
      --accent-blue: #2563eb;
      --accent-blue-hover: #1d4ed8;
      --accent-blue-subtle: #eff6ff;
      --accent-blue-border: #bfdbfe;

      /* Role Semantics (High-fashion refinement) */
      --student-color: #047857;
      --student-bg: #f0fdf4;
      --student-border: #bbf7d0;

      --bcs-color: #2563eb;
      --bcs-bg: #eff6ff;
      --bcs-border: #bfdbfe;

      --advisor-color: #6d28d9;
      --advisor-bg: #f5f3ff;
      --advisor-border: #ddd6fe;

      --danger-color: #b91c1c;
      --danger-bg: #fef2f2;
      --danger-border: #fecaca;

      --warning-color: #b45309;
      --warning-bg: #fffbeb;
      --warning-border: #fde68a;

      /* Borders & Layout */
      --border-thin: 1px solid #e4e4e7;
      --border-dark: 1px solid #09090b;
      --max-width: 1360px;
      --header-height: 72px;

      --radius-sm: 4px;
      --radius-md: 8px;
      --radius-lg: 12px;
      --radius-full: 9999px;

      --transition-fast: 0.18s cubic-bezier(0.16, 1, 0.3, 1);
      --transition-smooth: 0.25s cubic-bezier(0.16, 1, 0.3, 1);
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
      background-color: var(--bg-secondary);
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
      letter-spacing: -0.025em;
      line-height: 1.2;
    }

    a {
      color: inherit;
      text-decoration: none;
      transition: color var(--transition-fast);
    }

    .editorial-tag {
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: var(--gray-500);
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }

    .editorial-tag::before {
      content: "";
      display: inline-block;
      width: 6px;
      height: 6px;
      background: var(--accent-blue);
      border-radius: 50%;
    }

    /* TOPBAR HEADER */
    .app-topbar {
      position: sticky;
      top: 0;
      z-index: 1000;
      background: rgba(255, 255, 255, 0.95);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border-bottom: var(--border-thin);
      height: var(--header-height);
      display: flex;
      align-items: center;
      transition: all var(--transition-fast);
    }

    .topbar-container {
      width: 100%;
      max-width: var(--max-width);
      margin: 0 auto;
      padding: 0 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
    }

    .brand-group {
      display: flex;
      align-items: center;
      gap: 14px;
      flex-shrink: 0;
    }

    .brand-logo-mark {
      width: 38px;
      height: 38px;
      background: var(--black-pure);
      color: var(--white-pure);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 900;
      font-size: 0.95rem;
      letter-spacing: 0.05em;
      border-radius: var(--radius-sm);
      transition: transform var(--transition-fast), background var(--transition-fast);
    }

    .brand-logo-mark:hover {
      background: var(--accent-blue);
      transform: scale(1.04);
    }

    .brand-titles {
      display: flex;
      flex-direction: column;
    }

    .brand-main {
      font-size: 1.05rem;
      font-weight: 800;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--black-pure);
      line-height: 1.1;
    }

    .brand-sub {
      font-size: 0.65rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--gray-500);
      margin-top: 2px;
    }

    /* TOPBAR NAVIGATION */
    .topbar-nav {
      display: flex;
      align-items: center;
      gap: 28px;
      list-style: none;
    }

    .nav-item-link {
      font-size: 0.8rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--gray-600);
      position: relative;
      padding: 6px 0;
      transition: color var(--transition-fast);
    }

    .nav-item-link::after {
      content: "";
      position: absolute;
      bottom: 0;
      left: 0;
      width: 0%;
      height: 2px;
      background: var(--black-pure);
      transition: width var(--transition-smooth);
    }

    .nav-item-link:hover {
      color: var(--black-pure);
    }

    .nav-item-link:hover::after {
      width: 100%;
    }

    .nav-roster-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 0.76rem;
      font-weight: 600;
      padding: 4px 10px;
      border: 1px solid var(--gray-300);
      border-radius: var(--radius-full);
      background: var(--gray-50);
      color: var(--black-rich);
      cursor: pointer;
      transition: all var(--transition-fast);
    }

    .nav-roster-pill:hover {
      border-color: var(--black-pure);
      background: var(--white-pure);
    }

    /* TOPBAR ACTIONS */
    .topbar-actions {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-shrink: 0;
    }

    .network-badge-minimal {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      background: var(--white-pure);
      border: var(--border-thin);
      border-radius: var(--radius-full);
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--gray-700);
      letter-spacing: 0.02em;
    }

    .network-dot-live {
      width: 7px;
      height: 7px;
      background: #10b981;
      border-radius: 50%;
      box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
      animation: pulseDot 2.2s infinite ease-in-out;
    }

    @keyframes pulseDot {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.85); }
    }

    /* LUXURY BUTTONS */
    .btn-yg {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      font-family: inherit;
      font-size: 0.82rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      padding: 10px 20px;
      border-radius: var(--radius-sm);
      cursor: pointer;
      transition: all var(--transition-fast);
      border: 1px solid transparent;
      outline: none;
      white-space: nowrap;
    }

    .btn-yg-black {
      background: var(--black-pure);
      color: var(--white-pure);
      border-color: var(--black-pure);
    }

    .btn-yg-black:hover {
      background: var(--accent-blue);
      border-color: var(--accent-blue);
      color: var(--white-pure);
      transform: translateY(-1px);
    }

    .btn-yg-outline {
      background: transparent;
      color: var(--black-pure);
      border: 1px solid var(--gray-300);
    }

    .btn-yg-outline:hover {
      border-color: var(--black-pure);
      background: var(--white-pure);
    }

    .btn-yg-blue {
      background: var(--accent-blue);
      color: var(--white-pure);
      border-color: var(--accent-blue);
    }

    .btn-yg-blue:hover {
      background: var(--accent-blue-hover);
      transform: translateY(-1px);
    }

    .btn-yg-danger {
      background: var(--danger-bg);
      color: var(--danger-color);
      border-color: var(--danger-border);
    }

    .btn-yg-danger:hover {
      background: var(--danger-color);
      color: var(--white-pure);
    }

    .btn-sm-yg {
      padding: 6px 14px;
      font-size: 0.75rem;
    }

    /* MOBILE NAV TOGGLE */
    .btn-mobile-toggle {
      display: none;
      background: transparent;
      border: var(--border-thin);
      border-radius: var(--radius-sm);
      padding: 8px;
      cursor: pointer;
      color: var(--black-pure);
    }

    /* SIDEBAR OFF-CANVAS (FOR MOBILE COMPATIBILITY) */
    .app-sidebar {
      position: fixed;
      top: 0;
      right: 0;
      width: 320px;
      height: 100vh;
      background: var(--white-pure);
      border-left: var(--border-thin);
      z-index: 2000;
      display: flex;
      flex-direction: column;
      transform: translateX(100%);
      transition: transform var(--transition-smooth);
      box-shadow: -8px 0 24px rgba(0, 0, 0, 0.08);
      padding: 24px;
      overflow-y: auto;
    }

    .app-sidebar.show {
      transform: translateX(0);
    }

    .sidebar-backdrop {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(0, 0, 0, 0.4);
      backdrop-filter: blur(4px);
      z-index: 1999;
      opacity: 0;
      pointer-events: none;
      transition: opacity var(--transition-smooth);
    }

    .sidebar-backdrop.show {
      opacity: 1;
      pointer-events: auto;
    }

    /* MAIN CONTAINER */
    .app-main {
      flex: 1;
      width: 100%;
      max-width: var(--max-width);
      margin: 0 auto;
      padding: 40px 24px 80px 24px;
      display: flex;
      flex-direction: column;
      gap: 48px;
    }

    /* HERO SECTION */
    .hero-editorial {
      background: var(--white-pure);
      border: var(--border-thin);
      border-radius: var(--radius-md);
      padding: 48px 48px 40px 48px;
      display: flex;
      flex-direction: column;
      gap: 28px;
      position: relative;
    }

    .hero-top-row {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 24px;
      flex-wrap: wrap;
    }

    .hero-header-text {
      max-width: 820px;
    }

    .hero-title-giant {
      font-size: clamp(2rem, 3.6vw, 3.1rem);
      font-weight: 900;
      letter-spacing: -0.035em;
      text-transform: uppercase;
      color: var(--black-pure);
      line-height: 1.1;
      margin-top: 8px;
      margin-bottom: 12px;
    }

    .hero-sub-editorial {
      font-size: 1rem;
      font-weight: 500;
      color: var(--gray-600);
      line-height: 1.6;
      max-width: 760px;
    }

    /* HERO USER IDENTITY CARD */
    .hero-user-badge-card {
      background: var(--gray-50);
      border: var(--border-thin);
      border-radius: var(--radius-sm);
      padding: 16px 20px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      min-width: 280px;
    }

    .user-card-label {
      font-size: 0.68rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--gray-500);
    }

    .user-card-name {
      font-size: 1.05rem;
      font-weight: 800;
      color: var(--black-pure);
    }

    .user-card-meta {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }

    .user-card-address {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.8rem;
      color: var(--gray-600);
      background: var(--white-pure);
      border: 1px solid var(--gray-200);
      padding: 2px 8px;
      border-radius: var(--radius-xs);
    }

    /* QUICK CONTRACT BAR */
    .quick-contract-strip {
      background: var(--gray-50);
      border: var(--border-thin);
      border-radius: var(--radius-sm);
      padding: 12px 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
    }

    .contract-label-group {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .contract-input-pill {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.82rem;
      font-weight: 600;
      color: var(--black-rich);
      background: var(--white-pure);
      border: 1px solid var(--gray-300);
      border-radius: var(--radius-xs);
      padding: 7px 12px;
      min-width: 380px;
      outline: none;
      transition: border-color var(--transition-fast);
    }

    .contract-input-pill:focus {
      border-color: var(--black-pure);
    }

    .contract-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    /* GUEST WARNING BANNER */
    .guest-warning-editorial {
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

    /* OVERVIEW METRICS GRID (EDITORIAL HIGH IMPACT) */
    .metrics-editorial-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
    }

    .metric-card-editorial {
      background: var(--white-pure);
      border: var(--border-thin);
      border-radius: var(--radius-sm);
      padding: 24px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 16px;
      transition: transform var(--transition-fast), border-color var(--transition-fast);
    }

    .metric-card-editorial:hover {
      border-color: var(--black-pure);
      transform: translateY(-2px);
    }

    .metric-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
    }

    .metric-card-tag {
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--gray-500);
    }

    .metric-card-icon {
      font-size: 1rem;
      opacity: 0.8;
    }

    .metric-number-giant {
      font-size: clamp(1.8rem, 2.5vw, 2.3rem);
      font-weight: 800;
      font-feature-settings: "tnum";
      font-variant-numeric: tabular-nums;
      color: var(--black-pure);
      letter-spacing: -0.025em;
      line-height: 1.1;
    }

    .metric-unit-text {
      font-size: 0.88rem;
      font-weight: 600;
      color: var(--gray-500);
      margin-left: 4px;
    }

    .metric-sub-note {
      font-size: 0.78rem;
      color: var(--gray-500);
      border-top: 1px solid var(--gray-100);
      padding-top: 10px;
    }

    /* ANNOUNCEMENT CARD */
    .announcement-box-editorial {
      background: var(--white-pure);
      border: var(--border-thin);
      border-radius: var(--radius-sm);
      padding: 32px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    .ann-header-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 14px;
    }

    .ann-title-main {
      font-size: 1.35rem;
      font-weight: 800;
      color: var(--black-pure);
    }

    .ann-stats-ribbon {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      background: var(--gray-50);
      border: var(--border-thin);
      border-radius: var(--radius-xs);
      padding: 16px 20px;
    }

    .ann-stat-item {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .ann-stat-lbl {
      font-size: 0.7rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--gray-500);
    }

    .ann-stat-val {
      font-size: 1.1rem;
      font-weight: 800;
      color: var(--black-pure);
    }

    .ann-progress-wrapper {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .ann-progress-track {
      width: 100%;
      height: 6px;
      background: var(--gray-200);
      border-radius: var(--radius-full);
      overflow: hidden;
    }

    .ann-progress-fill {
      height: 100%;
      background: var(--black-pure);
      border-radius: var(--radius-full);
      transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .ann-progress-labels {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.78rem;
      color: var(--gray-600);
      font-weight: 600;
    }

    /* WORKSPACE ROLES SECTION */
    .workspace-section {
      background: var(--white-pure);
      border: var(--border-thin);
      border-radius: var(--radius-sm);
      overflow: hidden;
    }

    .workspace-tab-nav {
      display: flex;
      align-items: center;
      border-bottom: var(--border-thin);
      background: var(--white-pure);
      overflow-x: auto;
    }

    .workspace-tab-btn {
      flex: 1;
      padding: 18px 24px;
      background: transparent;
      border: none;
      border-right: var(--border-thin);
      border-bottom: 2px solid transparent;
      font-family: inherit;
      font-size: 0.82rem;
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

    .workspace-tab-btn:hover {
      color: var(--black-pure);
      background: var(--gray-50);
    }

    .workspace-tab-btn.active {
      color: var(--black-pure);
      border-bottom-color: var(--black-pure);
      background: var(--white-pure);
    }

    .workspace-tab-btn:last-child {
      border-right: none;
    }

    .workspace-panel-body {
      padding: 36px;
    }

    .role-panel-content {
      display: none;
      flex-direction: column;
      gap: 32px;
    }

    .role-panel-content.active {
      display: flex;
    }

    /* FORMS & INPUTS (ARCHITECTURAL & CRISP) */
    .form-group-editorial {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .form-label-editorial {
      font-size: 0.76rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--black-pure);
    }

    .form-control-editorial {
      width: 100%;
      padding: 11px 16px;
      background: var(--white-pure);
      border: 1px solid var(--gray-300);
      border-radius: var(--radius-xs);
      font-family: inherit;
      font-size: 0.9rem;
      color: var(--black-pure);
      outline: none;
      transition: border-color var(--transition-fast);
    }

    .form-control-editorial:focus {
      border-color: var(--black-pure);
    }

    .form-hint {
      font-size: 0.74rem;
      color: var(--gray-500);
    }

    .split-calc-box {
      background: var(--gray-50);
      border: var(--border-thin);
      border-radius: var(--radius-xs);
      padding: 14px 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      font-size: 0.82rem;
      flex-wrap: wrap;
    }

    /* DATA TABLES & LISTS */
    .table-container-minimal {
      width: 100%;
      overflow-x: auto;
      border: var(--border-thin);
      border-radius: var(--radius-xs);
    }

    .table-minimal {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.84rem;
      text-align: left;
    }

    .table-minimal th {
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

    .table-minimal td {
      padding: 14px 18px;
      border-bottom: 1px solid var(--gray-100);
      color: var(--black-rich);
      vertical-align: middle;
    }

    .table-minimal tr:last-child td {
      border-bottom: none;
    }

    .table-minimal tr:hover td {
      background: var(--gray-50);
    }

    /* STATUS PILL BADGES */
    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 0.72rem;
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
      background: var(--accent-blue-subtle);
      color: var(--accent-blue);
      border-color: var(--accent-blue-border);
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

    /* TERMINAL LOG (EDITORIAL DARK MINIMAL) */
    .terminal-box-minimal {
      background: var(--black-pure);
      border-radius: var(--radius-sm);
      padding: 20px 24px;
      color: #e4e4e7;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.8rem;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .terminal-content {
      max-height: 220px;
      overflow-y: auto;
      line-height: 1.6;
      word-break: break-all;
    }

    /* MODAL STYLES (LUXURY OVERLAY) */
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
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
      animation: modalSlideIn 0.22s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .modal-card.modal-lg {
      max-width: 880px;
    }

    @keyframes modalSlideIn {
      from { transform: translateY(16px); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
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

    .modal-close-btn {
      background: transparent;
      border: none;
      font-size: 1.3rem;
      color: var(--gray-500);
      cursor: pointer;
      line-height: 1;
      transition: color var(--transition-fast);
    }

    .modal-close-btn:hover {
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

    /* AI FLOATING CHAT WIDGET */
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
      letter-spacing: 0.04em;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 10px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
      transition: all var(--transition-fast);
    }

    .ai-fab-btn:hover {
      background: var(--accent-blue);
      border-color: var(--accent-blue);
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
      letter-spacing: 0.02em;
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

    .ai-header-close:hover {
      color: var(--white-pure);
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

    .ai-quick-prompts {
      margin-top: 10px;
      display: flex;
      flex-direction: column;
      gap: 6px;
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
      transition: all var(--transition-fast);
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

    .ai-input:focus {
      border-color: var(--black-pure);
    }

    .ai-send-btn {
      padding: 8px 16px;
      background: var(--black-pure);
      color: var(--white-pure);
      border: none;
      border-radius: var(--radius-xs);
      font-weight: 700;
      font-size: 0.8rem;
      cursor: pointer;
      transition: background var(--transition-fast);
    }

    .ai-send-btn:hover {
      background: var(--accent-blue);
    }

    .ai-footer-note {
      font-size: 0.68rem;
      color: var(--gray-500);
      text-align: center;
    }

    /* FOOTER */
    .site-footer-editorial {
      background: var(--white-pure);
      border-top: var(--border-thin);
      padding: 48px 24px;
      margin-top: auto;
    }

    .footer-container {
      max-width: var(--max-width);
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 24px;
      flex-wrap: wrap;
    }

    .footer-brand {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .footer-brand-title {
      font-size: 0.95rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .footer-brand-copy {
      font-size: 0.76rem;
      color: var(--gray-500);
    }

    /* RESPONSIVE BREAKPOINTS */
    @media (max-width: 1024px) {
      .topbar-nav {
        display: none;
      }
      .btn-mobile-toggle {
        display: flex;
      }
      .hero-editorial {
        padding: 32px 24px;
      }
      .workspace-panel-body {
        padding: 24px;
      }
    }

    @media (max-width: 640px) {
      .hero-title-giant {
        font-size: 1.85rem;
      }
      .contract-input-pill {
        min-width: 100%;
      }
      .topbar-actions .network-badge-minimal {
        display: none;
      }
      .ai-chat-drawer {
        width: calc(100vw - 32px);
        right: 16px;
        bottom: 80px;
        height: 520px;
      }
      .ai-fab-container {
        bottom: 16px;
        right: 16px;
      }
    }
    """

if __name__ == "__main__":
    css = generate_yg_css()
    print(f"Generated CSS length: {len(css)} characters")
