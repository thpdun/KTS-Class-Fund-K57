#!/usr/bin/env python3
"""
Máy chủ Backend Python trung gian cho Trợ lý AI Quỹ Lớp (KTS-Class-Fund)
Tuân thủ quy ước AGENTS.md:
- Python 3.10+
- Không ghi khóa API trong mã nguồn; đọc từ biến môi trường hoặc .env
- Kiểm tra trạng thái phản hồi trước khi xử lý dữ liệu
- Đổi wei sang ETH trước khi hiển thị
"""

import os
import sys
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from typing import Optional

# Đảm bảo in tiếng Việt chuẩn trên Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def load_dotenv(env_path: Path):
    if not env_path.exists():
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val


root_dir = Path(__file__).parent.parent
load_dotenv(root_dir / ".env")
load_dotenv(Path(__file__).parent / ".env")

# Import module nghiệp vụ AI
try:
    from backend.ai_service import AIAssistantService
except ImportError:
    from ai_service import AIAssistantService

HOST = "0.0.0.0"
PORT = 8000


ANNOUNCEMENT_FILE = Path(__file__).parent / "announcements.json"
ROSTER_FILE = Path(__file__).parent / "class_roster.json"


def load_roster() -> list:
    if ROSTER_FILE.exists():
        try:
            with open(ROSTER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_roster(data: list):
    with open(ROSTER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_student_by_wallet(wallet: str) -> Optional[dict]:
    if not wallet:
        return None
    w = wallet.strip().lower()
    for s in load_roster():
        if s.get("wallet", "").strip().lower() == w:
            return s
    return None


def is_authorized_advisor(address: str, is_advisor: bool = False) -> bool:
    """Kiểm tra quyền CỐ VẤN HỌC TẬP (Chỉ Cố vấn học tập mới có quyền thêm/chỉnh sửa danh bạ)"""
    if is_advisor:
        return True
    if not address or address.lower() in ["sinh viên", "guest", "anonymous", "null", "undefined"]:
        return False
    advisor_env = os.environ.get("ADVISOR_ADDRESS", "").strip().lower()
    if advisor_env and address.strip().lower() == advisor_env:
        return True
    s = find_student_by_wallet(address)
    if s and s.get("role") == "advisor":
        return True
    return False


def is_authorized_viewer(address: str, is_bcs: bool = False, is_advisor: bool = False) -> bool:
    """Kiểm tra quyền xem danh bạ & thông báo (Cố vấn học tập và Ban cán sự có quyền xem)"""
    if is_authorized_advisor(address, is_advisor=is_advisor):
        return True
    if is_bcs:
        return True
    if not address or address.lower() in ["sinh viên", "guest", "anonymous", "null", "undefined"]:
        return False
    s = find_student_by_wallet(address)
    if s and s.get("role") in ["bcs", "advisor"]:
        return True
    return False


def load_announcement() -> dict:
    roster_len = len(load_roster())
    if ANNOUNCEMENT_FILE.exists():
        try:
            with open(ANNOUNCEMENT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Sĩ số lớp tự động bằng số người trong danh sách lớp
                data["classSize"] = roster_len if roster_len > 0 else int(data.get("classSize", 5))
                return data
        except Exception:
            pass
    return {
        "title": "Kêu gọi nộp Quỹ Lớp Học kỳ 1 - Khóa K57 Kinh tế Số",
        "targetAmountEth": "0.01",
        "deadline": "23:59 ngày 15/11/2026",
        "classSize": roster_len if roster_len > 0 else 5,
        "purpose": "Kinh phí phục vụ tài liệu học tập, các buổi sinh hoạt chuyên đề ngoại khóa và quỹ dự phòng hỗ trợ sinh viên K57.",
        "status": "Đang diễn ra",
        "updatedAt": None,
        "updatedBy": None
    }


def save_announcement(data: dict):
    # Sĩ số lớp tự động bằng số người trong danh sách lớp
    roster_len = len(load_roster())
    if roster_len > 0:
        data["classSize"] = roster_len
    with open(ANNOUNCEMENT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class AIChatRequestHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _send_json(self, status_code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/api/status" or path == "/":
            ai_service = AIAssistantService()
            status_data = {
                "service": "KTS-Class-Fund AI Backend",
                "status": "online",
                "is_configured": ai_service.is_configured(),
                "note": "AI Key đã sẵn sàng" if ai_service.is_configured() else "Chưa cấu hình GEMINI_API_KEY trong .env"
            }
            self._send_json(200, status_data)
        elif path == "/api/announcement":
            data = load_announcement()
            self._send_json(200, {"success": True, "announcement": data})
        elif path == "/api/roster":
            signer = qs.get("address", [""])[0]
            is_bcs = qs.get("isBcs", ["0"])[0] in ["1", "true", "True"]
            is_advisor = qs.get("isAdvisor", ["0"])[0] in ["1", "true", "True"]
            if not is_authorized_viewer(signer, is_bcs=is_bcs, is_advisor=is_advisor):
                self._send_json(403, {
                    "success": False,
                    "error": "Truy cập bị từ chối: Danh sách sinh viên chỉ dành riêng cho Cố vấn học tập và Ban cán sự."
                })
                return
            roster = load_roster()
            self._send_json(200, {"success": True, "count": len(roster), "roster": roster})
        elif path == "/api/roster/check":
            addr = qs.get("address", [""])[0]
            student = find_student_by_wallet(addr)
            self._send_json(200, {
                "success": True,
                "isMember": student is not None,
                "student": student
            })
        else:
            self._send_json(404, {"error": "Not Found"})

    def do_POST(self):
        if self.path == "/api/announcement":
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self._send_json(400, {"success": False, "error": "Thiếu dữ liệu thông báo."})
                return

            try:
                raw_body = self.rfile.read(content_length).decode("utf-8")
                req_data = json.loads(raw_body)
            except Exception as e:
                self._send_json(400, {"success": False, "error": f"Dữ liệu JSON không hợp lệ: {str(e)}"})
                return

            title = str(req_data.get("title", "")).strip()
            target_amount = str(req_data.get("targetAmountEth", "")).strip()
            if not title or not target_amount:
                self._send_json(400, {"success": False, "error": "Tiêu đề và mức đóng không được để trống."})
                return

            try:
                amount_val = float(target_amount)
                if amount_val <= 0:
                    self._send_json(400, {"success": False, "error": "Mức đóng phải lớn hơn 0 ETH."})
                    return
            except ValueError:
                self._send_json(400, {"success": False, "error": "Mức đóng không hợp lệ."})
                return

            signer = str(req_data.get("signerAddress", "")).strip()
            is_bcs = bool(req_data.get("isBcsMember", False))
            is_advisor = bool(req_data.get("isAdvisor", False))
            if not is_authorized_viewer(signer, is_bcs=is_bcs, is_advisor=is_advisor):
                self._send_json(403, {"success": False, "error": "Truy cập bị từ chối: Chỉ tài khoản Ban cán sự hoặc Cố vấn học tập mới có quyền cập nhật thông báo."})
                return

            roster_len = len(load_roster())
            actual_class_size = roster_len if roster_len > 0 else int(req_data.get("classSize", 5))
            announcement_data = {
                "title": title,
                "targetAmountEth": target_amount,
                "deadline": str(req_data.get("deadline", "Chưa xác định")).strip(),
                "classSize": actual_class_size,
                "purpose": str(req_data.get("purpose", "")).strip(),
                "status": str(req_data.get("status", "Đang diễn ra")),
                "updatedBy": signer,
                "updatedAt": req_data.get("updatedAt")
            }

            save_announcement(announcement_data)
            self._send_json(200, {"success": True, "announcement": announcement_data})

        elif self.path == "/api/roster/register":
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self._send_json(400, {"success": False, "error": "Thiếu dữ liệu đăng ký."})
                return

            try:
                raw_body = self.rfile.read(content_length).decode("utf-8")
                req_data = json.loads(raw_body)
            except Exception as e:
                self._send_json(400, {"success": False, "error": f"Dữ liệu JSON không hợp lệ: {str(e)}"})
                return

            signer = str(req_data.get("signerAddress", "")).strip()
            is_advisor = bool(req_data.get("isAdvisor", False))
            if not is_authorized_advisor(signer, is_advisor=is_advisor):
                self._send_json(403, {"success": False, "error": "Truy cập bị từ chối: Chỉ Cố vấn học tập mới có quyền thêm/chỉnh sửa danh bạ sinh viên. Ban cán sự chỉ có quyền xem danh sách."})
                return

            mssv = str(req_data.get("mssv", "")).strip()
            name = str(req_data.get("name", "")).strip()
            wallet = str(req_data.get("wallet", "")).strip()
            role_raw = str(req_data.get("role", "student")).strip()
            original_mssv = str(req_data.get("originalMssv", "")).strip()

            # Vai trò chỉ có 2 loại duy nhất: "bcs" (Ban cán sự) hoặc "student" (Sinh viên)
            role = "bcs" if role_raw == "bcs" else "student"
            role_title = "Ban cán sự" if role == "bcs" else "Sinh viên"

            if not mssv or not name or not wallet:
                self._send_json(400, {"success": False, "error": "MSSV, Họ tên và Địa chỉ ví không được để trống."})
                return

            if not wallet.startswith("0x") or len(wallet) != 42:
                self._send_json(400, {"success": False, "error": "Địa chỉ ví Ethereum không hợp lệ (cần đúng 42 ký tự, bắt đầu bằng 0x)."})
                return

            roster = load_roster()
            # Tìm sinh viên để cập nhật in-place:
            # 1. Khớp originalMssv (nếu đang ở chế độ chỉnh sửa)
            # 2. Hoặc khớp MSSV hiện tại
            match_idx = None
            for idx, item in enumerate(roster):
                if original_mssv and item.get("mssv") == original_mssv:
                    match_idx = idx
                    break
                if item.get("mssv") == mssv:
                    match_idx = idx
                    break

            if match_idx is not None:
                # Cập nhật thông tin in-place, không tạo sinh viên mới
                roster[match_idx]["mssv"] = mssv
                roster[match_idx]["name"] = name
                roster[match_idx]["wallet"] = wallet
                roster[match_idx]["role"] = role
                roster[match_idx]["roleTitle"] = role_title
                updated = True
            else:
                # Nếu không trùng MSSV, kiểm tra xem địa chỉ ví có đang gắn với ai khác không để cập nhật
                for item in roster:
                    if item.get("wallet", "").lower() == wallet.lower():
                        item["mssv"] = mssv
                        item["name"] = name
                        item["role"] = role
                        item["roleTitle"] = role_title
                        updated = True
                        break
                else:
                    # Thêm sinh viên mới
                    roster.append({
                        "mssv": mssv,
                        "name": name,
                        "wallet": wallet,
                        "role": role,
                        "roleTitle": role_title
                    })
                    updated = False

            save_roster(roster)
            self._send_json(200, {
                "success": True,
                "message": f"Đã {'cập nhật thông tin' if updated else 'thêm mới'} sinh viên {name} ({mssv}) thành công.",
                "roster": roster
            })

        elif self.path == "/api/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self._send_json(400, {"success": False, "error": "Thiếu dữ liệu yêu cầu."})
                return

            try:
                raw_body = self.rfile.read(content_length).decode("utf-8")
                req_data = json.loads(raw_body)
            except Exception as e:
                self._send_json(400, {"success": False, "error": f"Dữ liệu JSON không hợp lệ: {str(e)}"})
                return

            question = req_data.get("question", "").strip()
            if not question:
                self._send_json(400, {"success": False, "error": "Vui lòng nhập câu hỏi."})
                return

            onchain_data = req_data.get("onchain_data", {})
            signer = str(req_data.get("signerAddress") or onchain_data.get("userAddress", "")).strip()
            is_bcs = bool(req_data.get("isBcsMember", False) or onchain_data.get("isBcsMember", False))
            is_advisor = bool(req_data.get("isAdvisor", False) or onchain_data.get("isAdvisor", False))

            is_auth = is_authorized_viewer(signer, is_bcs=is_bcs, is_advisor=is_advisor)

            if is_auth:
                # Cố vấn học tập hoặc Ban cán sự có quyền xem danh bạ nội bộ để đối soát
                onchain_data["viewerRole"] = "advisor" if is_authorized_advisor(signer, is_advisor) else "bcs"
                if "roster" not in onchain_data or not onchain_data["roster"]:
                    onchain_data["roster"] = load_roster()
            else:
                # Sinh viên hoặc khách vãng lai: BẢO VỆ TUYỆT ĐỐI DANH TÍNH
                # 1. Xoá bỏ hoàn toàn danh bạ lớp khỏi ngữ cảnh AI
                onchain_data["viewerRole"] = "student"
                onchain_data["roster"] = []
                # 2. Xoá sạch mọi trường name, mssv trong depositorsList
                if "depositorsList" in onchain_data and isinstance(onchain_data["depositorsList"], list):
                    clean_deps = []
                    for dep in onchain_data["depositorsList"]:
                        clean_deps.append({
                            "address": dep.get("fullAddress") or dep.get("address") or "0x...",
                            "amountEth": dep.get("amountEth", "0")
                        })
                    onchain_data["depositorsList"] = clean_deps

            api_key_override = req_data.get("api_key")
            ai_service = AIAssistantService(api_key=api_key_override)
            result = ai_service.answer_question(question, onchain_data)

            if result.get("model_used") == "local-fallback-engine":
                sys.stdout.write(f"[AI Backend Info] Kích hoạt Local Fallback Engine do: {result.get('fallback_reason')}\n")
                sys.stdout.flush()

            status_code = 200 if result.get("success") else 500
            if not result.get("success"):
                sys.stdout.write(f"[AI Backend Error] {result.get('error')}\n")
                sys.stdout.flush()
            self._send_json(status_code, result)
        else:
            self._send_json(404, {"error": "Not Found"})

    def log_message(self, format, *args):
        sys.stdout.write(f"[AI Backend] {self.address_string()} - {format % args}\n")
        sys.stdout.flush()


def run_server():
    server_address = (HOST, PORT)
    httpd = HTTPServer(server_address, AIChatRequestHandler)
    ai_service = AIAssistantService()
    print("=" * 60, flush=True)
    print(f"🚀 KTS-Class-Fund AI Backend đang chạy tại http://localhost:{PORT}", flush=True)
    print(f"   Trạng thái Gemini API Key: {'ĐÃ CẤU HÌNH' if ai_service.is_configured() else 'CHƯA CẤU HÌNH (Hãy tạo file .env)'}", flush=True)
    print(f"   Endpoint hỏi đáp: POST http://localhost:{PORT}/api/chat", flush=True)
    print(f"   Endpoint trạng thái: GET http://localhost:{PORT}/api/status", flush=True)
    print("=" * 60, flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nĐang dừng máy chủ...", flush=True)
        httpd.server_close()


if __name__ == "__main__":
    run_server()
