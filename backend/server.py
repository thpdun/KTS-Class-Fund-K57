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
import copy
import threading
import logging

logger = logging.getLogger('kts.server')
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
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

# Import module Hạch toán & Lưu trữ nguyên tử V4.4 (Phase 1)
try:
    from backend.accounting_engine import (
        VN_TZ_KEY,
        get_vn_tz,
        parse_deadline_to_vn_timestamp,
        DualLayerFileLock,
        atomic_write_json,
        safe_load_json,
        validate_announcement_store_structure,
        validate_concurrency_and_idempotency,
        record_mutation_commit,
        RevisionConflictError,
        IdempotencyConflictError,
        CorruptedStorageError,
        AtomicStorageError,
    )
except ImportError:
    from accounting_engine import (
        VN_TZ_KEY,
        get_vn_tz,
        parse_deadline_to_vn_timestamp,
        DualLayerFileLock,
        atomic_write_json,
        safe_load_json,
        validate_announcement_store_structure,
        validate_concurrency_and_idempotency,
        record_mutation_commit,
        RevisionConflictError,
        IdempotencyConflictError,
        CorruptedStorageError,
        AtomicStorageError,
    )

# Import module Quản lý Thông báo đa luồng & Lịch sử Schema V3
try:
    from backend.notification_store import (
        NOTIFICATION_SCHEMA_VERSION,
        NotificationStatus,
        normalize_notification,
        validate_notifications_store,
        migrate_to_notifications_store,
        expire_due_notifications,
        append_audit_event,
        verify_audit_chain,
        create_notification,
        edit_notification,
        find_notification,
        transition_notification,
        resolve_target_id,
        build_views,
        NotificationValidationError,
    )
except ImportError:
    from notification_store import (
        NOTIFICATION_SCHEMA_VERSION,
        NotificationStatus,
        normalize_notification,
        validate_notifications_store,
        migrate_to_notifications_store,
        expire_due_notifications,
        append_audit_event,
        verify_audit_chain,
        create_notification,
        edit_notification,
        find_notification,
        transition_notification,
        resolve_target_id,
        build_views,
    )

# Import module Quản lý Tiến độ đóng góp & Attribution Layer (Stage 1 & 2)
try:
    from backend.contribution_store import (
        create_claim_intent,
        get_claim_intent,
        verify_and_claim_contribution,
        get_campaign_progress_view,
        freeze_campaign_progress_record,
        record_adjusted_final_progress,
        load_contributions_store,
        ContributionAttributionError,
    )
except ImportError:
    from contribution_store import (
        create_claim_intent,
        get_claim_intent,
        verify_and_claim_contribution,
        get_campaign_progress_view,
        freeze_campaign_progress_record,
        record_adjusted_final_progress,
        load_contributions_store,
        ContributionAttributionError,
    )

# Import module Chuẩn hóa và Băm Danh bạ Sinh viên (Phase 3 / Mục D)
try:
    from backend.import_roster import (
        ROSTER_HASH_ALGORITHM,
        ROSTER_CANONICAL_VERSION,
        ROSTER_CANONICAL_SPEC,
        build_roster_hash_payload,
        compute_roster_hash,
    )
except ImportError:
    from import_roster import (
        ROSTER_HASH_ALGORITHM,
        ROSTER_CANONICAL_VERSION,
        ROSTER_CANONICAL_SPEC,
        build_roster_hash_payload,
        compute_roster_hash,
    )

HOST = "0.0.0.0"
PORT = 8000

DEFAULT_ANNOUNCEMENT_FILE = (Path(__file__).parent / "announcements.json").resolve()
DEFAULT_ROSTER_FILE = (Path(__file__).parent / "class_roster.json").resolve()

ANNOUNCEMENT_FILE = Path(os.environ.get("ANNOUNCEMENT_FILE_PATH", str(DEFAULT_ANNOUNCEMENT_FILE)))
ROSTER_FILE = Path(os.environ.get("CLASS_ROSTER_FILE_PATH", str(DEFAULT_ROSTER_FILE)))


def get_announcement_file() -> Path:
    """Lấy đường dẫn file thông báo hiện hành (ưu tiên biến môi trường ANNOUNCEMENT_FILE_PATH)."""
    env_val = os.environ.get("ANNOUNCEMENT_FILE_PATH", "").strip()
    if env_val:
        return Path(env_val).resolve()
    return Path(ANNOUNCEMENT_FILE).resolve()


def get_roster_file() -> Path:
    """Lấy đường dẫn file danh bạ hiện hành (ưu tiên biến môi trường CLASS_ROSTER_FILE_PATH)."""
    env_val = os.environ.get("CLASS_ROSTER_FILE_PATH", "").strip()
    if env_val:
        return Path(env_val).resolve()
    return Path(ROSTER_FILE).resolve()


def _is_real_data_write_blocked(target_path: Path) -> bool:
    """
    Khóa bảo vệ Phase 1: Ngăn chặn tuyệt đối việc vô tình ghi đè hoặc xóa dữ liệu thật
    trong `backend/announcements.json` và `backend/class_roster.json` trừ khi cờ
    `ALLOW_REAL_DATA_MUTATION=1` được bật tường minh ở các giai đoạn được phép.
    """
    resolved = Path(target_path).resolve()
    if resolved in (DEFAULT_ANNOUNCEMENT_FILE, DEFAULT_ROSTER_FILE):
        return os.environ.get("ALLOW_REAL_DATA_MUTATION", "0").strip() != "1"
    return False

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


def _validate_roster_structure(data) -> Tuple[bool, Optional[str]]:
    if not isinstance(data, list):
        return False, "Danh bạ sinh viên phải là một danh sách (list)."
    return True, None


def load_roster() -> list:
    roster_file = get_roster_file()
    if roster_file.exists() or roster_file.with_name(roster_file.name + ".bak").exists():
        try:
            data, _ = safe_load_json(roster_file, validator_fn=_validate_roster_structure)
            if isinstance(data, list):
                return data
        except CorruptedStorageError:
            raise
        except Exception:
            pass
    return []


def save_roster(data: list):
    roster_file = get_roster_file()
    if _is_real_data_write_blocked(roster_file):
        raise AtomicStorageError(
            f"PHASE1_REAL_DATA_PROTECTED: Từ chối ghi đè file dữ liệu thật {roster_file} trong Phase 1."
        )
    atomic_write_json(roster_file, data, validator_fn=_validate_roster_structure)


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
    """
    Phân tích chuỗi hạn chót (tiếng Việt hoặc ISO) thành Unix timestamp float
    sử dụng múi giờ chuẩn `Asia/Ho_Chi_Minh` (+07:00).
    """
    ts_int = parse_deadline_to_vn_timestamp(deadline_str)
    return float(ts_int) if ts_int is not None else None


def normalize_announcement_item(item: dict, default_id: str = None) -> dict:
    """Chuẩn hóa cấu trúc của một thông báo theo vòng đời (active | expired | completed | archived)."""
    if not isinstance(item, dict):
        return {}
    item_id = str(item.get("id") or default_id or f"ann-{secrets.token_hex(4)}")
    raw_status = str(item.get("status", "active")).strip()
    if raw_status in ["Đang diễn ra", "active", "OPEN"]:
        status = "active"
    elif raw_status in ["Đã hết hạn", "expired", "EXPIRED"]:
        status = "expired"
    elif raw_status in ["Đã hoàn thành", "completed", "COMPLETED"]:
        status = "completed"
    else:
        status = "archived"

    deadline_str = str(item.get("deadline", "Chưa xác định")).strip()
    ts = item.get("deadlineTimestamp")
    if ts is None:
        ts = parse_deadline_to_timestamp(deadline_str)
    else:
        parsed_vn_ts = parse_deadline_to_timestamp(deadline_str)
        ts = parsed_vn_ts if parsed_vn_ts is not None else float(ts)

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
        "createdAt": item.get("createdAt") or datetime.now(get_vn_tz()).isoformat(),
        "endedAt": item.get("endedAt"),
        "endReason": item.get("endReason"),
        "updatedBy": item.get("updatedBy"),
        "updatedAt": item.get("updatedAt")
    }


def load_announcements_store() -> dict:
    """
    Đọc dữ liệu thông báo và lịch sử Schema V3 qua khóa an toàn (`safe_load_json`),
    đồng thời tự động kiểm tra và chuyển thông báo quá hạn sang `expired` một cách idempotent.
    """
    roster_len = len(load_roster())
    actual_size = roster_len if roster_len > 0 else None
    ann_file = get_announcement_file()
    bak_file = ann_file.with_name(ann_file.name + ".bak")

    store = None
    if ann_file.exists() or bak_file.exists():
        try:
            raw, _ = safe_load_json(ann_file, validator_fn=validate_notifications_store)
            if isinstance(raw, dict) and "notifications" in raw:
                store = raw
            else:
                migrated_store, _ = migrate_to_notifications_store(raw)
                store = migrated_store
        except Exception:
            # Nếu kiểm tra Schema V3 chưa khớp, nạp raw và thực hiện migration tự động
            try:
                raw, _ = safe_load_json(ann_file)
                if isinstance(raw, dict):
                    migrated_store, _ = migrate_to_notifications_store(raw)
                    store = migrated_store
            except Exception:
                store = None

    if not isinstance(store, dict):
        store = {
            "schemaVersion": NOTIFICATION_SCHEMA_VERSION,
            "revision": 1,
            "timezone": VN_TZ_KEY,
            "notifications": [],
            "processedRequests": {},
            "auditChain": [],
        }

    store.setdefault("schemaVersion", NOTIFICATION_SCHEMA_VERSION)
    store.setdefault("revision", 1)
    store.setdefault("timezone", VN_TZ_KEY)
    store.setdefault("notifications", [])
    store.setdefault("processedRequests", {})
    store.setdefault("auditChain", [])

    # Đồng bộ sĩ số lớp vào các thông báo
    for item in store["notifications"]:
        if isinstance(item, dict):
            item["classSize"] = actual_size

    # KIỂM TRA TỰ ĐỘNG CHUYỂN TRẠNG THÁI (AUTO-EXPIRE RULE THEO VN TIMEZONE)
    expired_ids = expire_due_notifications(store)
    if expired_ids and not _is_real_data_write_blocked(ann_file):
        store["revision"] = int(store.get("revision", 1)) + 1
        save_announcements_store(store)

    # Gắn các views tương thích ngược (active, history, activeNotifications)
    views = build_views(store)
    store["activeNotifications"] = views["activeNotifications"]
    store["active"] = views["active"]
    store["history"] = views["history"]

    return store


def save_announcements_store(store: dict):
    """Ghi cấu trúc thông báo Schema V3 vào tệp JSON qua Atomic Write 7 bước và File Lock."""
    ann_file = get_announcement_file()
    if _is_real_data_write_blocked(ann_file):
        raise AtomicStorageError(
            f"PHASE1_REAL_DATA_PROTECTED: Từ chối ghi đè file dữ liệu thật {ann_file} trong Phase 1."
        )
    if "schemaVersion" not in store:
        store["schemaVersion"] = NOTIFICATION_SCHEMA_VERSION
    if "revision" not in store or not isinstance(store["revision"], int) or store["revision"] < 1:
        store["revision"] = 1
    if "timezone" not in store:
        store["timezone"] = VN_TZ_KEY
    if "notifications" not in store or not isinstance(store["notifications"], list):
        store["notifications"] = []
    if "processedRequests" not in store or not isinstance(store["processedRequests"], dict):
        store["processedRequests"] = {}
    if "auditChain" not in store or not isinstance(store["auditChain"], list):
        store["auditChain"] = []

    # Cập nhật views đồng bộ trước khi lưu
    views = build_views(store)
    store["activeNotifications"] = views["activeNotifications"]
    store["active"] = views["active"]
    store["history"] = views["history"]

    atomic_write_json(ann_file, store, validator_fn=validate_notifications_store)


def load_announcement() -> dict:
    """Tương thích ngược cho các module hoặc endpoint cũ đọc announcement đơn lẻ."""
    store = load_announcements_store()
    if store.get("active"):
        return store["active"]
    elif store.get("history"):
        return store["history"][0]
    return {
        "id": None,
        "title": "Hiện chưa có thông báo kêu gọi nộp quỹ",
        "targetAmountEth": "0",
        "deadline": "Không có",
        "classSize": len(load_roster()) or None,
        "purpose": "Ban cán sự lớp K57 chưa phát động đợt thu quỹ mới. Mọi thông tin thu quỹ chính thức sẽ được công bố tại đây.",
        "status": "none",
        "updatedAt": None,
        "updatedBy": None
    }


def save_announcement(data: dict):
    """Tương thích ngược: tạo thông báo mới vào store mà không làm thay đổi hay đóng các thông báo khác."""
    ann_file = get_announcement_file()
    with DualLayerFileLock(ann_file):
        store = load_announcements_store()
        create_notification(store, data, actor=data.get("updatedBy", "legacy_system"))
        save_announcements_store(store)


# --- BACKGROUND EXPIRATION SCANNER DAEMON ---
_EXPIRATION_SCANNER_STOP = threading.Event()
_EXPIRATION_SCANNER_THREAD: Optional[threading.Thread] = None


def _expiration_scanner_loop(interval_sec: float = 30.0):
    """Vòng lặp chạy nền tự động kiểm tra và chuyển trạng thái thông báo quá hạn sang expired."""
    while not _EXPIRATION_SCANNER_STOP.is_set():
        try:
            ann_file = get_announcement_file()
            if ann_file.exists() and not _is_real_data_write_blocked(ann_file):
                with DualLayerFileLock(ann_file):
                    load_announcements_store()
        except Exception:
            pass
        _EXPIRATION_SCANNER_STOP.wait(interval_sec)


def start_expiration_daemon(interval_sec: float = 30.0):
    """Khởi động daemon thread quét hết hạn thông báo."""
    global _EXPIRATION_SCANNER_THREAD
    if _EXPIRATION_SCANNER_THREAD is None or not _EXPIRATION_SCANNER_THREAD.is_alive():
        _EXPIRATION_SCANNER_STOP.clear()
        _EXPIRATION_SCANNER_THREAD = threading.Thread(
            target=_expiration_scanner_loop,
            args=(interval_sec,),
            daemon=True,
            name="AnnouncementExpirationDaemon"
        )
        _EXPIRATION_SCANNER_THREAD.start()


def stop_expiration_daemon():
    """Dừng daemon thread quét hết hạn thông báo."""
    global _EXPIRATION_SCANNER_THREAD
    _EXPIRATION_SCANNER_STOP.set()
    if _EXPIRATION_SCANNER_THREAD is not None and _EXPIRATION_SCANNER_THREAD.is_alive():
        _EXPIRATION_SCANNER_THREAD.join(timeout=2.0)
    _EXPIRATION_SCANNER_THREAD = None


# =============================================================================
# HTTP REQUEST HANDLER
# =============================================================================

class AIChatRequestHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        origin = self.headers.get("Origin")
        if not origin:
            origin = "http://localhost:3000"

        if origin in DEV_ALLOWED_ORIGINS or (origin == "null" and not IS_PRODUCTION):
            self.send_header("Access-Control-Allow-Origin", origin)
        else:
            self.send_header("Access-Control-Allow-Origin", "http://localhost:3000")

        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
        self.send_header("Access-Control-Max-Age", "86400")

    def send_error(self, code, message=None, explain=None):
        """Đảm bảo mọi phản hồi lỗi HTTP đều có đầy đủ CORS headers và trả về JSON chuẩn."""
        self._send_json(code, {"success": False, "error": message or f"Lỗi HTTP {code}"})

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
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            target_id = query_params.get("id", [None])[0]

            try:
                store = load_announcements_store()
            except CorruptedStorageError as exc:
                self._send_json(500, {
                    "success": False,
                    "code": "CORRUPTED_STORAGE",
                    "error": str(exc),
                })
                return

            views = build_views(store)

            if target_id:
                target_item = next((n for n in views["notifications"] if n.get("id") == target_id), None)
                if not target_item:
                    self._send_json(404, {
                        "success": False,
                        "error": f"Không tìm thấy thông báo có ID '{target_id}'."
                    })
                    return
                audits = store.get("auditLog") or store.get("auditChain") or []
                item_audits = [ev for ev in audits if ev.get("notificationId") == target_id or ev.get("targetId") == target_id]
                self._send_json(200, {
                    "success": True,
                    "revision": int(views.get("revision", store.get("revision", 1))),
                    "timezone": views.get("timezone", store.get("timezone", VN_TZ_KEY)),
                    "notification": target_item,
                    "announcement": target_item,
                    "auditTrail": item_audits,
                })
                return

            # Gắn tiến độ độc lập từ contribution_store vào từng thông báo active & history
            roster_len = len(load_roster())
            effective_class_sz = roster_len if roster_len > 0 else None

            active_notifs_with_progress = []
            auto_closed_any = False
            for an in views.get("activeNotifications", []):
                an_copy = copy.deepcopy(an)
                nid = an_copy.get("id")
                if nid:
                    prog = get_campaign_progress_view(nid, class_size=effective_class_sz)
                    an_copy["progress"] = prog
                    
                    # TỰ ĐỘNG ĐÓNG ĐỢT THU KHI TOÀN BỘ LỚP ĐÃ NỘP ĐỦ (100% SĨ SỐ)
                    cnt = int(prog.get("contributingWalletsCount", 0))
                    sz = int(prog.get("classSize") or effective_class_sz or 0)
                    if sz > 0 and cnt >= sz:
                        try:
                            auto_reason = f"Đã hoàn thành sớm: 100% sinh viên ({cnt}/{sz} ví) đã nộp đủ quỹ."
                            final_prog = freeze_campaign_progress_record(nid, reason=auto_reason, class_size=sz)
                            archived_item = transition_notification(
                                store,
                                target_id=nid,
                                new_status=NotificationStatus.ARCHIVED,
                                reason=auto_reason,
                                actor="SYSTEM_AUTO_EXEC",
                            )
                            archived_item["finalProgress"] = final_prog
                            archived_item["progress"] = prog
                            auto_closed_any = True
                            continue  # Chuyển vào lịch sử, không đưa vào danh sách active nữa
                        except Exception:
                            pass
                active_notifs_with_progress.append(an_copy)

            if auto_closed_any:
                try:
                    save_announcements_store(store)
                    views = build_views(store)
                except Exception as ex:
                    logger.warning("Không thể lưu trạng thái tự động đóng đợt thu: %s", ex)

            history_with_progress = []
            for hn in views.get("history", []):
                hn_copy = copy.deepcopy(hn)
                nid = hn_copy.get("id")
                if nid:
                    hn_copy["progress"] = get_campaign_progress_view(nid, class_size=effective_class_sz)
                history_with_progress.append(hn_copy)

            fallback = views["active"] or (views["history"][0] if views["history"] else {
                "id": None,
                "title": "Hiện chưa có thông báo kêu gọi nộp quỹ",
                "targetAmountEth": "0",
                "status": "none",
                "classSize": effective_class_sz,
                "deadline": "Không có",
                "purpose": "Ban cán sự lớp K57 chưa phát động đợt thu quỹ mới. Mọi thông tin thu quỹ chính thức sẽ được công bố tại đây."
            })
            valid_chain, chain_err = verify_audit_chain(store)
            audits = store.get("auditLog") or store.get("auditChain") or []
            self._send_json(200, {
                "success": True,
                "revision": int(views.get("revision", store.get("revision", 1))),
                "timezone": views.get("timezone", store.get("timezone", VN_TZ_KEY)),
                "announcement": fallback,
                "active": active_notifs_with_progress[0] if active_notifs_with_progress else None,
                "activeNotifications": active_notifs_with_progress,
                "history": history_with_progress,
                "notifications": views["notifications"],
                "auditChainSummary": {
                    "length": len(audits),
                    "valid": valid_chain,
                    "error": chain_err,
                }
            })

        # 4b. Lấy riêng danh sách lịch sử thông báo (GET /api/announcement/history)
        elif path == "/api/announcement/history":
            try:
                store = load_announcements_store()
            except CorruptedStorageError as exc:
                self._send_json(500, {
                    "success": False,
                    "code": "CORRUPTED_STORAGE",
                    "error": str(exc),
                })
                return

            views = build_views(store)
            roster_len = len(load_roster())
            effective_class_sz = roster_len if roster_len > 0 else None

            history_with_progress = []
            for hn in views.get("history", []):
                hn_copy = copy.deepcopy(hn)
                nid = hn_copy.get("id")
                if nid:
                    hn_copy["progress"] = get_campaign_progress_view(nid, class_size=effective_class_sz)
                history_with_progress.append(hn_copy)

            self._send_json(200, {
                "success": True,
                "revision": int(views.get("revision", store.get("revision", 1))),
                "timezone": views.get("timezone", store.get("timezone", VN_TZ_KEY)),
                "count": len(views["history"]),
                "history": history_with_progress
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

        # 5b. Truy vấn mã băm danh bạ lớp on-chain (GET /api/roster/hash - Phase 3 / Mục D)
        # BẢO VỆ QUYỀN RIÊNG TƯ TUYỆT ĐỐI:
        # Endpoint trả về mã băm keccak256 và siêu dữ liệu kỹ thuật, TUYỆT ĐỐI KHÔNG chứa PII (Họ tên, MSSV, Ví).
        # Phục vụ đối soát tính toàn vẹn của danh bạ off-chain với rosterHash lưu trên hợp đồng ProjectCore.
        elif path == "/api/roster/hash":
            try:
                roster = load_roster()
            except CorruptedStorageError as cse:
                logger.error("Lỗi hỏng dữ liệu lưu trữ khi đọc danh bạ: %s", cse, exc_info=True)
                self._send_json(500, {
                    "success": False,
                    "code": "CORRUPTED_STORAGE",
                    "error": "Tệp danh bạ sinh viên bị lỗi cấu trúc hoặc hư hỏng dữ liệu. Vui lòng kiểm tra lưu trữ trên máy chủ.",
                })
                return
            except Exception as ex:
                logger.error("Lỗi hệ thống khi tải danh bạ: %s", ex, exc_info=True)
                self._send_json(500, {
                    "success": False,
                    "code": "INTERNAL_SERVER_ERROR",
                    "error": "Lỗi nội bộ trên máy chủ khi nạp dữ liệu danh bạ.",
                })
                return

            if not roster:
                self._send_json(400, {
                    "success": False,
                    "code": "ROSTER_EMPTY",
                    "error": "Danh sách sinh viên hiện đang trống, chưa thể tính toán mã băm danh bạ (rosterHash).",
                })
                return

            try:
                hash_payload = build_roster_hash_payload(roster)
                self._send_json(200, {
                    "success": True,
                    **hash_payload
                })
            except ValueError as ve:
                self._send_json(400, {
                    "success": False,
                    "code": "INVALID_ROSTER_DATA",
                    "error": str(ve),
                })
            except Exception as he:
                logger.error("Lỗi khi tính mã băm danh bạ: %s", he, exc_info=True)
                self._send_json(500, {
                    "success": False,
                    "code": "INTERNAL_SERVER_ERROR",
                    "error": "Đã xảy ra lỗi nội bộ khi băm danh bạ sinh viên.",
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
            return

        # 7. Truy vấn tiến độ chiến dịch và trạng thái giao dịch (GET /api/contribution/status)
        elif path == "/api/contribution/status":
            target_tx = qs.get("txHash", [""])[0].strip().lower()
            target_nid = qs.get("notificationId", [""])[0].strip()

            if not target_tx and not target_nid:
                self._send_json(400, {"success": False, "error": "Yêu cầu cung cấp txHash hoặc notificationId."})
                return

            c_store = load_contributions_store()
            resp_payload = {"success": True}

            if target_tx:
                allocated_nid = c_store.get("claimedTxHashes", {}).get(target_tx)
                tx_info = c_store.get("transactions", {}).get(target_tx)
                resp_payload["txHash"] = target_tx
                resp_payload["isAllocated"] = allocated_nid is not None
                resp_payload["allocatedNotificationId"] = allocated_nid
                resp_payload["transaction"] = tx_info

            if target_nid:
                roster_len = len(load_roster())
                resp_payload["notificationId"] = target_nid
                resp_payload["progress"] = get_campaign_progress_view(target_nid, class_size=roster_len or None)

            self._send_json(200, resp_payload)
            return

            student = find_student_by_wallet(target_addr)
            self._send_json(200, {
                "success": True,
                "isMember": student is not None,
                "student": student
            })

        else:
            self._send_json(404, {"error": "Not Found"})

    def _safe_save_announcements(self, store: dict) -> bool:
        """Ghi store thông báo nguyên tử an toàn, phân biệt lỗi bảo vệ dữ liệu và lỗi hệ thống."""
        try:
            save_announcements_store(store)
            return True
        except AtomicStorageError as ase:
            logger.warning("Thao tác lưu trữ bị từ chối do bảo vệ dữ liệu: %s", ase)
            self._send_json(503, {
                "success": False,
                "code": "STORAGE_PROTECTED",
                "error": "Hệ thống lưu trữ đang ở chế độ bảo vệ dữ liệu (Read-Only). Vui lòng cấu hình cho phép ghi dữ liệu trên máy chủ triển khai.",
            })
            return False
        except Exception as ex:
            logger.error("Lỗi hệ thống khi lưu thông báo: %s", ex, exc_info=True)
            self._send_json(500, {
                "success": False,
                "code": "INTERNAL_SERVER_ERROR",
                "error": "Đã xảy ra lỗi nội bộ trên máy chủ khi lưu thông báo. Vui lòng liên hệ quản trị viên.",
            })
            return False

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

            role_title = "Cố vấn học tập" if is_advisor else ("Ban cán sự" if is_bcs else ("Sinh viên" if role == "student" else "Khách vãng lai"))
            self._send_json(200, {
                "success": True,
                "message": "Xác thực chữ ký ví thành công.",
                "token": token,
                "address": claimed_addr,
                "role": role,
                "roleTitle": role_title,
                "isAdvisor": is_advisor,
                "isBcs": is_bcs,
                "expiresIn": SESSION_LIFETIME_SEC,
                "session": {
                    "token": token,
                    "address": claimed_addr,
                    "role": role,
                    "roleTitle": role_title,
                    "isAdvisor": is_advisor,
                    "isBcs": is_bcs,
                    "expiresIn": SESSION_LIFETIME_SEC
                }
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

        # 3. Tạo / Cập nhật / Kết thúc / Thu hồi thông báo nộp quỹ (POST /api/announcement, /api/announcement/close, /api/announcement/revoke)
        # BẢO VỆ BẰNG SESSION (Stage 3B.4)
        elif path in ("/api/announcement", "/api/announcement/close", "/api/announcement/revoke"):
            content_length = int(self.headers.get("Content-Length", 0))
            req_data = {}
            if content_length > 0:
                try:
                    raw_body = self.rfile.read(content_length).decode("utf-8")
                    req_data = json.loads(raw_body)
                except Exception as e:
                    self._send_json(400, {"success": False, "error": f"Dữ liệu JSON không hợp lệ: {str(e)}"})
                    return

            session = get_authenticated_session(self.headers)
            is_close_request = (path == "/api/announcement/close" or req_data.get("action") in ("close", "archive"))
            is_revoke_request = (path == "/api/announcement/revoke" or req_data.get("action") == "revoke")

            # Hỗ trợ tự động chốt sổ đợt thu khi 100% sinh viên trong lớp đã hoàn thành nộp quỹ
            is_auto_complete = is_close_request and (
                req_data.get("autoComplete") is True 
                or req_data.get("isAutoComplete") is True 
                or "100%" in str(req_data.get("reason", ""))
                or "nộp đủ" in str(req_data.get("reason", "")).lower()
            )

            if not is_auto_complete and (not session or session.get("role") not in ["bcs", "advisor"]):
                self._send_json(403, {
                    "success": False,
                    "error": "Truy cập bị từ chối: Yêu cầu phiên xác thực chữ ký của Ban cán sự hoặc Cố vấn học tập."
                })
                return

            expected_revision = req_data.get("expectedRevision")
            client_request_id = req_data.get("clientRequestId")
            actor_addr = session["address"] if (session and session.get("address")) else "SYSTEM_AUTO_EXEC"

            if is_close_request:
                mode = "close"
                action_name = "close_announcement"
            elif is_revoke_request:
                mode = "revoke"
                action_name = "revoke_announcement"
            else:
                mode = str(req_data.get("mode", "create")).strip().lower()
                if mode not in ["create", "edit"]:
                    self._send_json(400, {"success": False, "error": "Tham số mode chỉ chấp nhận 'create' hoặc 'edit'."})
                    return
                action_name = "edit_announcement" if mode == "edit" else "create_announcement"

            ann_file = get_announcement_file()
            with DualLayerFileLock(ann_file):
                try:
                    store = load_announcements_store()
                except CorruptedStorageError as exc:
                    self._send_json(500, {
                        "success": False,
                        "code": "CORRUPTED_STORAGE",
                        "error": str(exc),
                    })
                    return

                try:
                    is_replay, replay_payload = validate_concurrency_and_idempotency(
                        store,
                        expected_revision=expected_revision,
                        client_request_id=client_request_id,
                        action=action_name,
                        actor=actor_addr,
                    )
                except IdempotencyConflictError as exc:
                    self._send_json(409, {
                        "success": False,
                        "code": "IDEMPOTENCY_CONTEXT_MISMATCH",
                        "error": str(exc),
                        "clientRequestId": exc.client_request_id,
                        "savedAction": exc.saved_action,
                        "actualAction": exc.actual_action,
                        "savedActor": exc.saved_actor,
                        "actualActor": exc.actual_actor,
                    })
                    return
                except RevisionConflictError as exc:
                    self._send_json(409, {
                        "success": False,
                        "code": "REVISION_CONFLICT",
                        "error": str(exc),
                        "expectedRevision": exc.expected_revision,
                        "currentRevision": exc.current_revision,
                    })
                    return
                except ValueError as exc:
                    self._send_json(400, {
                        "success": False,
                        "error": str(exc),
                    })
                    return

                if is_replay and replay_payload is not None:
                    self._send_json(200, replay_payload)
                    return

                # 1. Thao tác kết thúc sớm / lưu trữ đợt thu (close/archive)
                if is_close_request:
                    req_target_id = req_data.get("id") or req_data.get("targetId")
                    try:
                        resolved_id = resolve_target_id(store, req_target_id)
                    except ValueError as ve:
                        self._send_json(400, {"success": False, "error": str(ve)})
                        return

                    reason = str(req_data.get("reason") or "Ban cán sự chủ động kết thúc đợt thu").strip()
                    req_wallets_cnt = req_data.get("walletsCount")
                    req_class_sz = req_data.get("classSize")
                    req_raised_eth = req_data.get("raisedEth")
                    try:
                        # Kiểm tra tính Idempotent: Nếu thông báo đã ở trạng thái lưu trữ/đóng trước đó thì trả về thành công ngay
                        existing_item = find_notification(store, resolved_id)
                        if existing_item and existing_item.get("status") in ("archived", "closed", "completed"):
                            views = build_views(store)
                            self._send_json(200, {
                                "success": True,
                                "idempotentReplay": True,
                                "alreadyArchived": True,
                                "message": f"Thông báo '{resolved_id}' đã ở trạng thái kết thúc/lưu trữ trước đó.",
                                "archived": existing_item,
                                "notification": existing_item,
                                "active": views["active"],
                                "activeNotifications": views["activeNotifications"],
                                "history": views["history"],
                            })
                            return

                        # Đóng băng tiến độ cuối cùng của đợt thu (Giai đoạn 2)
                        final_prog = freeze_campaign_progress_record(
                            resolved_id,
                            reason=reason,
                            class_size=int(req_class_sz) if req_class_sz else None,
                            contributing_wallets_count=int(req_wallets_cnt) if req_wallets_cnt else None,
                            raised_eth=str(req_raised_eth) if req_raised_eth else None,
                        )
                        archived_item = transition_notification(
                            store,
                            target_id=resolved_id,
                            new_status=NotificationStatus.ARCHIVED,
                            reason=reason,
                            actor=actor_addr,
                            client_request_id=client_request_id,
                        )
                        archived_item["finalProgress"] = final_prog
                    except (KeyError, ValueError) as err:
                        self._send_json(400, {"success": False, "error": str(err)})
                        return

                    views = build_views(store)
                    resp_payload = {
                        "success": True,
                        "idempotentReplay": False,
                        "message": "Đã kết thúc đợt thu và chuyển vào lịch sử thông báo.",
                        "archived": archived_item,
                        "notification": archived_item,
                        "active": views["active"],
                        "activeNotifications": views["activeNotifications"],
                        "history": views["history"],
                    }
                    new_rev = record_mutation_commit(
                        store,
                        action="close_announcement",
                        actor=actor_addr,
                        client_request_id=client_request_id,
                        response_payload=resp_payload,
                    )
                    resp_payload["revision"] = new_rev
                    if client_request_id:
                        resp_payload["clientRequestId"] = str(client_request_id).strip()
                    if not self._safe_save_announcements(store):
                        return
                    self._send_json(200, resp_payload)
                    return

                # 2. Thao tác thu hồi đợt thu (revoke)
                if is_revoke_request:
                    req_target_id = req_data.get("id") or req_data.get("targetId")
                    try:
                        resolved_id = resolve_target_id(store, req_target_id)
                    except ValueError as ve:
                        self._send_json(400, {"success": False, "error": str(ve)})
                        return

                    reason = str(req_data.get("reason") or "Ban cán sự thu hồi thông báo").strip()
                    try:
                        final_prog = freeze_campaign_progress_record(resolved_id, reason=reason)
                        revoked_item = transition_notification(
                            store,
                            target_id=resolved_id,
                            new_status=NotificationStatus.REVOKED,
                            reason=reason,
                            actor=session["address"],
                            client_request_id=client_request_id,
                        )
                        revoked_item["finalProgress"] = final_prog
                    except (KeyError, ValueError) as err:
                        self._send_json(400, {"success": False, "error": str(err)})
                        return

                    views = build_views(store)
                    resp_payload = {
                        "success": True,
                        "idempotentReplay": False,
                        "message": "Đã thu hồi thông báo thành công.",
                        "revoked": revoked_item,
                        "notification": revoked_item,
                        "active": views["active"],
                        "activeNotifications": views["activeNotifications"],
                        "history": views["history"],
                    }
                    new_rev = record_mutation_commit(
                        store,
                        action="revoke_announcement",
                        actor=session["address"],
                        client_request_id=client_request_id,
                        response_payload=resp_payload,
                    )
                    resp_payload["revision"] = new_rev
                    if client_request_id:
                        resp_payload["clientRequestId"] = str(client_request_id).strip()
                    if not self._safe_save_announcements(store):
                        return
                    self._send_json(200, resp_payload)
                    return

                # 3. Thao tác chỉnh sửa (mode="edit") hoặc tạo mới (mode="create")
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
                req_class_size = req_data.get("classSize")
                if req_class_size is not None and int(req_class_size) > 0:
                    actual_class_size = int(req_class_size)
                elif roster_len > 0:
                    actual_class_size = roster_len
                else:
                    self._send_json(400, {"success": False, "error": "Không thể xác định sĩ số từ danh sách lớp (Roster rỗng hoặc không hợp lệ)."})
                    return
                req_data["classSize"] = actual_class_size

                if mode == "edit":
                    req_target_id = req_data.get("id") or req_data.get("targetId")
                    try:
                        resolved_id = resolve_target_id(store, req_target_id)
                    except ValueError as ve:
                        self._send_json(400, {"success": False, "error": str(ve)})
                        return

                    try:
                        updated_item = edit_notification(
                            store,
                            target_id=resolved_id,
                            updates=req_data,
                            actor=session["address"],
                            client_request_id=client_request_id,
                        )
                    except (KeyError, ValueError) as err:
                        self._send_json(400, {"success": False, "error": str(err)})
                        return

                    announcement_data = updated_item
                    action_name = "edit_announcement"
                else:
                    # mode == "create": Thêm mới độc lập, KHÔNG đóng hay ảnh hưởng bất kỳ thông báo cũ nào!
                    try:
                        announcement_data = create_notification(
                            store,
                            req_data,
                            actor=session["address"],
                            client_request_id=client_request_id,
                        )
                    except (NotificationValidationError, ValueError, KeyError) as nve:
                        self._send_json(400, {"success": False, "error": str(nve)})
                        return
                    action_name = "create_announcement" 

                views = build_views(store)
                resp_payload = {
                    "success": True,
                    "idempotentReplay": False,
                    "mode": mode,
                    "announcement": announcement_data,
                    "active": views["active"],
                    "activeNotifications": views["activeNotifications"],
                    "history": views["history"],
                    "notifications": views["notifications"],
                }
                new_rev = record_mutation_commit(
                    store,
                    action=action_name,
                    actor=session["address"],
                    client_request_id=client_request_id,
                    response_payload=resp_payload,
                )
                resp_payload["revision"] = new_rev
                if client_request_id:
                    resp_payload["clientRequestId"] = str(client_request_id).strip()
                if not self._safe_save_announcements(store):
                    return
                self._send_json(200, resp_payload)
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

            roster_file = get_roster_file()
            with DualLayerFileLock(roster_file):
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
                roster_snapshot = list(roster)

            self._send_json(200, {
                "success": True,
                "message": f"Đã {'cập nhật thông tin' if updated else 'thêm mới'} sinh viên {name} ({mssv}) thành công.",
                "roster": roster_snapshot
            })

        # 4c. Tạo Claim Intent trước khi mở ví MetaMask (POST /api/contribution/intent)
        elif path == "/api/contribution/intent":
            session = get_authenticated_session(self.headers)
            if not session or not session.get("address"):
                self._send_json(401, {
                    "success": False,
                    "error": "Yêu cầu đăng nhập và xác thực ví trước khi tạo ý định nộp quỹ."
                })
                return

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

            target_nid = str(req_data.get("notificationId", "")).strip()
            if not target_nid:
                self._send_json(400, {"success": False, "error": "Thiếu mã đợt thu (notificationId)."})
                return

            # Kiểm tra trạng thái đợt thu từ notification_store
            store = load_announcements_store()
            views = build_views(store)
            active_ids = [a.get("id") for a in views.get("activeNotifications", [])]
            if target_nid not in active_ids:
                self._send_json(400, {
                    "success": False,
                    "error": f"Đợt thu '{target_nid}' hiện không ở trạng thái ACTIVE. Không thể tạo ý định nộp quỹ."
                })
                return

            matching_notif = next((a for a in views["activeNotifications"] if a.get("id") == target_nid), None)
            target_amount = matching_notif.get("targetAmountEth") if matching_notif else None

            try:
                intent_rec = create_claim_intent(
                    notification_id=target_nid,
                    verified_wallet=session["address"],
                    notification_status="active",
                    target_amount_eth=target_amount
                )
                self._send_json(200, {
                    "success": True,
                    "message": "Đã tạo ý định nộp quỹ thành công. Có hiệu lực trong 30 phút.",
                    "intent": intent_rec
                })
            except Exception as e:
                self._send_json(400, {"success": False, "error": str(e)})
            return

        # 4d. Xác minh biên lai on-chain và phân bổ đóng góp (POST /api/contribution/claim)
        elif path == "/api/contribution/claim":
            session = get_authenticated_session(self.headers)
            if not session or not session.get("address"):
                self._send_json(401, {
                    "success": False,
                    "error": "Yêu cầu đăng nhập và xác thực chữ ký ví trước khi gửi claim đóng góp."
                })
                return

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

            target_nid = str(req_data.get("notificationId", "")).strip()
            tx_hash = str(req_data.get("txHash", "")).strip()
            claim_intent_id = req_data.get("claimIntentId")

            if not target_nid or not tx_hash:
                self._send_json(400, {"success": False, "error": "Yêu cầu cung cấp đầy đủ notificationId và txHash."})
                return

            store = load_announcements_store()
            views = build_views(store)
            notif_rec = next((n for n in views["notifications"] if n.get("id") == target_nid), None)
            notif_status = notif_rec.get("status", "none") if notif_rec else "none"
            ended_at_ts = None
            if notif_rec and notif_rec.get("endedAt"):
                from backend.accounting_engine import parse_deadline_to_vn_timestamp
                # Parse endedAt thành timestamp
                try:
                    import datetime
                    dt = datetime.datetime.fromisoformat(str(notif_rec["endedAt"]))
                    ended_at_ts = dt.timestamp()
                except Exception:
                    pass

            roster_len = len(load_roster())
            effective_class_sz = (notif_rec.get("classSize") if notif_rec and notif_rec.get("classSize") else None) or (roster_len if roster_len > 0 else None)
            target_eth_val = notif_rec.get("targetAmountEth") if notif_rec else None

            try:
                claim_res = verify_and_claim_contribution(
                    notification_id=target_nid,
                    tx_hash=tx_hash,
                    verified_wallet=session["address"],
                    claim_intent_id=claim_intent_id,
                    notification_status=notif_status,
                    notification_ended_at_ts=ended_at_ts,
                    class_size=effective_class_sz,
                    target_eth=target_eth_val
                )

                # TỰ ĐỘNG ĐÓNG ĐỢT THU KHI PHÂN BỔ ĐẠT 100% SĨ SỐ LỚP
                if claim_res.get("success") and effective_class_sz and int(effective_class_sz) > 0:
                    cnt = int(claim_res.get("contributingWalletsCount", 0))
                    if cnt >= int(effective_class_sz):
                        try:
                            store = load_announcements_store()
                            auto_reason = f"Đã hoàn thành sớm: 100% sinh viên ({cnt}/{effective_class_sz} ví) đã nộp đủ quỹ."
                            final_prog = freeze_campaign_progress_record(target_nid, reason=auto_reason, class_size=int(effective_class_sz))
                            archived_item = transition_notification(
                                store,
                                target_id=target_nid,
                                new_status=NotificationStatus.ARCHIVED,
                                reason=auto_reason,
                                actor="SYSTEM_AUTO_EXEC",
                            )
                            archived_item["finalProgress"] = final_prog
                            self._safe_save_announcements(store)
                            claim_res["autoClosed"] = True
                            claim_res["autoClosedReason"] = auto_reason
                        except Exception:
                            pass

                self._send_json(200, claim_res)
            except ContributionAttributionError as cae:
                self._send_json(409 if "đã được phân bổ" in str(cae) else 400, {
                    "success": False,
                    "error": str(cae)
                })
            except Exception as exc:
                self._send_json(500, {
                    "success": False,
                    "error": f"Lỗi hệ thống khi xác minh đóng góp: {str(exc)}"
                })
            return

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

            question = (req_data.get("question") or req_data.get("message") or "").strip()
            if not question:
                self._send_json(400, {"success": False, "error": "Vui lòng nhập câu hỏi."})
                return

            try:
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
                    "bcsMembers": raw_onchain.get("bcsMembers", []),
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
            except Exception as e:
                sys.stdout.write(f"[AI Backend Fatal] Lỗi xử lý chat: {str(e)}\n")
                sys.stdout.flush()
                self._send_json(500, {"success": False, "error": f"Lỗi nội bộ máy chủ AI: {str(e)}"})

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
    httpd = ThreadingHTTPServer(server_address, AIChatRequestHandler)
    ai_service = AIAssistantService()
    start_expiration_daemon(interval_sec=30.0)
    print("=" * 65, flush=True)
    print(f"🚀 KTS-Class-Fund Backend (Auth Protected) đang chạy tại http://localhost:{PORT}", flush=True)
    print(f"   Xác thực: Challenge-Response Signature (eth_account)", flush=True)
    print(f"   Trạng thái Gemini API Key: {'ĐÃ CẤU HÌNH' if ai_service.is_configured() else 'CHƯA CẤU HÌNH'}", flush=True)
    print(f"   Quét hết hạn nền (Background Scanner): ĐANG HOẠT ĐỘNG (chu kỳ 30s)", flush=True)
    print("=" * 65, flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nĐang dừng máy chủ...", flush=True)
        stop_expiration_daemon()
        httpd.server_close()


if __name__ == "__main__":
    run_server()
