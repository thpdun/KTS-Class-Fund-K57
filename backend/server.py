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
        if self.path == "/api/status" or self.path == "/":
            ai_service = AIAssistantService()
            status_data = {
                "service": "KTS-Class-Fund AI Backend",
                "status": "online",
                "is_configured": ai_service.is_configured(),
                "note": "AI Key đã sẵn sàng" if ai_service.is_configured() else "Chưa cấu hình GEMINI_API_KEY trong .env"
            }
            self._send_json(200, status_data)
        else:
            self._send_json(404, {"error": "Not Found"})

    def do_POST(self):
        if self.path == "/api/chat":
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
            api_key_override = req_data.get("api_key")

            ai_service = AIAssistantService(api_key=api_key_override)
            result = ai_service.answer_question(question, onchain_data)

            status_code = 200 if result.get("success") else 500
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
