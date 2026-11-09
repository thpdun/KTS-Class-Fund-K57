import re

# 1. Update web/index.html
with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

old_footer_pattern = re.compile(r'<!-- FOOTER -->\s*<footer class="site-footer">.*?</footer>', re.DOTALL)

new_footer_html = '''<!-- FOOTER - DẢI THANH NGANG TRỌN VẸN (SLIM HORIZONTAL FOOTER BAR) -->
    <footer class="site-footer">
      <div class="container footer-horizontal-bar">
        <!-- Brand & Thông tin lớp bên trái -->
        <div class="footer-brand-horizontal">
          <strong class="footer-brand-title">KTS CLASS FUND</strong>
          <span class="footer-sep-dot">•</span>
          <span class="footer-brand-sub">Lớp K57 Kinh Tế Số (ECO2432)</span>
          <span class="footer-sep-dot">•</span>
          <span class="footer-brand-copy">&copy; 2026</span>
        </div>

        <!-- Dải liên kết chạy ngang ở giữa (Horizontal Links) -->
        <nav class="footer-nav-horizontal" aria-label="Liên kết chân trang">
          <a href="#hero" class="footer-hlink">Tổng quan</a>
          <span class="footer-sep-dot">•</span>
          <a href="#workflow" class="footer-hlink">Quy trình</a>
          <span class="footer-sep-dot">•</span>
          <a href="#governance" class="footer-hlink">Biểu quyết</a>
          <span class="footer-sep-dot">•</span>
          <a href="#economics" class="footer-hlink">Phân bổ 99/1</a>
          <span class="footer-sep-dot">•</span>
          <a href="https://sepolia.etherscan.io" target="_blank" rel="noopener noreferrer" class="footer-hlink">Sepolia Etherscan ↗</a>
          <span class="footer-sep-dot">•</span>
          <a href="https://metamask.io/download/" target="_blank" rel="noopener noreferrer" class="footer-hlink">MetaMask ↗</a>
          <span class="footer-sep-dot">•</span>
          <a href="https://sepoliafaucet.com" target="_blank" rel="noopener noreferrer" class="footer-hlink">Faucet ETH ↗</a>
        </nav>

        <!-- Trạng thái mạng Sepolia & An toàn on-chain bên phải -->
        <div class="footer-meta-horizontal">
          <span class="footer-net-chip">
            <span class="footer-green-dot"></span>
            Ethereum Sepolia • Minh bạch on-chain
          </span>
        </div>
      </div>
    </footer>'''

if old_footer_pattern.search(html):
    html = old_footer_pattern.sub(new_footer_html, html)
    print("Replaced footer in web/index.html via regex!")
else:
    # Try alternate match
    alt_pattern = re.compile(r'<footer class="site-footer">.*?</footer>', re.DOTALL)
    if alt_pattern.search(html):
        html = alt_pattern.sub(new_footer_html, html)
        print("Replaced footer in web/index.html via alt regex!")
    else:
        print("ERROR: Could not find footer in web/index.html")

with open('web/index.html', 'w', encoding='utf-8') as f:
    f.write(html)


# 2. Update web/styles.css
with open('web/styles.css', 'r', encoding='utf-8') as f:
    css = f.read()

target_marker = '/* ==========================================================================\n   SITE FOOTER - DẢI NGANG TRỌN VẸN (FULL-WIDTH HORIZONTAL STRIP)'
if target_marker not in css:
    target_marker = 'SITE FOOTER - DẢI NGANG TRỌN VẸN'

new_footer_css = '''/* ==========================================================================
   SITE FOOTER - DẢI THANH NGANG TRỌN VẸN (SLIM HORIZONTAL FOOTER BAR)
   ========================================================================== */
footer.site-footer,
.site-footer {
  width: 100% !important;
  max-width: 100vw !important;
  background: #05352B !important; /* Xanh đậm thương hiệu chuẩn mực */
  color: #94a3b8 !important;
  padding: 16px 0 calc(80px + env(safe-area-inset-bottom, 0px)) 0 !important;
  border-top: 1px solid rgba(255, 255, 255, 0.1) !important;
  margin-top: 48px !important;
  position: relative !important;
  z-index: 10 !important;
  clear: both !important;
  box-sizing: border-box !important;
  display: block !important;
}

@media (min-width: 769px) {
  footer.site-footer,
  .site-footer {
    padding: 18px 0 !important; /* Dải thanh ngang thanh thoát trên desktop */
  }
}

.site-footer .container,
.site-footer .footer-horizontal-bar {
  width: 100% !important;
  max-width: 1300px !important;
  margin: 0 auto !important;
  padding: 0 24px !important;
  box-sizing: border-box !important;
  display: flex !important;
  flex-direction: row !important;
  align-items: center !important;
  justify-content: space-between !important;
  flex-wrap: wrap !important;
  gap: 14px 24px !important;
}

.footer-brand-horizontal {
  display: inline-flex !important;
  align-items: center !important;
  gap: 8px !important;
  font-size: 0.88rem !important;
  color: #cbd5e1 !important;
  flex-shrink: 0 !important;
}

.footer-brand-title {
  color: #ffffff !important;
  font-weight: 700 !important;
  letter-spacing: 0.5px !important;
  font-size: 0.92rem !important;
}

.footer-brand-sub {
  color: #a7f3d0 !important;
}

.footer-brand-copy {
  color: #94a3b8 !important;
}

.footer-nav-horizontal {
  display: inline-flex !important;
  flex-direction: row !important;
  align-items: center !important;
  flex-wrap: wrap !important;
  gap: 8px 12px !important;
  font-size: 0.84rem !important;
}

.footer-hlink {
  color: #cbd5e1 !important;
  text-decoration: none !important;
  transition: color 0.15s ease !important;
  white-space: nowrap !important;
}

.footer-hlink:hover {
  color: #F2B84B !important; /* Vàng nhấn thương hiệu */
  text-decoration: underline !important;
}

.footer-sep-dot {
  color: rgba(255, 255, 255, 0.28) !important;
  font-size: 0.75rem !important;
  user-select: none !important;
}

.footer-meta-horizontal {
  display: inline-flex !important;
  align-items: center !important;
  flex-shrink: 0 !important;
}

.footer-net-chip {
  display: inline-flex !important;
  align-items: center !important;
  gap: 7px !important;
  padding: 5px 12px !important;
  border-radius: 999px !important;
  background: rgba(255, 255, 255, 0.08) !important;
  border: 1px solid rgba(255, 255, 255, 0.14) !important;
  font-size: 0.8rem !important;
  color: #e2e8f0 !important;
  white-space: nowrap !important;
}

.footer-green-dot {
  width: 7px !important;
  height: 7px !important;
  border-radius: 50% !important;
  background: #10b981 !important;
  box-shadow: 0 0 6px #10b981 !important;
  display: inline-block !important;
}

@media (max-width: 900px) {
  .site-footer .container,
  .site-footer .footer-horizontal-bar {
    justify-content: center !important;
    text-align: center !important;
  }
  .footer-brand-horizontal,
  .footer-nav-horizontal,
  .footer-meta-horizontal {
    justify-content: center !important;
  }
}

/* Dark mode overrides for footer & workspace modal */
body.dark-theme footer.site-footer,
body.dark-theme .site-footer {
  background: #061e18 !important;
  border-color: rgba(255, 255, 255, 0.08) !important;
}

body.dark-theme #dapp-workspace .workspace-modal-box {
  background: #1e293b !important;
  color: #f8fafc !important;
  border-color: #334155 !important;
}
body.dark-theme #dapp-workspace .workspace-modal-header {
  background: #0f172a !important;
  border-color: #334155 !important;
}
body.dark-theme #dapp-workspace .workspace-modal-title {
  color: #f8fafc !important;
}
'''

idx = css.find('/* ==========================================================================\n   SITE FOOTER')
if idx != -1:
    css = css[:idx] + new_footer_css
    print("Replaced footer in web/styles.css!")
else:
    print("Warning: marker not found, appending to web/styles.css")
    css += "\n" + new_footer_css

with open('web/styles.css', 'w', encoding='utf-8') as f:
    f.write(css)

print("SUCCESS: Horizontal footer bar applied!")

