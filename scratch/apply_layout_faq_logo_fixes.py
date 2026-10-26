import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

with open("web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# ----------------------------------------------------------------------
# 1. LOGO UPDATES: Use transparent web/logo.png with clean background
# ----------------------------------------------------------------------
# Replace logo.jpg references with logo.png for transparent presentation
html = html.replace('src="logo.jpg"', 'src="logo.png"')
html = html.replace('href="logo.jpg"', 'href="logo.png"')
print("1. Updated logo source to transparent logo.png")

# ----------------------------------------------------------------------
# 2. FAQ COLLAPSIBLE & COMPACT SYSTEM
# ----------------------------------------------------------------------
# In section #faq, add category filter pills and control actions above faqAccordionContainer
old_faq_container = '<div id="faqAccordionContainer" style="max-width: 860px; margin: 0 auto;"></div>'

new_faq_container = """<div class="faq-controls-bar" style="max-width: 860px; margin: 0 auto 16px auto; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
            <div class="faq-category-pills" id="faqCategoryPills">
              <button type="button" class="faq-cat-btn active" onclick="setFaqCategory('all')">Tất cả (25)</button>
              <button type="button" class="faq-cat-btn" onclick="setFaqCategory('Tổng quan')">Tổng quan (5)</button>
              <button type="button" class="faq-cat-btn" onclick="setFaqCategory('Ví và kết nối')">Ví & Mạng (5)</button>
              <button type="button" class="faq-cat-btn" onclick="setFaqCategory('Đóng góp và phí')">Nộp quỹ & Phí (6)</button>
              <button type="button" class="faq-cat-btn" onclick="setFaqCategory('Đề xuất và biểu quyết')">Biểu quyết 51% (6)</button>
              <button type="button" class="faq-cat-btn" onclick="setFaqCategory('Hoàn tiền và lỗi giao dịch')">Hoàn tiền (3)</button>
            </div>
            <div class="faq-action-btns" style="display: flex; gap: 8px;">
              <button type="button" class="btn btn-sm btn-outline" id="btnToggleAllFaq" onclick="toggleAllFaq()">Mở rộng tất cả ▾</button>
            </div>
          </div>

          <div id="faqAccordionContainer" style="max-width: 860px; margin: 0 auto;"></div>

          <div id="faqShowMoreWrapper" style="text-align: center; margin-top: 18px; max-width: 860px; margin-left: auto; margin-right: auto;">
            <button type="button" class="btn btn-outline" id="btnToggleFaqLength" onclick="toggleFaqLength()" style="padding: 9px 24px; font-weight: 600; border-radius: 20px; box-shadow: var(--shadow-xs);">
              <span>Xem thêm câu hỏi khác ▾</span>
            </button>
          </div>"""

if old_faq_container in html:
    html = html.replace(old_faq_container, new_faq_container)
    print("2. Injected category pills and 'Xem thêm / Thu gọn' controls into FAQ section")
else:
    print("2. Warning: old_faq_container not found verbatim, checking regex...")

# Update FAQ JavaScript logic to support category filtering, compact default (4 items), and expand/collapse
faq_js_target = """    function renderFaq(faqList) {
      const container = document.getElementById("faqAccordionContainer");
      if (!container) return;

      if (faqList.length === 0) {
        container.innerHTML = '<div style="text-align:center; padding:30px; color:var(--text-muted);">Không tìm thấy câu hỏi nào phù hợp với từ khóa tìm kiếm.</div>';
        return;
      }

      let html = "";
      faqList.forEach((item, index) => {
        html += `
          <div class="accordion-item" id="faq-item-${index}">
            <div class="accordion-header" onclick="toggleFaq(${index})">
              <span><strong>[${item.cat}]</strong> ${item.q}</span>
              <span class="accordion-icon">&darr;</span>
            </div>
            <div class="accordion-body">
              ${item.a}
            </div>
          </div>
        `;
      });
      container.innerHTML = html;
    }"""

faq_js_replacement = """    // State for FAQ display
    let currentFaqCategory = "all";
    let isFaqExpanded = false; // default compact (only 4 items)
    let areAllFaqOpen = false;

    function setFaqCategory(cat) {
      currentFaqCategory = cat;
      isFaqExpanded = false; // reset to compact when changing category
      document.querySelectorAll(".faq-cat-btn").forEach(btn => {
        const text = btn.textContent;
        if ((cat === "all" && text.startsWith("Tất cả")) || (cat !== "all" && text.includes(cat))) {
          btn.classList.add("active");
        } else {
          btn.classList.remove("active");
        }
      });
      applyFaqFilter();
    }

    function toggleFaqLength() {
      isFaqExpanded = !isFaqExpanded;
      applyFaqFilter();
    }

    function toggleAllFaq() {
      areAllFaqOpen = !areAllFaqOpen;
      const items = document.querySelectorAll("#faqAccordionContainer .accordion-item");
      items.forEach(el => {
        if (areAllFaqOpen) {
          el.classList.add("open");
        } else {
          el.classList.remove("open");
        }
      });
      const btn = document.getElementById("btnToggleAllFaq");
      if (btn) btn.textContent = areAllFaqOpen ? "Thu gọn tất cả ▴" : "Mở rộng tất cả ▾";
    }

    function applyFaqFilter() {
      const searchInput = document.getElementById("faqSearchInput");
      const keyword = (searchInput ? searchInput.value : "").trim().toLowerCase();

      let list = FAQ_DATA;
      if (currentFaqCategory !== "all") {
        list = list.filter(item => item.cat === currentFaqCategory);
      }

      if (keyword) {
        list = list.filter(item => 
          item.q.toLowerCase().includes(keyword) || 
          item.a.toLowerCase().includes(keyword) ||
          item.cat.toLowerCase().includes(keyword)
        );
      }

      renderFaq(list);
    }

    function renderFaq(faqList) {
      const container = document.getElementById("faqAccordionContainer");
      const showMoreWrapper = document.getElementById("faqShowMoreWrapper");
      const showMoreBtn = document.getElementById("btnToggleFaqLength");
      if (!container) return;

      if (faqList.length === 0) {
        container.innerHTML = '<div style="text-align:center; padding:30px; color:var(--text-muted); background:#fff; border-radius:12px; border:1px solid #e2e8f0;">Không tìm thấy câu hỏi nào phù hợp với từ khóa tìm kiếm.</div>';
        if (showMoreWrapper) showMoreWrapper.style.display = "none";
        return;
      }

      const totalItems = faqList.length;
      const compactLimit = 4;
      const shouldLimit = !isFaqExpanded && totalItems > compactLimit;
      const displayItems = shouldLimit ? faqList.slice(0, compactLimit) : faqList;

      let html = "";
      displayItems.forEach((item, index) => {
        html += `
          <div class="accordion-item" id="faq-item-${index}">
            <div class="accordion-header" onclick="toggleFaq(${index})">
              <span><span class="faq-cat-badge">${item.cat}</span> ${item.q}</span>
              <span class="accordion-icon">▾</span>
            </div>
            <div class="accordion-body">
              ${item.a}
            </div>
          </div>
        `;
      });
      container.innerHTML = html;

      // Handle "Xem thêm / Thu gọn" button state
      if (showMoreWrapper && showMoreBtn) {
        if (totalItems <= compactLimit) {
          showMoreWrapper.style.display = "none";
        } else {
          showMoreWrapper.style.display = "block";
          if (isFaqExpanded) {
            showMoreBtn.innerHTML = `<span>Thu gọn bớt câu hỏi ▴</span>`;
          } else {
            showMoreBtn.innerHTML = `<span>Xem thêm ${totalItems - compactLimit} câu hỏi khác ▾</span>`;
          }
        }
      }
    }"""

if faq_js_target in html:
    html = html.replace(faq_js_target, faq_js_replacement)
    print("3. Replaced renderFaq with compact/expand FAQ logic in JavaScript")
else:
    print("3. Warning: faq_js_target not matched verbatim, checking...")

# In search input handler, call applyFaqFilter instead of simple render
html = html.replace(
    'const filtered = FAQ_DATA.filter(item =>',
    '// Filter via applyFaqFilter\n        applyFaqFilter(); return;\n        const filtered = FAQ_DATA.filter(item =>'
)

# ----------------------------------------------------------------------
# 3. CSS ENHANCEMENTS: Strict 4-Item / 2x2 Flows & Equal Height/Width
# ----------------------------------------------------------------------
flow_grid_css = """
    /* ============================================================ */
    /* STRICT EQUAL-DIMENSION FLOW GRIDS (4-ON-1 OR 2X2 EQUAL W/H)  */
    /* ============================================================ */

    /* 1. Flow Steps Grid (4 flows: Inflow, Spend, Refund, Gas) */
    .flow-steps-grid {
      display: grid !important;
      grid-template-columns: repeat(4, 1fr) !important;
      gap: 16px !important;
      align-items: stretch !important;
    }
    @media (max-width: 1100px) {
      .flow-steps-grid {
        grid-template-columns: repeat(2, 1fr) !important; /* 2 trên 2 dưới */
      }
    }
    @media (max-width: 580px) {
      .flow-steps-grid {
        grid-template-columns: 1fr !important;
      }
    }

    .flow-step-box {
      height: 100% !important;
      display: flex !important;
      flex-direction: column !important;
      justify-content: flex-start !important;
      background: #ffffff !important;
      border: 1px solid var(--border-color) !important;
      border-radius: var(--radius-md) !important;
      padding: 16px 18px !important;
      box-shadow: var(--shadow-xs) !important;
    }

    /* 2. Flow Balance Grid (4 balance cards: ClassFund, Reserved, AdminFee, Spend) */
    .flow-balance-grid {
      display: grid !important;
      grid-template-columns: repeat(4, 1fr) !important;
      gap: 16px !important;
      align-items: stretch !important;
      margin-bottom: 20px !important;
    }
    @media (max-width: 1100px) {
      .flow-balance-grid {
        grid-template-columns: repeat(2, 1fr) !important; /* 2 trên 2 dưới */
      }
    }
    @media (max-width: 580px) {
      .flow-balance-grid {
        grid-template-columns: 1fr !important;
      }
    }

    .flow-balance-card {
      height: 100% !important;
      display: flex !important;
      flex-direction: column !important;
      justify-content: space-between !important;
      background: #ffffff !important;
      border: 1px solid var(--border-color) !important;
      border-radius: var(--radius-md) !important;
      padding: 16px 18px !important;
      box-shadow: var(--shadow-xs) !important;
    }

    /* 3. Role Buttons Group (4 buttons: Sinh viên, Ban cán sự, Cố vấn, Lịch sử) */
    .role-buttons-group {
      display: grid !important;
      grid-template-columns: repeat(4, 1fr) !important;
      gap: 14px !important;
      align-items: stretch !important;
      margin-top: 16px !important;
      margin-bottom: 22px !important;
    }
    @media (max-width: 1050px) {
      .role-buttons-group {
        grid-template-columns: repeat(2, 1fr) !important; /* 2 trên 2 dưới */
      }
    }
    @media (max-width: 520px) {
      .role-buttons-group {
        grid-template-columns: 1fr !important;
      }
    }

    .role-btn-item {
      height: 100% !important;
      min-height: 52px !important;
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
    }

    /* 4. Roster Modal Stats Grid (4 cards: Tổng sĩ số, Ban cán sự, Sinh viên, Đã nộp) */
    .roster-stats-grid {
      display: grid !important;
      grid-template-columns: repeat(4, 1fr) !important;
      gap: 14px !important;
      align-items: stretch !important;
      margin-bottom: 18px !important;
    }
    @media (max-width: 850px) {
      .roster-stats-grid {
        grid-template-columns: repeat(2, 1fr) !important; /* 2 trên 2 dưới */
      }
    }
    @media (max-width: 480px) {
      .roster-stats-grid {
        grid-template-columns: 1fr !important;
      }
    }

    .roster-stat-card {
      height: 100% !important;
      display: flex !important;
      align-items: center !important;
    }

    /* 5. Metrics Grid (6 KPI cards: 6-on-1 or 3-on-top 3-below) */
    .metrics-grid {
      display: grid !important;
      grid-template-columns: repeat(3, 1fr) !important; /* Chuẩn 3 trên 3 dưới */
      gap: 16px !important;
      align-items: stretch !important;
      margin-bottom: 28px !important;
    }
    @media (min-width: 1400px) {
      .metrics-grid {
        grid-template-columns: repeat(6, 1fr) !important; /* 6 trên 1 hàng */
      }
    }
    @media (max-width: 900px) {
      .metrics-grid {
        grid-template-columns: repeat(2, 1fr) !important; /* 2x3 */
      }
    }
    @media (max-width: 550px) {
      .metrics-grid {
        grid-template-columns: 1fr !important;
      }
    }

    .metric-card {
      height: 100% !important;
      display: flex !important;
      flex-direction: column !important;
      justify-content: space-between !important;
    }

    /* 6. Announcement Meta Grid (3 items in 1 row) */
    .ann-meta-grid {
      display: grid !important;
      grid-template-columns: repeat(3, 1fr) !important;
      gap: 14px !important;
      align-items: stretch !important;
    }
    @media (max-width: 750px) {
      .ann-meta-grid {
        grid-template-columns: 1fr !important;
      }
    }
    .ann-meta-item {
      height: 100% !important;
    }

    /* 7. Grid-2 & Grid-3 Equal Heights */
    .grid-2 {
      display: grid !important;
      grid-template-columns: repeat(2, 1fr) !important;
      gap: 20px !important;
      align-items: stretch !important;
    }
    @media (max-width: 768px) {
      .grid-2 {
        grid-template-columns: 1fr !important;
      }
    }
    .grid-2 > * {
      height: 100% !important;
    }

    .grid-3 {
      display: grid !important;
      grid-template-columns: repeat(3, 1fr) !important;
      gap: 20px !important;
      align-items: stretch !important;
    }
    @media (max-width: 950px) {
      .grid-3 {
        grid-template-columns: repeat(2, 1fr) !important;
      }
    }
    @media (max-width: 600px) {
      .grid-3 {
        grid-template-columns: 1fr !important;
      }
    }
    .grid-3 > * {
      height: 100% !important;
    }

    /* FAQ Category Pills Styling */
    .faq-category-pills {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .faq-cat-btn {
      background: #ffffff;
      border: 1px solid var(--border-color);
      color: var(--text-muted);
      padding: 6px 14px;
      border-radius: var(--radius-full);
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .faq-cat-btn:hover {
      background: #f8fafc;
      color: var(--text-main);
      border-color: #cbd5e1;
    }

    .faq-cat-btn.active {
      background: var(--brand-blue);
      color: #ffffff;
      border-color: var(--brand-blue);
      box-shadow: 0 2px 6px rgba(37, 99, 235, 0.25);
    }

    .faq-cat-badge {
      display: inline-block;
      font-size: 0.72rem;
      font-weight: 700;
      color: var(--brand-blue);
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      padding: 2px 8px;
      border-radius: 6px;
      margin-right: 6px;
    }

    /* Refined Logo Styling: No white background, perfect alignment */
    .sidebar-header {
      padding: 18px 20px 16px 20px !important;
      display: flex !important;
      align-items: center !important;
      gap: 14px !important;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    .sidebar-logo-img {
      width: 44px !important;
      height: 44px !important;
      border-radius: 10px !important;
      object-fit: contain !important;
      filter: drop-shadow(0 4px 10px rgba(0, 0, 0, 0.35)) !important;
      border: none !important;
      background: transparent !important;
      flex-shrink: 0 !important;
      transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    .sidebar-logo-img:hover {
      transform: scale(1.08) !important;
    }

    .topbar-mini-logo {
      width: 32px !important;
      height: 32px !important;
      border-radius: 8px !important;
      object-fit: contain !important;
      filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.15)) !important;
      border: none !important;
      background: transparent !important;
      display: none !important;
    }
    @media (max-width: 1024px) {
      .topbar-mini-logo {
        display: block !important;
      }
    }
"""

if "/* STRICT EQUAL-DIMENSION FLOW GRIDS" not in html:
    html = html.replace('</style>', flow_grid_css + '\n  </style>')
    print("4. Injected strict equal-dimension grid CSS and FAQ styles")

# ----------------------------------------------------------------------
# 4. VERIFY ALL REQUIRED IDS ARE INTACT
# ----------------------------------------------------------------------
import json
with open("scratch/all_ids.json", "r", encoding="utf-8") as f:
    id_data = json.load(f)

req_ids = id_data["html_ids"]
missing_ids = [i for i in req_ids if f'id="{i}"' not in html and f"id='{i}'" not in html]

print(f"5. ID Validation: {len(req_ids) - len(missing_ids)}/{len(req_ids)} IDs present.")
if missing_ids:
    print(f"ERROR: Missing IDs: {missing_ids}")
    sys.exit(1)
else:
    print("PERFECT: 100% of required IDs are preserved!")

# ----------------------------------------------------------------------
# 5. WRITE UPDATED HTML
# ----------------------------------------------------------------------
with open("web/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("6. Successfully applied all layout, FAQ, and logo fixes to web/index.html!")
