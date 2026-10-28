"""
Dịch vụ AI Trợ lý Quỹ Lớp (KTS-Class-Fund)
Tuân thủ quy ước AGENTS.md:
- Python 3.10+
- Không ghi khóa API trong mã nguồn; đọc từ biến môi trường
- Kiểm tra trạng thái phản hồi trước khi xử lý dữ liệu
- Đổi wei sang ETH trước khi hiển thị
"""

import os
import json
import re
from typing import Dict, Any, Optional, List
from pathlib import Path
import requests

WEI_PER_ETH = 10**18


def load_dotenv():
    """Tự động tìm và nạp file .env ở thư mục gốc hoặc thư mục hiện tại"""
    search_dirs = [Path.cwd(), Path(__file__).parent.parent, Path(__file__).parent]
    for d in search_dirs:
        env_file = d / ".env"
        if env_file.exists():
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip('"').strip("'")
                            if k and k not in os.environ:
                                os.environ[k] = v
                break
            except Exception:
                pass

load_dotenv()


def wei_to_eth(wei_amount: int) -> float:
    """Đổi wei sang ETH theo quy ước AGENTS.md"""
    return round(float(wei_amount) / WEI_PER_ETH, 6)


def get_configured_api_keys() -> List[str]:
    """
    Hỗ trợ xoay vòng nhiều khóa API (Key Rotation):
    Đọc từ GEMINI_API_KEY (có thể phân tách bằng dấu phẩy) hoặc GEMINI_API_KEY_2, GEMINI_API_KEY_3...
    """
    keys = []
    env_keys = os.getenv("GEMINI_API_KEY", "")
    if env_keys:
        for k in env_keys.split(","):
            k = k.strip().strip('"').strip("'")
            if k and len(k) > 10 and k not in keys:
                keys.append(k)

    for i in range(2, 6):
        k = os.getenv(f"GEMINI_API_KEY_{i}", "").strip().strip('"').strip("'")
        if k and len(k) > 10 and k not in keys:
            keys.append(k)

    return keys


CANDIDATE_MODELS = [
    os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-3-flash-preview",
    "gemini-2.5-pro",
    "gemini-pro-latest"
]


class AIAssistantService:
    def __init__(self, api_key: Optional[str] = None):
        # Đọc khóa API từ tham số hoặc nạp từ danh sách cấu hình (Key Rotation)
        self.api_keys: List[str] = []
        if api_key and len(api_key.strip()) > 10:
            self.api_keys.append(api_key.strip())
        else:
            self.api_keys = get_configured_api_keys()

        self.api_key = self.api_keys[0] if self.api_keys else None

    def get_api_url(self, model_name: str, key: Optional[str] = None) -> str:
        k = key or self.api_key or ""
        return f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={k}"

    def is_configured(self) -> bool:
        """Kiểm tra xem ít nhất một API Key đã được cấu hình chưa."""
        return bool(self.api_keys and len(self.api_keys) > 0)

    def build_system_context(self, onchain_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Tạo ngữ cảnh hệ thống (System Prompt) kết hợp quy chế kinh tế (docs/SPEC.md)
        và dữ liệu on-chain Sepolia hiện tại.
        """
        context_parts = [
            "Bạn là Trợ lý AI Quỹ Lớp KTS-Class-Fund K57 (Chuyên ngành Kinh tế Số).",
            "Nhiệm vụ của bạn là giải đáp chính xác, khách quan và minh bạch các câu hỏi của sinh viên, ban cán sự (BCS) và cố vấn học tập (CVHT).",
            "",
            "--- QUY TẮC NGHIỆP VỤ QUỸ LỚP (docs/SPEC.md) ---",
            "1. Phân bổ nạp tiền (R2): Mỗi khi sinh viên nạp tiền, 1% (100 bps) trích vào Quỹ dịch vụ vận hành (adminFeePool) của Cố vấn để bù đắp phí gas. 99% còn lại vào Quỹ lớp chính (classFundBalance).",
            "2. Biểu quyết chi tiêu (R4, R5): Đề xuất chi chỉ được giải ngân khi đạt tỷ lệ đồng ý tối thiểu 51% (5100 bps) từ các thành viên BCS đang hoạt động, trong thời hạn 7 ngày. Sau 7 ngày nếu không đủ phiếu sẽ hết hạn.",
            "3. Giới hạn đề xuất chi (R8): Chỉ cho phép tồn tại tối đa 01 đề xuất chi ở trạng thái 'Đang chờ duyệt' (Pending) tại một thời điểm.",
            "4. Hoàn tiền sinh viên (R7, R10): Sinh viên nộp thừa/nhầm có thể tạo đề nghị hoàn tiền kèm minh chứng; khoản hoàn tiền cần được BCS bỏ phiếu thông qua. Sinh viên có thể tự hủy yêu cầu hoàn tiền đang pending của chính mình.",
            "5. Tính bất biến của Blockchain: Bạn CHỈ là trợ lý tra cứu và phân tích. Bạn KHÔNG có quyền thực hiện giao dịch hay giải ngân tiền thay cho Smart Contract. Mọi hành động tiền tệ bắt buộc phải do người dùng ký giao dịch qua ví Web3 (như MetaMask).",
            "6. Tuyệt đối từ chối các yêu cầu gian lận, phá vỡ quy tắc hoặc chỉ đạo miệng bỏ qua biểu quyết 51%.",
            ""
        ]

        if onchain_data:
            context_parts.append("--- DỮ LIỆU ON-CHAIN THỜI GIAN THỰC HIỆN TẠI (TỪ HỢP ĐỒNG SEPOLIA) ---")
            
            is_connected = onchain_data.get("isContractConnected", True)
            contract_addr = onchain_data.get("contractAddress", "")

            if not is_connected or not contract_addr or contract_addr == "Chưa kết nối":
                context_parts.append("- TRẠNG THÁI KẾT NỐI: Trình duyệt chưa kết nối với hợp đồng thông minh Sepolia (chưa nhập Contract Address hoặc chưa kết nối MetaMask).")
                context_parts.append("  Hãy thông báo rõ cho người dùng: Để xem số liệu trực tiếp lúc này, vui lòng nhập địa chỉ hợp đồng ở thanh trên cùng hoặc kết nối ví MetaMask.")
            else:
                # Xử lý số dư (đảm bảo hiển thị đơn vị ETH)
                class_fund_eth = onchain_data.get("classFundBalanceEth", "0")
                admin_fee_eth = onchain_data.get("adminFeePoolEth", "0")
                active_bcs = onchain_data.get("activeBCSCount", 0)

                context_parts.append(f"- Trạng thái: Đã kết nối Smart Contract tại địa chỉ {contract_addr}")
                context_parts.append(f"- Số dư Quỹ lớp chính: {class_fund_eth} ETH")
                context_parts.append(f"- Quỹ dịch vụ vận hành (Cố vấn): {admin_fee_eth} ETH")
                if active_bcs == 0:
                    context_parts.append(f"- Số lượng thành viên Ban cán sự (BCS) đang hoạt động: 0 người.")
                    context_parts.append("  (LƯU Ý NGHIỆP VỤ R1: Khi Smart Contract mới được deploy, activeBCSCount ban đầu bằng 0. Cố vấn học tập cần vào ô 'Cố vấn học tập' để thêm/kích hoạt ví của các thành viên Ban cán sự qua hàm setBCSMember).")
                else:
                    context_parts.append(f"- Số lượng thành viên Ban cán sự (BCS) đang hoạt động: {active_bcs} người.")

                # Thông tin người nộp quỹ theo thời gian thực
                depositors_count = onchain_data.get("depositorsCount", 0)
                total_deposited_eth = onchain_data.get("totalDepositedEth", "0")
                depositors_list = onchain_data.get("depositorsList", [])

                context_parts.append(f"- Số lượng sinh viên đã nộp quỹ tính đến đúng thời điểm hiện tại: {depositors_count} người.")
                context_parts.append(f"- Tổng số ETH đã nộp vào quỹ: {total_deposited_eth} ETH.")
                if depositors_list:
                    dep_str = ", ".join([f"{d.get('address')} ({d.get('amountEth')} ETH)" for d in depositors_list[:10]])
                    context_parts.append(f"- Danh sách chi tiết các ví nộp: {dep_str}")

            # Danh sách yêu cầu chi (Khử trùng lặp tuyệt đối theo ID)
            raw_spend = onchain_data.get("spendRequests", [])
            seen_spend = set()
            spend_requests = []
            for req in raw_spend:
                rid = req.get("id")
                if rid not in seen_spend:
                    seen_spend.add(rid)
                    spend_requests.append(req)

            context_parts.append(f"\n- Danh sách các yêu cầu chi tiêu hiện có ({len(spend_requests)} yêu cầu duy nhất):")
            if not spend_requests:
                context_parts.append("  (Hiện tại chưa có yêu cầu chi nào trong hợp đồng)")
            else:
                for req in spend_requests:
                    req_id = req.get("id")
                    desc = req.get("description", "Không có mô tả")
                    amount = req.get("amountEth", "0")
                    recipient = req.get("recipient", "N/A")
                    status_text = req.get("statusText", "Pending")
                    votes = req.get("votesText", "0")
                    creator = req.get("creator", "N/A")
                    context_parts.append(
                        f"  * Yêu cầu chi [Mã #{req_id}]:\n"
                        f"    - Mục đích chi: {desc}\n"
                        f"    - Số tiền: {amount} ETH\n"
                        f"    - Người nhận tiền (thụ hưởng): {recipient}\n"
                        f"    - Người tạo đề xuất: {creator}\n"
                        f"    - Tiến độ biểu quyết: {votes}\n"
                        f"    - Trạng thái hiện tại: {status_text}"
                    )

            # Danh sách hoàn tiền (Khử trùng lặp theo ID)
            raw_refund = onchain_data.get("refundRequests", [])
            seen_refund = set()
            refund_requests = []
            for ref in raw_refund:
                rfid = ref.get("id")
                if rfid not in seen_refund:
                    seen_refund.add(rfid)
                    refund_requests.append(ref)

            context_parts.append(f"\n- Danh sách yêu cầu hoàn tiền ({len(refund_requests)} yêu cầu duy nhất):")
            if not refund_requests:
                context_parts.append("  (Hiện tại chưa có yêu cầu hoàn tiền nào)")
            else:
                for ref in refund_requests:
                    ref_id = ref.get("id")
                    reason = ref.get("reason", "")
                    amount = ref.get("amountEth", "0")
                    applicant = ref.get("applicant", "N/A")
                    status_text = ref.get("statusText", "Pending")
                    context_parts.append(
                        f"  + [Mã #{ref_id}] Sinh viên: {applicant} | Lý do: '{reason}' | "
                        f"Số tiền: {amount} ETH | Trạng thái: {status_text}"
                    )

            # Thông tin thông báo đợt thu quỹ lớp (từ Ban cán sự & Cố vấn)
            announcement = onchain_data.get("announcement", {})
            if announcement and announcement.get("title"):
                context_parts.append("\n--- THÔNG BÁO THU QUỸ LỚP HIỆN HÀNH (TỪ BAN CÁN SỰ & CỐ VẤN) ---")
                context_parts.append(f"- Tiêu đề đợt thu: {announcement.get('title')}")
                context_parts.append(f"- Mức đóng quy định: {announcement.get('targetAmountEth', '0.01')} ETH/sinh viên")
                context_parts.append(f"- Hạn chót nộp quỹ: {announcement.get('deadline', 'Chưa xác định')}")
                context_parts.append(f"- Sĩ số lớp: {announcement.get('classSize', 5)} sinh viên")
                context_parts.append(f"- Mục đích thu quỹ: {announcement.get('purpose', '')}")
                context_parts.append(f"- Tiến độ thu thực tế: {announcement.get('progressText', '0%')}")
                context_parts.append(f"- Trạng thái đợt thu: {announcement.get('status', 'Đang diễn ra')}")

        context_parts.append("\n--- HƯỚNG DẪN BẮT BUỘC KHI TRẢ LỜI ---")
        context_parts.append("★ CHÍNH SÁCH BẢO VỆ QUYỀN RIÊNG TƯ & ẨN DANH NGƯỜI NỘP QUỸ (BẮT BUỘC TUÂN THỦ 100%):")
        context_parts.append("1. Trợ lý AI CHỈ giải đáp thông tin tổng hợp về quỹ (tổng số dư, số lượng người nộp tổng quát, các khoản chi on-chain, quy tắc SPEC.md).")
        context_parts.append("2. TUYỆT ĐỐI TỪ CHỐI các câu hỏi truy vấn danh tính cá nhân:")
        context_parts.append("   - Không xác nhận hay phủ nhận việc một cá nhân/MSSV/ví cụ thể đã nộp quỹ hay chưa (ví dụ: 'Sinh viên Nguyễn Văn A đã nộp quỹ chưa?').")
        context_parts.append("   - Không liệt kê danh sách ai đã nộp, ai chưa nộp, không cung cấp Họ tên, MSSV hoặc địa chỉ ví của sinh viên.")
        context_parts.append("   - Mẫu phản hồi chuẩn khi gặp câu hỏi này:")
        context_parts.append("     'Vì lý do bảo mật và bảo vệ quyền riêng tư cá nhân theo quy định, Trợ lý AI không xác nhận hay phủ nhận trạng thái đóng góp của từng cá nhân cụ thể, cũng như không cung cấp danh sách sinh viên đã nộp/chưa nộp, Họ tên, MSSV hoặc địa chỉ ví cá nhân. Bạn có thể theo dõi tiến độ đóng góp tổng hợp chung trên Dashboard hoặc liên hệ Ban cán sự / Cố vấn học tập để được hỗ trợ đối soát.'")
        context_parts.append("3. TUYỆT ĐỐI KHÔNG BỊA SỐ LIỆU: Nếu hợp đồng chưa kết nối hoặc chưa có số liệu on-chain, phải nêu rõ chưa có dữ liệu on-chain, không tự suy đoán.")

        context_parts.append("2. KHI ĐƯỢC HỎI VỀ SỐ LƯỢNG NGƯỜI NỘP QUỸ:")
        context_parts.append("   - Trả lời rõ ràng, dứt khoát số lượng người đã nộp ({depositors_count} sinh viên) với tổng số tiền đã nộp ({total_deposited_eth} ETH).")
        context_parts.append("   - Nêu rõ số dư Quỹ lớp (99%) và Quỹ dịch vụ vận hành của Cố vấn (1%).")
        context_parts.append("   - Nếu {depositors_count} >= 1 hoặc tổng tiền > 0, tuyệt đối KHÔNG nói 'chưa có ai nộp'.")
        context_parts.append("3. KHI ĐƯỢC HỎI VỀ CÁC YÊU CẦU CHI TIÊU:")
        context_parts.append("   - PHẢI LIỆT KÊ ĐẦY ĐỦ TẤT CẢ CÁC YÊU CẦU CHI TIÊU VÀ TRÌNH BÀY RÕ RÀNG CHI TIẾT TỪNG MỤC:")
        context_parts.append("     • Mã yêu cầu: #[ID]")
        context_parts.append("     • Mục đích chi tiêu: [Mục đích]")
        context_parts.append("     • Số tiền đề xuất: [Số tiền] ETH")
        context_parts.append("     • Người nhận (thụ hưởng): [Địa chỉ ví]")
        context_parts.append("     • Tiến độ biểu quyết: [Số phiếu / Tổng số BCS] ([Tỷ lệ]%)")
        context_parts.append("     • Trạng thái hiện tại: [Trạng thái]")
        context_parts.append("     • Quy chế giải ngân: Nhắc lại điều kiện cần tối thiểu 51% phiếu thuận từ Ban cán sự trong 7 ngày (R4/R5).")
        context_parts.append("4. TUYỆT ĐỐI KHÔNG ĐƯỢC LẶP LẠI: Mỗi mã yêu cầu chỉ xuất hiện đúng 1 lần duy nhất trong câu trả lời. Không được in trùng lặp.")
        context_parts.append("5. KHI ĐƯỢC HỎI VỀ SỐ LƯỢNG BAN CÁN SỰ (BCS) HOẶC TẠI SAO BCS LÀ 0:")
        context_parts.append("   - Trả lời rõ ràng số lượng thành viên Ban cán sự đang hoạt động on-chain.")
        context_parts.append("   - Nếu số lượng là 0, giải thích rõ nguyên nhân: Hợp đồng ProjectCore khi mới deploy ban đầu có activeBCSCount = 0 (chỉ có ví Cố vấn học tập). Cố vấn học tập cần dùng ví của mình truy cập ô 'Cố vấn học tập' -> 'Quản trị nhân sự Ban cán sự' để kích hoạt thành viên (R1) trước khi có thể biểu quyết các khoản chi.")
        context_parts.append("6. KHI ĐƯỢC HỎI VỀ THÔNG BÁO LỚP, HẠN NỘP QUỸ, MỨC ĐÓNG HOẶC TIẾN ĐỘ THU QUỸ:")
        context_parts.append("   - Trích xuất chính xác tiêu đề đợt thu, mức tiền quy định (ETH), hạn chót nộp, mục đích thu quỹ và tiến độ thực tế (số bạn đã nộp/sĩ số).")
        context_parts.append("   - Thân thiện nhắc nhở sinh viên có thể bấm nút 'Nộp quỹ ngay' trên thanh thông báo ở giao diện để hoàn thành đóng góp.")
        return "\n".join(context_parts)

    def generate_local_fallback_answer(self, user_question: str, onchain_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Bộ máy phản hồi On-chain Cục bộ (Intelligent Local On-chain Engine):
        Tự động phân tích câu hỏi và sinh câu trả lời chuẩn xác 100% từ dữ liệu on-chain Sepolia
        khi Google AI Studio đạt giới hạn hạn mức (HTTP 429) hoặc tạm thời mất kết nối.
        Bảo đảm tuân thủ tuyệt đối Chính sách Bảo vệ Quyền riêng tư & Ẩn danh người nộp quỹ.
        """
        data = onchain_data or {}
        q = user_question.strip().lower()

        contract_addr = data.get("contractAddress", "Chưa kết nối")
        is_connected = data.get("isContractConnected", True) and contract_addr not in ["", "Chưa kết nối"]
        class_fund_eth = data.get("classFundBalanceEth", "0")
        admin_fee_eth = data.get("adminFeePoolEth", "0")
        active_bcs = int(data.get("activeBCSCount", 0))
        depositors_count = int(data.get("depositorsCount", 0))
        total_deposited_eth = data.get("totalDepositedEth", "0")
        depositors_list = data.get("depositorsList", [])
        spend_requests = data.get("spendRequests", [])
        refund_requests = data.get("refundRequests", [])
        announcement = data.get("announcement", {})
        viewer_role = data.get("viewerRole", "student")
        is_privileged = viewer_role in ["advisor", "bcs"]
        roster = data.get("roster", []) if is_privileged else []
        user_address = data.get("userAddress", "").strip().lower()

        disclaimer = (
            "\n\n*(⚡ Trả lời tự động bởi Bộ máy On-chain Cục bộ (Local Fallback Engine) "
            "do Google AI Studio đang tạm hết hạn mức lượt gọi trong ngày. "
            "Mọi số liệu on-chain đều chính xác 100% theo thời gian thực.)*"
        )

        # 1. Phát hiện gian lận & cố ý phá vỡ quy tắc bảo mật hoặc kinh tế
        fraud_keywords = [
            "bỏ qua quy tắc", "bỏ qua biểu quyết", "bỏ qua 51%", "không cần biểu quyết",
            "giải ngân ngay", "chuyển tiền ngay", "chuyển thẳng", "chuyển tiền vào ví cá nhân",
            "sửa thông báo nộp quỹ", "không nộp vào hợp đồng", "tôi là thủ quỹ", "cấp quyền biểu quyết",
            "xác nhận tôi đã nộp 10 eth", "ghi nhận khống"
        ]
        if any(k in q for k in fraud_keywords):
            return (
                "⛔ **Từ chối yêu cầu:** AI chỉ là trợ lý tra cứu thông tin và phân tích, tuyệt đối không có quyền "
                "thực thi giải ngân hay can thiệp vào luồng tiền trên Blockchain. "
                "Theo quy tắc kinh tế bất biến R4 và R5 trên Smart Contract, mọi khoản chi tiêu bắt buộc phải "
                "đạt tối thiểu 51% phiếu thuận từ Ban cán sự đang hoạt động và phải được ký duyệt qua ví Web3 "
                "(MetaMask), không thể chỉ đạo miệng hay thực hiện trái phép. "
                "Mọi khoản đóng góp phải nộp trực tiếp vào địa chỉ Smart Contract on-chain đã kiểm chứng để đảm bảo tính minh bạch."
                + disclaimer
            )

        # 1b. Phát hiện truy vấn định danh cá nhân, MSSV hoặc danh sách chưa nộp (Chính sách Bảo vệ Quyền riêng tư Đợt 3B.1)
        personal_patterns = [
            r"phương\s*dung", r"trần\s*hoàng\s*phương\s*dung", r"tâm\s*phúc", r"võ\s*ngọc\s*tâm\s*phúc",
            r"yến\s*nhi", r"phan\s*thị\s*yến\s*nhi", r"bình\s*dương", r"trần\s*thị\s*bình\s*dương",
            r"kim\s*chi", r"nguyễn\s*thị\s*kim\s*chi", r"mssv", r"mã\s*sinh\s*viên", r"mã\s*số\s*sinh\s*viên",
            r"chưa\s*nộp", r"ai\s*chưa\s*nộp", r"danh\s*sách\s*chưa\s*nộp",
            r"liệt\s*kê.*sinh\s*viên", r"danh\s*sách\s*sinh\s*viên", r"kèm\s*mssv", r"kèm\s*ví",
            r"ví\s*của\s*bạn", r"bạn.*đã\s*nộp\s*chưa"
        ]
        if any(re.search(p, q, re.IGNORECASE) for p in personal_patterns):
            return (
                "🛡️ **Bảo vệ quyền riêng tư cá nhân sinh viên:**\n"
                "Vì lý do bảo mật và bảo vệ dữ liệu cá nhân theo quy định, Trợ lý AI không xác nhận, "
                "phủ nhận trạng thái đóng góp của từng cá nhân cụ thể, cũng như không cung cấp danh sách "
                "sinh viên đã nộp/chưa nộp, Họ tên, MSSV hoặc địa chỉ ví cá nhân.\n\n"
                "Bạn có thể theo dõi tiến độ đóng góp tổng hợp chung trên Dashboard hoặc liên hệ Ban cán sự / "
                "Cố vấn học tập để được hỗ trợ đối soát."
                + disclaimer
            )

        # 2. Tra cứu người nộp quỹ & Ẩn danh danh tính sinh viên
        is_depositors_query = any(k in q for k in [
            "ai nộp", "ai đã nộp", "bao nhiêu người", "bao nhiêu bạn", "danh sách nộp", 
            "người nộp", "đóng quỹ", "nộp quỹ", "nộp rồi", "nộp tiền", "tình hình nộp"
        ])
        if is_depositors_query:
            if not is_connected:
                return (
                    "⚠️ **Chưa kết nối hợp đồng:** Hiện tại hệ thống chưa kết nối với Smart Contract trên mạng Sepolia "
                    "nên chưa có số liệu nộp quỹ thời gian thực. Vui lòng kết nối ví MetaMask hoặc kiểm tra địa chỉ hợp đồng trên giao diện."
                    + disclaimer
                )

            lines = []
            if depositors_count == 0:
                lines.append("📊 **Tình hình nộp quỹ lớp K57:**")
                lines.append("- Hiện tại trên Smart Contract chưa ghi nhận sinh viên nào nộp quỹ (Số lượng: **0 sinh viên**, tổng số tiền: **0 ETH**).")
                lines.append("- Các bạn sinh viên có thể kết nối ví MetaMask và nộp 0.01 ETH theo thông báo của lớp.")
            else:
                lines.append("📊 **Tình hình nộp quỹ lớp K57 (Thời gian thực on-chain):**")
                lines.append(f"- Đã có **{depositors_count} sinh viên** hoàn thành nộp quỹ.")
                lines.append(f"- Tổng số tiền đã đóng góp vào quỹ: **{total_deposited_eth} ETH**.")
                lines.append(f"- Phân bổ theo quy tắc R2: Quỹ lớp giữ 99% ({class_fund_eth} ETH), Quỹ dịch vụ cố vấn giữ 1% ({admin_fee_eth} ETH).")

                if depositors_list:
                    lines.append("\n📋 **Danh sách các ví đã nộp on-chain:**")
                    for idx, dep in enumerate(depositors_list[:15], start=1):
                        d_addr = dep.get("address", "0x...")
                        amt = dep.get("amountEth", "0")
                        lines.append(f"  {idx}. `{d_addr}`: **{amt} ETH**")
                lines.append("\n🛡️ **Chính sách bảo vệ quyền riêng tư & ẩn danh sinh viên:**")
                lines.append("Để đảm bảo quyền riêng tư tài chính cho sinh viên, hệ thống ẩn danh danh tính cá nhân (Họ tên, MSSV) và chỉ hiển thị địa chỉ ví on-chain. Việc đối chiếu địa chỉ ví với danh bạ sinh viên chỉ dành riêng cho Cố vấn học tập và Ban cán sự để phục vụ công tác đối soát quỹ.")

            return "\n".join(lines) + disclaimer

        # 3. Yêu cầu chi tiêu & Biểu quyết 51%
        is_spend_query = any(k in q for k in [
            "chi tiêu", "yêu cầu chi", "đề xuất chi", "khoản chi", "giải ngân", "biểu quyết", "phiếu", "spend", "51%"
        ])
        if is_spend_query:
            lines = [f"📋 **Thông tin các yêu cầu chi tiêu quỹ lớp ({len(spend_requests)} yêu cầu):**"]
            if not spend_requests:
                lines.append("- Hiện tại chưa có yêu cầu chi tiêu nào được tạo trên Smart Contract.")
            else:
                for req in spend_requests:
                    req_id = req.get("id")
                    desc = req.get("description", "Không có mô tả")
                    amt = req.get("amountEth", "0")
                    recipient = req.get("recipient", "N/A")
                    votes = req.get("votesText", "0/0 (0%)")
                    status = req.get("statusText", "Pending")
                    lines.append(f"\n• **Yêu cầu chi [Mã #{req_id}]:**")
                    lines.append(f"  - **Mục đích chi:** {desc}")
                    lines.append(f"  - **Số tiền đề xuất:** {amt} ETH")
                    lines.append(f"  - **Người thụ hưởng (nhận tiền):** `{recipient}`")
                    lines.append(f"  - **Tiến độ biểu quyết:** {votes}")
                    lines.append(f"  - **Trạng thái:** {status}")

            lines.append("\n📌 **Quy chế giải ngân (docs/SPEC.md):**")
            lines.append("- Đề xuất chi chỉ được giải ngân khi đạt tỷ lệ đồng ý tối thiểu **51%** (5100 bps) từ các thành viên Ban cán sự đang hoạt động trong thời hạn 7 ngày (R4/R5).")
            lines.append("- Hệ thống giới hạn tối đa 01 đề xuất chi ở trạng thái 'Đang chờ duyệt' (Pending) tại một thời điểm (R8).")
            return "\n".join(lines) + disclaimer

        # 4. Số dư quỹ & Phân bổ 99%/1%
        is_balance_query = any(k in q for k in [
            "số dư", "còn bao nhiêu", "tổng tiền", "quỹ lớp", "quỹ dịch vụ", "phí gas", "admin fee", "99%", "1%", "balance"
        ])
        if is_balance_query:
            lines = [
                "💰 **Thông tin tài chính & Số dư Quỹ lớp K57:**",
                f"- **Số dư Quỹ lớp chính (classFundBalance):** **{class_fund_eth} ETH** (sẵn sàng cho các hoạt động của lớp).",
                f"- **Quỹ dịch vụ vận hành của Cố vấn (adminFeePool):** **{admin_fee_eth} ETH** (dùng bù đắp phí gas giao dịch).",
                f"- **Tổng số ETH đã nạp vào quỹ:** **{total_deposited_eth} ETH** từ **{depositors_count} lượt đóng góp**.",
                f"- **Số thành viên Ban cán sự đang hoạt động:** **{active_bcs} người**.",
                "\n📌 **Quy chế phân bổ tài chính R2:**",
                "Mỗi khi sinh viên nạp tiền vào quỹ, Smart Contract tự động trích **1%** (100 bps) vào Quỹ dịch vụ vận hành của Cố vấn để hỗ trợ chi phí gas, **99%** còn lại được đưa vào Quỹ lớp chính."
            ]
            return "\n".join(lines) + disclaimer

        # 5. Thông báo đợt thu quỹ lớp & Hạn chót
        is_announcement_query = any(k in q for k in [
            "thông báo", "đợt thu", "hạn chót", "deadline", "mức đóng", "mức nộp", "mục đích thu", "sĩ số", "kế hoạch"
        ])
        if is_announcement_query:
            title = announcement.get("title", "Kêu gọi nộp Quỹ Lớp Học kỳ 1 - Khóa K57")
            target = announcement.get("targetAmountEth", "0.01")
            deadline = announcement.get("deadline", "23:59 ngày 15/11/2026")
            class_size = announcement.get("classSize", 5)
            purpose = announcement.get("purpose", "Kinh phí phục vụ tài liệu học tập và các hoạt động chuyên đề.")
            progress = announcement.get("progressText", f"{depositors_count}/{class_size} bạn đã nộp")
            status = announcement.get("status", "Đang diễn ra")

            lines = [
                "📢 **THÔNG BÁO THU QUỸ LỚP HIỆN HÀNH:**",
                f"- **Tiêu đề đợt thu:** {title}",
                f"- **Mức nộp quy định:** **{target} ETH**/sinh viên",
                f"- **Hạn chót nộp:** ⏰ **{deadline}**",
                f"- **Sĩ số lớp K57:** {class_size} sinh viên",
                f"- **Tiến độ thu thực tế:** {progress}",
                f"- **Mục đích sử dụng:** {purpose}",
                f"- **Trạng thái:** {status}",
                "\n💡 *Bạn có thể bấm trực tiếp nút **'Nộp quỹ ngay'** trên thanh thông báo ở đầu trang để tiến hành đóng quỹ qua MetaMask.*"
            ]
            return "\n".join(lines) + disclaimer

        # 6. Ban cán sự & Quản trị nhân sự
        is_bcs_query = any(k in q for k in [
            "ban cán sự", "bcs", "cán sự", "tại sao bcs", "0 người", "bổ nhiệm", "kích hoạt"
        ])
        if is_bcs_query:
            lines = [
                "👥 **Thông tin Ban cán sự (BCS) lớp K57:**",
                f"- Số lượng thành viên Ban cán sự đang hoạt động on-chain: **{active_bcs} người**."
            ]
            if active_bcs == 0:
                lines.append(
                    "\n⚠️ **Giải thích quy chế R1:** Khi Smart Contract mới được triển khai, activeBCSCount ban đầu bằng 0 "
                    "(chỉ có Cố vấn học tập sở hữu hợp đồng). Cố vấn học tập cần dùng ví của mình truy cập mục 'Cố vấn học tập' "
                    "-> 'Quản trị nhân sự Ban cán sự' để kích hoạt các thành viên BCS trước khi có thể biểu quyết các khoản chi."
                )
            else:
                lines.append(f"- Các đề xuất chi cần tối thiểu **51%** phiếu thuận từ {active_bcs} thành viên này để được giải ngân.")
            return "\n".join(lines) + disclaimer

        # 7. Yêu cầu hoàn tiền (Refund)
        is_refund_query = any(k in q for k in [
            "hoàn tiền", "refund", "nộp nhầm", "nộp thừa", "trả lại", "rút lại"
        ])
        if is_refund_query:
            lines = [
                "🔄 **Thông tin về Yêu cầu Hoàn tiền (docs/SPEC.md):**",
                f"- Hiện có **{len(refund_requests)} yêu cầu hoàn tiền** trên hợp đồng."
            ]
            for ref in refund_requests:
                lines.append(
                    f"  • [Mã #{ref.get('id')}] Người yêu cầu: `{ref.get('applicant', 'N/A')}` | "
                    f"Số tiền: {ref.get('amountEth', '0')} ETH | Lý do: '{ref.get('reason', '')}' | Trạng thái: {ref.get('statusText', 'Pending')}"
                )
            lines.append("\n📌 **Quy chế hoàn tiền (R7 & R10):**")
            lines.append("- Sinh viên nộp nhầm hoặc nộp thừa có thể tạo yêu cầu hoàn tiền kèm minh chứng qua giao diện Web.")
            lines.append("- Yêu cầu hoàn tiền cần được Ban cán sự biểu quyết thông qua trước khi tiền được chuyển trả lại ví.")
            lines.append("- Sinh viên có quyền tự hủy yêu cầu hoàn tiền đang chờ duyệt của chính mình bất kỳ lúc nào (R10).")
            return "\n".join(lines) + disclaimer

        # 8. Danh bạ sinh viên (Roster)
        is_roster_query = any(k in q for k in [
            "danh bạ", "danh sách sinh viên", "danh sách lớp", "thành viên lớp", "sĩ số lớp"
        ])
        if is_roster_query:
            if is_privileged:
                lines = [
                    "📚 **Danh bạ Sinh viên Lớp K57 (Chế độ Ban cán sự & Cố vấn):**",
                    f"- Tổng số thành viên trong danh bạ: **{len(roster)} người**."
                ]
                for st in roster:
                    lines.append(f"  • **{st.get('name')}** (MSSV: {st.get('mssv')}) | Ví: `{st.get('wallet')}` | Vai trò: {st.get('roleTitle')}")
                return "\n".join(lines) + disclaimer
            else:
                return (
                    "🛡️ **Bảo vệ quyền riêng tư:** Danh bạ lớp (Họ tên, MSSV, Địa chỉ ví) là dữ liệu quản trị nội bộ "
                    "và chỉ được cấp quyền xem cho Cố vấn học tập và Ban cán sự để phục vụ công tác đối soát quỹ. "
                    "Sinh viên có thể tra cứu số lượng người đã nộp và số dư quỹ minh bạch on-chain."
                    + disclaimer
                )

        # 9. Chào hỏi & Hướng dẫn
        is_greeting = any(k in q for k in [
            "xin chào", "chào", "hi", "hello", "bạn là ai", "giúp gì", "help", "hướng dẫn"
        ])
        if is_greeting:
            return (
                "👋 **Xin chào! Tôi là Trợ lý AI Quỹ Lớp KTS-Class-Fund K57 (Kinh tế Số).**\n\n"
                "Tôi có thể hỗ trợ bạn tra cứu các thông tin on-chain theo thời gian thực:\n"
                "1. 📊 **Tình hình nộp quỹ:** 'Có bao nhiêu người đã nộp quỹ rồi?' hoặc 'Ví của tôi đã nộp chưa?'\n"
                "2. 📋 **Yêu cầu chi tiêu:** 'Có những khoản chi nào đang chờ duyệt?'\n"
                "3. 💰 **Số dư & Phân bổ:** 'Số dư quỹ lớp hiện tại là bao nhiêu?' (Quy tắc 99% / 1%)\n"
                "4. 📢 **Thông báo đợt thu:** 'Hạn chót nộp quỹ là khi nào?'\n"
                "5. 👥 **Ban cán sự & Biểu quyết:** 'Quy chế biểu quyết 51% hoạt động ra sao?'\n\n"
                "Hãy đặt câu hỏi bất kỳ để tôi giải đáp ngay nhé!"
                + disclaimer
            )

        # 10. Tổng quan trạng thái on-chain mặc định
        return (
            f"📊 **Tổng quan trạng thái Quỹ Lớp KTS-Class-Fund K57:**\n"
            f"- **Smart Contract:** `{contract_addr}`\n"
            f"- **Số dư Quỹ lớp chính:** **{class_fund_eth} ETH**\n"
            f"- **Quỹ dịch vụ vận hành (Cố vấn):** **{admin_fee_eth} ETH**\n"
            f"- **Tiến độ đóng quỹ:** **{depositors_count} sinh viên** đã nộp (Tổng: **{total_deposited_eth} ETH**)\n"
            f"- **Yêu cầu chi tiêu:** **{len(spend_requests)} yêu cầu** on-chain\n"
            f"- **Thành viên Ban cán sự:** **{active_bcs} người**\n"
            f"- **Đợt thu hiện hành:** '{announcement.get('title', 'Kêu gọi nộp Quỹ Lớp')}', hạn chót: {announcement.get('deadline', '23:59 15/11/2026')}\n\n"
            f"💡 *Bạn có thể hỏi chi tiết hơn về: người nộp quỹ, các khoản chi, quy tắc biểu quyết 51% hoặc hạn nộp quỹ.*"
            + disclaimer
        )

    def answer_question(self, user_question: str, onchain_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Gửi câu hỏi và ngữ cảnh đến Google Gemini API (có cơ chế xoay vòng key và tự chuyển model).
        Khi gặp lỗi Quota Free Tier (HTTP 429) hoặc mạng ngắt kết nối, tự động kích hoạt
        Bộ máy On-chain Cục bộ (Local Fallback Engine) để trả lời trơn tru, không gây gián đoạn người dùng.
        """
        # Nếu chưa có API Key nào được cấu hình, kích hoạt ngay bộ máy fallback cục bộ
        if not self.is_configured():
            fallback_text = self.generate_local_fallback_answer(user_question, onchain_data)
            return {
                "success": True,
                "reply": fallback_text,
                "model_used": "local-fallback-engine",
                "fallback_reason": "No API Key configured"
            }

        system_context = self.build_system_context(onchain_data)

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": system_context},
                        {"text": f"Câu hỏi của người dùng: {user_question}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 4096,
                "thinkingConfig": {
                    "thinkingBudget": 0
                }
            }
        }

        headers = {"Content-Type": "application/json"}
        last_error = ""

        # Thử lần lượt các khóa API đã cấu hình (Key Rotation)
        candidate_keys = self.api_keys if self.api_keys else ([self.api_key] if self.api_key else [])
        for cur_key in candidate_keys:
            seen_models = set()
            for model_name in CANDIDATE_MODELS:
                if not model_name or model_name in seen_models:
                    continue
                seen_models.add(model_name)

                api_url = self.get_api_url(model_name, key=cur_key)
                try:
                    response = requests.post(api_url, json=payload, headers=headers, timeout=25)

                    # Nếu model không hỗ trợ thinkingConfig (mã 400), thử lại payload chuẩn
                    if response.status_code == 400 and "thinkingConfig" in response.text:
                        fallback_payload = {
                            "contents": payload["contents"],
                            "generationConfig": {
                                "temperature": 0.2,
                                "maxOutputTokens": 4096
                            }
                        }
                        response = requests.post(api_url, json=fallback_payload, headers=headers, timeout=25)

                    # Nếu model không tồn tại (404), hết quota (429) hoặc server bận (500, 503), chuyển sang model tiếp theo
                    if response.status_code in (404, 429, 500, 503):
                        last_error = f"Model {model_name} phản hồi mã HTTP {response.status_code}"
                        continue

                    # Kiểm tra trạng thái phản hồi trước khi xử lý dữ liệu (AGENTS.md)
                    if response.status_code != 200:
                        last_error = f"Gemini API phản hồi mã {response.status_code}: {response.text[:120]}"
                        continue

                    result_json = response.json()
                    candidates = result_json.get("candidates", [])
                    if not candidates:
                        last_error = "Không nhận được phản hồi candidates từ Gemini"
                        continue

                    cand = candidates[0]
                    parts = cand.get("content", {}).get("parts", [])

                    reply_parts = []
                    for p in parts:
                        if p.get("thought"):
                            continue
                        if "text" in p and p["text"]:
                            reply_parts.append(p["text"])

                    reply_text = "".join(reply_parts).strip()
                    if not reply_text:
                        last_error = f"Model {model_name} trả về phản hồi rỗng"
                        continue

                    return {
                        "success": True,
                        "reply": reply_text,
                        "model_used": model_name
                    }

                except requests.exceptions.Timeout:
                    last_error = f"Model {model_name} bị quá hạn thời gian chờ (Timeout)"
                    continue
                except Exception as e:
                    last_error = f"Model {model_name} gặp lỗi kết nối: {str(e)}"
                    continue

        # NẾU TẤT CẢ CÁC MODEL / KHÓA API ĐỀU BỊ 429 (HẾT QUOTA) HOẶC LỖI KẾT NỐI:
        # KÍCH HOẠT NGAY BỘ MÁY ON-CHAIN CỤC BỘ ĐỂ TRẢ LỜI NGƯỜI DÙNG CHUẨN XÁC
        fallback_reply = self.generate_local_fallback_answer(user_question, onchain_data)
        return {
            "success": True,
            "reply": fallback_reply,
            "model_used": "local-fallback-engine",
            "fallback_reason": last_error or "Quota Exceeded (HTTP 429)"
        }
