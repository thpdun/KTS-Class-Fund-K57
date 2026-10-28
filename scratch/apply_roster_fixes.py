import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open("web/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. DEFAULT CLASS ROSTER & INITIAL STATE
old_roster_decl = "let classRoster = [];"
new_roster_decl = """// Danh bạ lớp K57 mặc định (khởi tạo ngoại tuyến & đồng bộ với backend)
    const DEFAULT_CLASS_ROSTER = [
      {
        mssv: "23K4300004",
        name: "Trần Hoàng Phương Dung",
        wallet: "0x78567A377559F0cB30173f93869326a82320159a",
        role: "bcs",
        roleTitle: "Ban cán sự"
      },
      {
        mssv: "23K4300015",
        name: "Võ Ngọc Tâm Phúc",
        wallet: "0xf5D971952dbDF69058a28D23110381d96B00cb50",
        role: "bcs",
        roleTitle: "Ban cán sự"
      },
      {
        mssv: "23K4300014",
        name: "Phan Thị Yến Nhi",
        wallet: "0x7Af21f18DEfDA4a141BAD89681C0d4767A42333C",
        role: "bcs",
        roleTitle: "Ban cán sự"
      },
      {
        mssv: "23K4300005",
        name: "Trần Thị Bình Dương",
        wallet: "0x64ADE1f3E814c98dEFeC19f07253afeBDD2DBfcf",
        role: "student",
        roleTitle: "Sinh viên"
      },
      {
        mssv: "23K4300025",
        name: "Nguyễn Thị Kim Chi",
        wallet: "0x372819EB492cc6A071b946d5b82BF46174FE8394",
        role: "student",
        roleTitle: "Sinh viên"
      }
    ];

    let classRoster = (() => {
      try {
        const cached = localStorage.getItem("kts_class_roster");
        if (cached) {
          const parsed = JSON.parse(cached);
          if (Array.isArray(parsed) && parsed.length > 0) return parsed;
        }
      } catch (e) { }
      return [...DEFAULT_CLASS_ROSTER];
    })();"""

assert old_roster_decl in content, "old_roster_decl not found"
content = content.replace(old_roster_decl, new_roster_decl, 1)

# 2. LOOKUP STUDENT (Case-insensitive wallet match with fallback)
old_lookup = """function lookupStudent(addr) {
      if (!addr) return null;
      if (myStudentProfile && myStudentProfile.wallet && myStudentProfile.wallet.toLowerCase() === addr.toLowerCase()) {
        return myStudentProfile;
      }
      if (classRoster && classRoster.length > 0) {
        const target = addr.toLowerCase().trim();
        return classRoster.find(s => s.wallet && s.wallet.toLowerCase().trim() === target) || null;
      }
      return null;
    }"""

new_lookup = """function lookupStudent(addr) {
      if (!addr) return null;
      const target = addr.toLowerCase().trim();
      if (myStudentProfile && myStudentProfile.wallet && myStudentProfile.wallet.toLowerCase().trim() === target) {
        return myStudentProfile;
      }
      if (classRoster && classRoster.length > 0) {
        const found = classRoster.find(s => s.wallet && s.wallet.toLowerCase().trim() === target);
        if (found) return found;
      }
      return DEFAULT_CLASS_ROSTER.find(s => s.wallet && s.wallet.toLowerCase().trim() === target) || null;
    }"""

assert old_lookup in content, "old_lookup not found"
content = content.replace(old_lookup, new_lookup, 1)

# 3. LOAD CLASS ROSTER (Updates both badges, syncs localStorage, updates identity)
old_load = """async function loadClassRoster(signerAddr = null) {
      const caller = signerAddr || userAddress || "";
      const isBcs = isBcsMember || (myStudentProfile && myStudentProfile.role === "bcs");
      try {
        const res = await fetch(`http://localhost:8000/api/roster?address=${encodeURIComponent(caller)}&isBcs=${isBcs ? '1' : '0'}&isAdvisor=${isAdvisor ? '1' : '0'}`);
        if (res.ok) {
          const data = await res.json();
          if (data && data.success && Array.isArray(data.roster)) {
            classRoster = data.roster;
            const countBadge = document.getElementById("rosterCountBadge");
            if (countBadge) countBadge.textContent = classRoster.length;
            renderRosterTable();
            renderAnnouncementUI(); // Tự động cập nhật sĩ số lớp và tiến độ nộp quỹ theo danh bạ mới nhất
            return classRoster;
          }
        } else if (res.status === 403) {
          // Sinh viên hoặc khách vãng lai không có quyền xem toàn bộ danh bạ
          classRoster = [];
        }
      } catch (err) {
        console.warn("Chưa thể tải danh bạ từ backend:", err);
      }
      return classRoster;
    }"""

new_load = """async function loadClassRoster(signerAddr = null) {
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
    }"""

assert old_load in content, "old_load not found"
content = content.replace(old_load, new_load, 1)

# 4. HANDLE DISCONNECT (Clears both quick control and sidebar drawer)
old_disc = """async function handleDisconnect() {
      userAddress = null;
      signer = null;
      contract = null;
      isAdvisor = false;
      isBcsMember = false;
      document.getElementById("walletBtnText").textContent = "Kết nối MetaMask";
      document.getElementById("networkDot").className = "badge-dot";
      document.getElementById("networkText").textContent = "Chưa kết nối ví";
      document.getElementById("quickWalletAccount").textContent = "Chưa kết nối ví";
      updateRoleDisplay("none");
      const bSwitch = document.getElementById("btnSwitchWallet");
      const bDisc = document.getElementById("btnDisconnectWallet");
      const bQSwitch = document.getElementById("btnQuickSwitch");
      const bQDisc = document.getElementById("btnQuickDisconnect");
      if (bSwitch) bSwitch.style.display = "none";
      if (bDisc) bDisc.style.display = "none";
      if (bQSwitch) bQSwitch.style.display = "none";
      if (bQDisc) bQDisc.style.display = "none";
      logToTerminal("[MetaMask] Đã ngắt kết nối tài khoản.");
    }"""

new_disc = """async function handleDisconnect() {
      userAddress = null;
      signer = null;
      contract = null;
      isAdvisor = false;
      isBcsMember = false;
      myStudentProfile = null;
      document.getElementById("walletBtnText").textContent = "Kết nối MetaMask";
      document.getElementById("networkDot").className = "badge-dot";
      document.getElementById("networkText").textContent = "Chưa kết nối ví";
      document.getElementById("quickWalletAccount").textContent = "Chưa kết nối ví";
      updateRoleDisplay("none");
      const bSwitch = document.getElementById("btnSwitchWallet");
      const bDisc = document.getElementById("btnDisconnectWallet");
      const bQSwitch = document.getElementById("btnQuickSwitch");
      const bQDisc = document.getElementById("btnQuickDisconnect");
      if (bSwitch) bSwitch.style.display = "none";
      if (bDisc) bDisc.style.display = "none";
      if (bQSwitch) bQSwitch.style.display = "none";
      if (bQDisc) bQDisc.style.display = "none";
      logToTerminal("[MetaMask] Đã ngắt kết nối tài khoản.");
    }"""

assert old_disc in content, "old_disc not found"
content = content.replace(old_disc, new_disc, 1)

# 5. OPEN ROSTER MODAL (Allows viewing for all, edit form for BCS & Advisor)
old_open_roster = """function openRosterModal() {
      // Phân quyền bảo mật: Sinh viên và khách vãng lai tuyệt đối không được mở modal danh bạ
      const isBcs = isBcsMember || (myStudentProfile && myStudentProfile.role === "bcs");
      if (!isAdvisor && !isBcs) {
        alert("Quyền riêng tư: Danh bạ sinh viên chỉ dành riêng cho Cố vấn học tập và Ban cán sự.");
        return;
      }
      const modal = document.getElementById("rosterModal");
      const adminSec = document.getElementById("rosterAdminSection");
      const bcsNote = document.getElementById("rosterBcsViewNote");

      // CHỈ CỐ VẤN HỌC TẬP MỚI ĐƯỢC HIỂN THỊ KHUNG THÊM/SỬA
      if (adminSec) {
        adminSec.style.display = isAdvisor ? "block" : "none";
      }
      // Ban cán sự chỉ xem đối soát nộp quỹ
      if (bcsNote) {
        bcsNote.style.display = (isBcs && !isAdvisor) ? "block" : "none";
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
    }"""

new_open_roster = """function openRosterModal() {
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
    }"""

assert old_open_roster in content, "old_open_roster not found"
content = content.replace(old_open_roster, new_open_roster, 1)

# 6. EDIT & SAVE ROSTER (Allows BCS and Advisor)
old_edit = """function editRosterStudent(mssv) {
      if (!isAdvisor) {
        alert("Chỉ Cố vấn học tập mới có quyền chỉnh sửa thông tin sinh viên!");
        return;
      }"""

new_edit = """function editRosterStudent(mssv) {
      const isBcs = isBcsMember || (myStudentProfile && myStudentProfile.role === "bcs");
      if (!isAdvisor && !isBcs) {
        alert("Chỉ Ban cán sự hoặc Cố vấn học tập mới có quyền chỉnh sửa thông tin sinh viên!");
        return;
      }"""

assert old_edit in content, "old_edit not found"
content = content.replace(old_edit, new_edit, 1)

old_save = """async function saveRosterEntry() {
      // Bảo vệ phân quyền: CHỈ CỐ VẤN HỌC TẬP MỚI CÓ QUYỀN THÊM/SỬA
      if (!isAdvisor) {
        alert("Quyền hạn: Chỉ Cố vấn học tập mới có quyền thêm mới hoặc chỉnh sửa danh bạ sinh viên! Ban cán sự chỉ có quyền xem danh sách.");
        return;
      }

      const mssv = document.getElementById("formRosterMssv").value.trim();
      const name = document.getElementById("formRosterName").value.trim();
      const wallet = document.getElementById("formRosterWallet").value.trim();
      const roleVal = document.getElementById("formRosterRole").value;
      const [role, roleTitle] = roleVal.split("|");

      if (!mssv || !name || !wallet) {
        alert("Vui lòng nhập đầy đủ MSSV, Họ và tên và Địa chỉ ví!");
        return;
      }
      if (!wallet.startsWith("0x") || wallet.length !== 42) {
        alert("Địa chỉ ví không hợp lệ (phải bắt đầu bằng 0x và đủ 42 ký tự)!");
        return;
      }

      try {
        const res = await fetch("http://localhost:8000/api/roster/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            originalMssv: currentEditingMssv,
            mssv,
            name,
            wallet,
            role,
            roleTitle: (role === "bcs") ? "Ban cán sự" : "Sinh viên",
            signerAddress: userAddress || "advisor",
            isAdvisor: true
          })
        });
        const data = await res.json();
        if (data && data.success) {
          alert(data.message || "Lưu thành công vào danh bạ K57!");
          classRoster = data.roster;
          const countBadge = document.getElementById("rosterCountBadge");
          if (countBadge) countBadge.textContent = classRoster.length;
          cancelEditRoster();
          renderRosterTable();
          renderAnnouncementUI(); // Tự động cập nhật sĩ số lớp và tiến độ nộp quỹ khi thêm/sửa sinh viên
          if (userAddress) updateRoleDisplay(isAdvisor ? "advisor" : (isBcsMember ? "bcs" : "student"));
        } else {
          alert("Lỗi: " + (data.error || "Không thể lưu"));
        }
      } catch (err) {
        alert("Không thể kết nối đến máy chủ backend để lưu danh bạ.");
      }
    }"""

new_save = """async function saveRosterEntry() {
      const isBcs = isBcsMember || (myStudentProfile && myStudentProfile.role === "bcs");
      if (!isAdvisor && !isBcs) {
        alert("Quyền hạn: Chỉ Ban cán sự hoặc Cố vấn học tập mới có quyền thêm mới hoặc chỉnh sửa danh bạ sinh viên!");
        return;
      }

      const mssv = document.getElementById("formRosterMssv").value.trim();
      const name = document.getElementById("formRosterName").value.trim();
      const wallet = document.getElementById("formRosterWallet").value.trim();
      const roleVal = document.getElementById("formRosterRole").value;
      const [role, roleTitle] = roleVal.split("|");

      if (!mssv || !name || !wallet) {
        alert("Vui lòng nhập đầy đủ MSSV, Họ và tên và Địa chỉ ví!");
        return;
      }
      if (!wallet.startsWith("0x") || wallet.length !== 42) {
        alert("Địa chỉ ví không hợp lệ (phải bắt đầu bằng 0x và đủ 42 ký tự)!");
        return;
      }

      let savedSuccessfully = false;
      try {
        const res = await fetch("http://localhost:8000/api/roster/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            originalMssv: currentEditingMssv,
            mssv,
            name,
            wallet,
            role,
            roleTitle: (role === "bcs") ? "Ban cán sự" : "Sinh viên",
            signerAddress: userAddress || (isAdvisor ? "advisor" : "bcs"),
            isAdvisor: isAdvisor,
            isBcs: isBcs
          })
        });
        const data = await res.json();
        if (data && data.success) {
          alert(data.message || "Lưu thành công vào danh bạ K57!");
          classRoster = data.roster;
          savedSuccessfully = true;
        } else {
          alert("Lỗi từ server: " + (data.error || "Không thể lưu"));
          return;
        }
      } catch (err) {
        console.warn("Máy chủ backend offline, lưu vào bộ nhớ cục bộ:", err);
        let matchIdx = classRoster.findIndex(item => (currentEditingMssv && item.mssv === currentEditingMssv) || item.mssv === mssv);
        if (matchIdx !== -1) {
          classRoster[matchIdx] = { mssv, name, wallet, role, roleTitle: (role === "bcs" ? "Ban cán sự" : "Sinh viên") };
        } else {
          classRoster.push({ mssv, name, wallet, role, roleTitle: (role === "bcs" ? "Ban cán sự" : "Sinh viên") });
        }
        savedSuccessfully = true;
        alert(`Đã lưu thành công sinh viên ${name} (${mssv}) vào bộ nhớ cục bộ!`);
      }

      if (savedSuccessfully) {
        try { localStorage.setItem("kts_class_roster", JSON.stringify(classRoster)); } catch(e){}
        const countBadge = document.getElementById("rosterCountBadge");
        if (countBadge) countBadge.textContent = classRoster.length;
        const sbBadge = document.getElementById("sidebarRosterBadge");
        if (sbBadge) sbBadge.textContent = classRoster.length;
        cancelEditRoster();
        renderRosterTable();
        renderAnnouncementUI(); // Tự động cập nhật sĩ số lớp và tiến độ nộp quỹ khi thêm/sửa sinh viên
        if (userAddress) {
          const s = lookupStudent(userAddress);
          if (s) {
            myStudentProfile = s;
            if (s.role === "bcs") isBcsMember = true;
            updateRoleDisplay(isAdvisor ? "advisor" : (s.role === "bcs" ? "bcs" : "student"), s);
          }
        }
      }
    }"""

assert old_save in content, "old_save not found"
content = content.replace(old_save, new_save, 1)

# 7. ACTION BUTTON IN TABLE (Allow BCS and Advisor to see edit button)
old_action_btn = """const actionBtn = isAdvisor
          ? `<button class=\"btn btn-sm btn-outline\" onclick=\"editRosterStudent('${s.mssv}')\" style=\"padding: 4px 10px; font-size: 0.75rem; border-radius: 6px; cursor: pointer; color: #0284c7; border: 1px solid #bae6fd; background: #f0f9ff; font-weight: 600;\" title=\"Chỉnh sửa thông tin, vai trò hoặc địa chỉ ví của sinh viên này\">✏️ Sửa</button>`
          : '<span style=\"color: #94a3b8; font-size: 0.75rem;\">--</span>';"""

new_action_btn = """const canEditStudent = isAdvisor || isBcsMember || (myStudentProfile && myStudentProfile.role === "bcs");
        const actionBtn = canEditStudent
          ? `<button class=\"btn btn-sm btn-outline\" onclick=\"editRosterStudent('${s.mssv}')\" style=\"padding: 4px 10px; font-size: 0.75rem; border-radius: 6px; cursor: pointer; color: #0284c7; border: 1px solid #bae6fd; background: #f0f9ff; font-weight: 600;\" title=\"Chỉnh sửa thông tin, vai trò hoặc địa chỉ ví của sinh viên này\">✏️ Sửa</button>`
          : '<span style=\"color: #94a3b8; font-size: 0.75rem;\">--</span>';"""

assert old_action_btn in content, "old_action_btn not found"
content = content.replace(old_action_btn, new_action_btn, 1)

# 8. UPDATE ROLE DISPLAY
idx_start = content.find("function updateRoleDisplay(roleType, studentObj = null) {")
idx_end = content.find("// Apply contract address & save to localStorage", idx_start)
assert idx_start != -1 and idx_end != -1, "updateRoleDisplay block not found"

new_update_role_block = """function updateRoleDisplay(roleType, studentObj = null) {
      const badge = document.getElementById("quickRoleBadge");
      const idEl = document.getElementById("quickStudentIdentity");
      const warnBanner = document.getElementById("guestWarningBanner");
      const adminSec = document.getElementById("rosterAdminSection");

      const sbId = document.getElementById("sidebarUserIdentity");
      const sbRole = document.getElementById("sidebarRoleBadge");
      const sbAddr = document.getElementById("sidebarWalletShort");

      if (!studentObj && userAddress) {
        studentObj = lookupStudent(userAddress);
      }

      // Cập nhật địa chỉ ví vào ngăn kéo sidebar
      if (sbAddr) sbAddr.textContent = userAddress ? shortenAddress(userAddress) : "--";

      if (roleType === "advisor") {
        isAdvisor = true;
        isBcsMember = false;
        if (sbId) sbId.textContent = "Giảng viên phụ trách K57";
        if (sbRole) {
          sbRole.textContent = "🏛️ Cố vấn";
          sbRole.className = "status-pill";
          sbRole.style.background = "var(--advisor-bg, #f3e8ff)";
          sbRole.style.color = "var(--advisor-color, #6d28d9)";
        }
        if (badge) {
          badge.textContent = "🏛️ Cố vấn học tập";
          badge.className = "status-pill";
          badge.style.background = "var(--purple-bg, #f3e8ff)";
          badge.style.color = "#6d28d9";
          badge.style.border = "1px solid #ddd6fe";
        }
        if (idEl) idEl.innerHTML = `<span style="color:#a855f7;">Giảng viên phụ trách K57</span>`;
        if (warnBanner) warnBanner.style.display = "none";
        if (adminSec) adminSec.style.display = "block";
      } else if (roleType === "bcs") {
        isBcsMember = true;
        const nameStr = studentObj ? `${studentObj.name} (${studentObj.mssv})` : "Ban cán sự lớp K57";
        const title = studentObj ? (studentObj.roleTitle || "Ban cán sự") : "Ban cán sự lớp";
        if (sbId) sbId.textContent = nameStr;
        if (sbRole) {
          sbRole.textContent = `⭐ ${title}`;
          sbRole.className = "status-pill";
          sbRole.style.background = "var(--bcs-bg, #dbeafe)";
          sbRole.style.color = "var(--bcs-color, #1d4ed8)";
        }
        if (badge) {
          badge.textContent = `⭐ ${title}`;
          badge.className = "status-pill status-ready";
          badge.style.background = "#dbeafe";
          badge.style.color = "#1d4ed8";
          badge.style.border = "1px solid #bfdbfe";
        }
        if (idEl) {
          idEl.innerHTML = studentObj ? `<strong>${studentObj.name}</strong> (${studentObj.mssv})` : `<span style="color:#93c5fd;">BCS (Chưa liên kết MSSV)</span>`;
        }
        if (warnBanner) warnBanner.style.display = "none";
        // Ban cán sự có quyền mở form quản lý danh bạ
        if (adminSec) adminSec.style.display = "block";
      } else if (studentObj) {
        if (sbId) sbId.textContent = `${studentObj.name} (${studentObj.mssv})`;
        if (sbRole) {
          sbRole.textContent = "🎓 Sinh viên";
          sbRole.className = "status-pill";
          sbRole.style.background = "var(--student-bg, #ecfdf5)";
          sbRole.style.color = "var(--student-color, #047857)";
        }
        if (badge) {
          badge.textContent = "🎓 Sinh viên lớp K57";
          badge.className = "status-pill status-executed";
          badge.style.background = "var(--success-bg, #ecfdf5)";
          badge.style.color = "#047857";
          badge.style.border = "1px solid #a7f3d0";
        }
        if (idEl) idEl.innerHTML = `<strong>${studentObj.name}</strong> (${studentObj.mssv})`;
        if (warnBanner) warnBanner.style.display = "none";
        if (adminSec) adminSec.style.display = "none";
      } else if (userAddress) {
        if (sbId) sbId.textContent = shortenAddress(userAddress);
        if (sbRole) {
          sbRole.textContent = "Khách vãng lai";
          sbRole.className = "status-pill";
          sbRole.style.background = "var(--warning-bg, #fffbeb)";
          sbRole.style.color = "#b45309";
        }
        if (badge) {
          badge.textContent = "⚠️ Khách vãng lai (Chỉ xem)";
          badge.className = "status-pill";
          badge.style.background = "var(--warning-bg, #fffbeb)";
          badge.style.color = "#b45309";
          badge.style.border = "1px solid #fde68a";
        }
        if (idEl) idEl.innerHTML = `<span style="color:#f59e0b;">Chưa có trong danh bạ</span>`;
        if (warnBanner) warnBanner.style.display = "flex";
        if (adminSec) adminSec.style.display = "none";
      } else {
        if (sbId) sbId.textContent = "Chưa kết nối ví";
        if (sbRole) {
          sbRole.textContent = "Chưa xác thực";
          sbRole.className = "status-pill";
          sbRole.style.background = "";
          sbRole.style.color = "";
        }
        if (badge) {
          badge.textContent = "Chưa kết nối ví";
          badge.className = "status-pill status-ready";
          badge.style.background = "";
          badge.style.color = "";
          badge.style.border = "";
        }
        if (idEl) idEl.textContent = "--";
        if (warnBanner) warnBanner.style.display = "none";
        if (adminSec) adminSec.style.display = "none";
      }

      // Phân quyền hiển thị nút Quản trị thông báo: CHỈ HIỆN VỚI BAN CÁN SỰ (HOẶC CỐ VẤN)
      const btnOpenAnn = document.getElementById("btnOpenAnnModal");
      if (btnOpenAnn) {
        if (roleType === "bcs" || roleType === "advisor") {
          btnOpenAnn.style.display = "inline-flex";
        } else {
          btnOpenAnn.style.display = "none";
        }
      }

      // Nút mở modal danh bạ trên thanh hero (hiển thị cho Cố vấn hoặc Ban cán sự)
      const itemRoster = document.getElementById("itemRosterModalBtn");
      if (itemRoster) {
        if (roleType === "bcs" || roleType === "advisor" || isAdvisor || isBcsMember) {
          itemRoster.style.display = "flex";
        } else {
          itemRoster.style.display = "none";
        }
      }
    }

    """

content = content[:idx_start] + new_update_role_block + content[idx_end:]

# Write to file
with open("web/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("SUCCESS: All roster and wallet fixes applied to web/index.html!")
