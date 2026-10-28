import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('web/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = "    // --- KHU VỰC: VIỆC CẦN XỬ LÝ (ACTION CENTER - ĐỢT 3B.2) ---\n    async function renderPendingActions() {"
end_marker = "      window.__pendingTaskClick = function(id) {\n        if (window.__pendingTaskMap && window.__pendingTaskMap[id]) {\n          window.__pendingTaskMap[id]();\n        }\n      };\n    }"

start_idx = content.find(start_marker)
if start_idx == -1:
    # Try more flexible find
    start_marker = "async function renderPendingActions() {"
    start_idx = content.find(start_marker)

end_idx = content.find(end_marker, start_idx) + len(end_marker)

if start_idx == -1 or end_idx < start_idx:
    print(f"Error: start={start_idx}, end={end_idx}")
    sys.exit(1)

new_func = """    // --- KHU VỰC: VIỆC CẦN XỬ LÝ & VÒNG ĐỜI THÔNG BÁO (ACTION CENTER - ĐỢT 3B.3) ---
    async function renderPendingActions() {
      const container = document.getElementById("pendingActionsSection");
      const listEl = document.getElementById("pendingActionsList");
      const countBadge = document.getElementById("pendingCountBadge");
      if (!container || !listEl) return;

      const role = window.currentVerifiedRole || "none";
      const actionTasks = [];    // 1. Việc cần xử lý (Nhiệm vụ cá nhân còn tồn đọng)
      const waitingTasks = [];   // 2. Đang chờ (Tiến trình đang chờ bước tiếp theo)
      const completedTasks = []; // 3. Đã hoàn thành (Đã xác minh xong)
      const historyTasks = [];   // 4. Lịch sử thông báo & Hết hạn

      // 1. CHƯA KẾT NỐI VÍ
      if (!userAddress || role === "none") {
        actionTasks.push({
          id: "task-connect-wallet",
          icon: "🦊",
          statusClass: "status-unverified",
          statusText: "Chưa kết nối ví",
          title: "Kết nối ví MetaMask",
          desc: "Kết nối ví để kiểm tra trạng thái đóng góp quỹ, quyền biểu quyết đề xuất hoặc tác vụ quản trị của bạn.",
          actionText: "Kết nối ví ngay",
          actionClass: "btn-primary",
          onClick: () => connectWallet()
        });
      }
      // 2. KHÁCH VÃNG LAI
      else if (role === "guest") {
        actionTasks.push({
          id: "task-guest-notice",
          icon: "⚠️",
          statusClass: "status-unlinked",
          statusText: "Ví ngoài danh bạ",
          title: "Ví chưa được định danh trong danh bạ K57",
          desc: `Địa chỉ ví ${shortenAddress(userAddress)} đang ở chế độ xem công khai. Nếu bạn là sinh viên lớp K57, vui lòng liên hệ Ban cán sự để cập nhật ví.`,
          actionText: "Xem danh bạ lớp",
          actionClass: "btn-outline",
          onClick: () => openRosterModal()
        });
      }
      // 3. CỐ VẤN HỌC TẬP
      else if (role === "advisor") {
        if (contract) {
          try {
            const activeBCS = Number(await contract.activeBCSCount());
            const adminFeeWei = await contract.adminFeePool();
            const adminFeeEth = formatEth(adminFeeWei);

            if (activeBCS === 0) {
              actionTasks.push({
                id: "task-advisor-set-bcs",
                icon: "🚨",
                statusClass: "status-action",
                statusText: "Cần xử lý gấp",
                title: "Kích hoạt nhân sự Ban cán sự (R1)",
                desc: "Hợp đồng hiện chưa có thành viên Ban cán sự hoạt động (activeBCSCount = 0). Cần kích hoạt ít nhất 1 BCS để bắt đầu biểu quyết và giải ngân chi tiêu.",
                actionText: "Quản trị nhân sự BCS",
                actionClass: "btn-warning",
                onClick: () => {
                  selectRoleView("advisor");
                  const sec = document.getElementById("sectionAdvisorManageBcs");
                  if (sec) {
                    sec.scrollIntoView({ behavior: "smooth", block: "center" });
                    sec.classList.add("form-highlight-pulse");
                    setTimeout(() => sec.classList.remove("form-highlight-pulse"), 2500);
                  }
                }
              });
            } else {
              completedTasks.push({
                id: "task-advisor-bcs-active",
                icon: "👥",
                statusClass: "status-completed",
                statusText: "Đã kích hoạt",
                title: `Nhân sự Ban cán sự: ${activeBCS} thành viên đang hoạt động`,
                desc: "Bộ máy biểu quyết của lớp đã sẵn sàng thẩm định và biểu quyết các đề xuất chi tiêu.",
                actionText: "Xem nhân sự BCS",
                actionClass: "btn-outline",
                onClick: () => {
                  selectRoleView("advisor");
                  const sec = document.getElementById("sectionAdvisorManageBcs");
                  if (sec) sec.scrollIntoView({ behavior: "smooth", block: "center" });
                }
              });
            }

            if (Number(adminFeeEth) > 0) {
              actionTasks.push({
                id: "task-advisor-withdraw-fee",
                icon: "⛽",
                statusClass: "status-ready",
                statusText: "Khả dụng",
                title: `Quỹ phí vận hành có sẵn ${adminFeeEth} ETH`,
                desc: "Khoản 1% trích từ tiền nạp để Cố vấn bù đắp chi phí gas khi thực hiện giao dịch quản trị trên Sepolia.",
                actionText: "Đến biểu mẫu rút phí",
                actionClass: "btn-primary",
                onClick: () => {
                  selectRoleView("advisor");
                  const sec = document.getElementById("sectionAdvisorWithdrawFee");
                  if (sec) {
                    sec.scrollIntoView({ behavior: "smooth", block: "center" });
                    sec.classList.add("form-highlight-pulse");
                    setTimeout(() => sec.classList.remove("form-highlight-pulse"), 2500);
                  }
                }
              });
            }
          } catch (e) {
            console.warn("Lỗi kiểm tra task Advisor:", e);
          }
        }
      }
      // 4. SINH VIÊN HOẶC BAN CÁN SỰ
      else if (role === "student" || role === "bcs") {
        if (contract) {
          try {
            // Kiểm tra trạng thái đóng góp cá nhân (không suy đoán từ số dư quỹ)
            const myContribWei = await contract.studentContributions(userAddress);
            const myContribEth = formatEth(myContribWei);
            const ann = getAnnouncementData();
            const targetEth = ann.targetAmountEth || "0.01";

            if (Number(myContribEth) === 0) {
              actionTasks.push({
                id: "task-student-deposit",
                icon: "⚡",
                statusClass: "status-action",
                statusText: "Chưa nộp quỹ (OPEN)",
                title: `Đóng góp Quỹ Lớp K57 (${targetEth} ETH)`,
                desc: `Đợt thu quỹ học kỳ 1 đang diễn ra (Mục đích: ${ann.purpose || "Kinh phí học tập & hoạt động lớp"}). Bạn chưa hoàn thành nộp quỹ.`,
                actionText: "Nộp quỹ ngay",
                actionClass: "btn-success",
                onClick: () => handleQuickDepositClick()
              });
            } else if (Number(myContribEth) < Number(targetEth)) {
              actionTasks.push({
                id: "task-student-deposit-partial",
                icon: "⚠️",
                statusClass: "status-action",
                statusText: "Đã nộp một phần",
                title: `Đóng góp bổ sung Quỹ Lớp (${myContribEth}/${targetEth} ETH)`,
                desc: `Bạn đã đóng góp một phần ${myContribEth} ETH. Vui lòng đóng góp nốt phần còn lại để hoàn thành nghĩa vụ.`,
                actionText: "Nộp bổ sung",
                actionClass: "btn-warning",
                onClick: () => handleQuickDepositClick()
              });
            } else {
              completedTasks.push({
                id: "task-student-paid",
                icon: "✅",
                statusClass: "status-completed",
                statusText: "Đã nộp quỹ (COMPLETED)",
                title: "Đã hoàn thành nghĩa vụ đóng góp quỹ lớp",
                desc: `Bạn đã đóng góp thành công ${myContribEth} ETH on-chain cho tập thể lớp K57. Trạng thái đã được ghi nhận trên blockchain.`,
                actionText: "Xem chi tiết đóng góp",
                actionClass: "btn-outline",
                onClick: () => {
                  selectRoleView("student");
                  const sec = document.getElementById("myTotalContribution");
                  if (sec) sec.scrollIntoView({ behavior: "smooth", block: "center" });
                }
              });
            }

            // Quét các yêu cầu hoàn tiền của CHÍNH VÍ NÀY
            const refundCount = Number(await contract.refundRequestCount());
            const activeBCS = Number(await contract.activeBCSCount());
            for (let i = 1; i <= refundCount; i++) {
              try {
                const ref = await contract.getRefundRequest(i);
                const applicant = ref[1];
                if (applicant && applicant.toLowerCase() === userAddress.toLowerCase()) {
                  const status = Number(ref[7]);
                  const amountEth = formatEth(ref[2]);
                  const yesVotes = Number(ref[5]);
                  const pct = activeBCS > 0 ? ((yesVotes / activeBCS) * 100).toFixed(0) : 0;

                  if (status === 0) { // Pending
                    waitingTasks.push({
                      id: `task-my-refund-pending-${i}`,
                      icon: "⏳",
                      statusClass: "status-pending",
                      statusText: "Đang chờ duyệt",
                      title: `Yêu cầu hoàn tiền #${i} (${amountEth} ETH)`,
                      desc: `Lý do: "${ref[3]}" — Đang chờ Ban cán sự bỏ phiếu (Tiến độ: ${yesVotes}/${activeBCS} - ${pct}%).`,
                      actionText: "Xem đơn hoàn tiền",
                      actionClass: "btn-outline",
                      onClick: () => {
                        selectRoleView("student");
                        const sec = document.getElementById("studentRefundTableBody");
                        if (sec) sec.scrollIntoView({ behavior: "smooth", block: "center" });
                      }
                    });
                  } else if (status === 1) { // Ready - Đã duyệt ≥ 51%, chờ nhận tiền
                    actionTasks.push({
                      id: `task-my-refund-ready-${i}`,
                      icon: "🚀",
                      statusClass: "status-ready",
                      statusText: "Đã thông qua – Sẵn sàng nhận",
                      title: `Đơn hoàn tiền #${i} (${amountEth} ETH) đã được phê duyệt!`,
                      desc: `Ban cán sự đã thông qua (${pct}% ≥ 51%). Bạn có thể vào tab Sinh viên để thực thi giải ngân nhận lại tiền về ví.`,
                      actionText: "Đi đến nhận tiền",
                      actionClass: "btn-success",
                      onClick: () => {
                        selectRoleView("student");
                        const sec = document.getElementById("studentRefundTableBody");
                        if (sec) {
                          sec.scrollIntoView({ behavior: "smooth", block: "center" });
                          sec.classList.add("form-highlight-pulse");
                          setTimeout(() => sec.classList.remove("form-highlight-pulse"), 2500);
                        }
                      }
                    });
                  } else if (status === 2) { // Executed
                    completedTasks.push({
                      id: `task-my-refund-exec-${i}`,
                      icon: "💸",
                      statusClass: "status-completed",
                      statusText: "Đã giải ngân (Executed)",
                      title: `Đơn hoàn tiền #${i} (${amountEth} ETH) đã hoàn tất`,
                      desc: `Khoản tiền ${amountEth} ETH đã được chuyển thành công về địa chỉ ví của bạn.`,
                      actionText: "Xem lịch sử",
                      actionClass: "btn-outline",
                      onClick: () => {
                        selectRoleView("history");
                        const sec = document.getElementById("flowLedgerTableBody");
                        if (sec) sec.scrollIntoView({ behavior: "smooth", block: "center" });
                      }
                    });
                  } else if (status === 4 || status === 5) { // Expired or Cancelled
                    historyTasks.push({
                      id: `task-my-refund-expired-${i}`,
                      icon: "📁",
                      statusClass: "status-expired",
                      statusText: status === 4 ? "Đã hết hạn 7 ngày" : "Đã hủy",
                      title: `Đơn hoàn tiền #${i} (${amountEth} ETH) ${status === 4 ? "đã hết hạn" : "đã hủy"}`,
                      desc: `Đơn hoàn tiền không còn hiệu lực thực thi trên hợp đồng.`,
                      actionText: "Xem chi tiết",
                      actionClass: "btn-outline",
                      onClick: () => {
                        selectRoleView("student");
                        const sec = document.getElementById("studentRefundTableBody");
                        if (sec) sec.scrollIntoView({ behavior: "smooth", block: "center" });
                      }
                    });
                  }
                }
              } catch (e) {
                console.warn(`Lỗi đọc refund #${i}:`, e);
              }
            }

            // Quét các nhiệm vụ của BAN CÁN SỰ
            if (role === "bcs") {
              const spendCount = Number(await contract.spendRequestCount());
              for (let i = 1; i <= spendCount; i++) {
                try {
                  const sp = await contract.getSpendRequest(i);
                  const status = Number(sp[8]);
                  const amountEth = formatEth(sp[2]);
                  const desc = sp[3];
                  const yesVotes = Number(sp[6]);
                  const pct = activeBCS > 0 ? ((yesVotes / activeBCS) * 100).toFixed(0) : 0;

                  if (status === 0) { // Pending
                    const voted = await contract.hasVoted(i, userAddress);
                    if (!voted) {
                      actionTasks.push({
                        id: `task-bcs-spend-vote-${i}`,
                        icon: "🗳️",
                        statusClass: "status-action",
                        statusText: "Chưa biểu quyết",
                        title: `Biểu quyết Đề xuất chi #${i}: "${desc}"`,
                        desc: `Số tiền: ${amountEth} ETH — Tiến độ hiện tại: ${yesVotes}/${activeBCS} (${pct}%). Cần bạn bỏ phiếu.`,
                        actionText: "Bỏ phiếu ngay",
                        actionClass: "btn-primary",
                        onClick: () => {
                          selectRoleView("bcs");
                          const sec = document.getElementById("bcsSpendTableBody");
                          if (sec) {
                            sec.scrollIntoView({ behavior: "smooth", block: "center" });
                            sec.classList.add("form-highlight-pulse");
                            setTimeout(() => sec.classList.remove("form-highlight-pulse"), 2500);
                          }
                        }
                      });
                    } else {
                      waitingTasks.push({
                        id: `task-bcs-spend-waiting-${i}`,
                        icon: "⏳",
                        statusClass: "status-pending",
                        statusText: "Đang chờ đủ phiếu",
                        title: `Đề xuất chi #${i}: "${desc}" (Bạn đã vote)`,
                        desc: `Tiến độ hiện tại: ${yesVotes}/${activeBCS} (${pct}%). Đang chờ các thành viên BCS khác bỏ phiếu để đạt ngưỡng 51%.`,
                        actionText: "Xem bảng biểu quyết",
                        actionClass: "btn-outline",
                        onClick: () => {
                          selectRoleView("bcs");
                          const sec = document.getElementById("bcsSpendTableBody");
                          if (sec) sec.scrollIntoView({ behavior: "smooth", block: "center" });
                        }
                      });
                    }
                  } else if (status === 1) { // Ready - Đã thông qua ≥ 51%, chờ giải ngân
                    actionTasks.push({
                      id: `task-bcs-spend-execute-${i}`,
                      icon: "⚡",
                      statusClass: "status-ready",
                      statusText: "Đã thông qua – Chờ thực thi",
                      title: `Giải ngân Đề xuất chi #${i}: "${desc}"`,
                      desc: `Đề xuất đã đạt ${pct}% phiếu thuận (≥ 51%). Bạn có thể vào tab Ban cán sự để kích hoạt thực thi giải ngân ${amountEth} ETH.`,
                      actionText: "Đi đến giải ngân",
                      actionClass: "btn-success",
                      onClick: () => {
                        selectRoleView("bcs");
                        const sec = document.getElementById("bcsSpendTableBody");
                        if (sec) {
                          sec.scrollIntoView({ behavior: "smooth", block: "center" });
                          sec.classList.add("form-highlight-pulse");
                          setTimeout(() => sec.classList.remove("form-highlight-pulse"), 2500);
                        }
                      }
                    });
                  } else if (status === 2) { // Executed
                    completedTasks.push({
                      id: `task-bcs-spend-exec-${i}`,
                      icon: "✅",
                      statusClass: "status-completed",
                      statusText: "Đã giải ngân (Executed)",
                      title: `Đề xuất chi #${i}: "${desc}" (${amountEth} ETH)`,
                      desc: `Khoản chi đã được giải ngân thành công trên blockchain Ethereum Sepolia.`,
                      actionText: "Xem sổ dòng tiền",
                      actionClass: "btn-outline",
                      onClick: () => {
                        selectRoleView("history");
                        const sec = document.getElementById("flowLedgerTableBody");
                        if (sec) sec.scrollIntoView({ behavior: "smooth", block: "center" });
                      }
                    });
                  } else if (status === 4) { // Expired
                    historyTasks.push({
                      id: `task-bcs-spend-expired-${i}`,
                      icon: "📁",
                      statusClass: "status-expired",
                      statusText: "Đã hết hạn 7 ngày",
                      title: `Đề xuất chi #${i}: "${desc}" đã hết hạn`,
                      desc: `Đề xuất không đạt đủ 51% phiếu thuận trong thời hạn 7 ngày. Tiền tạm giữ đã được giải phóng về quỹ khả dụng.`,
                      actionText: "Xem chi tiết",
                      actionClass: "btn-outline",
                      onClick: () => {
                        selectRoleView("history");
                        const sec = document.getElementById("flowLedgerTableBody");
                        if (sec) sec.scrollIntoView({ behavior: "smooth", block: "center" });
                      }
                    });
                  }
                } catch (e) {
                  console.warn(`Lỗi đọc spend #${i}:`, e);
                }
              }

              // Kiểm tra các yêu cầu hoàn tiền mà BCS chưa vote
              for (let i = 1; i <= refundCount; i++) {
                try {
                  const ref = await contract.getRefundRequest(i);
                  const status = Number(ref[7]);
                  if (status === 0) { // Pending
                    const votedRefund = await contract.hasVotedRefund(i, userAddress);
                    const amountEth = formatEth(ref[2]);
                    const reason = ref[3];
                    const yesVotes = Number(ref[5]);
                    const pct = activeBCS > 0 ? ((yesVotes / activeBCS) * 100).toFixed(0) : 0;

                    if (!votedRefund) {
                      actionTasks.push({
                        id: `task-bcs-refund-vote-${i}`,
                        icon: "⚖️",
                        statusClass: "status-action",
                        statusText: "Chưa biểu quyết",
                        title: `Biểu quyết Đơn hoàn tiền #${i} (${amountEth} ETH)`,
                        desc: `Lý do: "${reason}" — Tiến độ: ${yesVotes}/${activeBCS} (${pct}%). Cần Ban cán sự xem xét.`,
                        actionText: "Xem xét & Bỏ phiếu",
                        actionClass: "btn-primary",
                        onClick: () => {
                          selectRoleView("bcs");
                          const sec = document.getElementById("bcsRefundTableBody");
                          if (sec) {
                            sec.scrollIntoView({ behavior: "smooth", block: "center" });
                            sec.classList.add("form-highlight-pulse");
                            setTimeout(() => sec.classList.remove("form-highlight-pulse"), 2500);
                          }
                        }
                      });
                    } else {
                      waitingTasks.push({
                        id: `task-bcs-refund-waiting-${i}`,
                        icon: "⏳",
                        statusClass: "status-pending",
                        statusText: "Đang chờ đủ phiếu",
                        title: `Đơn hoàn tiền #${i} (${amountEth} ETH) - Bạn đã vote`,
                        desc: `Đang chờ các thành viên BCS khác bỏ phiếu (${yesVotes}/${activeBCS} - ${pct}%).`,
                        actionText: "Xem bảng biểu quyết",
                        actionClass: "btn-outline",
                        onClick: () => {
                          selectRoleView("bcs");
                          const sec = document.getElementById("bcsRefundTableBody");
                          if (sec) sec.scrollIntoView({ behavior: "smooth", block: "center" });
                        }
                      });
                    }
                  }
                } catch (e) {
                  console.warn(`Lỗi đọc refund vote #${i}:`, e);
                }
              }
            }
          } catch (e) {
            console.warn("Lỗi kiểm tra task sinh viên/BCS:", e);
          }
        }
      }

      // Helper kết xuất HTML danh sách task
      function renderTaskListHtml(taskArray) {
        return taskArray.map(t => `
          <div class="pending-task-item ${t.statusClass}" id="${t.id}">
            <div class="pending-task-left">
              <span class="task-icon">${t.icon}</span>
              <div class="task-info">
                <div class="task-header-row">
                  <span class="task-title">${t.title}</span>
                  <span class="task-badge ${t.statusClass}">${t.statusText}</span>
                </div>
                <p class="task-desc">${t.desc}</p>
              </div>
            </div>
            <div class="pending-task-right">
              <button class="btn btn-sm ${t.actionClass}" onclick="window.__pendingTaskClick('${t.id}')">
                ${t.actionText}
              </button>
            </div>
          </div>
        `).join("");
      }

      // Cập nhật số lượng việc cần xử lý lên badge
      if (countBadge) {
        const count = actionTasks.length;
        countBadge.textContent = `${count} việc cần xử lý`;
        countBadge.className = count > 0 ? "pending-count-badge has-tasks" : "pending-count-badge all-clear";
      }

      // Kết xuất theo 4 nhóm chuẩn mực (Đợt 3B.3)
      let groupsHtml = "";

      // NHÓM 1: VIỆC CẦN XỬ LÝ (Nhiệm vụ cá nhân còn tồn đọng)
      if (actionTasks.length > 0) {
        groupsHtml += `
          <div class="pending-group-block">
            <h4 class="pending-group-title" style="color:#b45309; font-size:0.92rem; margin:10px 0 8px 0; display:flex; align-items:center; gap:6px;">
              <span>⚡</span> 1. Việc cần xử lý (${actionTasks.length})
            </h4>
            ${renderTaskListHtml(actionTasks)}
          </div>
        `;
      } else {
        groupsHtml += `
          <div class="pending-all-clear" style="margin-bottom:10px;">
            <div class="all-clear-icon">✨</div>
            <div class="all-clear-content">
              <h4>Không có việc nào tồn đọng</h4>
              <p>Bạn đã hoàn thành toàn bộ các nghĩa vụ đóng góp hoặc tác vụ biểu quyết thuộc quyền của mình.</p>
            </div>
          </div>
        `;
      }

      // NHÓM 2: ĐANG CHỜ (Tiến trình đang chờ bước tiếp theo)
      if (waitingTasks.length > 0) {
        groupsHtml += `
          <div class="pending-group-block">
            <h4 class="pending-group-title" style="color:#1d4ed8; font-size:0.92rem; margin:14px 0 8px 0; display:flex; align-items:center; gap:6px;">
              <span>⏳</span> 2. Đang chờ tiến trình (${waitingTasks.length})
            </h4>
            ${renderTaskListHtml(waitingTasks)}
          </div>
        `;
      }

      // NHÓM 3: ĐÃ HOÀN THÀNH (Đã xác minh xong)
      if (completedTasks.length > 0) {
        groupsHtml += `
          <div class="pending-group-block">
            <h4 class="pending-group-title" style="color:#047857; font-size:0.92rem; margin:14px 0 8px 0; display:flex; align-items:center; gap:6px;">
              <span>✅</span> 3. Đã hoàn thành (${completedTasks.length})
            </h4>
            ${renderTaskListHtml(completedTasks)}
          </div>
        `;
      }

      // NHÓM 4: LỊCH SỬ THÔNG BÁO & HẾT HẠN
      if (historyTasks.length > 0) {
        groupsHtml += `
          <div class="pending-group-block">
            <h4 class="pending-group-title" style="color:#64748b; font-size:0.92rem; margin:14px 0 8px 0; display:flex; align-items:center; gap:6px;">
              <span>📜</span> 4. Lịch sử &amp; Hết hạn (${historyTasks.length})
            </h4>
            ${renderTaskListHtml(historyTasks)}
          </div>
        `;
      }

      listEl.innerHTML = groupsHtml;

      // Đăng ký sự kiện click an toàn cho tất cả tasks (chỉ điều hướng/cuộn, không gửi tx)
      window.__pendingTaskMap = {};
      [...actionTasks, ...waitingTasks, ...completedTasks, ...historyTasks].forEach(t => {
        window.__pendingTaskMap[t.id] = t.onClick;
      });
      window.__pendingTaskClick = function (id) {
        if (window.__pendingTaskMap && window.__pendingTaskMap[id]) {
          try {
            window.__pendingTaskMap[id]();
          } catch (e) {
            console.error("Lỗi thực thi điều hướng pending task:", e);
          }
        }
      };
    }"""

updated_content = content[:start_idx] + new_func + content[end_idx:]
with open('web/index.html', 'w', encoding='utf-8') as f:
    f.write(updated_content)

print(f"Successfully replaced renderPendingActions from {start_idx} to {end_idx}. New length: {len(updated_content)}")
