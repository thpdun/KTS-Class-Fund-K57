import re

# 1. Update web/index.html
with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

new_footer_html = '''<!-- FOOTER - DẢI THANH NGANG 4 CỘT PHONG CÁCH HIỆN ĐẠI (FAIRTICKET-STYLE) -->
    <footer class="site-footer">
      <div class="container footer-strip-container">
        <!-- Cột 1: Logo, Tên dự án & Giới thiệu ngắn -->
        <div class="footer-col-brand">
          <div class="footer-brand-header">
            <div class="footer-brand-icon">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
                <path d="M2 17l10 5 10-5"></path>
                <path d="M2 12l10 5 10-5"></path>
              </svg>
            </div>
            <span class="footer-brand-title">KTS Class Fund</span>
          </div>
          <p class="footer-brand-desc">
            Nền tảng quản lý quỹ lớp ứng dụng blockchain: phân bổ tự động 99/1, biểu quyết chi tiêu &ge; 51%, minh bạch sổ quỹ on-chain trên Ethereum Sepolia.
          </p>
        </div>

        <!-- Cột 2: Khám phá -->
        <div class="footer-col">
          <h4 class="footer-col-title">Khám phá</h4>
          <ul class="footer-col-list">
            <li><a href="#hero" class="footer-link">Tất cả dịch vụ quỹ</a></li>
            <li><a href="#dapp-workspace" class="footer-link" onclick="if(typeof openActionModal==='function'){openActionModal('spend');}return false;">Đề xuất chi tiêu</a></li>
            <li><a href="#ledger" class="footer-link" onclick="if(typeof navigateTo==='function'){navigateTo('ledger');}return false;">Sổ quỹ on-chain</a></li>
            <li><a href="#workflow" class="footer-link">Quy trình 4 luồng tiền</a></li>
          </ul>
        </div>

        <!-- Cột 3: Tài khoản -->
        <div class="footer-col">
          <h4 class="footer-col-title">Tài khoản</h4>
          <ul class="footer-col-list">
            <li><a href="#dapp-workspace" class="footer-link" onclick="if(typeof openActionModal==='function'){openActionModal('deposit');}return false;">Đóng góp quỹ của tôi</a></li>
            <li><a href="#dapp-workspace" class="footer-link" onclick="if(typeof openActionModal==='function'){openActionModal('refund');}return false;">Yêu cầu hoàn tiền</a></li>
            <li><a href="#governance" class="footer-link">Phân quyền Ban cán sự</a></li>
            <li><a href="https://metamask.io/download/" target="_blank" rel="noopener noreferrer" class="footer-link">Tải ví MetaMask ↗</a></li>
          </ul>
        </div>

        <!-- Cột 4: Minh bạch -->
        <div class="footer-col">
          <h4 class="footer-col-title">Minh bạch</h4>
          <ul class="footer-col-list">
            <li><a href="https://sepolia.etherscan.io" target="_blank" rel="noopener noreferrer" class="footer-link">Hợp đồng trên Etherscan ↗</a></li>
            <li class="footer-text-item">
              <span class="footer-live-dot"></span>
              Mạng: Ethereum Sepolia (testnet)
            </li>
            <li><a href="https://sepoliafaucet.com" target="_blank" rel="noopener noreferrer" class="footer-link">Nhận SepoliaETH miễn phí ↗</a></li>
            <li class="footer-text-item" style="color: #64748b; font-size: 0.8rem; margin-top: 4px;">Dự án học phần ECO2432</li>
          </ul>
        </div>
      </div>

      <!-- Dải bản quyền dưới cùng -->
      <div class="container footer-strip-bottom">
        <div>&copy; 2026 KTS-Class-Fund (Lớp K57 Kinh Tế Số) — Dự án môn học ECO2432.</div>
        <div class="footer-bottom-privacy">Thiết kế minh bạch • An toàn dữ liệu • Tôn trọng quyền riêng tư</div>
      </div>
    </footer>'''

footer_pattern = re.compile(r'<!-- FOOTER.*?<footer class="site-footer">.*?</footer>', re.DOTALL)
if footer_pattern.search(html):
    html = footer_pattern.sub(new_footer_html, html)
    print("Replaced footer with FairTicket-style footer in web/index.html!")
else:
    alt_pattern = re.compile(r'<footer class="site-footer">.*?</footer>', re.DOTALL)
    if alt_pattern.search(html):
        html = alt_pattern.sub(new_footer_html, html)
        print("Replaced footer with FairTicket-style footer via alt pattern!")
    else:
        print("ERROR: footer tag not found in web/index.html")

with open('web/index.html', 'w', encoding='utf-8') as f:
    f.write(html)


# 2. Update web/styles.css
with open('web/styles.css', 'r', encoding='utf-8') as f:
    css = f.read()

new_footer_css = '''/* ==========================================================================
   SITE FOOTER - DẢI THANH NGANG 4 CỘT PHONG CÁCH HIỆN ĐẠI (FAIRTICKET-STYLE)
   ========================================================================== */
footer.site-footer,
.site-footer {
  width: 100% !important;
  max-width: 100vw !important;
  background: #090d16 !important; /* Đen huyền bí siêu sang như mẫu FairTicket */
  color: #94a3b8 !important;
  padding: 56px 0 32px 0 !important;
  border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
  margin-top: 60px !important;
  position: relative !important;
  z-index: 10 !important;
  clear: both !important;
  box-sizing: border-box !important;
  display: block !important;
}

@media (max-width: 768px) {
  footer.site-footer,
  .site-footer {
    padding: 40px 0 calc(80px + env(safe-area-inset-bottom, 0px)) 0 !important;
  }
}

.site-footer .footer-strip-container {
  width: 100% !important;
  max-width: 1280px !important;
  margin: 0 auto !important;
  padding: 0 32px !important;
  box-sizing: border-box !important;
  display: grid !important;
  grid-template-columns: 2.2fr 1.2fr 1.2fr 1.4fr !important;
  gap: 48px !important;
}

@media (max-width: 1024px) {
  .site-footer .footer-strip-container {
    grid-template-columns: 1fr 1fr !important;
    gap: 36px !important;
  }
}

@media (max-width: 640px) {
  .site-footer .footer-strip-container {
    grid-template-columns: 1fr !important;
    gap: 28px !important;
  }
}

.footer-col-brand {
  display: flex !important;
  flex-direction: column !important;
  gap: 12px !important;
}

.footer-brand-header {
  display: flex !important;
  align-items: center !important;
  gap: 12px !important;
}

.footer-brand-icon {
  width: 36px !important;
  height: 36px !important;
  border-radius: 10px !important;
  background: linear-gradient(135deg, #0B6B57 0%, #10b981 100%) !important;
  color: #ffffff !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3) !important;
  flex-shrink: 0 !important;
}

.footer-brand-title {
  font-size: 1.25rem !important;
  font-weight: 700 !important;
  color: #ffffff !important;
  letter-spacing: -0.2px !important;
}

.footer-brand-desc {
  font-size: 0.88rem !important;
  line-height: 1.65 !important;
  color: #94a3b8 !important;
  margin: 0 !important;
  max-width: 380px !important;
}

.footer-col {
  display: flex !important;
  flex-direction: column !important;
}

.footer-col-title {
  font-size: 0.96rem !important;
  font-weight: 700 !important;
  color: #ffffff !important;
  margin: 0 0 16px 0 !important;
  letter-spacing: 0.2px !important;
}

.footer-col-list {
  list-style: none !important;
  padding: 0 !important;
  margin: 0 !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 11px !important;
}

.footer-col-list li a.footer-link,
.site-footer .footer-link {
  font-size: 0.88rem !important;
  color: #94a3b8 !important;
  text-decoration: none !important;
  transition: color 0.18s ease, transform 0.18s ease !important;
  display: inline-block !important;
}

.footer-col-list li a.footer-link:hover,
.site-footer .footer-link:hover {
  color: #ffffff !important;
  text-decoration: none !important;
  transform: translateX(2px) !important;
}

.footer-text-item {
  font-size: 0.88rem !important;
  color: #94a3b8 !important;
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
}

.footer-live-dot {
  width: 7px !important;
  height: 7px !important;
  border-radius: 50% !important;
  background: #10b981 !important;
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.8) !important;
  display: inline-block !important;
  flex-shrink: 0 !important;
}

.footer-strip-bottom {
  width: 100% !important;
  max-width: 1280px !important;
  margin: 36px auto 0 auto !important;
  padding: 24px 32px 0 32px !important;
  border-top: 1px solid rgba(255, 255, 255, 0.06) !important;
  display: flex !important;
  justify-content: space-between !important;
  align-items: center !important;
  font-size: 0.84rem !important;
  color: #64748b !important;
  flex-wrap: wrap !important;
  gap: 12px !important;
}

@media (max-width: 640px) {
  .footer-strip-bottom {
    flex-direction: column !important;
    align-items: flex-start !important;
    gap: 8px !important;
  }
}

/* Dark mode overrides for footer & workspace modal */
body.dark-theme footer.site-footer,
body.dark-theme .site-footer {
  background: #060910 !important;
  border-top-color: rgba(255, 255, 255, 0.08) !important;
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

print("SUCCESS: FairTicket-style footer applied!")

