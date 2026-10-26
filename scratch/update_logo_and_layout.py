import re
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

with open("web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1. Add Favicon in <head>
if '<link rel="icon"' not in html:
    fav_tag = '  <link rel="icon" type="image/jpeg" href="logo.jpg">\n'
    html = html.replace('</head>', fav_tag + '</head>')
    print("1. Added favicon in <head>")

# 2. Update Sidebar Logo to use web/logo.jpg
old_sidebar_logo = """      <div class="sidebar-logo-icon">
        <svg viewBox="0 0 24 24">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
        </svg>
      </div>"""

new_sidebar_logo = """      <img src="logo.jpg" alt="Logo KTS Class Fund" class="sidebar-logo-img">"""

if old_sidebar_logo in html:
    html = html.replace(old_sidebar_logo, new_sidebar_logo)
    print("2. Replaced sidebar SVG with logo.jpg")
else:
    # Try regex match for sidebar-logo-icon
    html = re.sub(
        r'<div class="sidebar-logo-icon">[\s\S]*?</div>',
        '<img src="logo.jpg" alt="Logo KTS Class Fund" class="sidebar-logo-img">',
        html,
        count=1
    )
    print("2. Replaced sidebar logo icon via regex with logo.jpg")

# 3. Add topbar-mini-logo for mobile/compact views in topbar-left
if '<img src="logo.jpg" alt="KTS Logo" class="topbar-mini-logo">' not in html:
    html = html.replace(
        '<button class="menu-toggle" id="btnToggleNav" aria-label="Mở menu điều hướng">☰</button>',
        '<button class="menu-toggle" id="btnToggleNav" aria-label="Mở menu điều hướng">☰</button>\n        <img src="logo.jpg" alt="KTS Logo" class="topbar-mini-logo">'
    )
    print("3. Added topbar-mini-logo in topbar-left")

# 4. Remove "Mạng mục tiêu" from Quick Control Bar
# Currently:
# <div class="quick-status-item">
#   <span class="quick-status-label">Mạng mục tiêu</span>
#   <span class="quick-status-val" id="quickNetworkStatus">Ethereum Sepolia (11155111)</span>
# </div>
target_net_pattern = r'<div class="quick-status-item">\s*<span class="quick-status-label">Mạng mục tiêu</span>\s*<span class="quick-status-val" id="quickNetworkStatus">[^<]*</span>\s*</div>'
if re.search(target_net_pattern, html):
    html = re.sub(target_net_pattern, '<span id="quickNetworkStatus" style="display: none;"></span>', html)
    print("4. Removed 'Mạng mục tiêu' from Quick Control Bar (retained hidden id='quickNetworkStatus')")
else:
    print("4. Target net pattern not matched directly, checking alternative match...")
    alt_net = '<div class="quick-status-item">\n              <span class="quick-status-label">Mạng mục tiêu</span>\n              <span class="quick-status-val" id="quickNetworkStatus">Ethereum Sepolia (11155111)</span>\n            </div>'
    if alt_net in html:
        html = html.replace(alt_net, '<span id="quickNetworkStatus" style="display: none;"></span>')
        print("4. Replaced alt_net successfully!")

# 5. Remove "Mạng mục tiêu" from section #transparency
old_trans_net = '<strong>Mạng mục tiêu:</strong> Ethereum Sepolia Testnet (Mã mạng Chain ID: 11155111 - 0xaa36a7)<br>'
if old_trans_net in html:
    html = html.replace(old_trans_net, '')
    print("5. Removed 'Mạng mục tiêu' from section #transparency")

# 6. CSS enhancements for logo, quick-control-bar alignment, and professional layout
additional_css = """
    /* --- ENHANCED LOGO & POLISHED LAYOUT --- */
    .sidebar-logo-img {
      width: 44px;
      height: 44px;
      border-radius: 11px;
      object-fit: cover;
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.4);
      flex-shrink: 0;
      border: 1.5px solid rgba(255, 255, 255, 0.2);
      transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .sidebar-logo-img:hover {
      transform: scale(1.06);
    }

    .topbar-mini-logo {
      width: 34px;
      height: 34px;
      border-radius: 8px;
      object-fit: cover;
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
      border: 1px solid var(--border-color);
      display: none;
    }
    @media (max-width: 1024px) {
      .topbar-mini-logo {
        display: block;
      }
    }

    /* Polished Quick Control Bar */
    .quick-control-bar {
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-lg);
      padding: 18px 22px;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      gap: 16px;
      margin-bottom: 22px;
    }

    .quick-status-group {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
      align-items: center;
    }

    .quick-status-item {
      display: flex;
      flex-direction: column;
      gap: 5px;
      padding: 10px 14px;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
    }

    .quick-status-label {
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-muted);
    }

    .quick-status-val {
      font-size: 0.92rem;
      font-weight: 700;
      color: var(--primary-navy);
      word-break: break-all;
    }

    /* Enhanced Contract Input Bar in Toolbar */
    .contract-toolbar-row {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      padding-top: 4px;
      border-top: 1px solid #f1f5f9;
    }

    .contract-input-bar {
      display: flex;
      align-items: center;
      gap: 10px;
      background: #f8fafc;
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 8px 14px;
      flex: 1;
      min-width: 290px;
      transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    .contract-input-bar:focus-within {
      border-color: var(--brand-blue);
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
      background: #ffffff;
    }

    .contract-input-bar input {
      border: none;
      background: transparent;
      outline: none;
      font-family: monospace;
      font-size: 0.88rem;
      color: var(--text-main);
      width: 100%;
    }

    /* Crisp Role Buttons Group */
    .role-buttons-group {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      margin-top: 14px;
      margin-bottom: 20px;
    }
    @media (max-width: 900px) {
      .role-buttons-group {
        grid-template-columns: repeat(2, 1fr);
      }
    }
    @media (max-width: 500px) {
      .role-buttons-group {
        grid-template-columns: 1fr;
      }
    }

    .role-btn-item {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      padding: 14px 16px;
      border-radius: var(--radius-lg);
      background: #ffffff;
      border: 1.5px solid var(--border-color);
      cursor: pointer;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      font-weight: 700;
      font-size: 0.92rem;
      color: var(--text-main);
      box-shadow: var(--shadow-xs);
    }
    .role-btn-item:hover {
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
      border-color: #cbd5e1;
    }
    .role-btn-student.active {
      border-color: var(--student-color) !important;
      background: var(--student-bg) !important;
      color: var(--student-color) !important;
      box-shadow: 0 4px 12px rgba(5, 150, 105, 0.15) !important;
    }
    .role-btn-bcs.active {
      border-color: var(--bcs-color) !important;
      background: var(--bcs-bg) !important;
      color: var(--bcs-color) !important;
      box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15) !important;
    }
    .role-btn-advisor.active {
      border-color: var(--advisor-color) !important;
      background: var(--advisor-bg) !important;
      color: var(--advisor-color) !important;
      box-shadow: 0 4px 12px rgba(124, 58, 237, 0.15) !important;
    }
    .role-btn-history.active {
      border-color: var(--primary-navy) !important;
      background: #f1f5f9 !important;
      color: var(--primary-navy) !important;
      box-shadow: 0 4px 12px rgba(15, 23, 42, 0.15) !important;
    }
"""

if "/* --- ENHANCED LOGO & POLISHED LAYOUT --- */" not in html:
    html = html.replace('</style>', additional_css + '\n  </style>')
    print("6. Injected enhanced CSS for logo and polished layout")

# 7. Verify all IDs remain intact
with open("scratch/all_ids.json", "r", encoding="utf-8") as f:
    id_data = json.load(f)

req_ids = id_data["html_ids"]
missing_ids = [i for i in req_ids if f'id="{i}"' not in html and f"id='{i}'" not in html]

print(f"7. ID Validation: {len(req_ids) - len(missing_ids)}/{len(req_ids)} IDs present.")
if missing_ids:
    print(f"ERROR: Missing IDs: {missing_ids}")
    sys.exit(1)
else:
    print("PERFECT: 100% of required IDs are preserved!")

# 8. Write updated file to web/index.html
with open("web/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("8. Successfully updated web/index.html!")
