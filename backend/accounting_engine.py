#!/usr/bin/env python3
"""
Module Hạch Toán & Lưu Trữ Nguyên Tử Quỹ Lớp K57 (Phase 1 - V4.4)
Dự án: KTS-Class-Fund-K57

Phạm vi Phase 1 (Đã phê duyệt có điều kiện):
1. Xử lý múi giờ chuẩn Asia/Ho_Chi_Minh (ZoneInfo) độc lập với múi giờ hệ điều hành.
2. Sao lưu ban đầu bất biến (announcements.pre_v4_migration.bak) và kiểm chứng JSON/SHA-256.
3. Khóa đồng bộ đa tầng (In-process threading.RLock + Cross-process File Lock msvcrt/fcntl).
4. Ghi nguyên tử 7 bước (Atomic Write via .tmp -> flush -> fsync -> verify -> .bak -> os.replace)
   và cơ chế tự phục hồi an toàn từ bản .bak đã xác minh (dừng & báo lỗi nếu cả chính và .bak đều hỏng).
5. Kiểm soát tương tranh lạc quan (revision / expectedRevision -> HTTP 409 Conflict)
   và chống ghi trùng (clientRequestId idempotency).
6. Hash kiểm toán (recordSha256) kèm trường liên kết chuỗi (previousRecordHash) sẵn sàng cho Phase 2.
   LƯU Ý GIỚI HẠN BẢO MẬT: Một mã băm recordSha256 đơn lẻ chỉ phát hiện lỗi hỏng dữ liệu ngẫu nhiên
   hoặc chỉnh sửa thủ công quên tính lại hash; tự thân hash đơn lẻ KHÔNG bảo đảm tính bất biến trước
   tác nhân có quyền ghi file và tính lại hash. Do đó mọi bản ghi đều tích hợp sẵn previousRecordHash
   để nối chuỗi băm (Hash Chain) đối chiếu chéo ở giai đoạn tiếp theo.
7. Migration Schema V1 -> Schema V2 (thử nghiệm an toàn trên bản sao / thư mục tạm) và chính sách
   phân loại giao dịch tại giây biên trùng nhau (1793619753) giữa ann-k57-hk1 và ann-20261102114233.
"""

from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import re
import secrets
import shutil
import struct
import sys
import tempfile
import threading
import time
import zoneinfo
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

# =============================================================================
# 1. CẤU HÌNH MÚI GIỜ CHUẨN ASIA/HO_CHI_MINH & ĐỔI ĐƠN VỊ WEI <-> ETH
# =============================================================================

VN_TZ_KEY = "Asia/Ho_Chi_Minh"
WEI_PER_ETH = Decimal("1000000000000000000")
BOUNDARY_WINDOW_SECONDS = 12
PROCESSED_REQUEST_TTL_SECONDS = 86400  # 24 giờ
GENESIS_PREV_HASH = "0" * 64
AUDIT_HASH_SPEC_VERSION = "v4.4-sha256-chain-ready-v1"
AUDIT_HASH_LIMITATION_NOTE = (
    "SINGLE_HASH_LIMITATION: recordSha256 đơn lẻ chỉ giúp phát hiện lỗi hỏng file hoặc "
    "sửa trực tiếp nội dung JSON mà không tính lại mã băm; KHÔNG tự bảo đảm tính bất biến "
    "nếu kẻ tấn công sửa đồng thời cả dữ liệu lẫn hash. Cấu trúc này đã gắn sẵn previousRecordHash "
    "để liên kết Hash Chain bất biến ở giai đoạn tiếp theo."
)


def _build_vn_tzif_bytes() -> bytes:
    """
    Tạo dữ liệu nhị phân chuẩn RFC 8536 TZif v2 cho múi giờ Asia/Ho_Chi_Minh (UTC+07:00 cố định).
    Dùng để nạp vào zoneinfo.TZPATH trong trường hợp máy chủ Windows chưa cài gói pip `tzdata`,
    bảo đảm `ZoneInfo("Asia/Ho_Chi_Minh")` luôn hoạt động chuẩn xác trên mọi môi trường Python 3.10+.
    """
    header = b"TZif2" + (b"\x00" * 15) + struct.pack(">6l", 1, 1, 0, 0, 1, 4)
    # utoff = +7 giờ = 25200 giây, dst = 0, idx = 0, abbrev = "+07\x00", ttisstd = 0, ttisut = 0
    data_block = struct.pack(">lBB", 25200, 0, 0) + b"+07\x00\x00\x00"
    footer = b"\n<-07>-7\n"
    return header + data_block + header + data_block + footer


def _ensure_vn_zoneinfo_available() -> None:
    """Bảo đảm `ZoneInfo("Asia/Ho_Chi_Minh")` luôn khởi tạo thành công."""
    try:
        ZoneInfo(VN_TZ_KEY)
        return
    except Exception:
        pass

    tz_root = Path(tempfile.gettempdir()) / "kts_k57_tzdata_v44"
    tz_file = tz_root / "Asia" / "Ho_Chi_Minh"
    try:
        tz_file.parent.mkdir(parents=True, exist_ok=True)
        if not tz_file.exists():
            tz_file.write_bytes(_build_vn_tzif_bytes())
        current_paths = list(zoneinfo.TZPATH)
        if str(tz_root) not in current_paths:
            zoneinfo.reset_tzpath([str(tz_root)] + current_paths)
        ZoneInfo.clear_cache()
    except Exception:
        pass


_ensure_vn_zoneinfo_available()


def get_vn_tz() -> ZoneInfo:
    """Trả về đối tượng chuẩn `ZoneInfo("Asia/Ho_Chi_Minh")`."""
    _ensure_vn_zoneinfo_available()
    try:
        return ZoneInfo(VN_TZ_KEY)
    except Exception:
        return ZoneInfo.from_file(io.BytesIO(_build_vn_tzif_bytes()), key=VN_TZ_KEY)


def eth_to_wei_str(amount_eth: str | float | int | Decimal) -> str:
    """Chuyển đổi chính xác số lượng ETH sang chuỗi số nguyên Wei bằng Decimal."""
    if amount_eth is None or str(amount_eth).strip() == "":
        return "0"
    try:
        dec_eth = Decimal(str(amount_eth).strip())
        if dec_eth < 0:
            raise ValueError("Số lượng ETH không được âm.")
        wei_val = int((dec_eth * WEI_PER_ETH).to_integral_value())
        return str(wei_val)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Giá trị ETH không hợp lệ: {amount_eth}") from exc


def wei_to_eth_str(amount_wei: str | int) -> str:
    """Đổi Wei sang chuỗi ETH chuẩn trước khi hiển thị (Tuân thủ quy tắc AGENTS.md)."""
    if amount_wei is None or str(amount_wei).strip() == "":
        return "0"
    try:
        dec_wei = Decimal(int(str(amount_wei).strip()))
        dec_eth = dec_wei / WEI_PER_ETH
        formatted = f"{dec_eth:.18f}".rstrip("0").rstrip(".")
        return formatted if formatted else "0"
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Giá trị Wei không hợp lệ: {amount_wei}") from exc


def parse_deadline_to_vn_timestamp(deadline_str: str) -> Optional[int]:
    """
    Phân tích chuỗi thời hạn (tiếng Việt hoặc ISO-8601) thành Unix timestamp (int giây)
    theo đúng múi giờ `Asia/Ho_Chi_Minh` (+07:00), tuyệt đối không phụ thuộc múi giờ hệ điều hành.
    """
    if not deadline_str:
        return None
    s = str(deadline_str).strip()
    if not s or s.lower() in ["chưa xác định", "không có", "none", "null"]:
        return None

    vn_tz = get_vn_tz()

    # 1. Định dạng: 'HH:MM:SS ngày DD/MM/YYYY' hoặc 'HH:MM ngày DD/MM/YYYY'
    m_time_date = re.search(
        r"(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?\s*ngày\s*(\d{1,2})/(\d{1,2})/(\d{4})",
        s,
        re.IGNORECASE,
    )
    if m_time_date:
        hr = int(m_time_date.group(1))
        mn = int(m_time_date.group(2))
        sec = int(m_time_date.group(3)) if m_time_date.group(3) is not None else 0
        day = int(m_time_date.group(4))
        mon = int(m_time_date.group(5))
        yr = int(m_time_date.group(6))
        try:
            dt = datetime(yr, mon, day, hr, mn, sec, tzinfo=vn_tz)
            return int(dt.timestamp())
        except ValueError:
            return None

    # 2. Định dạng chỉ có ngày: 'DD/MM/YYYY' -> mặc định cuối ngày 23:59:59 Asia/Ho_Chi_Minh
    m_date_only = re.fullmatch(r"(?:ngày\s*)?(\d{1,2})/(\d{1,2})/(\d{4})", s, re.IGNORECASE)
    if m_date_only:
        day, mon, yr = map(int, m_date_only.groups())
        try:
            dt = datetime(yr, mon, day, 23, 59, 59, tzinfo=vn_tz)
            return int(dt.timestamp())
        except ValueError:
            return None

    # 3. Định dạng ISO-8601 (예: '2026-11-02T23:59:00+07:00', '2026-10-20T00:00:00Z', '2026-11-02')
    try:
        clean_s = s.replace("Z", "+00:00")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", clean_s):
            yr, mon, day = map(int, clean_s.split("-"))
            dt = datetime(yr, mon, day, 23, 59, 59, tzinfo=vn_tz)
            return int(dt.timestamp())
        dt = datetime.fromisoformat(clean_s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=vn_tz)
        return int(dt.timestamp())
    except ValueError:
        return None


def parse_iso_timestamp_detail(iso_str: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Phân tích chuỗi thời gian ISO-8601 thành thông tin chi tiết gồm:
    - timestampInt (int giây Unix)
    - timestampFloat (float giây có phần thập phân microsecond)
    - isoUtc (chuỗi ISO ở UTC)
    - isoVn (chuỗi ISO ở Asia/Ho_Chi_Minh +07:00)
    """
    if not iso_str or not str(iso_str).strip():
        return None
    vn_tz = get_vn_tz()
    clean_s = str(iso_str).strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(clean_s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=vn_tz)
    ts_float = dt.timestamp()
    ts_int = int(ts_float)
    return {
        "raw": str(iso_str),
        "timestampInt": ts_int,
        "timestampFloat": ts_float,
        "isoUtc": dt.astimezone(timezone.utc).isoformat(),
        "isoVn": dt.astimezone(vn_tz).isoformat(),
    }


def verify_timestamp_vn(
    timestamp_val: int | float,
    expected_year: int,
    expected_month: int,
    expected_day: int,
    expected_hour: int,
    expected_minute: int,
    expected_second: int = 0,
) -> Dict[str, Any]:
    """
    Kiểm tra ngược Unix timestamp sang múi giờ `Asia/Ho_Chi_Minh` để xác nhận đúng
    ngày, giờ, phút, giây và độ lệch UTC+07:00.
    """
    vn_tz = get_vn_tz()
    dt_vn = datetime.fromtimestamp(float(timestamp_val), tz=vn_tz)
    matches = (
        dt_vn.year == expected_year
        and dt_vn.month == expected_month
        and dt_vn.day == expected_day
        and dt_vn.hour == expected_hour
        and dt_vn.minute == expected_minute
        and dt_vn.second == expected_second
        and dt_vn.utcoffset() == timedelta(hours=7)
    )
    return {
        "matches": matches,
        "timestamp": int(timestamp_val),
        "isoVn": dt_vn.isoformat(),
        "timezone": dt_vn.tzname() or VN_TZ_KEY,
        "utcOffsetHours": 7,
        "actual": {
            "year": dt_vn.year,
            "month": dt_vn.month,
            "day": dt_vn.day,
            "hour": dt_vn.hour,
            "minute": dt_vn.minute,
            "second": dt_vn.second,
        },
    }


def get_vn_day_bounds(year: int, month: int, day: int) -> Dict[str, int]:
    """
    Trả về Unix timestamp (int) cho các mốc trong ngày theo múi giờ Asia/Ho_Chi_Minh:
    - startOfDayTs: 00:00:00+07:00
    - deadlineMinuteTs: 23:59:00+07:00
    - endOfDayTs: 23:59:59+07:00
    """
    vn_tz = get_vn_tz()
    start_dt = datetime(year, month, day, 0, 0, 0, tzinfo=vn_tz)
    dl_min_dt = datetime(year, month, day, 23, 59, 0, tzinfo=vn_tz)
    end_dt = datetime(year, month, day, 23, 59, 59, tzinfo=vn_tz)
    return {
        "startOfDayTs": int(start_dt.timestamp()),
        "deadlineMinuteTs": int(dl_min_dt.timestamp()),
        "endOfDayTs": int(end_dt.timestamp()),
    }


# =============================================================================
# 2. HASH KIỂM TOÁN (recordSha256 & previousRecordHash CHAIN READINESS)
# =============================================================================

def canonical_json_bytes(payload: Dict[str, Any]) -> bytes:
    """Tuần tự hóa dict thành chuỗi JSON chuẩn hóa (sorted keys, không khoảng trắng thừa, UTF-8)."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_record_sha256(
    record: Dict[str, Any],
    previous_record_hash: str = GENESIS_PREV_HASH,
) -> str:
    """
    Tính mã băm SHA-256 cho một bản ghi kiểm toán/chiến dịch.
    Bao gồm `previousRecordHash` trong dữ liệu đầu vào của hàm băm để sẵn sàng cho Hash Chain.
    """
    if not isinstance(record, dict):
        raise ValueError("Bản ghi cần tính hash phải là một dict.")
    clean_copy = copy.deepcopy(record)
    clean_copy.pop("recordSha256", None)
    clean_copy["previousRecordHash"] = str(previous_record_hash or GENESIS_PREV_HASH)
    clean_copy["hashSpecVersion"] = AUDIT_HASH_SPEC_VERSION
    return hashlib.sha256(canonical_json_bytes(clean_copy)).hexdigest()


def attach_record_audit_hash(
    record: Dict[str, Any],
    previous_record_hash: str = GENESIS_PREV_HASH,
    seq: int = 1,
) -> Dict[str, Any]:
    """Gắn `seq`, `previousRecordHash`, `hashSpecVersion` và `recordSha256` vào bản ghi."""
    enriched = copy.deepcopy(record)
    enriched["seq"] = int(seq)
    enriched["previousRecordHash"] = str(previous_record_hash or GENESIS_PREV_HASH)
    enriched["hashSpecVersion"] = AUDIT_HASH_SPEC_VERSION
    enriched["recordSha256"] = compute_record_sha256(enriched, previous_record_hash=enriched["previousRecordHash"])
    return enriched


def verify_record_audit_hash(record: Dict[str, Any]) -> bool:
    """Kiểm tra tính toàn vẹn của `recordSha256` trên một bản ghi đơn lẻ."""
    if not isinstance(record, dict):
        return False
    required_fields = ("seq", "previousRecordHash", "hashSpecVersion", "recordSha256")
    for field_name in required_fields:
        if field_name not in record or record.get(field_name) is None:
            return False
    if not isinstance(record.get("seq"), int) or isinstance(record.get("seq"), bool) or record["seq"] < 1:
        return False
    prev_hash = str(record.get("previousRecordHash"))
    if not prev_hash:
        return False
    expected = compute_record_sha256(record, previous_record_hash=prev_hash)
    return secrets.compare_digest(str(record["recordSha256"]), expected)


HASH_CHAIN_TAIL_TRUNCATION_NOTE = (
    "TAIL_TRUNCATION_LIMITATION: Kiểm tra liên kết nội bộ (seq, previousRecordHash, recordSha256) "
    "phát hiện mọi hành vi sửa, xóa giữa chuỗi, chèn hoặc đảo thứ tự, nhưng KHÔNG THỂ tự phát hiện "
    "việc cắt bỏ bản ghi cuối cùng (tail truncation) nếu không đối chiếu với expected_tail_hash "
    "hoặc expected_length từ một checkpoint đáng tin cậy."
)


def verify_record_hash_chain(
    records: List[Dict[str, Any]],
    expected_tail_hash: Optional[str] = None,
    expected_length: Optional[int] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Kiểm tra tính toàn vẹn của chuỗi băm (Hash Chain):
    1. Kiểm tra `seq` bắt đầu từ 1 và tăng liên tục đúng +1 (`seq == idx + 1`).
    2. Kiểm tra đầy đủ các trường bắt buộc (`seq`, `previousRecordHash`, `hashSpecVersion`, `recordSha256`).
    3. Kiểm tra `previousRecordHash` khớp với `recordSha256` của bản ghi liền trước (`GENESIS_PREV_HASH` tại `seq=1`).
    4. Kiểm tra `recordSha256` khớp với kết quả băm chuẩn hóa của bản ghi (không bao giờ tự tạo lại hash để hợp thức hóa dữ liệu bị sửa).
    5. Hỗ trợ đối chiếu `expected_length` và `expected_tail_hash` khi được cung cấp để phát hiện cắt cụt đuôi (tail truncation).
       Lưu ý: Nếu không cung cấp `expected_tail_hash` hoặc `expected_length`, việc kiểm tra chỉ dựa trên liên kết nội bộ
       không thể phát hiện chắc chắn trường hợp bản ghi cuối chuỗi bị cắt bỏ.
    """
    if not isinstance(records, list):
        return False, "Danh sách bản ghi kiểm tra Hash Chain phải là một list."

    if expected_length is not None:
        if len(records) != int(expected_length):
            return (
                False,
                f"Sai lệch độ dài chuỗi Hash Chain (expected_length={expected_length}, actual={len(records)}).",
            )

    expected_prev = GENESIS_PREV_HASH
    for idx, rec in enumerate(records):
        if not isinstance(rec, dict):
            return False, f"Bản ghi tại vị trí {idx} không phải là dict."

        for req_key in ("seq", "previousRecordHash", "hashSpecVersion", "recordSha256"):
            if req_key not in rec or rec.get(req_key) is None or str(rec.get(req_key)).strip() == "":
                return False, f"Bản ghi tại index {idx} thiếu trường bắt buộc '{req_key}'."

        actual_seq = rec.get("seq")
        expected_seq = idx + 1
        if not isinstance(actual_seq, int) or isinstance(actual_seq, bool) or actual_seq != expected_seq:
            return (
                False,
                f"Sai lệch số thứ tự seq tại index {idx}: kỳ vọng {expected_seq}, thực tế {actual_seq}.",
            )

        actual_prev = str(rec.get("previousRecordHash", ""))
        if actual_prev != expected_prev:
            return (
                False,
                f"Đứt gãy chuỗi previousRecordHash tại index {idx}: kỳ vọng {expected_prev}, thực tế {actual_prev}.",
            )

        if not verify_record_audit_hash(rec):
            return False, f"Sai lệch recordSha256 tại index {idx} (id={rec.get('adjustmentId') or rec.get('id')})."

        expected_prev = str(rec["recordSha256"])

    if expected_tail_hash is not None:
        clean_expected_tail = str(expected_tail_hash).strip()
        if expected_prev != clean_expected_tail:
            return (
                False,
                f"Sai lệch expected_tail_hash (phát hiện cắt cụt đuôi hoặc sai checkpoint): "
                f"kỳ vọng {clean_expected_tail}, thực tế {expected_prev}.",
            )

    return True, None


# =============================================================================
# 3. EXCEPTION TÙY BIẾN CHO LƯU TRỮ NGUYÊN TỬ & KIỂM SOÁT TƯƠNG TRANH
# =============================================================================

class StorageError(Exception):
    """Lỗi cơ sở của tầng lưu trữ."""


class AtomicStorageError(StorageError):
    """Lỗi xảy ra trong quá trình ghi nguyên tử hoặc khóa file."""


class CorruptedStorageError(StorageError):
    """Lỗi nghiêm trọng khi cả file dữ liệu chính và file backup đều không hợp lệ."""


class RevisionConflictError(StorageError):
    """Lỗi xung đột phiên bản (Optimistic Concurrency Control - HTTP 409 Conflict)."""

    def __init__(self, expected_revision: int, current_revision: int, message: str = ""):
        self.expected_revision = expected_revision
        self.current_revision = current_revision
        super().__init__(
            message
            or f"Xung đột phiên bản dữ liệu (expectedRevision={expected_revision}, currentRevision={current_revision})."
        )


class IdempotencyConflictError(StorageError):
    """Lỗi khi tái sử dụng clientRequestId cũ nhưng khác action hoặc khác actor (HTTP 409 Conflict)."""

    def __init__(
        self,
        client_request_id: str,
        saved_action: str,
        actual_action: str,
        saved_actor: str,
        actual_actor: str,
        message: str = "",
    ):
        self.client_request_id = client_request_id
        self.saved_action = saved_action
        self.actual_action = actual_action
        self.saved_actor = saved_actor
        self.actual_actor = actual_actor
        super().__init__(
            message
            or (
                f"Xung đột ngữ cảnh Idempotency cho clientRequestId='{client_request_id}': "
                f"đã lưu (action='{saved_action}', actor='{saved_actor}'), "
                f"nhưng yêu cầu mới là (action='{actual_action}', actor='{actual_actor}')."
            )
        )


# =============================================================================
# 4. KHÓA ĐỒNG BỘ ĐA TẦNG (IN-PROCESS RLOCK + CROSS-PROCESS FILE LOCK)
# =============================================================================

_PROCESS_LOCKS_GUARD = threading.Lock()
_PROCESS_RLOCKS: Dict[str, threading.RLock] = {}


def _get_inprocess_rlock(target_path: Path) -> threading.RLock:
    canonical_key = str(target_path.resolve())
    with _PROCESS_LOCKS_GUARD:
        if canonical_key not in _PROCESS_RLOCKS:
            _PROCESS_RLOCKS[canonical_key] = threading.RLock()
        return _PROCESS_RLOCKS[canonical_key]


class DualLayerFileLock:
    """
    Cơ chế khóa kép:
    1. Trong tiến trình (In-process): `threading.RLock()` theo từng đường dẫn file tuyệt đối.
    2. Liên tiến trình (Cross-process): OS-level file lock trên `<target>.lock` bằng
       `msvcrt.locking` (Windows) hoặc `fcntl.flock` (POSIX).
    Hỗ trợ re-entrant trong cùng một thread của cùng một tiến trình.
    """

    _thread_local = threading.local()

    def __init__(self, target_path: Path, timeout_sec: float = 10.0, poll_interval_sec: float = 0.02):
        self.target_path = Path(target_path).resolve()
        self.lock_file_path = self.target_path.with_name(self.target_path.name + ".lock")
        self.timeout_sec = float(timeout_sec)
        self.poll_interval_sec = float(poll_interval_sec)
        self._rlock = _get_inprocess_rlock(self.target_path)
        self._fd: Optional[int] = None
        self._owns_os_lock = False

    def _get_active_set(self) -> set:
        if not hasattr(self._thread_local, "held_os_locks"):
            self._thread_local.held_os_locks = set()
        return self._thread_local.held_os_locks

    def acquire(self) -> None:
        deadline = time.monotonic() + self.timeout_sec
        acquired_rlock = self._rlock.acquire(timeout=self.timeout_sec)
        if not acquired_rlock:
            raise AtomicStorageError(f"Quá thời gian chờ khóa luồng nội bộ cho file: {self.target_path}")

        key = str(self.lock_file_path)
        active_set = self._get_active_set()
        if key in active_set:
            # Thread hiện tại đã giữ khóa OS trên file này (re-entrant)
            self._owns_os_lock = False
            return

        try:
            self.lock_file_path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(str(self.lock_file_path), os.O_CREAT | os.O_RDWR, 0o666)
            # Đảm bảo file lock có ít nhất 1 byte để msvcrt.locking khóa vùng byte [0..1]
            if os.fstat(fd).st_size == 0:
                os.write(fd, b"L")
                os.fsync(fd)
            os.lseek(fd, 0, os.SEEK_SET)

            while True:
                try:
                    if sys.platform == "win32":
                        import msvcrt

                        os.lseek(fd, 0, os.SEEK_SET)
                        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError as exc:
                    if time.monotonic() >= deadline:
                        os.close(fd)
                        raise AtomicStorageError(
                            f"Quá thời gian chờ khóa file liên tiến trình ({self.timeout_sec}s): {self.lock_file_path}"
                        ) from exc
                    time.sleep(self.poll_interval_sec)

            self._fd = fd
            self._owns_os_lock = True
            active_set.add(key)
        except Exception:
            self._rlock.release()
            raise

    def release(self) -> None:
        key = str(self.lock_file_path)
        active_set = self._get_active_set()
        try:
            if self._owns_os_lock and self._fd is not None:
                try:
                    if sys.platform == "win32":
                        import msvcrt

                        os.lseek(self._fd, 0, os.SEEK_SET)
                        msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(self._fd, fcntl.LOCK_UN)
                finally:
                    os.close(self._fd)
                    self._fd = None
                    self._owns_os_lock = False
                    active_set.discard(key)
        finally:
            self._rlock.release()

    def __enter__(self) -> "DualLayerFileLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()


# =============================================================================
# 5. SAO LƯU BAN ĐẦU, KIỂM CHỨNG BACKUP & GHI NGUYÊN TỬ 7 BƯỚC
# =============================================================================

def compute_file_sha256(file_path: Path) -> str:
    """Tính SHA-256 của nội dung file trên đĩa."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_announcement_store_structure(data: Any) -> Tuple[bool, Optional[str]]:
    """
    Kiểm tra cấu trúc hợp lệ của dữ liệu thông báo/chiến dịch (hỗ trợ cả Schema V1 và Schema V2).
    """
    if not isinstance(data, dict):
        return False, "Root JSON phải là một đối tượng (dict)."

    schema_ver = data.get("schemaVersion", 1)
    if schema_ver == 2:
        required_v2_keys = [
            "schemaVersion",
            "revision",
            "campaigns",
            "voluntaryContributions",
            "refundRequests",
            "manualAdjustments",
            "reconciliation",
            "syncState",
            "processedRequests",
            "active",
            "history",
        ]
        for k in required_v2_keys:
            if k not in data:
                return False, f"Thiếu trường bắt buộc của Schema V2: '{k}'."
        if not isinstance(data["revision"], int) or data["revision"] < 1:
            return False, "Trường 'revision' phải là số nguyên dương >= 1."
        if not isinstance(data["campaigns"], dict):
            return False, "Trường 'campaigns' phải là dict."
        if not isinstance(data["history"], list):
            return False, "Trường 'history' phải là list."
        return True, None

    # Schema V1 hoặc legacy announcement
    if "active" in data or "history" in data:
        if "history" in data and not isinstance(data["history"], list):
            return False, "Trường 'history' trong Schema V1 phải là một danh sách (list)."
        if data.get("active") is not None and not isinstance(data.get("active"), dict):
            return False, "Trường 'active' phải là dict hoặc null."
        return True, None

    if "title" in data or "id" in data:
        return True, None

    return False, "Cấu trúc JSON không khớp với Schema V1 hoặc Schema V2 của hệ thống thông báo."


def verify_json_backup_file(
    backup_path: Path,
    validator_fn: Optional[Callable[[Any], Tuple[bool, Optional[str]]]] = validate_announcement_store_structure,
) -> Dict[str, Any]:
    """
    Đọc và xác minh một file backup có tồn tại, đọc được bằng JSON và đạt chuẩn cấu trúc hay không.
    """
    backup_path = Path(backup_path)
    if not backup_path.exists():
        return {
            "exists": False,
            "isValidJson": False,
            "isValidSchema": False,
            "sha256": None,
            "sizeBytes": 0,
            "error": f"File backup không tồn tại: {backup_path}",
            "data": None,
        }

    try:
        size_bytes = backup_path.stat().st_size
        if size_bytes == 0:
            return {
                "exists": True,
                "isValidJson": False,
                "isValidSchema": False,
                "sha256": None,
                "sizeBytes": 0,
                "error": "File backup rỗng (0 bytes).",
                "data": None,
            }
        sha256_hex = compute_file_sha256(backup_path)
        with open(backup_path, "r", encoding="utf-8") as f:
            parsed = json.load(f)
    except Exception as exc:
        return {
            "exists": True,
            "isValidJson": False,
            "isValidSchema": False,
            "sha256": None,
            "sizeBytes": backup_path.stat().st_size if backup_path.exists() else 0,
            "error": f"Không thể đọc JSON từ bản backup: {exc}",
            "data": None,
        }

    if validator_fn is not None:
        ok, err_msg = validator_fn(parsed)
        if not ok:
            return {
                "exists": True,
                "isValidJson": True,
                "isValidSchema": False,
                "sha256": sha256_hex,
                "sizeBytes": size_bytes,
                "error": f"Cấu trúc dữ liệu backup không hợp lệ: {err_msg}",
                "data": None,
            }

    return {
        "exists": True,
        "isValidJson": True,
        "isValidSchema": True,
        "sha256": sha256_hex,
        "sizeBytes": size_bytes,
        "error": None,
        "data": parsed,
    }


def ensure_initial_pre_v4_backup(
    source_path: Path,
    backup_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Tạo bản sao lưu ban đầu `announcements.pre_v4_migration.bak` từ `source_path`.
    QUY TẮC BẮT BUỘC:
    - Nếu file backup đã tồn tại: TUYỆT ĐỐI KHÔNG GHI ĐÈ (`overwritten = False`),
      nhưng vẫn kiểm tra và xác nhận bản backup hiện có đọc được bằng JSON hợp lệ.
    - Nếu chưa tồn tại: Sao chép nguyên vẹn qua file tạm, flush + fsync, kiểm tra JSON + SHA-256
      trước khi chốt tên file backup.
    """
    source_path = Path(source_path).resolve()
    if backup_path is None:
        backup_path = source_path.with_name("announcements.pre_v4_migration.bak")
    else:
        backup_path = Path(backup_path).resolve()

    with DualLayerFileLock(source_path):
        source_check = verify_json_backup_file(source_path)
        if not source_check["isValidJson"] or not source_check["isValidSchema"]:
            raise CorruptedStorageError(
                f"File dữ liệu nguồn không hợp lệ trước khi tạo backup: {source_check['error']}"
            )

        if backup_path.exists():
            existing_check = verify_json_backup_file(backup_path)
            if not existing_check["isValidJson"] or not existing_check["isValidSchema"]:
                raise CorruptedStorageError(
                    f"Bản sao lưu ban đầu đã tồn tại nhưng bị hỏng JSON: {existing_check['error']}"
                )
            return {
                "backupPath": str(backup_path),
                "sourcePath": str(source_path),
                "createdNow": False,
                "overwritten": False,
                "isValidJson": True,
                "isValidSchema": True,
                "backupSha256": existing_check["sha256"],
                "sourceSha256": source_check["sha256"],
                "matchesSource": existing_check["sha256"] == source_check["sha256"],
                "sizeBytes": existing_check["sizeBytes"],
            }

        tmp_backup = backup_path.with_name(f"{backup_path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        try:
            raw_bytes = source_path.read_bytes()
            with open(tmp_backup, "wb") as f:
                f.write(raw_bytes)
                f.flush()
                os.fsync(f.fileno())

            tmp_check = verify_json_backup_file(tmp_backup)
            if not tmp_check["isValidJson"] or not tmp_check["isValidSchema"]:
                raise AtomicStorageError(f"File backup tạm không hợp lệ: {tmp_check['error']}")
            if tmp_check["sha256"] != source_check["sha256"]:
                raise AtomicStorageError("SHA-256 của bản backup tạm không khớp với file nguồn.")

            # Tuyệt đối không ghi đè nếu trong lúc chờ có tiến trình khác vừa tạo
            if not backup_path.exists():
                os.replace(str(tmp_backup), str(backup_path))
                created_now = True
            else:
                tmp_backup.unlink(missing_ok=True)
                created_now = False
        finally:
            if tmp_backup.exists():
                tmp_backup.unlink(missing_ok=True)

        final_check = verify_json_backup_file(backup_path)
        if not final_check["isValidJson"] or not final_check["isValidSchema"]:
            raise CorruptedStorageError(f"Xác minh bản backup sau khi tạo thất bại: {final_check['error']}")

        return {
            "backupPath": str(backup_path),
            "sourcePath": str(source_path),
            "createdNow": created_now,
            "overwritten": False,
            "isValidJson": True,
            "isValidSchema": True,
            "backupSha256": final_check["sha256"],
            "sourceSha256": source_check["sha256"],
            "matchesSource": final_check["sha256"] == source_check["sha256"],
            "sizeBytes": final_check["sizeBytes"],
        }


def atomic_write_json(
    target_path: Path,
    data: Any,
    validator_fn: Optional[Callable[[Any], Tuple[bool, Optional[str]]]] = validate_announcement_store_structure,
    simulate_crash_after_tmp_write: bool = False,
    lock_timeout_sec: float = 10.0,
) -> Dict[str, Any]:
    """
    Thực hiện quy trình Ghi nguyên tử 7 bước (7-Step Atomic Write):
    1. Thu thập khóa trong tiến trình (RLock) và liên tiến trình (File Lock).
    2. Kiểm tra tính hợp lệ của dữ liệu trong RAM.
    3. Ghi dữ liệu ra file tạm `<target>.<pid>.<tid>.tmp`, gọi `flush()` và `os.fsync()`.
    4. Đọc ngược và kiểm tra file tạm bằng `json.load()` + `validator_fn` trước khi thay thế file chính.
    5. Nếu file chính hiện tại hợp lệ, cập nhật bản sao lưu quay vòng `<target>.bak` (không bao giờ đụng tới `.pre_v4_migration.bak`).
    6. Thực hiện `os.replace(tmp_path, target_path)` nguyên tử.
    7. Giải phóng khóa.
    """
    target_path = Path(target_path).resolve()
    rolling_bak_path = target_path.with_name(target_path.name + ".bak")
    tmp_path = target_path.with_name(f"{target_path.name}.{os.getpid()}.{threading.get_ident()}.tmp")

    with DualLayerFileLock(target_path, timeout_sec=lock_timeout_sec):
        # Bước 2: Kiểm tra dữ liệu trong bộ nhớ trước khi ghi
        if validator_fn is not None:
            ok, err_msg = validator_fn(data)
            if not ok:
                raise AtomicStorageError(f"Dữ liệu cần ghi không hợp lệ: {err_msg}")

        target_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Bước 3: Ghi vào file tạm kèm flush + fsync
            serialized = json.dumps(data, ensure_ascii=False, indent=2)
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(serialized)
                f.flush()
                os.fsync(f.fileno())

            # Điểm mô phỏng lỗi dừng đột ngột giữa lúc ghi (chỉ phục vụ Unit Test)
            if simulate_crash_after_tmp_write:
                raise RuntimeError("SIMULATED_PROCESS_ABORT_AFTER_TMP_WRITE")

            # Bước 4: Kiểm tra lại file tạm trên đĩa trước khi thay thế file chính
            tmp_check = verify_json_backup_file(tmp_path, validator_fn=validator_fn)
            if not tmp_check["isValidJson"] or not tmp_check["isValidSchema"]:
                raise AtomicStorageError(
                    f"Kiểm tra file tạm thất bại trước khi os.replace: {tmp_check['error']}"
                )

            # Bước 5: Cập nhật bản backup quay vòng (.bak) CHỈ KHI file chính hiện tại hợp lệ
            if target_path.exists():
                current_check = verify_json_backup_file(target_path, validator_fn=validator_fn)
                if current_check["isValidJson"] and current_check["isValidSchema"]:
                    bak_tmp = rolling_bak_path.with_name(
                        f"{rolling_bak_path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
                    )
                    try:
                        with open(bak_tmp, "wb") as bf:
                            bf.write(target_path.read_bytes())
                            bf.flush()
                            os.fsync(bf.fileno())
                        os.replace(str(bak_tmp), str(rolling_bak_path))
                    finally:
                        if bak_tmp.exists():
                            bak_tmp.unlink(missing_ok=True)

            # Bước 6: Thay thế nguyên tử file chính bằng file tạm đã xác minh
            os.replace(str(tmp_path), str(target_path))

            return {
                "success": True,
                "targetPath": str(target_path),
                "rollingBackupPath": str(rolling_bak_path) if rolling_bak_path.exists() else None,
                "sha256": tmp_check["sha256"],
                "sizeBytes": tmp_check["sizeBytes"],
            }
        except Exception:
            if not simulate_crash_after_tmp_write and tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise


def safe_load_json(
    target_path: Path,
    validator_fn: Optional[Callable[[Any], Tuple[bool, Optional[str]]]] = validate_announcement_store_structure,
    lock_timeout_sec: float = 10.0,
) -> Tuple[Any, Dict[str, Any]]:
    """
    Đọc dữ liệu JSON an toàn dưới cơ chế khóa:
    - Nếu file chính hợp lệ: trả về dữ liệu.
    - Nếu file chính bị hỏng / mất:
      + CHỈ tự động kiểm tra và phục hồi từ rolling backup `<target>.bak` bằng `verify_json_backup_file`.
      + TUYỆT ĐỐI KHÔNG tự động fallback về `announcements.pre_v4_migration.bak` (backup V1 chỉ được
        dùng trong quy trình phục hồi thủ công có chủ đích của quản trị viên).
      + TUYỆT ĐỐI không phục hồi từ bản backup chưa được xác minh hoặc bị lỗi.
      + Nếu cả file chính và rolling backup `<target>.bak` đều không hợp lệ: DỪNG NGAY và ném
        `CorruptedStorageError`, tuyệt đối không tự tạo dữ liệu mặc định thay thế làm mất lịch sử.
    """
    target_path = Path(target_path).resolve()
    rolling_bak_path = target_path.with_name(target_path.name + ".bak")

    with DualLayerFileLock(target_path, timeout_sec=lock_timeout_sec):
        primary_check = verify_json_backup_file(target_path, validator_fn=validator_fn)
        if primary_check["isValidJson"] and primary_check["isValidSchema"]:
            return primary_check["data"], {
                "recoveredFromBackup": False,
                "backupSource": None,
                "sha256": primary_check["sha256"],
            }

        # File chính không hợp lệ -> CHỈ kiểm tra bản backup quay vòng (.bak)
        cand_check = verify_json_backup_file(rolling_bak_path, validator_fn=validator_fn)
        if cand_check["isValidJson"] and cand_check["isValidSchema"]:
            restored_data = copy.deepcopy(cand_check["data"])
            # Khôi phục lại file chính từ bản rolling backup đã được xác minh hợp lệ
            tmp_restore = target_path.with_name(
                f"{target_path.name}.restore.{os.getpid()}.{threading.get_ident()}.tmp"
            )
            try:
                with open(tmp_restore, "w", encoding="utf-8") as rf:
                    rf.write(json.dumps(restored_data, ensure_ascii=False, indent=2))
                    rf.flush()
                    os.fsync(rf.fileno())
                verify_tmp = verify_json_backup_file(tmp_restore, validator_fn=validator_fn)
                if not verify_tmp["isValidJson"] or not verify_tmp["isValidSchema"]:
                    raise CorruptedStorageError("Không thể xác minh file tạm khi phục hồi từ rolling backup.")
                os.replace(str(tmp_restore), str(target_path))
            finally:
                if tmp_restore.exists():
                    tmp_restore.unlink(missing_ok=True)

            return restored_data, {
                "recoveredFromBackup": True,
                "backupSource": str(rolling_bak_path),
                "primaryError": primary_check["error"],
                "sha256": cand_check["sha256"],
            }

        # Cả file chính lẫn rolling backup (.bak) đều không hợp lệ -> Dừng và báo lỗi nghiêm trọng
        raise CorruptedStorageError(
            f"DỪNG KHẨN CẤP: Cả file dữ liệu chính ({target_path}: {primary_check['error']}) "
            f"và rolling backup ({rolling_bak_path}: {cand_check['error']}) đều không hợp lệ hoặc không tồn tại. "
            f"Hệ thống từ chối tự động lùi về backup V1 hoặc tự sinh dữ liệu thay thế để bảo vệ lịch sử."
        )


# =============================================================================
# 6. CHÍNH SÁCH PHÂN LOẠI GIAO DỊCH TẠI GIÂY BIÊN TRÙNG NHAU (REQUIREMENT D.2)
# =============================================================================

BOUNDARY_OVERLAP_POLICY_DOC = """
CHÍNH SÁCH XỬ LÝ HAI ĐỢT THU CÓ THỜI ĐIỂM CHUYỂN TIẾP CÙNG GIÂY (1793619753):
1. Bảo toàn dữ liệu gốc:
   - Đợt `ann-k57-hk1` có `endedAt = "2026-11-02T11:42:33.687398+00:00"` (timestampInt = 1793619753, float = 1793619753.687398).
   - Đợt `ann-20261102114233` có `createdAt = "2026-11-02T11:42:33.691211+00:00"` (timestampInt = 1793619753, float = 1793619753.691211).
   - Hệ thống KHÔNG tự ý sửa cứng `1793619753` thành `1793619752` trong dữ liệu gốc, mà lưu nguyên vẹn cả
     `timestampInt` (1793619753), `timestampFloat` (có microsecond) và chuỗi ISO-8601 gốc.
2. Quy tắc phân loại giao dịch theo `block.timestamp` (độ phân giải 1 giây của Ethereum):
   - Mọi giao dịch chỉ được phân bổ vào TỐI ĐA MỘT rổ (Single-Assignment Invariant) — tuyệt đối không nhân đôi
     vào cả 2 đợt và không làm rơi dữ liệu.
   - Tại đúng giây chuyển tiếp trùng nhau `block.timestamp == 1793619753` (nơi đợt cũ vừa đóng để mở đợt mới):
     + Do `block.timestamp` là số nguyên giây nên không thể phân biệt microsecond `.687398` và `.691211` chỉ từ timestamp.
     + Áp dụng quy ước nửa mở `[startTimestamp, effectiveEndTimestamp)` tại điểm cắt thay thế đợt thu: giao dịch tại
       giây `1793619753` được tạm gán (`PROVISIONAL_PENDING_REVIEW`) vào đợt kế tiếp `ann-20261102114233`,
       ĐỒNG THỜI bắt buộc bật cờ `needsBoundaryReview = True`, `boundaryReason = "SHARED_SECOND_CAMPAIGN_TRANSITION"`,
       và liệt kê đầy đủ `candidateCampaignIds = ["ann-k57-hk1", "ann-20261102114233"]` để BCS/CVHT đối soát.
   - Trong vùng biên `±12 giây` quanh `startTimestamp` hoặc `effectiveEndTimestamp`:
     + Giao dịch nằm trong khoảng của 1 đợt được gán vào đợt đó kèm `needsBoundaryReview = True`.
     + Giao dịch nằm ngoài mọi đợt thu nhưng cách mốc đóng/mở `<= 12 giây` được đưa vào mục
       `voluntaryContributions` (Ngoài đợt thu) kèm `needsBoundaryReview = True` và `candidateCampaignIds`.
"""


def classify_transaction_at_timestamp(
    tx_timestamp: int,
    campaigns: Dict[str, Dict[str, Any]],
    boundary_window_sec: int = BOUNDARY_WINDOW_SECONDS,
) -> Dict[str, Any]:
    """
    Mô phỏng và phân loại một giao dịch có `block.timestamp = tx_timestamp` vào đợt thu tương ứng
    hoặc vào mục Đóng góp tự nguyện / Ngoài đợt thu, xử lý chặt chẽ trường hợp 2 đợt trùng giây biên.
    Bảo đảm:
    - Không mất giao dịch (mọi giao dịch đều có đúng 1 đích đến).
    - Không phân bổ trùng (mỗi giao dịch chỉ thuộc tối đa 1 `campaignId` hoặc `voluntaryContributions`).
    - Đánh dấu `needsBoundaryReview = True` cho giao dịch tại giây trùng nhau hoặc trong vùng biên ±12s.
    """
    tx_ts = int(tx_timestamp)
    sorted_campaigns = sorted(
        campaigns.values(),
        key=lambda c: (int(c.get("startTimestamp", 0)), float(c.get("startTimestampFloat", 0.0))),
    )

    # Tìm tất cả các đợt có khoảng [startTimestamp, effectiveEndTimestamp] chứa tx_ts
    matching_campaigns: List[Dict[str, Any]] = []
    near_boundary_campaigns: List[str] = []
    boundary_reasons: List[str] = []

    for camp in sorted_campaigns:
        cid = str(camp["id"])
        start_ts = int(camp["startTimestamp"])
        end_ts = int(camp.get("effectiveEndTimestamp") or camp.get("deadlineTimestamp") or start_ts)

        if start_ts <= tx_ts <= end_ts:
            matching_campaigns.append(camp)

        if abs(tx_ts - start_ts) <= boundary_window_sec or abs(tx_ts - end_ts) <= boundary_window_sec:
            if cid not in near_boundary_campaigns:
                near_boundary_campaigns.append(cid)

    # Trường hợp 1: Giao dịch rơi vào đúng giây biên chung giữa 2 đợt liên tiếp (ví dụ: 1793619753)
    if len(matching_campaigns) > 1:
        # Sắp xếp theo thời điểm tạo chính xác (startTimestampFloat) để áp dụng quy tắc nửa mở [start, end)
        matching_sorted = sorted(
            matching_campaigns,
            key=lambda c: (float(c.get("startTimestampFloat", c.get("startTimestamp", 0))), str(c["id"])),
        )
        provisional_target = matching_sorted[-1]
        candidate_ids = [str(c["id"]) for c in matching_sorted]
        return {
            "txTimestamp": tx_ts,
            "assignedBucket": "campaign",
            "campaignId": str(provisional_target["id"]),
            "allocatedCampaignCount": 1,
            "classificationStatus": "PROVISIONAL_PENDING_REVIEW",
            "needsBoundaryReview": True,
            "boundaryReason": "SHARED_SECOND_CAMPAIGN_TRANSITION",
            "candidateCampaignIds": candidate_ids,
            "policyApplied": "HALF_OPEN_REPLACEMENT_TIEBREAKER_WITH_MANDATORY_REVIEW",
        }

    # Trường hợp 2: Giao dịch nằm trong duy nhất 1 đợt thu
    if len(matching_campaigns) == 1:
        target = matching_campaigns[0]
        cid = str(target["id"])
        start_ts = int(target["startTimestamp"])
        end_ts = int(target.get("effectiveEndTimestamp") or target.get("deadlineTimestamp") or start_ts)

        dist_start = abs(tx_ts - start_ts)
        dist_end = abs(tx_ts - end_ts)
        is_boundary = dist_start <= boundary_window_sec or dist_end <= boundary_window_sec

        if is_boundary:
            if dist_start <= boundary_window_sec and dist_end <= boundary_window_sec:
                reason = "WITHIN_12S_START_AND_END_BOUNDARY"
            elif dist_start <= boundary_window_sec:
                reason = "WITHIN_12S_START_BOUNDARY"
            else:
                reason = "WITHIN_12S_END_BOUNDARY"
            status = "ASSIGNED_WITH_BOUNDARY_FLAG"
        else:
            reason = None
            status = "CONFIRMED_IN_CAMPAIGN"

        return {
            "txTimestamp": tx_ts,
            "assignedBucket": "campaign",
            "campaignId": cid,
            "allocatedCampaignCount": 1,
            "classificationStatus": status,
            "needsBoundaryReview": is_boundary,
            "boundaryReason": reason,
            "candidateCampaignIds": near_boundary_campaigns if is_boundary else [cid],
            "policyApplied": "SINGLE_CAMPAIGN_WINDOW",
        }

    # Trường hợp 3: Giao dịch nằm ngoài mọi đợt thu -> vào mục Đóng góp tự nguyện / Ngoài đợt thu
    is_near_any = len(near_boundary_campaigns) > 0
    return {
        "txTimestamp": tx_ts,
        "assignedBucket": "voluntaryContributions",
        "campaignId": None,
        "allocatedCampaignCount": 0,
        "classificationStatus": (
            "VOLUNTARY_PENDING_BOUNDARY_REVIEW" if is_near_any else "VOLUNTARY_CONFIRMED"
        ),
        "needsBoundaryReview": is_near_any,
        "boundaryReason": "WITHIN_12S_OUTSIDE_CAMPAIGN_BOUNDARY" if is_near_any else None,
        "candidateCampaignIds": near_boundary_campaigns,
        "policyApplied": "OUTSIDE_CAMPAIGN_TO_VOLUNTARY",
    }


# =============================================================================
# 7. MIGRATION SCHEMA V1 -> SCHEMA V2 & ĐỐI CHIẾU TOÀN VẸN DỮ LIỆU
# =============================================================================

def _build_v2_campaign_record(
    raw_item: Dict[str, Any],
    reference_now_ts: int,
    previous_record_hash: str = GENESIS_PREV_HASH,
    seq: int = 1,
) -> Dict[str, Any]:
    """Chuẩn hóa 1 bản ghi đợt thu từ Schema V1 sang Schema V2, bảo toàn 100% trường dữ liệu gốc."""
    item_id = str(raw_item.get("id") or f"ann-{secrets.token_hex(4)}").strip()
    title = str(raw_item.get("title", "Kêu gọi nộp Quỹ Lớp K57")).strip()
    target_eth = str(raw_item.get("targetAmountEth", "0.01")).strip()
    target_wei = eth_to_wei_str(target_eth)
    deadline_str = str(raw_item.get("deadline", "Chưa xác định")).strip()

    # Xác định deadlineTimestamp bằng Asia/Ho_Chi_Minh và đối chiếu với giá trị gốc
    parsed_dl_ts = parse_deadline_to_vn_timestamp(deadline_str)
    raw_dl_ts = raw_item.get("deadlineTimestamp")
    if parsed_dl_ts is not None:
        deadline_ts = int(parsed_dl_ts)
    elif raw_dl_ts is not None:
        deadline_ts = int(float(raw_dl_ts))
    else:
        deadline_ts = None

    created_at_str = str(raw_item.get("createdAt") or datetime.now(timezone.utc).isoformat())
    created_detail = parse_iso_timestamp_detail(created_at_str)
    start_ts_int = created_detail["timestampInt"] if created_detail else int(reference_now_ts)
    start_ts_float = created_detail["timestampFloat"] if created_detail else float(reference_now_ts)

    ended_at_str = raw_item.get("endedAt")
    ended_detail = parse_iso_timestamp_detail(ended_at_str) if ended_at_str else None
    end_reason = raw_item.get("endReason")

    raw_status = str(raw_item.get("status", "active")).strip().lower()
    if raw_status in ["đang diễn ra", "active", "open"]:
        status = "active"
    elif raw_status in ["expired", "đã hết hạn"]:
        status = "expired"
    elif raw_status in ["đã hoàn thành", "completed"]:
        status = "completed"
    else:
        status = "archived"

    # Quy tắc nghiệp vụ 1: Đợt đang active nhưng đã quá hạn (reference_now_ts > deadline_ts)
    # -> chuyển sang trạng thái `expired`, không tự động gia hạn, không xóa dữ liệu cũ.
    if status == "active" and deadline_ts is not None and reference_now_ts > deadline_ts:
        status = "expired"
        if not ended_at_str:
            ended_at_str = datetime.fromtimestamp(deadline_ts, tz=get_vn_tz()).isoformat()
            ended_detail = parse_iso_timestamp_detail(ended_at_str)
        if not end_reason:
            end_reason = "Đã hết hạn nộp (Quá thời hạn quy định)"

    if ended_detail is not None:
        effective_end_ts = ended_detail["timestampInt"]
        effective_end_float = ended_detail["timestampFloat"]
    elif status == "expired" and deadline_ts is not None:
        effective_end_ts = int(deadline_ts)
        effective_end_float = float(deadline_ts)
    else:
        effective_end_ts = int(deadline_ts) if deadline_ts is not None else None
        effective_end_float = float(deadline_ts) if deadline_ts is not None else None

    campaign_obj = {
        "id": item_id,
        "title": title,
        "targetAmountEth": target_eth,
        "targetAmountWei": target_wei,
        "deadline": deadline_str,
        "deadlineTimestamp": float(deadline_ts) if deadline_ts is not None else None,
        "deadlineTimestampInt": int(deadline_ts) if deadline_ts is not None else None,
        "classSize": int(raw_item.get("classSize", 5)),
        "purpose": str(raw_item.get("purpose", "")).strip(),
        "status": status,
        "autoCloseOnTarget": bool(raw_item.get("autoCloseOnTarget", False)),
        "createdAt": created_at_str,
        "startTimestamp": start_ts_int,
        "startTimestampFloat": start_ts_float,
        "endedAt": ended_at_str,
        "effectiveEndTimestamp": effective_end_ts,
        "effectiveEndTimestampFloat": effective_end_float,
        "endReason": end_reason,
        "updatedBy": raw_item.get("updatedBy"),
        "updatedAt": raw_item.get("updatedAt"),
        "startBlock": None,
        "endBlock": None,
        "deposits": {},
        "totals": {
            "grossDepositedWei": "0",
            "allocatedRefundWei": "0",
            "netCampaignWei": "0",
            "completedStudentCount": 0,
        },
    }
    return attach_record_audit_hash(campaign_obj, previous_record_hash=previous_record_hash, seq=seq)


def _campaign_to_legacy_view(camp: Dict[str, Any]) -> Dict[str, Any]:
    """Trích xuất view tương thích ngược cho `active` và `history` từ bản ghi chiến dịch V2."""
    return {
        "id": camp["id"],
        "title": camp["title"],
        "targetAmountEth": camp["targetAmountEth"],
        "targetAmountWei": camp["targetAmountWei"],
        "deadline": camp["deadline"],
        "deadlineTimestamp": camp["deadlineTimestamp"],
        "classSize": camp["classSize"],
        "purpose": camp["purpose"],
        "status": camp["status"],
        "autoCloseOnTarget": camp["autoCloseOnTarget"],
        "createdAt": camp["createdAt"],
        "startTimestamp": camp["startTimestamp"],
        "endedAt": camp["endedAt"],
        "effectiveEndTimestamp": camp["effectiveEndTimestamp"],
        "endReason": camp["endReason"],
        "updatedBy": camp["updatedBy"],
        "updatedAt": camp["updatedAt"],
        "recordSha256": camp.get("recordSha256"),
        "previousRecordHash": camp.get("previousRecordHash"),
    }


def migrate_v1_to_v2_store(
    raw_store: Dict[str, Any],
    reference_now_ts: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Chuyển đổi cấu trúc dữ liệu từ Schema V1 (`active` + `history`) sang Schema V2 (V4.4)
    hoặc chuẩn hóa lại store Schema V2 hiện có.
    """
    if reference_now_ts is None:
        reference_now_ts = int(time.time())
    else:
        reference_now_ts = int(reference_now_ts)

    if not isinstance(raw_store, dict):
        raise ValueError("Dữ liệu đầu vào của migrate_v1_to_v2_store phải là dict.")

    # Nếu đã là Schema V2, chỉ đánh giá lại hạn nộp của đợt active (nếu có) và cập nhật view
    if raw_store.get("schemaVersion") == 2 and isinstance(raw_store.get("campaigns"), dict):
        store_v2 = copy.deepcopy(raw_store)
        prev_hash = GENESIS_PREV_HASH
        seq = 1
        for cid in store_v2.get("campaignOrder", list(store_v2["campaigns"].keys())):
            camp = store_v2["campaigns"][cid]
            dl_ts = camp.get("deadlineTimestampInt") or camp.get("deadlineTimestamp")
            if camp.get("status") == "active" and dl_ts is not None and reference_now_ts > int(dl_ts):
                camp["status"] = "expired"
                if not camp.get("endedAt"):
                    camp["endedAt"] = datetime.fromtimestamp(int(dl_ts), tz=get_vn_tz()).isoformat()
                if not camp.get("endReason"):
                    camp["endReason"] = "Đã hết hạn nộp (Quá thời hạn quy định)"
                camp["effectiveEndTimestamp"] = int(dl_ts)
                camp["effectiveEndTimestampFloat"] = float(dl_ts)
            camp = attach_record_audit_hash(camp, previous_record_hash=prev_hash, seq=seq)
            store_v2["campaigns"][cid] = camp
            prev_hash = camp["recordSha256"]
            seq += 1

        _rebuild_legacy_views_in_v2(store_v2)
        return store_v2

    # Thu thập danh sách đợt thu từ Schema V1 theo thứ tự thời gian tạo tăng dần để nối chuỗi hash
    v1_items: List[Dict[str, Any]] = []
    history_raw = raw_store.get("history", [])
    if isinstance(history_raw, list):
        for h in reversed(history_raw):
            if isinstance(h, dict):
                v1_items.append(copy.deepcopy(h))

    active_raw = raw_store.get("active")
    if isinstance(active_raw, dict):
        # Tránh trùng ID nếu active đã nằm trong history
        v1_items = [it for it in v1_items if it.get("id") != active_raw.get("id")]
        v1_items.append(copy.deepcopy(active_raw))

    campaigns_map: Dict[str, Dict[str, Any]] = {}
    campaign_order: List[str] = []
    prev_hash = GENESIS_PREV_HASH

    for idx, item in enumerate(v1_items, start=1):
        v2_camp = _build_v2_campaign_record(
            item,
            reference_now_ts=reference_now_ts,
            previous_record_hash=prev_hash,
            seq=idx,
        )
        cid = v2_camp["id"]
        campaigns_map[cid] = v2_camp
        campaign_order.append(cid)
        prev_hash = v2_camp["recordSha256"]

    store_v2 = {
        "schemaVersion": 2,
        "revision": int(raw_store.get("revision", 1)),
        "timezone": VN_TZ_KEY,
        "migratedAt": datetime.now(get_vn_tz()).isoformat(),
        "auditMeta": {
            "hashSpecVersion": AUDIT_HASH_SPEC_VERSION,
            "limitationNote": AUDIT_HASH_LIMITATION_NOTE,
            "lastCampaignChainHash": prev_hash,
            "boundaryOverlapPolicy": "HALF_OPEN_REPLACEMENT_TIEBREAKER_WITH_MANDATORY_REVIEW",
        },
        "campaigns": campaigns_map,
        "campaignOrder": campaign_order,
        "voluntaryContributions": {},
        "refundRequests": {},
        "manualAdjustments": [],
        "reconciliation": {
            "status": "NOT_SYNCED_YET",
            "lastCheckedAt": None,
            "checkedBlockNumber": None,
            "checkedBlockHash": None,
            "isMatched": True,
            "mismatches": [],
        },
        "syncState": {
            "contractAddress": "0x90948699FF04bC9cF159a39e200F09885439503D",
            "chainId": 11155111,
            "contractDeployBlock": None,
            "lastSyncedBlock": None,
            "lastSyncedBlockHash": None,
            "recentBlocks": [],
        },
        "processedRequests": {},
        "active": None,
        "history": [],
    }

    _rebuild_legacy_views_in_v2(store_v2)
    return store_v2


def _rebuild_legacy_views_in_v2(store_v2: Dict[str, Any]) -> None:
    """Đồng bộ hóa 2 trường `active` và `history` từ `campaigns` để bảo đảm tương thích ngược 100%."""
    active_view = None
    history_views: List[Dict[str, Any]] = []

    # Duyệt ngược từ mới nhất về cũ nhất để history có đợt mới nhất đứng đầu (giống hành vi V1)
    order = store_v2.get("campaignOrder") or list(store_v2.get("campaigns", {}).keys())
    for cid in reversed(order):
        camp = store_v2["campaigns"].get(cid)
        if not camp:
            continue
        view = _campaign_to_legacy_view(camp)
        if camp.get("status") == "active" and active_view is None:
            active_view = view
        else:
            history_views.append(view)

    store_v2["active"] = active_view
    store_v2["history"] = history_views


def compare_pre_post_migration(before_v1: Dict[str, Any], after_v2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Đối chiếu chi tiết dữ liệu trước (Schema V1) và sau khi migrate (Schema V2),
    xác nhận không mất ID, lịch sử, số tiền, thời hạn và các trường quan trọng
    (bao gồm cả `updatedAt` và `endReason`).
    """
    before_campaigns: Dict[str, Dict[str, Any]] = {}
    if isinstance(before_v1.get("active"), dict):
        c = before_v1["active"]
        before_campaigns[str(c["id"])] = c
    for h in before_v1.get("history", []):
        if isinstance(h, dict) and h.get("id"):
            before_campaigns[str(h["id"])] = h

    after_campaigns = after_v2.get("campaigns", {})
    rows: List[Dict[str, Any]] = []
    all_preserved = True

    critical_fields = [
        "id",
        "title",
        "targetAmountEth",
        "deadline",
        "deadlineTimestamp",
        "classSize",
        "purpose",
        "autoCloseOnTarget",
        "createdAt",
        "updatedBy",
        "updatedAt",
        "endReason",
    ]

    for cid, old_c in before_campaigns.items():
        new_c = after_campaigns.get(cid)
        if not new_c:
            all_preserved = False
            rows.append({"id": cid, "preserved": False, "reason": "Missing in after_v2.campaigns"})
            continue

        field_checks = {}
        for f_name in critical_fields:
            old_val = old_c.get(f_name)
            new_val = new_c.get(f_name)
            migration_rule_note = None
            if f_name == "deadlineTimestamp" and old_val is not None and new_val is not None:
                matched = float(old_val) == float(new_val)
            elif (
                f_name == "endReason"
                and old_c.get("status") == "active"
                and new_c.get("status") == "expired"
                and old_val is None
                and new_val == "Đã hết hạn nộp (Quá thời hạn quy định)"
            ):
                # Quy tắc nghiệp vụ 1: Đợt đang active nhưng đã quá hạn chuyển sang `expired`
                # nên `endReason` chuyển từ `None` sang lý do hết hạn chuẩn.
                matched = True
                migration_rule_note = (
                    "AUTO_EXPIRE_RULE: Đợt active quá hạn chuyển sang expired nên endReason "
                    "được gán lý do quá hạn theo quy tắc nghiệp vụ 1 (dữ liệu gốc có endReason=null)."
                )
            else:
                matched = old_val == new_val

            check_entry: Dict[str, Any] = {"before": old_val, "after": new_val, "matched": matched}
            if migration_rule_note:
                check_entry["migrationRuleExplanation"] = migration_rule_note
            field_checks[f_name] = check_entry
            if not matched:
                all_preserved = False

        rows.append(
            {
                "id": cid,
                "preserved": all(v["matched"] for v in field_checks.values()),
                "statusBefore": old_c.get("status"),
                "statusAfter": new_c.get("status"),
                "targetAmountEth": new_c.get("targetAmountEth"),
                "targetAmountWei": new_c.get("targetAmountWei"),
                "startTimestamp": new_c.get("startTimestamp"),
                "effectiveEndTimestamp": new_c.get("effectiveEndTimestamp"),
                "deadlineTimestamp": new_c.get("deadlineTimestamp"),
                "recordSha256": new_c.get("recordSha256"),
                "previousRecordHash": new_c.get("previousRecordHash"),
                "fieldChecks": field_checks,
            }
        )

    chain_records = [after_campaigns[cid] for cid in after_v2.get("campaignOrder", []) if cid in after_campaigns]
    expected_tail = after_v2.get("auditMeta", {}).get("lastCampaignChainHash")
    chain_ok, chain_err = verify_record_hash_chain(
        chain_records,
        expected_tail_hash=expected_tail,
        expected_length=len(before_campaigns),
    )
    if not chain_ok:
        all_preserved = False

    return {
        "allPreserved": all_preserved and (len(before_campaigns) == len(after_campaigns)),
        "beforeCount": len(before_campaigns),
        "afterCount": len(after_campaigns),
        "criticalFieldsChecked": list(critical_fields),
        "hashChainValid": chain_ok,
        "hashChainError": chain_err,
        "campaignComparisons": rows,
    }


def run_dry_run_migration_in_temp(
    source_path: Path,
    reference_now_ts: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Chạy migration thử nghiệm trên bản sao của `source_path` bên trong `tempfile.TemporaryDirectory()`.
    Tuyệt đối không chạm vào file thật.
    """
    source_path = Path(source_path).resolve()
    with tempfile.TemporaryDirectory(prefix="kts_v44_migration_dryrun_") as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        temp_ann_file = tmp_dir_path / "announcements.json"
        shutil.copy2(source_path, temp_ann_file)

        before_data, _ = safe_load_json(temp_ann_file)
        migrated_v2 = migrate_v1_to_v2_store(before_data, reference_now_ts=reference_now_ts)
        write_res = atomic_write_json(temp_ann_file, migrated_v2)
        reloaded_v2, load_meta = safe_load_json(temp_ann_file)

        comparison = compare_pre_post_migration(before_data, reloaded_v2)
        return {
            "tempDirUsed": str(tmp_dir_path),
            "writeResult": write_res,
            "loadMeta": load_meta,
            "beforeData": before_data,
            "afterData": reloaded_v2,
            "comparison": comparison,
        }


# =============================================================================
# 8. KIỂM SOÁT REVISION (HTTP 409 CONFLICT) & CHỐNG GHI TRÙNG (CLIENTREQUESTID)
# =============================================================================

def cleanup_expired_processed_requests(
    processed_requests: Dict[str, Dict[str, Any]],
    now_ts: Optional[int] = None,
) -> Dict[str, Dict[str, Any]]:
    """Dọn dẹp các `clientRequestId` đã quá hạn 24 giờ."""
    if not isinstance(processed_requests, dict):
        return {}
    now_val = int(now_ts if now_ts is not None else time.time())
    cleaned = {}
    for req_id, info in processed_requests.items():
        if isinstance(info, dict):
            expires_at = int(info.get("expiresAt", 0))
            if expires_at > now_val:
                cleaned[str(req_id)] = info
    return cleaned


def validate_concurrency_and_idempotency(
    store: Dict[str, Any],
    expected_revision: Optional[int] = None,
    client_request_id: Optional[str] = None,
    action: Optional[str] = None,
    actor: Optional[str] = None,
    now_ts: Optional[int] = None,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Kiểm tra `clientRequestId` (Idempotency kèm xác thực ngữ cảnh action + actor)
    và `expectedRevision` (Optimistic Concurrency Control):
    1. Nếu `client_request_id` đã tồn tại trong `processedRequests` (còn hạn):
       - Kiểm tra `action` và `actor` của yêu cầu mới so với `action` và `actor` đã lưu.
       - Nếu cả hai đều khớp: trả về `(True, cached_response)` để báo idempotent replay, KHÔNG thực hiện ghi trùng!
       - Nếu `action` hoặc `actor` KHÔNG khớp: ném `IdempotencyConflictError` (HTTP 409 Conflict),
         tuyệt đối không thực hiện thao tác mới và không trả payload của hành động/người dùng khác!
    2. Nếu `expected_revision` được gửi lên nhưng khác với `store.get("revision", 1)`:
       Ném `RevisionConflictError` để tầng HTTP trả về `409 Conflict`.
    3. Nếu hợp lệ và là request mới: trả về `(False, None)`.
    """
    now_val = int(now_ts if now_ts is not None else time.time())
    current_revision = int(store.get("revision", 1))
    processed_map = cleanup_expired_processed_requests(store.get("processedRequests", {}), now_ts=now_val)
    store["processedRequests"] = processed_map

    if client_request_id is not None and str(client_request_id).strip() != "":
        clean_req_id = str(client_request_id).strip()
        if clean_req_id in processed_map:
            cached_entry = processed_map[clean_req_id]
            saved_action = str(cached_entry.get("action", "")).strip()
            saved_actor = str(cached_entry.get("actor", "")).strip().lower()
            actual_action = str(action or "").strip()
            actual_actor = str(actor or "").strip().lower()

            if actual_action != saved_action or actual_actor != saved_actor:
                raise IdempotencyConflictError(
                    client_request_id=clean_req_id,
                    saved_action=saved_action,
                    actual_action=actual_action,
                    saved_actor=saved_actor,
                    actual_actor=actual_actor,
                )

            replay_payload = copy.deepcopy(cached_entry.get("responsePayload", {}))
            replay_payload["idempotentReplay"] = True
            replay_payload["clientRequestId"] = clean_req_id
            replay_payload["revision"] = int(cached_entry.get("revision", current_revision))
            return True, replay_payload

    if expected_revision is not None and str(expected_revision).strip() != "":
        try:
            exp_rev_int = int(expected_revision)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Giá trị expectedRevision không hợp lệ: {expected_revision}") from exc

        if exp_rev_int != current_revision:
            raise RevisionConflictError(
                expected_revision=exp_rev_int,
                current_revision=current_revision,
            )

    return False, None


def record_mutation_commit(
    store: Dict[str, Any],
    action: str,
    actor: str,
    client_request_id: Optional[str] = None,
    response_payload: Optional[Dict[str, Any]] = None,
    now_ts: Optional[int] = None,
) -> int:
    """
    Tăng `revision` thêm +1 sau khi thay đổi trạng thái và ghi nhận `clientRequestId` vào `processedRequests`.
    """
    now_val = int(now_ts if now_ts is not None else time.time())
    new_revision = int(store.get("revision", 1)) + 1
    store["revision"] = new_revision

    processed_map = cleanup_expired_processed_requests(store.get("processedRequests", {}), now_ts=now_val)
    if client_request_id is not None and str(client_request_id).strip() != "":
        clean_req_id = str(client_request_id).strip()
        cached_resp = copy.deepcopy(response_payload) if isinstance(response_payload, dict) else {}
        cached_resp["revision"] = new_revision
        cached_resp["clientRequestId"] = clean_req_id
        processed_map[clean_req_id] = {
            "clientRequestId": clean_req_id,
            "action": str(action),
            "actor": str(actor).lower(),
            "revision": new_revision,
            "processedAt": now_val,
            "expiresAt": now_val + PROCESSED_REQUEST_TTL_SECONDS,
            "responsePayload": cached_resp,
        }
    store["processedRequests"] = processed_map
    return new_revision

