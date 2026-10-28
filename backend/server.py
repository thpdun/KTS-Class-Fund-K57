#!/usr/bin/env python3
"""
Máy chủ Backend Python trung gian cho Trợ lý AI và Quản trị Quỹ Lớp (KTS-Class-Fund)
Giai đoạn 3B.4: Khắc phục xác thực Backend và bảo vệ dữ liệu cá nhân
Tuân thủ quy ước AGENTS.md:
- Python 3.10+
- Không ghi khóa API hoặc private key trong mã nguồn; đọc từ biến môi trường hoặc .env
- Kiểm tra trạng thái phản hồi trước khi xử lý dữ liệu
- Đổi wei sang ETH trước khi hiển thị
- Xác thực chữ ký ví mật mã (Challenge-Response) chống giả mạo quyền sở hữu ví
"""

import os
import sys
import re
import json
import secrets
import time
import threading
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from typing import Optional, Tuple

from eth_account import Account
from eth_account.messages import encode_defunct

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

# =============================================================================
# BẢO MẬT XÁC THỰC VÍ VÀ QUẢN LÝ PHIÊN (Stage 3B.4 - Session & Challenge Management)
# =============================================================================

# Nonce challenge: nonce -> {"address": addr_lower, "expires_at": float, "used": bool, "created_at": float}
ACTIVE_NONCES: dict[str, dict] = {}

# Session token: token -> {"token": str, "address": addr_lower, "role": str, "isAdvisor": bool, "isBcs": bool, "expires_at": float, "created_at": float}
ACTIVE_SESSIONS: dict[str, dict] = {}

# Khóa luồng (Mutex) bảo vệ tính nguyên tử của thao tác kiểm tra & tiêu thụ nonce trong tiến trình
AUTH_MUTEX = threading.Lock()

NONCE_LIFETIME_SEC = 300       # 5 phút cho một challenge nonce
SESSION_LIFETIME_SEC = 3600    # 1 giờ cho một phiên làm việc hợp lệ

# =============================================================================
# CẤU HÌNH CORS (Cross-Origin Resource Sharing)
# =============================================================================
# Whitelist các origin được sử dụng thực tế trong môi trường phát triển
DEV_ALLOWED_ORIGINS = {
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
}

# Cho phép "null" (file://) CHỈ KHI đang ở chế độ development
# Tuyệt đối không mặc định cho phép "null" trong production!
IS_PRODUCTION = os.environ.get("ENV", "development").lower() == "production"


def cleanup_expired_auth():
    """Tự động dọn dẹp các nonce và session đã hết hạn hoặc đã sử dụng."""
    with AUTH_MUTEX:
        now = time.time()
        expired_nonces = [k for k, v in ACTIVE_NONCES.items() if v.get("expires_at", 0) < now or v.get("used", False)]
        for k in expired_nonces:
            ACTIVE_NONCES.pop(k, None)

        expired_sessions = [k for k, v in ACTIVE_SESSIONS.items() if v.get("expires_at", 0) < now]
        for k in expired_sessions:
            ACTIVE_SESSIONS.pop(k, None)


def generate_auth_message(address: str, nonce: str) -> str:
    """Tạo nội dung thông điệp xác thực ví chuẩn mực có gắn nonce và địa chỉ."""
    return (
        f"KTS-Class-Fund-K57 Authentication\n"
        f"Address: {address.lower()}\n"
        f"Nonce: {nonce}\n"
        f"Mục đích: Xác thực quyền sở hữu ví và đăng nhập hệ thống KTS-Class-Fund-K57.\n"
        f"Lưu ý: Thao tác này không tốn phí Gas và không gửi transaction on-chain."
    )


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


def resolve_wallet_role(clean_addr: str) -> Tuple[str, bool, bool]:
    """
    Xác định vai trò của địa chỉ ví dựa trên dữ liệu phía server:
    Trả về: (role, isAdvisor, isBcs)
    - "advisor": Cố vấn học tập
    - "bcs": Ban cán sự
    - "student": Sinh viên thường trong danh bạ
    - "guest": Người ngoài danh bạ
    """
    if not clean_addr or len(clean_addr) != 42 or not clean_addr.startswith("0x"):
        return ("guest", False, False)

    advisor_env = os.environ.get("ADVISOR_ADDRESS", "").strip().lower()
    if advisor_env and clean_addr == advisor_env:
        return ("advisor", True, False)

    s = find_student_by_wallet(clean_addr)
    if s:
        role = s.get("role", "student")
        if role == "advisor":
            return ("advisor", True, False)
        elif role == "bcs":
            return ("bcs", False, True)
        return ("student", False, False)

    return ("guest", False, False)


def is_authorized_advisor(address: str, is_advisor: bool = False) -> bool:
    """Kiểm tra quyền CỐ VẤN HỌC TẬP. Không tin cờ boolean client."""
    role, is_adv, _ = resolve_wallet_role(str(address).strip().lower() if address else "")
    return is_adv


def is_authorized_viewer(address: str, is_bcs: bool = False, is_advisor: bool = False) -> bool:
    """Kiểm tra quyền BCS hoặc Cố vấn từ địa chỉ. Không tin cờ boolean client."""
    role, is_adv, is_b = resolve_wallet_role(str(address).strip().lower() if address else "")
    return is_adv or is_b


def get_authenticated_session(headers) -> Optional[dict]:
    """
    Trích xuất và kiểm tra phiên làm việc từ header HTTP Authorization: Bearer <token>.
    Bảo đảm token còn hạn và hợp lệ trong bộ nhớ server.
    """
    cleanup_expired_auth()
    auth_header = headers.get("Authorization", "").strip()
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:].strip()
    if not token or token not in ACTIVE_SESSIONS:
        return None

    session = ACTIVE_SESSIONS[token]
    if time.time() > session.get("expires_at", 0):
        ACTIVE_SESSIONS.pop(token, None)
        return None

    return session


def parse_deadline_to_timestamp(deadline_str: str) -> Optional[float]:
    """Phân tích chuỗi hạn chót (tiếng Việt hoặc ISO) thành Unix timestamp float."""
    if not deadline_str:
        return None
    s = str(deadline_str).strip()
    # 1. 'HH:MM ngày DD/MM/YYYY'
    m = re.search(r'(\d{1,2}):(\d{1,2})\s*ngày\s*(\d{1,2})/(\d{1,2})/(\d{4})', s, re.I)
    if m:
        try:
            hr, mn, day, mon, yr = map(int, m.groups())
            return datetime(yr, mon, day, hr, mn).timestamp()
        except Exception:
            pass
    # 2. 'DD/MM/YYYY'
    m = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', s)
    if m:
        try:
            day, mon, yr = map(int, m.groups())
            return datetime(yr, mon, day, 23, 59, 59).timestamp()
        except Exception:
            pass
    # 3. ISO format / standard YYYY-MM-DD
    try:
        clean_s = s.replace('Z', '+00:00')
        return datetime.fromisoformat(clean_s).timestamp()
    except Exception:
        pass
    return None


def normalize_announcement_item(item: dict, default_id: str = None) -> dict:
    """Chuẩn hóa cấu trúc của một thông báo theo vòng đời (active | completed | archived)."""
    if not isinstance(item, dict):
        return {}
    item_id = str(item.get("id") or default_id or f"ann-{secrets.token_hex(4)}")
    raw_status = str(item.get("status", "active")).strip()
    if raw_status in ["Đang diễn ra", "active", "OPEN"]:
        status = "active"
    elif raw_status in ["Đã hoàn thành", "completed", "COMPLETED"]:
        status = "completed"
    else:
        status = "archived"

    deadline_str = str(item.get("deadline", "Chưa xác định")).strip()
    ts = item.get("deadlineTimestamp")
    if ts is None:
        ts = parse_deadline_to_timestamp(deadline_str)

    return {
        "id": item_id,
        "title": str(item.get("title", "Kêu gọi nộp Quỹ Lớp K57")).strip(),
        "targetAmountEth": str(item.get("targetAmountEth", "0.0100")).strip(),
        "deadline": deadline_str,
        "deadlineTimestamp": ts,
        "classSize": int(item.get("classSize", 7)),
        "purpose": str(item.get("purpose", "")).strip(),
        "status": status,
        "autoCloseOnTarget": bool(item.get("autoCloseOnTarget", False)),
        "createdAt": item.get("createdAt") or datetime.now(timezone.utc).isoformat(),
        "endedAt": item.get("endedAt"),
        "endReason": item.get("endReason"),
        "updatedBy": item.get("updatedBy"),
        "updatedAt": item.get("updatedAt")
    }


def load_announcements_store() -> dict:
    """Đọc dữ liệu thông báo và lịch sử, đồng thời tự động lưu trữ thông báo hết hạn (Auto-archive)."""
    roster_len = len(load_roster())
    actual_size = roster_len if roster_len > 0 else 7

    store = {"active": None, "history": []}
    if ANNOUNCEMENT_FILE.exists():
        try:
            with open(ANNOUNCEMENT_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
                if isinstance(raw, dict):
                    if "active" in raw or "history" in raw:
                        # Cấu trúc mới hỗ trợ lịch sử
                        if raw.get("active"):
                            store["active"] = normalize_announcement_item(raw["active"], "ann-active-current")
                        history_raw = raw.get("history", [])
                        if isinstance(history_raw, list):
                            store["history"] = [normalize_announcement_item(h) for h in history_raw if isinstance(h, dict)]
                    else:
                        # Tương thích ngược: dữ liệu đơn lẻ trước đây
                        store["active"] = normalize_announcement_item(raw, "ann-k57-hk1")
                        store["history"] = []
        except Exception:
            pass

    if store["active"] is None and not store["history"]:
        store["active"] = {
            "id": "ann-k57-hk1",
            "title": "Kêu gọi nộp Quỹ Lớp K57 Học kỳ 1 (Auth Verified)",
            "targetAmountEth": "0.0100",
            "deadline": "23:59 ngày 30/11/2026",
            "deadlineTimestamp": parse_deadline_to_timestamp("23:59 ngày 30/11/2026"),
            "classSize": actual_size,
            "purpose": "Học tập và sinh hoạt chuyên đề K57",
            "status": "active",
            "autoCloseOnTarget": False,
            "createdAt": "2026-10-20T00:00:00Z",
            "endedAt": None,
            "endReason": None,
            "updatedBy": "0xe71f9ffb91a3f4ba78e25833ba48b05c0e7d9fc2",
            "updatedAt": None
        }

    if store["active"]:
        store["active"]["classSize"] = actual_size

    # KIỂM TRA TỰ ĐỘNG CHUYỂN TRẠNG THÁI (AUTO-ARCHIVE RULE)
    modified = False
    active = store["active"]
    now = time.time()
    if active:
        dl_ts = active.get("deadlineTimestamp")
        # 1. Hết hạn nộp: tự động chuyển sang lưu trữ
        if dl_ts and now > dl_ts:
            active["status"] = "archived"
            active["endedAt"] = datetime.now(timezone.utc).isoformat()
            active["endReason"] = "Đã hết hạn nộp (Quá thời hạn quy định)"
            if not any(h.get("id") == active["id"] for h in store["history"]):
                store["history"].insert(0, active)
            store["active"] = None
            modified = True
        elif active.get("status") in ["completed", "archived"]:
            active["status"] = "archived"
            if not active.get("endedAt"):
                active["endedAt"] = datetime.now(timezone.utc).isoformat()
            if not active.get("endReason"):
                active["endReason"] = "Đợt thu đã hoàn thành"
            if not any(h.get("id") == active["id"] for h in store["history"]):
                store["history"].insert(0, active)
            store["active"] = None
            modified = True

    if modified:
        save_announcements_store(store)

    return store


def save_announcements_store(store: dict):
    """Ghi cấu trúc thông báo và lịch sử vào tệp JSON."""
    with open(ANNOUNCEMENT_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def load_announcement() -> dict:
    """Tương thích ngược cho các module hoặc endpoint cũ đọc announcement đơn lẻ."""
    store = load_announcements_store()
    if store.get("active"):
        return store["active"]
    elif store.get("history"):
        return store["history"][0]
    return {
        "id": None,
        "title": "Kêu gọi nộp Quỹ Lớp K57",
        "targetAmountEth": "0.0100",
        "deadline": "Chưa xác định",
        "classSize": len(load_roster()) or 7,
        "purpose": "Hoạt động chung K57",
        "status": "none",
        "updatedAt": None,
        "updatedBy": None
    }


def save_announcement(data: dict):
    """Tương thích ngược: lưu announcement mới vào active và tự động lưu thông báo cũ vào history."""
    store = load_announcements_store()
    old_active = store.get("active")
    if old_active and old_active.get("status") == "active":
        old_active["status"] = "archived"
        old_active["endedAt"] = datetime.now(timezone.utc).isoformat()
        old_active["endReason"] = "Thay thế bởi đợt thu mới"
        if not any(h.get("id") == old_active["id"] for h in store["history"]):
            store["history"].insert(0, old_active)

    norm = normalize_announcement_item(data)
    norm["classSize"] = len(load_roster()) or norm.get("classSize", 7)
    store["active"] = norm
    save_announcements_store(store)


# =============================================================================
# HTTP REQUEST HANDLER
# =============================================================================

class AIChatRequestHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        origin = self.headers.get("Origin")
        if not origin:
            # Request không có Origin (curl, urllib, scripts nội bộ): Không gửi CORS header
            return

        is_allowed = False
        if origin in DEV_ALLOWED_ORIGINS:
            is_allowed = True
        elif origin == "null" and not IS_PRODUCTION:
            is_allowed = True

        if is_allowed:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.send_header("Access-Control-Max-Age", "86400")

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
        cleanup_expired_auth()
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        # 1. Trạng thái máy chủ
        if path == "/api/status" or path == "/":
            ai_service = AIAssistantService()
            status_data = {
                "service": "KTS-Class-Fund AI & Auth Backend",
                "status": "online",
                "auth_mode": "challenge-response-signature",
                "is_configured": ai_service.is_configured(),
                "note": "AI Key đã sẵn sàng" if ai_service.is_configured() else "Chưa cấu hình GEMINI_API_KEY trong .env"
            }
            self._send_json(200, status_data)

        # 2. Challenge Nonce cho xác thực ví (GET /api/auth/nonce?address=0x...)
        elif path == "/api/auth/nonce":
            addr = qs.get("address", [""])[0].strip().lower()
            if not addr.startswith("0x") or len(addr) != 42:
                self._send_json(400, {
                    "success": False,
                    "error": "Địa chỉ ví không hợp lệ (cần đúng 42 ký tự, bắt đầu bằng 0x)."
                })
                return

            now = time.time()
            nonce = secrets.token_hex(16)
            with AUTH_MUTEX:
                ACTIVE_NONCES[nonce] = {
                    "address": addr,
                    "expires_at": now + NONCE_LIFETIME_SEC,
                    "used": False,
                    "created_at": now
                }

            auth_msg = generate_auth_message(addr, nonce)
            self._send_json(200, {
                "success": True,
                "address": addr,
                "nonce": nonce,
                "message": auth_msg,
                "expiresIn": NONCE_LIFETIME_SEC
            })

        # 3. Kiểm tra phiên đăng nhập hiện hành (GET /api/auth/session)
        elif path == "/api/auth/session":
            session = get_authenticated_session(self.headers)
            if not session:
                self._send_json(401, {
                    "success": False,
                    "authenticated": False,
                    "error": "Chưa đăng nhập hoặc phiên làm việc đã hết hạn."
                })
                return

            self._send_json(200, {
                "success": True,
                "authenticated": True,
                "address": session["address"],
                "role": session["role"],
                "isAdvisor": session["isAdvisor"],
                "isBcs": session["isBcs"],
                "expiresIn": max(0, int(session["expires_at"] - time.time()))
            })

        # 4. Lấy thông báo nộp quỹ chung và lịch sử (GET /api/announcement)
        elif path == "/api/announcement":
            store = load_announcements_store()
            active = store.get("active")
            fallback = active or (store["history"][0] if store.get("history") else {
                "id": None,
                "title": "Hiện không có đợt thu quỹ nào đang diễn ra",
                "targetAmountEth": "0",
                "status": "none",
                "classSize": len(load_roster()) or 7,
                "deadline": "Không có",
                "purpose": "Các đợt thu trước đây đã được lưu trữ trong Lịch sử thông báo."
            })
            self._send_json(200, {
                "success": True,
                "announcement": fallback,
                "active": active,
                "history": store.get("history", [])
            })

        # 4b. Lấy riêng danh sách lịch sử thông báo (GET /api/announcement/history)
        elif path == "/api/announcement/history":
            store = load_announcements_store()
            self._send_json(200, {
                "success": True,
                "count": len(store.get("history", [])),
                "history": store.get("history", [])
            })

        # 5. Danh bạ lớp có phân quyền (GET /api/roster)
        # BẢO VỆ TUYỆT ĐỐI (Stage 3B.4):
        # Bắt buộc phải có Session Token hợp lệ của Ban cán sự hoặc Cố vấn học tập!
        # Không chấp nhận địa chỉ truyền qua query string để lấy PII.
        elif path == "/api/roster":
            roster = load_roster()
            session = get_authenticated_session(self.headers)

            if session and session.get("role") in ["bcs", "advisor"]:
                self._send_json(200, {
                    "success": True,
                    "count": len(roster),
                    "classSize": len(roster),
                    "isAuthorized": True,
                    "requesterRole": session["role"],
                    "roster": roster
                })
            else:
                self._send_json(200, {
                    "success": True,
                    "count": len(roster),
                    "classSize": len(roster),
                    "isAuthorized": False,
                    "roster": [],
                    "message": "Dữ liệu định danh được bảo vệ. Yêu cầu xác thực chữ ký ví Ban cán sự hoặc Cố vấn học tập để xem danh bạ."
                })

        # 6. Kiểm tra thông tin sinh viên theo ví (GET /api/roster/check?address=0x...)
        # BẢO VỆ CHỐNG TRA CỨU NGƯỢC TÙY TIỆN (Stage 3B.4):
        # - Yêu cầu phiên đăng nhập.
        # - Sinh viên thường CHỈ ĐƯỢC tra cứu thông tin của CHÍNH VÍ ĐANG ĐĂNG NHẬP.
        # - Chỉ BCS/CVHT mới được tra cứu các ví khác.
        elif path == "/api/roster/check":
            target_addr = qs.get("address", [""])[0].strip().lower()
            if not target_addr:
                self._send_json(400, {"success": False, "error": "Thiếu địa chỉ ví cần kiểm tra."})
                return

            session = get_authenticated_session(self.headers)
            if not session:
                self._send_json(401, {
                    "success": False,
                    "error": "Yêu cầu đăng nhập ví để tra cứu thông tin định danh sinh viên."
                })
                return

            # Kiểm tra quyền: Chỉ cho phép tự xem ví mình HOẶC người gọi là BCS/CVHT
            is_self = (session["address"] == target_addr)
            is_manager = session["role"] in ["bcs", "advisor"]

            if not is_self and not is_manager:
                self._send_json(403, {
                    "success": False,
                    "error": "Truy cập bị từ chối: Bạn chỉ được phép tra cứu thông tin định danh của chính ví của mình."
                })
                return

            student = find_student_by_wallet(target_addr)
            self._send_json(200, {
                "success": True,
                "isMember": student is not None,
                "student": student
            })

        else:
            self._send_json(404, {"error": "Not Found"})

    def do_POST(self):
        cleanup_expired_auth()
        parsed = urlparse(self.path)
        path = parsed.path

        # 1. Đăng nhập ví qua chữ ký (POST /api/auth/login)
        if path == "/api/auth/login":
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self._send_json(400, {"success": False, "error": "Thiếu dữ liệu đăng nhập."})
                return

            try:
                raw_body = self.rfile.read(content_length).decode("utf-8")
                req_data = json.loads(raw_body)
            except Exception as e:
                self._send_json(400, {"success": False, "error": f"Dữ liệu JSON không hợp lệ: {str(e)}"})
                return

            claimed_addr = str(req_data.get("address", "")).strip().lower()
            nonce = str(req_data.get("nonce", "")).strip()
            signature = str(req_data.get("signature", "")).strip()

            if not claimed_addr or not nonce or not signature:
                self._send_json(400, {
                    "success": False,
                    "error": "Yêu cầu cung cấp đầy đủ address, nonce và signature."
                })
                return

            # 1.1 Kiểm tra sơ bộ Nonce dưới khóa nguyên tử AUTH_MUTEX
            with AUTH_MUTEX:
                if nonce not in ACTIVE_NONCES:
                    self._send_json(400, {
                        "success": False,
                        "error": "Nonce không tồn tại hoặc đã bị hủy. Vui lòng lấy challenge nonce mới."
                    })
                    return

                nonce_info = ACTIVE_NONCES[nonce]

                # 1.2 Kiểm tra Nonce đã dùng chưa (Chống Replay Attack)
                if nonce_info.get("used", False):
                    ACTIVE_NONCES.pop(nonce, None)
                    self._send_json(400, {
                        "success": False,
                        "error": "Nonce này đã được sử dụng trước đó (Replay attack prevented)."
                    })
                    return

                # 1.3 Kiểm tra Nonce hết hạn
                if time.time() > nonce_info.get("expires_at", 0):
                    ACTIVE_NONCES.pop(nonce, None)
                    self._send_json(400, {
                        "success": False,
                        "error": "Nonce đã hết hạn (quá 5 phút). Vui lòng thử lại với nonce mới."
                    })
                    return

                # 1.4 Kiểm tra Nonce có đúng ví yêu cầu ban đầu không
                if nonce_info.get("address") != claimed_addr:
                    self._send_json(400, {
                        "success": False,
                        "error": "Nonce này không khớp với địa chỉ ví yêu cầu xác thực."
                    })
                    return

            # 1.5 Xác minh chữ ký mật mã bằng eth_account (Thao tác CPU nặng - chạy ngoài khóa)
            expected_msg = generate_auth_message(claimed_addr, nonce)
            try:
                msg_encoded = encode_defunct(text=expected_msg)
                recovered_addr = Account.recover_message(msg_encoded, signature=signature)
            except Exception as e:
                self._send_json(400, {
                    "success": False,
                    "error": f"Chữ ký không đúng định dạng Ethereum: {str(e)}"
                })
                return

            if recovered_addr.lower() != claimed_addr:
                self._send_json(401, {
                    "success": False,
                    "error": f"Xác minh chữ ký thất bại: Chữ ký không khớp với ví {claimed_addr}."
                })
                # BẢO VỆ: Chữ ký sai KHÔNG tiêu thụ nonce hợp lệ
                return

            # 1.6 Tiêu thụ Nonce nguyên tử và Cấp phiên dưới khóa AUTH_MUTEX
            now = time.time()
            with AUTH_MUTEX:
                # 1.6.1 Kiểm tra nonce vẫn tồn tại
                if nonce not in ACTIVE_NONCES:
                    self._send_json(400, {
                        "success": False,
                        "error": "Nonce không tồn tại hoặc đã bị hủy. Vui lòng lấy challenge nonce mới."
                    })
                    return

                nonce_info = ACTIVE_NONCES[nonce]

                # 1.6.2 Kiểm tra nonce chưa được sử dụng (chống Replay Attack / Race Condition)
                if nonce_info.get("used", False):
                    ACTIVE_NONCES.pop(nonce, None)
                    self._send_json(400, {
                        "success": False,
                        "error": "Nonce này đã được tiêu thụ bởi một yêu cầu đồng thời khác (Replay prevented)."
                    })
                    return

                # 1.6.3 Kiểm tra lại thời gian hết hạn tại thời điểm kiểm tra cuối
                if now > nonce_info.get("expires_at", 0):
                    ACTIVE_NONCES.pop(nonce, None)
                    self._send_json(400, {
                        "success": False,
                        "error": "Nonce đã hết hạn trong lúc xác thực. Vui lòng thử lại với nonce mới."
                    })
                    return

                # 1.6.4 Kiểm tra nonce có khớp ví yêu cầu ban đầu không
                if nonce_info.get("address") != claimed_addr:
                    self._send_json(400, {
                        "success": False,
                        "error": "Nonce này không khớp với địa chỉ ví yêu cầu xác thực."
                    })
                    return

                # Đánh dấu Nonce đã sử dụng thành công (One-time use) và hủy ngay lập tức
                ACTIVE_NONCES[nonce]["used"] = True
                ACTIVE_NONCES.pop(nonce, None)

                # 1.7 Xác định vai trò từ dữ liệu phía server (Class Roster & Advisor Env)
                role, is_advisor, is_bcs = resolve_wallet_role(claimed_addr)

                # 1.8 Cấp Session Token an toàn
                token = secrets.token_hex(32)
                session_data = {
                    "token": token,
                    "address": claimed_addr,
                    "role": role,
                    "isAdvisor": is_advisor,
                    "isBcs": is_bcs,
                    "expires_at": now + SESSION_LIFETIME_SEC,
                    "created_at": now
                }
                ACTIVE_SESSIONS[token] = session_data

            self._send_json(200, {
                "success": True,
                "message": "Xác thực chữ ký ví thành công.",
                "token": token,
                "address": claimed_addr,
                "role": role,
                "isAdvisor": is_advisor,
                "isBcs": is_bcs,
                "expiresIn": SESSION_LIFETIME_SEC
            })

        # 2. Đăng xuất (POST /api/auth/logout)
        elif path == "/api/auth/logout":
            content_length = int(self.headers.get("Content-Length", 0))
            token = None
            if content_length > 0:
                try:
                    req_data = json.loads(self.rfile.read(content_length).decode("utf-8"))
                    token = req_data.get("token")
                except Exception:
                    pass

            if not token:
                auth_header = self.headers.get("Authorization", "")
                if auth_header.startswith("Bearer "):
                    token = auth_header[7:].strip()

            if token and token in ACTIVE_SESSIONS:
                ACTIVE_SESSIONS.pop(token, None)

            self._send_json(200, {
                "success": True,
                "message": "Đã đăng xuất và hủy phiên làm việc thành công."
            })

        # 3. Tạo / Cập nhật / Kết thúc thông báo nộp quỹ (POST /api/announcement)
        # BẢO VỆ BẰNG SESSION (Stage 3B.4)
        elif path == "/api/announcement" or path == "/api/announcement/close":
            session = get_authenticated_session(self.headers)
            if not session or session.get("role") not in ["bcs", "advisor"]:
                self._send_json(403, {
                    "success": False,
                    "error": "Truy cập bị từ chối: Yêu cầu phiên xác thực chữ ký của Ban cán sự hoặc Cố vấn học tập."
                })
                return

            content_length = int(self.headers.get("Content-Length", 0))
            req_data = {}
            if content_length > 0:
                try:
                    raw_body = self.rfile.read(content_length).decode("utf-8")
                    req_data = json.loads(raw_body)
                except Exception as e:
                    self._send_json(400, {"success": False, "error": f"Dữ liệu JSON không hợp lệ: {str(e)}"})
                    return

            store = load_announcements_store()

            # Thao tác kết thúc sớm đợt thu (Action: close)
            if path == "/api/announcement/close" or req_data.get("action") == "close":
                active = store.get("active")
                if not active:
                    self._send_json(400, {"success": False, "error": "Hiện không có đợt thu nào đang diễn ra để kết thúc."})
                    return

                active["status"] = "archived"
                active["endedAt"] = datetime.now(timezone.utc).isoformat()
                active["endReason"] = str(req_data.get("reason") or "Ban cán sự chủ động kết thúc đợt thu").strip()
                active["updatedBy"] = session["address"]
                active["updatedAt"] = datetime.now(timezone.utc).isoformat()

                if not any(h.get("id") == active["id"] for h in store["history"]):
                    store["history"].insert(0, active)
                store["active"] = None
                save_announcements_store(store)

                self._send_json(200, {
                    "success": True,
                    "message": "Đã kết thúc đợt thu và chuyển vào lịch sử thông báo.",
                    "archived": active,
                    "active": None,
                    "history": store["history"]
                })
                return

            # Thao tác tạo đợt thu mới hoặc cập nhật
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

            roster_len = len(load_roster())
            actual_class_size = roster_len if roster_len > 0 else int(req_data.get("classSize", 7))

            # Lưu trữ đợt thu active cũ nếu có (không ghi đè mất mát)
            old_active = store.get("active")
            if old_active and old_active.get("status") == "active":
                old_active["status"] = "archived"
                old_active["endedAt"] = datetime.now(timezone.utc).isoformat()
                old_active["endReason"] = "Thay thế bởi đợt thu mới"
                if not any(h.get("id") == old_active["id"] for h in store["history"]):
                    store["history"].insert(0, old_active)

            deadline_str = str(req_data.get("deadline", "Chưa xác định")).strip()
            new_id = str(req_data.get("id") or f"ann-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}")

            announcement_data = {
                "id": new_id,
                "title": title,
                "targetAmountEth": target_amount,
                "deadline": deadline_str,
                "deadlineTimestamp": parse_deadline_to_timestamp(deadline_str),
                "classSize": actual_class_size,
                "purpose": str(req_data.get("purpose", "")).strip(),
                "status": "active",
                "autoCloseOnTarget": bool(req_data.get("autoCloseOnTarget", False)),
                "createdAt": req_data.get("createdAt") or datetime.now(timezone.utc).isoformat(),
                "endedAt": None,
                "endReason": None,
                "updatedBy": session["address"],
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }

            store["active"] = announcement_data
            save_announcements_store(store)
            self._send_json(200, {
                "success": True,
                "announcement": announcement_data,
                "active": announcement_data,
                "history": store["history"]
            })

        # 4. Thêm / Chỉnh sửa danh bạ sinh viên (POST /api/roster/register)
        # BẢO VỆ BẰNG SESSION (Stage 3B.4)
        elif path == "/api/roster/register":
            session = get_authenticated_session(self.headers)
            if not session or session.get("role") not in ["bcs", "advisor"]:
                self._send_json(403, {
                    "success": False,
                    "error": "Truy cập bị từ chối: Yêu cầu phiên xác thực chữ ký của Ban cán sự hoặc Cố vấn học tập."
                })
                return

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

            mssv = str(req_data.get("mssv", "")).strip()
            name = str(req_data.get("name", "")).strip()
            wallet = str(req_data.get("wallet", "")).strip()
            role_raw = str(req_data.get("role", "student")).strip()
            original_mssv = str(req_data.get("originalMssv", "")).strip()

            role = "bcs" if role_raw == "bcs" else "student"
            role_title = "Ban cán sự" if role == "bcs" else "Sinh viên"

            if not mssv or not name or not wallet:
                self._send_json(400, {"success": False, "error": "MSSV, Họ tên và Địa chỉ ví không được để trống."})
                return

            if not wallet.startswith("0x") or len(wallet) != 42:
                self._send_json(400, {"success": False, "error": "Địa chỉ ví Ethereum không hợp lệ (cần đúng 42 ký tự, bắt đầu bằng 0x)."})
                return

            roster = load_roster()
            match_idx = None
            for idx, item in enumerate(roster):
                if original_mssv and item.get("mssv") == original_mssv:
                    match_idx = idx
                    break
                if item.get("mssv") == mssv:
                    match_idx = idx
                    break

            if match_idx is not None:
                roster[match_idx]["mssv"] = mssv
                roster[match_idx]["name"] = name
                roster[match_idx]["wallet"] = wallet
                roster[match_idx]["role"] = role
                roster[match_idx]["roleTitle"] = role_title
                updated = True
            else:
                for item in roster:
                    if item.get("wallet", "").lower() == wallet.lower():
                        item["mssv"] = mssv
                        item["name"] = name
                        item["role"] = role
                        item["roleTitle"] = role_title
                        updated = True
                        break
                else:
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

        # 5. Hỏi đáp Trợ lý AI (POST /api/chat)
        elif path == "/api/chat":
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

            # Lọc sạch PII trước khi chuyển sang AI Assistant Service
            raw_onchain = req_data.get("onchain_data", {})
            if not isinstance(raw_onchain, dict):
                raw_onchain = {}

            onchain_data = {
                "isContractConnected": bool(raw_onchain.get("isContractConnected", False)),
                "contractAddress": str(raw_onchain.get("contractAddress", "")),
                "viewerRole": "public",
                "classFundBalanceEth": str(raw_onchain.get("classFundBalanceEth", "0")),
                "adminFeePoolEth": str(raw_onchain.get("adminFeePoolEth", "0")),
                "spendCount": int(raw_onchain.get("spendCount", 0)),
                "refundCount": int(raw_onchain.get("refundCount", 0)),
                "activeBCSCount": int(raw_onchain.get("activeBCSCount", 0)),
                "depositorsCount": int(raw_onchain.get("depositorsCount", 0)),
                "totalDepositedEth": str(raw_onchain.get("totalDepositedEth", "0")),
                "announcement": raw_onchain.get("announcement", {}),
                "spendRequests": raw_onchain.get("spendRequests", []),
                "refundRequests": raw_onchain.get("refundRequests", []),
                "roster": []  # Luôn rỗng, không bao giờ chứa danh bạ PII
            }

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
        """Khử bỏ query string và thông tin nhạy cảm khỏi server access log."""
        sanitized = format % args
        if "?" in sanitized:
            parts = sanitized.split("?")
            sanitized = parts[0] + " [QUERY_PARAMS_REDACTED]"
        sys.stdout.write(f"[Server Log] {self.address_string()} - {sanitized}\n")
        sys.stdout.flush()


def run_server():
    server_address = (HOST, PORT)
    httpd = HTTPServer(server_address, AIChatRequestHandler)
    ai_service = AIAssistantService()
    print("=" * 65, flush=True)
    print(f"🚀 KTS-Class-Fund Backend (Auth Protected) đang chạy tại http://localhost:{PORT}", flush=True)
    print(f"   Xác thực: Challenge-Response Signature (eth_account)", flush=True)
    print(f"   Trạng thái Gemini API Key: {'ĐÃ CẤU HÌNH' if ai_service.is_configured() else 'CHƯA CẤU HÌNH'}", flush=True)
    print("=" * 65, flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nĐang dừng máy chủ...", flush=True)
        httpd.server_close()


if __name__ == "__main__":
    run_server()
