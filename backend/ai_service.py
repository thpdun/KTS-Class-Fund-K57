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
from typing import Dict, Any, Optional
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


CANDIDATE_MODELS = [
    os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-flash-latest"
]


class AIAssistantService:
    def __init__(self, api_key: Optional[str] = None):
        # Đọc khóa API từ biến môi trường nếu không được truyền trực tiếp
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

    def get_api_url(self, model_name: str) -> str:
        return f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"

    def is_configured(self) -> bool:
        """Kiểm tra xem API Key đã được cấu hình chưa."""
        return bool(self.api_key and len(self.api_key.strip()) > 10)

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
                context_parts.append(f"- Mục tiêu sĩ số: {announcement.get('classSize', 50)} sinh viên")
                context_parts.append(f"- Mục đích thu quỹ: {announcement.get('purpose', '')}")
                context_parts.append(f"- Tiến độ thu thực tế: {announcement.get('progressText', '0%')}")
                context_parts.append(f"- Trạng thái đợt thu: {announcement.get('status', 'Đang diễn ra')}")

        context_parts.append("\n--- HƯỚNG DẪN BẮT BUỘC KHI TRẢ LỜI ---")
        context_parts.append("1. KHI ĐƯỢC HỎI VỀ SỐ LƯỢNG NGƯỜI NỘP QUỸ:")
        context_parts.append("   - Trả lời rõ ràng, dứt khoát số lượng người đã nộp ({depositors_count} sinh viên) với tổng số tiền đã nộp ({total_deposited_eth} ETH).")
        context_parts.append("   - Nêu rõ số dư Quỹ lớp (99%) và Quỹ dịch vụ vận hành của Cố vấn (1%).")
        context_parts.append("   - Nếu {depositors_count} >= 1 hoặc tổng tiền > 0, tuyệt đối KHÔNG nói 'chưa có ai nộp'.")
        context_parts.append("2. KHI ĐƯỢC HỎI VỀ CÁC YÊU CẦU CHI TIÊU:")
        context_parts.append("   - PHẢI LIỆT KÊ ĐẦY ĐỦ TẤT CẢ CÁC YÊU CẦU CHI TIÊU VÀ TRÌNH BÀY RÕ RÀNG CHI TIẾT TỪNG MỤC:")
        context_parts.append("     • Mã yêu cầu: #[ID]")
        context_parts.append("     • Mục đích chi tiêu: [Mục đích]")
        context_parts.append("     • Số tiền đề xuất: [Số tiền] ETH")
        context_parts.append("     • Người nhận (thụ hưởng): [Địa chỉ ví]")
        context_parts.append("     • Tiến độ biểu quyết: [Số phiếu / Tổng số BCS] ([Tỷ lệ]%)")
        context_parts.append("     • Trạng thái hiện tại: [Trạng thái]")
        context_parts.append("     • Quy chế giải ngân: Nhắc lại điều kiện cần tối thiểu 51% phiếu thuận từ Ban cán sự trong 7 ngày (R4/R5).")
        context_parts.append("3. TUYỆT ĐỐI KHÔNG ĐƯỢC LẶP LẠI: Mỗi mã yêu cầu chỉ xuất hiện đúng 1 lần duy nhất trong câu trả lời. Không được in trùng lặp.")
        context_parts.append("4. KHI ĐƯỢC HỎI VỀ SỐ LƯỢNG BAN CÁN SỰ (BCS) HOẶC TẠI SAO BCS LÀ 0:")
        context_parts.append("   - Trả lời rõ ràng số lượng thành viên Ban cán sự đang hoạt động on-chain.")
        context_parts.append("   - Nếu số lượng là 0, giải thích rõ nguyên nhân: Hợp đồng ProjectCore khi mới deploy ban đầu có activeBCSCount = 0 (chỉ có ví Cố vấn học tập). Cố vấn học tập cần dùng ví của mình truy cập ô 'Cố vấn học tập' -> 'Quản trị nhân sự Ban cán sự' để kích hoạt thành viên (R1) trước khi có thể biểu quyết các khoản chi.")
        context_parts.append("5. KHI ĐƯỢC HỎI VỀ THÔNG BÁO LỚP, HẠN NỘP QUỸ, MỨC ĐÓNG HOẶC TIẾN ĐỘ THU QUỸ:")
        context_parts.append("   - Trích xuất chính xác tiêu đề đợt thu, mức tiền quy định (ETH), hạn chót nộp, mục đích thu quỹ và tiến độ thực tế (số bạn đã nộp/sĩ số).")
        context_parts.append("   - Thân thiện nhắc nhở sinh viên có thể bấm nút 'Nộp quỹ ngay' trên thanh thông báo ở giao diện để hoàn thành đóng góp.")
        return "\n".join(context_parts)

    def answer_question(self, user_question: str, onchain_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Gửi câu hỏi và ngữ cảnh đến Google Gemini API, kiểm tra mã phản hồi HTTP trước khi xử lý.
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "API Key của Gemini chưa được cấu hình. Vui lòng thiết lập biến môi trường GEMINI_API_KEY trong tệp .env."
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

        # Thử lần lượt các model tương thích (tự động chuyển model nếu gặp 404, 429 Quota Exceeded, 500, 503)
        seen_models = set()
        for model_name in CANDIDATE_MODELS:
            if not model_name or model_name in seen_models:
                continue
            seen_models.add(model_name)

            api_url = self.get_api_url(model_name)
            try:
                response = requests.post(api_url, json=payload, headers=headers, timeout=25)

                # Nếu model không hỗ trợ thinkingConfig (mã 400), thử lại payload chuẩn không có thinkingConfig
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

                # Quy tắc AGENTS.md: Kiểm tra trạng thái phản hồi trước khi xử lý dữ liệu
                if response.status_code != 200:
                    error_msg = f"Gemini API phản hồi lỗi (Mã {response.status_code}): {response.text}"
                    return {
                        "success": False,
                        "error": error_msg
                    }

                result_json = response.json()
                candidates = result_json.get("candidates", [])
                if not candidates:
                    return {
                        "success": False,
                        "error": "Không nhận được phản hồi phù hợp từ AI."
                    }

                cand = candidates[0]
                parts = cand.get("content", {}).get("parts", [])

                # Ghép toàn bộ các phân đoạn (parts) để tránh bị cắt cụt văn bản khi Gemini chia nhiều đoạn
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

        if "429" in last_error:
            return {
                "success": False,
                "error": f"Hạn mức lượt gọi (Quota Free Tier) của Google AI Studio trong ngày đã đạt giới hạn ({last_error}). Bạn có thể bổ sung API Key mới trong .env hoặc thử lại sau khi Google làm mới quota."
            }

        return {
            "success": False,
            "error": f"Tất cả các model Gemini đều không khả dụng: {last_error}. Vui lòng kiểm tra lại tài khoản Google AI Studio."
        }
