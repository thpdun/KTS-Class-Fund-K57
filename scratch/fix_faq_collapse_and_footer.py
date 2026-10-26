import sys

sys.stdout.reconfigure(encoding='utf-8')

with open("web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# ----------------------------------------------------------------------
# 1. FIX FAQ COLLAPSE: Add strict .accordion-body { display: none !important; }
# ----------------------------------------------------------------------
faq_collapse_css = """
    /* ============================================================ */
    /* FAQ ACCORDION COLLAPSE & EXPAND SYSTEM                       */
    /* ============================================================ */
    .accordion-item {
      background: #ffffff !important;
      border: 1px solid var(--border-color) !important;
      border-radius: var(--radius-md) !important;
      margin-bottom: 12px !important;
      overflow: hidden !important;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
      box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04) !important;
    }
    .accordion-item:hover {
      border-color: #cbd5e1 !important;
      box-shadow: 0 2px 6px rgba(15, 23, 42, 0.06) !important;
    }
    .accordion-item.open {
      border-color: var(--brand-blue) !important;
      box-shadow: 0 4px 14px rgba(37, 99, 235, 0.1) !important;
    }

    .accordion-header {
      padding: 16px 20px !important;
      display: flex !important;
      align-items: center !important;
      justify-content: space-between !important;
      cursor: pointer !important;
      user-select: none !important;
      font-weight: 600 !important;
      color: var(--primary-navy) !important;
      font-size: 0.95rem !important;
      background: #ffffff !important;
      transition: background 0.15s ease !important;
    }
    .accordion-header:hover {
      background: #f8fafc !important;
    }
    .accordion-item.open .accordion-header {
      background: #f8fafc !important;
      border-bottom: 1px solid #f1f5f9 !important;
      color: var(--brand-blue) !important;
    }

    .accordion-icon {
      font-size: 1.15rem !important;
      font-weight: 700 !important;
      color: #94a3b8 !important;
      transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1), color 0.2s ease !important;
      flex-shrink: 0 !important;
      margin-left: 14px !important;
      display: inline-block !important;
    }
    .accordion-item.open .accordion-icon {
      transform: rotate(180deg) !important;
      color: var(--brand-blue) !important;
    }

    /* ĐẶC BIỆT: THU GỌN MẶC ĐỊNH 100% CÂU TRẢ LỜI */
    .accordion-body {
      display: none !important; /* MẶC ĐỊNH ẨN HOÀN TOÀN */
      padding: 18px 22px !important;
      color: #334155 !important;
      font-size: 0.92rem !important;
      line-height: 1.7 !important;
      background: #ffffff !important;
      border-top: 1px solid #f1f5f9 !important;
    }
    .accordion-item.open .accordion-body {
      display: block !important; /* CHỈ HIỂN THỊ KHI CÓ CLASS .OPEN */
      animation: faqSlideFadeIn 0.22s ease-out !important;
    }

    @keyframes faqSlideFadeIn {
      from {
        opacity: 0;
        transform: translateY(-6px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
"""

# ----------------------------------------------------------------------
# 2. FIX FOOTER: Prevent overlapping, add safety clearance for FAB button
# ----------------------------------------------------------------------
footer_fix_css = """
    /* ============================================================ */
    /* SITE FOOTER CLEARANCE & UNCOVERED SAFE AREA                  */
    /* ============================================================ */
    .site-footer {
      background: #0f172a !important;
      color: #94a3b8 !important;
      padding: 48px 0 calc(96px + env(safe-area-inset-bottom, 0px)) 0 !important; /* Khoảng đệm an toàn không bị nút AI che */
      border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
      margin-top: auto !important;
      position: relative !important;
      z-index: 10 !important;
      width: 100% !important;
      clear: both !important;
    }

    .site-footer .container {
      padding: 0 32px !important;
      max-width: 1300px !important;
      margin: 0 auto !important;
    }

    .footer-grid {
      display: grid !important;
      grid-template-columns: 2fr 1fr 1fr !important;
      gap: 36px !important;
      margin-bottom: 32px !important;
    }
    @media (max-width: 900px) {
      .footer-grid {
        grid-template-columns: 1fr !important;
        gap: 24px !important;
      }
    }

    .footer-bottom {
      border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
      padding-top: 22px !important;
      padding-right: 80px !important; /* Né vị trí nút AI Fab Button ở góc phải */
      display: flex !important;
      justify-content: space-between !important;
      align-items: center !important;
      font-size: 0.8rem !important;
      flex-wrap: wrap !important;
      gap: 12px !important;
    }
    @media (max-width: 768px) {
      .footer-bottom {
        padding-right: 0 !important;
        flex-direction: column !important;
        align-items: flex-start !important;
      }
    }
"""

# Inject the new styles right before </style>
html = html.replace('</style>', faq_collapse_css + '\n' + footer_fix_css + '\n  </style>')
print("1. Injected FAQ Accordion Collapse CSS (.accordion-body display:none by default)")
print("2. Injected Site Footer Clearance CSS (padding-bottom 96px, padding-right 80px)")

# Verify toggleFaq in JavaScript
# Ensure toggleFaq properly toggles the class 'open' on the accordion-item
toggle_faq_code = """    function toggleFaq(index) {
      const item = document.getElementById(`faq-item-${index}`);
      if (!item) return;
      const isOpen = item.classList.contains("open");
      // Optional: If accordion style, close others, or allow multiple open
      // Let's toggle smoothly:
      if (isOpen) {
        item.classList.remove("open");
      } else {
        item.classList.add("open");
      }
    }"""

old_toggle = """    function toggleFaq(index) {
      const item = document.getElementById(`faq-item-${index}`);
      if (!item) return;
      const isOpen = item.classList.contains("open");
      document.querySelectorAll(".accordion-item").forEach(el => el.classList.remove("open"));
      if (!isOpen) {
        item.classList.add("open");
      }
    }"""

if old_toggle in html:
    html = html.replace(old_toggle, toggle_faq_code)
    print("3. Updated toggleFaq function so clicking an open item collapses it smoothly")
else:
    print("3. Old toggle function not matched verbatim, checking if already customized")

# Verify all required IDs are present
import json
with open("scratch/all_ids.json", "r", encoding="utf-8") as f:
    id_data = json.load(f)

req_ids = id_data["html_ids"]
missing_ids = [i for i in req_ids if f'id="{i}"' not in html and f"id='{i}'" not in html]

print(f"4. ID Validation: {len(req_ids) - len(missing_ids)}/{len(req_ids)} IDs present.")
if missing_ids:
    print(f"ERROR: Missing IDs: {missing_ids}")
    sys.exit(1)
else:
    print("PERFECT: 100% of required IDs are preserved!")

with open("web/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("5. Successfully updated web/index.html with FAQ collapse & footer clearance!")
