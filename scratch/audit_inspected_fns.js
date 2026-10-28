
// ==================== loadClassRoster ====================
async function loadClassRoster(signerAddr = null) {
      const caller = signerAddr || userAddress || "";
      const isBcs = isBcsMember || (myStudentProfile && myStudentProfile.role === "bcs");
      try {
        const res = await fetch(`http://localhost:8000/api/roster?address=${encodeURIComponent(caller)}&isBcs=${isBcs ? '1' : '0'}&isAdvisor=${isAdvisor ? '1' : '0'}`);
        if (res.ok) {
          const data = await res.json();
          if (data && data.success && Array.isArray(data.roster) && data.roster.length > 0) {
            classRoster = data.roster;
            try { localStorage.setItem("kts_class_roster", JSON.stringify(classRoster)); } catch(e){}
          }
        }
      } catch (err) {
        console.warn("Chưa thể tải danh bạ từ backend, sử dụng danh bạ cục bộ:", err);
      }

      // Cập nhật số lượng trên cả 2 vị trí badge (modal và topbar)
      const countBadge = document.getElementById("rosterCountBadge");
      if (countBadge) countBadge.textContent = classRoster.length;
      const sbBadge = document.getElementById("sidebarRosterBadge");
      if (sbBadge) sbBadge.textContent = classRoster.length;

      renderRosterTable();
      renderAnnouncementUI(); // Tự động cập nhật sĩ số lớp và tiến độ nộp quỹ theo danh bạ mới nhất

      if (userAddress) {
        const s = lookupStudent(userAddress);
        if (s) {
          myStudentProfile = s;
          if (s.role === "bcs") isBcsMember = true;
          updateRoleDisplay(isAdvisor ? "advisor" : (s.role === "bcs" ? "bcs" : "student"), s);
        }
      }
      return classRoster;
    }

// ==================== renderRosterTable ====================
async function renderRosterTable() {
      const tbody = document.getElementById("rosterTableBody");
      if (!tbody) return;
      if (!classRoster || classRoster.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:32px 16px; color:#64748b;">Đang tải danh bạ sinh viên K57 hoặc chưa có dữ liệu...</td></tr>`;
        return;
      }

      // 1. Đồng bộ số liệu on-chain cho từng sinh viên (kèm bộ nhớ đệm cache hợp lệ)
      let paidCount = 0;
      for (const s of classRoster) {
        if (!s.wallet || !ethers.isAddress(s.wallet)) {
          // Chưa liên kết ví hoặc ví không hợp lệ -> bỏ qua on-chain call
          continue;
        }
        const key = s.wallet.toLowerCase().trim();
        if (!rosterContribCache.has(key)) {
          if (contract) {
            try {
              const contrib = await contract.studentContributions(s.wallet);
              const isPaid = contrib && contrib > 0n;
              rosterContribCache.set(key, {
                status: isPaid ? "paid" : "unpaid",
                isPaid: isPaid,
                amountWei: contrib || 0n
              });
            } catch (e) {
              console.warn("Lỗi truy vấn studentContributions on-chain cho ví:", s.wallet, e);
              // LỖI RPC HOẶC TIMEOUT: TUYỆT ĐỐI KHÔNG LƯU VÀO CACHE KẾT QUẢ "CHƯA NỘP"!
            }
          } else {
            // CONTRACT CHƯA SẴN SÀNG: KHÔNG LƯU KẾT QUẢ GIẢ VÀO CACHE!
          }
        }
        const entry = rosterContribCache.get(key);
        if (entry && entry.isPaid) {
          paidCount++;
        }
      }

      // 2. Cập nhật 4 thẻ thống kê ở đầu danh bạ
      const totalCount = classRoster.length;
      const bcsCount = classRoster.filter(s => s.role === "bcs").length;
      const studentCount = classRoster.filter(s => s.role !== "bcs").length;

      const elTotal = document.getElementById("rosterStatTotal");
      const elBcs = document.getElementById("rosterStatBcs");
      const elStudents = document.getElementById("rosterStatStudents");
      const elPaid = document.getElementById("rosterStatPaid");

      if (elTotal) elTotal.textContent = `${totalCount} bạn`;
      if (elBcs) elBcs.textContent = `${bcsCount} thành viên`;
      if (elStudents) elStudents.textContent = `${studentCount} bạn`;
      if (elPaid) elPaid.textContent = `${paidCount}/${totalCount} (${Math.round((paidCount / (totalCount || 1)) * 100)}%)`;

      // 3. Lọc danh sách theo từ khóa tìm kiếm và nút filter
      const searchInput = document.getElementById("rosterSearchInput");
      const keyword = (searchInput ? searchInput.value : "").toLowerCase().trim();

      const filtered = classRoster.filter(s => {
        // Xác định trạng thái 4 nhánh
        let studentStatus = "unverified";
        if (!s.wallet || !ethers.isAddress(s.wallet)) {
          studentStatus = "unlinked";
        } else {
          const key = s.wallet.toLowerCase().trim();
          const cached = rosterContribCache.get(key);
          if (cached) {
            studentStatus = cached.status;
          } else if (!contract) {
            studentStatus = "unverified";
          }
        }

        if (currentRosterFilter === "bcs" && s.role !== "bcs") return false;
        if (currentRosterFilter === "student" && s.role === "bcs") return false;
        if (currentRosterFilter === "paid" && studentStatus !== "paid") return false;
        if (currentRosterFilter === "unpaid" && studentStatus !== "unpaid") return false;

        // Lọc theo từ khóa (Tên, MSSV, Địa chỉ ví)
        if (keyword) {
          const matchName = (s.name || "").toLowerCase().includes(keyword);
          const matchMssv = (s.mssv || "").toLowerCase().includes(keyword);
          const matchWallet = (s.wallet || "").toLowerCase().includes(keyword);
          if (!matchName && !matchMssv && !matchWallet) return false;
        }

        return true;
      });

      // 4. Cập nhật tóm tắt ở footer
      const footerSum = document.getElementById("rosterFooterSummary");
      if (footerSum) {
        footerSum.innerHTML = `Đang hiển thị <strong>${filtered.length}</strong> / <strong>${totalCount}</strong> sinh viên K57`;
      }

      // 5. Render bảng sinh viên
      if (filtered.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="7" style="text-align: center; padding: 36px 16px; color: #64748b;">
              <div style="font-size: 2rem; margin-bottom: 8px;">🔍</div>
              <div style="font-weight: 600; color: #0f172a; margin-bottom: 4px;">Không tìm thấy sinh viên phù hợp</div>
              <div style="font-size: 0.8rem;">Thử nhập lại từ khóa khác hoặc chuyển bộ lọc sang "Tất cả".</div>
            </td>
          </tr>
        `;
        return;
      }

      let html = "";
      for (let i = 0; i < filtered.length; i++) {
        const s = filtered[i];
        const isMe = userAddress && s.wallet && userAddress.toLowerCase() === s.wallet.toLowerCase();

        // 4 Trạng thái đóng góp chuẩn mực:
        // 1. "paid": Đã nộp (truy vấn thành công on-chain và số đóng góp > 0)
        // 2. "unpaid": Chưa nộp (truy vấn thành công on-chain và số đóng góp == 0)
        // 3. "unlinked": Chưa liên kết ví (ví trống hoặc sai định dạng Ethereum)
        // 4. "unverified": Chưa xác minh (chưa có hợp đồng, lỗi RPC, timeout hoặc kết quả chưa đáng tin cậy)
        let studentStatus = "unverified";
        let paidAmount = null;

        if (!s.wallet || !ethers.isAddress(s.wallet)) {
          studentStatus = "unlinked";
        } else {
          const key = s.wallet.toLowerCase().trim();
          const cached = rosterContribCache.get(key);
          if (cached) {
            studentStatus = cached.status;
            if (cached.amountWei && cached.amountWei > 0n) {
              paidAmount = formatEth(cached.amountWei);
            }
          } else if (!contract) {
            studentStatus = "unverified";
          }
        }

        let statusBadge = "";
        if (studentStatus === "paid") {
          statusBadge = `<span class="status-pill status-executed" style="font-size: 0.75rem; font-weight: 600; background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0;" title="Đã ghi nhận đóng góp trên Sepolia Smart Contract">✅ Đã nộp (${paidAmount || "0.0050"} ETH)</span>`;
        } else if (studentStatus === "unpaid") {
          statusBadge = `<span class="status-pill" style="font-size: 0.75rem; font-weight: 600; background: #fef2f2; color: #dc2626; border: 1px solid #fecaca;" title="Chưa có giao dịch nộp quỹ trên hợp đồng">⏳ Chưa nộp</span>`;
        } else if (studentStatus === "unlinked") {
          statusBadge = `<span class="status-pill" style="font-size: 0.75rem; font-weight: 600; background: #fffbeb; color: #b45309; border: 1px solid #fde68a;" title="Sinh viên chưa cập nhật hoặc địa chỉ ví không hợp lệ">⚠️ Chưa liên kết ví</span>`;
        } else {
          statusBadge = `<span class="status-pill" style="font-size: 0.75rem; font-weight: 600; background: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1;" title="Chưa kết nối hợp đồng thông minh hoặc đang tải dữ liệu">⚪ Chưa xác minh</span>`;
        }

        const roleBadge = (s.role === "bcs")
          ? `<span class="status-pill" style="font-size: 0.75rem; font-weight: 700; background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd;">⭐ ${s.roleTitle || 'Ban cán sự'}</span>`
          : `<span class="status-pill" style="font-size: 0.75rem; font-weight: 600; background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1;">🎓 ${s.roleTitle || 'Sinh viên'}</span>`;

        const canEditStudent = isAdvisor || isBcsMember || (myStudentProfile && myStudentProfile.role === "bcs");
        const actionBtn = canEditStudent
          ? `<button class="btn btn-sm btn-outline" onclick="editRosterStudent('${s.mssv}')" style="padding: 4px 10px; font-size: 0.75rem; border-radius: 6px; cursor: pointer; color: #0284c7; border: 1px solid #bae6fd; background: #f0f9ff; font-weight: 600;" title="Chỉnh sửa thông tin, vai trò hoặc địa chỉ ví của sinh viên này">✏️ Sửa</button>`
          : '<span style="color: #94a3b8; font-size: 0.75rem;">--</span>';

        const avatarGrad = getRosterAvatarGradient(s.mssv || s.name);
        const initials = getInitials(s.name);

        html += `
          <tr class="${isMe ? 'is-me' : ''}">
            <td style="text-align: center; font-weight: 700; color: #64748b; font-size: 0.8rem;">${i + 1}</td>
            <td>
              <div class="roster-student-info">
                <span class="roster-avatar" style="background: ${avatarGrad};">${initials}</span>
                <span class="roster-student-name">
                  ${escapeHtml(s.name)}
                  ${isMe ? '<span class="status-pill status-executed" style="font-size: 0.65rem; padding: 1px 6px; font-weight: 700; background: #22c55e; color: #fff; margin-left: 4px;">Tôi</span>' : ''}
                </span>
              </div>
            </td>
            <td>
              <span class="roster-mssv-badge">${escapeHtml(s.mssv)}</span>
            </td>
            <td>${roleBadge}</td>
            <td>
              <div class="roster-wallet-box">
                <span class="roster-wallet-addr" title="${s.wallet || 'Chưa liên kết ví'}">${s.wallet || '<em style="color:#94a3b8;">Chưa cập nhật ví</em>'}</span>
                ${s.wallet ? `<button class="roster-copy-btn" onclick="copyRosterWallet('${s.wallet}', this)" title="Sao chép toàn bộ địa chỉ ví">📋</button>` : ''}
                ${s.wallet ? `<a class="roster-explorer-link" href="https://sepolia.etherscan.io/address/${s.wallet}" target="_blank" rel="noopener noreferrer" title="Mở trên Sepolia Etherscan">↗</a>` : ''}
              </div>
            </td>
            <td>${statusBadge}</td>
            <td style="text-align: center;">${actionBtn}</td>
          </tr>
        `;
      }

      tbody.innerHTML = html;
    }

// ==================== openRosterModal ====================
function openRosterModal() {
      const isBcs = isBcsMember || (myStudentProfile && myStudentProfile.role === "bcs");
      const canManage = isAdvisor || isBcs;

      const modal = document.getElementById("rosterModal");
      const adminSec = document.getElementById("rosterAdminSection");
      const bcsNote = document.getElementById("rosterBcsViewNote");

      // Cả Cố vấn học tập và Ban cán sự đều có quyền thêm/sửa địa chỉ ví sinh viên
      if (adminSec) {
        adminSec.style.display = canManage ? "block" : "none";
      }
      if (bcsNote) {
        if (canManage) {
          bcsNote.style.display = "block";
          bcsNote.innerHTML = isAdvisor
            ? "🏛️ <strong>Tài khoản Cố vấn học tập:</strong> Bạn có quyền thêm mới, xóa và cập nhật danh bạ sinh viên K57."
            : "⭐ <strong>Tài khoản Ban cán sự:</strong> Bạn có quyền thêm mới, cập nhật MSSV và địa chỉ ví sinh viên để đối soát nộp quỹ.";
        } else {
          bcsNote.style.display = "none";
        }
      }

      if (modal) {
        modal.classList.add("open");
        modal.classList.add("show");

        // Đặt lại ô tìm kiếm và bộ lọc về Tất cả mỗi khi mở
        const searchInput = document.getElementById("rosterSearchInput");
        if (searchInput) searchInput.value = "";
        currentRosterFilter = "all";
        ["rfFilterAll", "rfFilterBcs", "rfFilterStudent", "rfFilterPaid", "rfFilterUnpaid"].forEach(id => {
          const btn = document.getElementById(id);
          if (btn) {
            if (id === "rfFilterAll") btn.classList.add("active");
            else btn.classList.remove("active");
          }
        });

        if (!classRoster || classRoster.length === 0) {
          loadClassRoster(userAddress);
        } else {
          renderRosterTable();
        }
      }
    }

// ==================== syncDepositorsData ====================
async function syncDepositorsData(classFundWei, adminFeeWei) {
      const depNumEl = document.getElementById("metricDepositorsCount");
      const depNoteEl = document.getElementById("metricDepositorsNote");

      let uniqueMap = new Map();
      let totalWei = 0n;

      // 1. Kiểm tra ví hiện tại của người dùng đang kết nối
      if (userAddress && contract) {
        try {
          const myContrib = await contract.studentContributions(userAddress);
          if (myContrib && myContrib > 0n) {
            totalWei += BigInt(myContrib);
            uniqueMap.set(userAddress.toLowerCase(), {
              address: userAddress,
              totalWei: BigInt(myContrib)
            });
            saveKnownDepositor(userAddress);
          }
        } catch (e) { }
      }

      // 2. Tải danh sách ví đã lưu trong localStorage
      try {
        const cached = JSON.parse(localStorage.getItem("kts_known_depositors") || "[]");
        for (const addr of cached) {
          if (ethers.isAddress(addr) && !uniqueMap.has(addr.toLowerCase()) && contract) {
            try {
              const c = await contract.studentContributions(addr);
              if (c && c > 0n) {
                totalWei += BigInt(c);
                uniqueMap.set(addr.toLowerCase(), {
                  address: addr,
                  totalWei: BigInt(c)
                });
              }
            } catch (e) { }
          }
        }
      } catch (e) { }

      // 3. Quét các applicant từ yêu cầu hoàn tiền (sinh viên làm đơn xin hoàn tiền chắc chắn đã từng nộp quỹ)
      if (contract) {
        try {
          const refCount = Number(await contract.refundRequestCount());
          for (let r = 1; r <= refCount; r++) {
            const req = await contract.getRefundRequest(r);
            const applicant = req[1];
            if (applicant && ethers.isAddress(applicant)) {
              saveKnownDepositor(applicant);
              if (!uniqueMap.has(applicant.toLowerCase())) {
                const c = await contract.studentContributions(applicant);
                if (c && c > 0n) {
                  totalWei += BigInt(c);
                  uniqueMap.set(applicant.toLowerCase(), {
                    address: applicant,
                    totalWei: BigInt(c)
                  });
                }
              }
            }
          }
        } catch (e) { }
      }

      // 4. Quét sự kiện FundDeposited chia thành 5 chunks (mỗi chunk 9000 block, quét ngược tối đa ~45.000 block)
      if (contract && provider) {
        try {
          const currentBlock = await provider.getBlockNumber();
          let toBlock = currentBlock;
          const filter = contract.filters.FundDeposited();
          for (let chunk = 0; chunk < 5; chunk++) {
            if (toBlock <= 0) break;
            const fromBlock = Math.max(0, toBlock - 9000);
            try {
              const events = await contract.queryFilter(filter, fromBlock, toBlock);
              if (events && events.length > 0) {
                events.forEach(ev => {
                  const student = ev.args ? (ev.args[0] || ev.args.student) : null;
                  const amt = ev.args ? (ev.args[1] || ev.args.amount) : 0n;
                  if (student && ethers.isAddress(student)) {
                    saveKnownDepositor(student);
                    const addrLower = student.toLowerCase();
                    if (!uniqueMap.has(addrLower)) {
                      uniqueMap.set(addrLower, {
                        address: student,
                        totalWei: BigInt(amt)
                      });
                    }
                  }
                });
              }
            } catch (chunkErr) {
              console.warn("Chunk scan queryFilter warning:", chunkErr);
              break;
            }
            toBlock = fromBlock - 1;
          }
        } catch (filterErr) {
          console.warn("RPC queryFilter warning:", filterErr);
        }
      }

      // 5. Kiểm tra các sinh viên trong danh bạ K57
      if (contract && classRoster && classRoster.length > 0) {
        for (const s of classRoster) {
          if (s.wallet && ethers.isAddress(s.wallet) && !uniqueMap.has(s.wallet.toLowerCase())) {
            try {
              const c = await contract.studentContributions(s.wallet);
              if (c && c > 0n) {
                totalWei += BigInt(c);
                uniqueMap.set(s.wallet.toLowerCase(), {
                  address: s.wallet,
                  totalWei: BigInt(c)
                });
              }
            } catch (e) { }
          }
        }
      }

      // 6. Đối chiếu số dư thực tế trên hợp đồng
      const cfWei = classFundWei || 0n;
      const afWei = adminFeeWei || 0n;
      const totalOnchainWei = cfWei + afWei;
      const totalOnchainEth = formatEth(totalOnchainWei);

      let finalCount = uniqueMap.size;
      let finalEth = totalOnchainEth;

      // Cập nhật lên Dashboard
      if (depNumEl) depNumEl.textContent = `${finalCount} sinh viên`;
      if (depNoteEl) depNoteEl.textContent = `Tổng nộp: ${finalEth} ETH`;

      // Cập nhật thanh tiến độ trên Bảng thông báo lớp
      updateAnnouncementProgress(finalCount);

      // BẢO VỆ QUYỀN RIÊNG TƯ (ĐỢT 3B.3):
      // Tuyệt đối không gắn Họ tên / MSSV vào danh sách nộp quỹ công khai
      const list = Array.from(uniqueMap.values()).map(item => {
        return {
          address: shortenAddress(item.address),
          fullAddress: item.address,
          name: "",
          mssv: "",
          amountEth: formatEth(item.totalWei)
        };
      });

      return {
        count: finalCount,
        totalEth: finalEth,
        list: list
      };
    }

// ==================== updateAnnouncementProgress ====================
async function updateAnnouncementProgress(depositorsCount) {
      const ann = getAnnouncementData();
      const count = Number(depositorsCount) || 0;
      const classSize = getDynamicClassSize(ann);
      const percent = classSize > 0 ? Math.min(100, Math.round((count / classSize) * 100)) : 0;

      const progTextEl = document.getElementById("annProgressText");
      const progBarEl = document.getElementById("annProgressBar");
      const statusTextEl = document.getElementById("annStatusText");

      if (progTextEl) {
        progTextEl.textContent = `${count}/${classSize} bạn đã nộp (${percent}%)`;
      }
      if (progBarEl) {
        progBarEl.style.width = `${percent}%`;
      }

      // 1. TRẠNG THÁI CHUNG CỦA LỚP (Group Status - Đợt 3B.3)
      // Chỉ đánh dấu COMPLETED khi xác minh được 100% sinh viên lớp đã nộp đủ
      if (statusTextEl) {
        if (classSize > 0 && count >= classSize) {
          statusTextEl.textContent = "Hoàn thành 100% (COMPLETED)";
        } else {
          statusTextEl.textContent = ann.status || "Đang diễn ra (OPEN)";
        }
      }

      // 2. TRẠNG THÁI CÁ NHÂN (Personal Status - Đợt 3B.3)
      // Dựa trên studentContributions[userAddress], không dựa vào tổng số dư quỹ
      const pBadge = document.getElementById("annPersonalStatusBadge");
      const pDesc = document.getElementById("annPersonalStatusDesc");
      if (pBadge && pDesc) {
        if (!userAddress || window.currentVerifiedRole === "none") {
          pBadge.className = "task-badge status-unverified";
          pBadge.textContent = "Chưa kết nối ví";
          pDesc.textContent = "Kết nối ví MetaMask để kiểm tra trạng thái đóng góp của bạn";
        } else if (window.currentVerifiedRole === "advisor") {
          pBadge.className = "task-badge status-ready";
          pBadge.textContent = "Cố vấn học tập";
          pDesc.textContent = "Tài khoản Cố vấn quản trị, không thuộc diện nộp quỹ thường niên";
        } else if (window.currentVerifiedRole === "guest") {
          pBadge.className = "task-badge status-unlinked";
          pBadge.textContent = "Ví ngoài danh bạ";
          pDesc.textContent = "Địa chỉ ví của bạn chưa được liên kết danh bạ sinh viên K57";
        } else {
          // Sinh viên hoặc Ban cán sự
          let myContribWei = 0n;
          if (contract && userAddress) {
            try {
              myContribWei = await contract.studentContributions(userAddress);
            } catch (e) {
              console.warn("Lỗi đọc studentContributions cá nhân:", e);
            }
          }
          const myContribEth = formatEth(myContribWei);
          const targetEth = ann.targetAmountEth || "0.01";
          if (Number(myContribEth) >= Number(targetEth) && Number(targetEth) > 0) {
            pBadge.className = "task-badge status-completed";
            pBadge.textContent = "Đã hoàn thành (COMPLETED)";
            pDesc.textContent = `Bạn đã hoàn thành đóng góp ${myContribEth} ETH on-chain cho quỹ lớp K57.`;
          } else if (Number(myContribEth) > 0) {
            pBadge.className = "task-badge status-action";
            pBadge.textContent = "Đã nộp một phần";
            pDesc.textContent = `Bạn đã nộp ${myContribEth} / ${targetEth} ETH. Vui lòng đóng góp phần còn lại.`;
          } else {
            pBadge.className = "task-badge status-action";
            pBadge.textContent = "Chưa nộp quỹ (OPEN)";
            pDesc.textContent = `Nghĩa vụ cá nhân: ${targetEth} ETH theo thông báo của lớp`;
          }
        }
      }
    }
