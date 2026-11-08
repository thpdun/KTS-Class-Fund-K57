#!/usr/bin/env python3
"""
Kho thông báo Quỹ lớp K57 - Schema v3 (nhiều thông báo hoạt động đồng thời).

Nguyên tắc thiết kế:
1. `notifications` là NGUỒN SỰ THẬT DUY NHẤT. Mỗi thông báo có `id` duy nhất và vòng đời độc lập:
       active  -> expired   (hệ thống tự động khi quá `expiresAt`, múi giờ Asia/Ho_Chi_Minh)
       active  -> archived  (BCS/CVHT lưu trữ)
       active  -> revoked   (BCS/CVHT thu hồi, bắt buộc có lý do)
   Trạng thái kết thúc (expired / archived / revoked) là bất biến: không sửa, không chuyển tiếp.
2. Tạo thông báo mới CHỈ thêm vào danh sách; tuyệt đối không đụng tới thông báo khác.
3. `active` và `history` ở cấp gốc chỉ là VIEW DẪN XUẤT, được tính lại mỗi lần ghi
   (giữ để phiên bản server cũ vẫn đọc được file khi cần rollback).
4. Mọi chuyển trạng thái được ghi vào `auditLog` nối chuỗi hash (seq + previousRecordHash +
   recordSha256) dùng lại hạ tầng hash của accounting_engine (không sửa module đó).
5. Hết hạn tự động là idempotent: chỉ chuyển `active -> expired` đúng một lần, `endedAt`
   được gán bằng đúng mốc hạn chót (tất định), nên khởi động lại không tạo bản ghi trùng.
"""

from __future__ import annotations

import copy
import hashlib
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

try:
    from backend.accounting_engine import (
        AUDIT_HASH_SPEC_VERSION,
        GENESIS_PREV_HASH,
        VN_TZ_KEY,
        attach_record_audit_hash,
        canonical_json_bytes,
        eth_to_wei_str,
        get_vn_tz,
        parse_deadline_to_vn_timestamp,
        parse_iso_timestamp_detail,
        validate_announcement_store_structure,
        verify_record_hash_chain,
    )
except ImportError:  # pragma: no cover - khi chạy trực tiếp trong thư mục backend
    from accounting_engine import (
        AUDIT_HASH_SPEC_VERSION,
        GENESIS_PREV_HASH,
        VN_TZ_KEY,
        attach_record_audit_hash,
        canonical_json_bytes,
        eth_to_wei_str,
        get_vn_tz,
        parse_deadline_to_vn_timestamp,
        parse_iso_timestamp_detail,
        validate_announcement_store_structure,
        verify_record_hash_chain,
    )

# =============================================================================
# HẰNG SỐ
# =============================================================================

NOTIFICATION_SCHEMA_VERSION = 3
NOTIFICATION_SCHEMA_NAME = "kts-notifications"

STATUS_ACTIVE = "active"
STATUS_COMPLETED = "completed"
STATUS_EXPIRED = "expired"
STATUS_ARCHIVED = "archived"
STATUS_REVOKED = "revoked"
TERMINAL_STATUSES = (STATUS_COMPLETED, STATUS_EXPIRED, STATUS_ARCHIVED, STATUS_REVOKED)
VALID_STATUSES = (STATUS_ACTIVE,) + TERMINAL_STATUSES


class NotificationStatus:
    ACTIVE = STATUS_ACTIVE
    COMPLETED = STATUS_COMPLETED
    EXPIRED = STATUS_EXPIRED
    ARCHIVED = STATUS_ARCHIVED
    REVOKED = STATUS_REVOKED

AUTO_EXPIRE_REASON = "Đã hết hạn nộp (Quá thời hạn quy định)"
SYSTEM_EXPIRE_ACTOR = "system:auto-expire"
SYSTEM_MIGRATION_ACTOR = "system:migration"

# Các trường bắt buộc đối chiếu khi migration để chứng minh không mất dữ liệu
MIGRATION_CRITICAL_FIELDS = (
    "title",
    "purpose",
    "targetAmountEth",
    "deadline",
    "createdAt",
    "updatedBy",
    "updatedAt",
    "endedAt",
    "endReason",
)

EDITABLE_FIELDS = ("title", "targetAmountEth", "deadline", "purpose", "classSize", "autoCloseOnTarget")


# =============================================================================
# LỖI TÙY BIẾN
# =============================================================================

class NotificationError(ValueError):
    """Lỗi nghiệp vụ của kho thông báo, mang theo mã lỗi và HTTP status gợi ý."""

    code = "NOTIFICATION_ERROR"
    http_status = 400

    def __init__(self, message: str, **extra: Any):
        super().__init__(message)
        self.extra = extra


class NotificationValidationError(NotificationError):
    code = "INVALID_NOTIFICATION_INPUT"
    http_status = 400


class NotificationNotFoundError(NotificationError):
    code = "NOTIFICATION_NOT_FOUND"
    http_status = 404


class AmbiguousNotificationTargetError(NotificationError):
    code = "NOTIFICATION_ID_REQUIRED"
    http_status = 400


class InvalidTransitionError(NotificationError):
    code = "INVALID_STATUS_TRANSITION"
    http_status = 409


class AuditChainBrokenError(NotificationError):
    code = "AUDIT_CHAIN_INVALID"
    http_status = 409


class MigrationIntegrityError(NotificationError):
    code = "MIGRATION_INTEGRITY_FAILED"
    http_status = 500


# =============================================================================
# TIỆN ÍCH THỜI GIAN
# =============================================================================

def now_vn_iso() -> str:
    return datetime.now(get_vn_tz()).isoformat()


def ts_to_vn_iso(ts: Optional[float]) -> Optional[str]:
    if ts is None:
        return None
    return datetime.fromtimestamp(float(ts), tz=get_vn_tz()).isoformat()


def _iso_to_ts(value: Any) -> Optional[float]:
    if not value:
        return None
    try:
        detail = parse_iso_timestamp_detail(str(value))
        return detail["timestampFloat"] if detail else None
    except (ValueError, TypeError):
        return None


# =============================================================================
# CHUẨN HÓA MỘT THÔNG BÁO
# =============================================================================

def map_legacy_status(raw_status: Any) -> Tuple[str, Optional[str]]:
    """
    Ánh xạ trạng thái cũ sang 4 trạng thái chuẩn. Trả về (status_chuẩn, legacy_raw_nếu_khác).
    Trạng thái không nhận diện được KHÔNG bị coi là active (an toàn): chuyển archived và
    lưu nguyên giá trị gốc vào `legacyStatus` để truy vết.
    """
    raw = "" if raw_status is None else str(raw_status).strip()
    low = raw.lower()
    if low in ("active", "open", "đang diễn ra", "sắp kết thúc"):
        return STATUS_ACTIVE, (None if low == "active" else raw)
    if low in ("expired", "đã hết hạn"):
        return STATUS_EXPIRED, (None if low == "expired" else raw)
    if low in ("revoked", "đã thu hồi"):
        return STATUS_REVOKED, (None if low == "revoked" else raw)
    if low in ("completed", "đã hoàn thành"):
        return STATUS_COMPLETED, (None if low == "completed" else raw)
    if low == "archived":
        return STATUS_ARCHIVED, None
    if low == "":
        return STATUS_ACTIVE, None
    # completed / đã hoàn thành / giá trị lạ -> archived, giữ dấu vết gốc
    return STATUS_ARCHIVED, raw


def normalize_notification(item: Dict[str, Any], default_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Chuẩn hóa một thông báo mà KHÔNG làm mất trường nào của dữ liệu gốc (deepcopy toàn bộ rồi
    bổ sung/chuẩn hóa). Hàm idempotent: chuẩn hóa lại một bản đã chuẩn hóa không đổi nội dung.
    """
    if not isinstance(item, dict):
        raise NotificationValidationError("Thông báo phải là một đối tượng JSON (dict).")

    n = copy.deepcopy(item)
    n["id"] = str(item.get("id") or default_id or f"ann-{secrets.token_hex(4)}").strip()

    status, legacy = map_legacy_status(item.get("status"))
    n["status"] = status
    if legacy is not None and "legacyStatus" not in n:
        n["legacyStatus"] = legacy

    deadline_str = str(item.get("deadline") or "Chưa xác định").strip()
    parsed_ts = parse_deadline_to_vn_timestamp(deadline_str)
    raw_ts = item.get("deadlineTimestamp")
    raw_ts_num: Optional[float] = None
    if raw_ts is not None:
        try:
            raw_ts_num = float(raw_ts)
        except (TypeError, ValueError):
            raw_ts_num = None

    if parsed_ts is not None:
        expires_ts: Optional[int] = int(parsed_ts)
        # Lưu bằng chứng nếu timestamp cũ lệch với chuỗi hạn chót theo Asia/Ho_Chi_Minh
        if raw_ts_num is not None and abs(raw_ts_num - expires_ts) >= 1 and "deadlineTimestampLegacy" not in n:
            n["deadlineTimestampLegacy"] = raw_ts
    elif raw_ts_num is not None:
        expires_ts = int(raw_ts_num)
    else:
        expires_ts = None

    n["deadline"] = deadline_str
    n["deadlineTimestamp"] = float(expires_ts) if expires_ts is not None else None
    n["expiresAtTimestamp"] = expires_ts
    n["expiresAt"] = ts_to_vn_iso(expires_ts)

    n["title"] = str(item.get("title") or "Kêu gọi nộp Quỹ Lớp K57").strip()
    n["targetAmountEth"] = str(item.get("targetAmountEth") or "0").strip()
    try:
        n["targetAmountWei"] = eth_to_wei_str(n["targetAmountEth"])
    except ValueError:
        n["targetAmountWei"] = None
    n["purpose"] = str(item.get("purpose") or "").strip()
    req_sz = item.get("classSize")
    if req_sz is not None:
        try:
            n["classSize"] = max(1, int(req_sz))
        except (TypeError, ValueError):
            n["classSize"] = None
    else:
        n["classSize"] = None
    n["autoCloseOnTarget"] = bool(item.get("autoCloseOnTarget", False))

    # Không bịa người tạo: nếu dữ liệu cũ không có createdBy thì để None
    n.setdefault("createdBy", None)
    n["createdAt"] = item.get("createdAt") or now_vn_iso()
    n.setdefault("updatedBy", None)
    n.setdefault("updatedAt", None)
    n.setdefault("endedAt", None)
    n.setdefault("endReason", None)
    if not isinstance(n.get("statusHistory"), list):
        n["statusHistory"] = []
    return n


def notification_snapshot_sha256(n: Dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(n)).hexdigest()


# =============================================================================
# KIỂM TRA CẤU TRÚC FILE
# =============================================================================

def validate_notifications_store(data: Any) -> Tuple[bool, Optional[str]]:
    """Validator cho atomic_write_json / safe_load_json: chấp nhận Schema v3 và các schema cũ."""
    if isinstance(data, dict) and data.get("schemaVersion") == NOTIFICATION_SCHEMA_VERSION:
        notes = data.get("notifications")
        if not isinstance(notes, list):
            return False, "Schema v3: trường 'notifications' phải là list."
        rev = data.get("revision")
        if not isinstance(rev, int) or isinstance(rev, bool) or rev < 1:
            return False, "Schema v3: 'revision' phải là số nguyên >= 1."
        seen = set()
        for idx, n in enumerate(notes):
            if not isinstance(n, dict):
                return False, f"Schema v3: notifications[{idx}] không phải dict."
            nid = n.get("id")
            if not isinstance(nid, str) or not nid.strip():
                return False, f"Schema v3: notifications[{idx}] thiếu id."
            if nid in seen:
                return False, f"Schema v3: trùng id thông báo '{nid}'."
            seen.add(nid)
            if n.get("status") not in VALID_STATUSES:
                return False, f"Schema v3: trạng thái không hợp lệ ở '{nid}': {n.get('status')}."
        if "auditLog" in data and not isinstance(data["auditLog"], list):
            return False, "Schema v3: 'auditLog' phải là list."
        return True, None
    return validate_announcement_store_structure(data)


def detect_schema(raw: Any) -> str:
    if not isinstance(raw, dict) or not raw:
        return "empty"
    if raw.get("schemaVersion") == NOTIFICATION_SCHEMA_VERSION and isinstance(raw.get("notifications"), list):
        return "v3"
    if raw.get("schemaVersion") == 2 and isinstance(raw.get("campaigns"), dict):
        return "v2"
    if "active" in raw or "history" in raw:
        return "v1"
    if "title" in raw or "id" in raw:
        return "legacy_single"
    return "empty"


# =============================================================================
# AUDIT LOG (HASH CHAIN)
# =============================================================================

def append_audit_event(
    store: Dict[str, Any],
    event_type: str,
    notification: Dict[str, Any],
    actor: str,
    at_iso: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    log = store.setdefault("auditLog", [])
    prev_hash = log[-1]["recordSha256"] if log else GENESIS_PREV_HASH
    seq = len(log) + 1
    record = {
        "eventId": f"evt-{seq:06d}",
        "type": event_type,
        "notificationId": notification["id"],
        "statusAfter": notification.get("status"),
        "actor": actor,
        "at": at_iso,
        "notificationSnapshotSha256": notification_snapshot_sha256(notification),
        "details": details or {},
    }
    record = attach_record_audit_hash(record, previous_record_hash=prev_hash, seq=seq)
    log.append(record)
    store["auditMeta"] = {
        "hashSpecVersion": AUDIT_HASH_SPEC_VERSION,
        "tailHash": record["recordSha256"],
        "length": len(log),
    }
    return record


def verify_audit_chain(store: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    log = store.get("auditLog") or []
    meta = store.get("auditMeta") or {}
    if not log and not meta:
        return True, None
    return verify_record_hash_chain(
        log,
        expected_tail_hash=meta.get("tailHash"),
        expected_length=meta.get("length"),
    )


# =============================================================================
# VIEW DẪN XUẤT
# =============================================================================

def _sort_key_created(n: Dict[str, Any]) -> float:
    ts = _iso_to_ts(n.get("createdAt"))
    return ts if ts is not None else 0.0


def _sort_key_ended(n: Dict[str, Any]) -> float:
    ts = _iso_to_ts(n.get("endedAt"))
    if ts is None:
        ts = _iso_to_ts(n.get("createdAt"))
    return ts if ts is not None else 0.0


def build_views(store: Dict[str, Any]) -> Dict[str, Any]:
    notes = store.get("notifications", [])
    active = sorted([n for n in notes if n.get("status") == STATUS_ACTIVE], key=_sort_key_created, reverse=True)
    history = sorted([n for n in notes if n.get("status") in TERMINAL_STATUSES], key=_sort_key_ended, reverse=True)
    counts = {s: sum(1 for n in notes if n.get("status") == s) for s in VALID_STATUSES}
    counts["total"] = len(notes)
    return {
        "schemaVersion": store.get("schemaVersion", NOTIFICATION_SCHEMA_VERSION),
        "revision": store.get("revision", 1),
        "timezone": store.get("timezone", VN_TZ_KEY),
        "notifications": copy.deepcopy(notes),
        "activeNotifications": copy.deepcopy(active),
        "history": copy.deepcopy(history),
        "active": copy.deepcopy(active[0]) if active else None,
        "counts": counts,
    }


def refresh_derived_views(store: Dict[str, Any]) -> None:
    """Cập nhật view tương thích ngược `active` / `history` (dẫn xuất, không phải nguồn sự thật)."""
    views = build_views(store)
    store["active"] = views["active"]
    store["history"] = views["history"]


# =============================================================================
# MIGRATION
# =============================================================================

def _collect_legacy_items(raw: Dict[str, Any], schema: str) -> List[Dict[str, Any]]:
    if schema == "v3":
        return [copy.deepcopy(n) for n in raw.get("notifications", []) if isinstance(n, dict)]
    if schema == "v2":
        campaigns = raw.get("campaigns", {})
        order = raw.get("campaignOrder") or list(campaigns.keys())
        return [copy.deepcopy(campaigns[c]) for c in order if isinstance(campaigns.get(c), dict)]
    if schema == "v1":
        items: List[Dict[str, Any]] = []
        hist = raw.get("history", [])
        if isinstance(hist, list):
            for h in reversed(hist):  # history cũ: mới nhất đứng đầu -> đảo để cũ nhất trước
                if isinstance(h, dict):
                    items.append(copy.deepcopy(h))
        if isinstance(raw.get("active"), dict):
            items.append(copy.deepcopy(raw["active"]))
        return items
    if schema == "legacy_single":
        return [copy.deepcopy(raw)]
    return []


def _resolve_duplicate(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    """Cùng id xuất hiện 2 lần: ưu tiên bản ghi đã kết thúc (thông tin mới hơn) thay vì bản active."""
    ex_status, _ = map_legacy_status(existing.get("status"))
    in_status, _ = map_legacy_status(incoming.get("status"))
    if ex_status != STATUS_ACTIVE and in_status == STATUS_ACTIVE:
        return existing
    return incoming


def migrate_to_notifications_store(
    raw: Any,
    now_iso: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Chuyển mọi schema cũ (V1 active+history, V2 campaigns, bản ghi đơn lẻ) sang Schema v3.
    Với Schema v3 sẵn có: chỉ chuẩn hóa lại (idempotent), không ghi thêm audit event.
    Trả về (store_v3, report). report['allPreserved'] = False nếu có bất kỳ id/trường quan trọng
    nào bị mất -> tầng gọi PHẢI từ chối ghi file.
    """
    now_iso = now_iso or now_vn_iso()
    schema = detect_schema(raw)
    raw = raw if isinstance(raw, dict) else {}

    source_items = _collect_legacy_items(raw, schema)
    by_id: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    duplicates: List[str] = []
    for idx, item in enumerate(source_items):
        nid = str(item.get("id") or f"ann-legacy-{idx + 1:03d}")
        item["id"] = nid
        if nid in by_id:
            duplicates.append(nid)
            by_id[nid] = _resolve_duplicate(by_id[nid], item)
        else:
            by_id[nid] = item
            order.append(nid)

    normalized = [normalize_notification(by_id[nid]) for nid in order]
    if schema != "v3":
        # Sắp theo thời điểm tạo (ổn định) để danh sách phản ánh đúng trình tự lịch sử
        normalized = [n for _, n in sorted(enumerate(normalized), key=lambda p: (_sort_key_created(p[1]), p[0]))]

    if schema == "v3":
        store = copy.deepcopy(raw)
    else:
        store = {}
    store["schemaVersion"] = NOTIFICATION_SCHEMA_VERSION
    store["schemaName"] = NOTIFICATION_SCHEMA_NAME
    try:
        store["revision"] = max(1, int(raw.get("revision", 1)))
    except (TypeError, ValueError):
        store["revision"] = 1
    store["timezone"] = VN_TZ_KEY
    store["processedRequests"] = dict(raw.get("processedRequests") or {}) if isinstance(raw.get("processedRequests"), dict) else {}
    store["notifications"] = normalized
    store.setdefault("auditLog", [])

    migrated = schema not in ("v3", "empty")
    if migrated:
        store["migration"] = {
            "fromSchema": schema,
            "toSchemaVersion": NOTIFICATION_SCHEMA_VERSION,
            "migratedAt": now_iso,
            "sourceNotificationCount": len(source_items),
            "resultNotificationCount": len(normalized),
            "duplicateIdsResolved": duplicates,
        }
        for n in normalized:
            append_audit_event(
                store,
                "MIGRATED_FROM_" + schema.upper(),
                n,
                SYSTEM_MIGRATION_ACTOR,
                now_iso,
                {"legacyStatus": n.get("legacyStatus"), "status": n.get("status")},
            )

    # Đối chiếu bảo toàn dữ liệu
    field_mismatches: List[Dict[str, Any]] = []
    result_by_id = {n["id"]: n for n in normalized}
    for nid in order:
        src = by_id[nid]
        dst = result_by_id.get(nid)
        if dst is None:
            field_mismatches.append({"id": nid, "field": "*", "reason": "missing"})
            continue
        for f in MIGRATION_CRITICAL_FIELDS:
            if f in src and src.get(f) is not None and str(src.get(f)).strip() != str(dst.get(f)).strip():
                field_mismatches.append({"id": nid, "field": f, "before": src.get(f), "after": dst.get(f)})

    refresh_derived_views(store)
    report = {
        "fromSchema": schema,
        "migrated": migrated,
        "sourceIds": order,
        "resultIds": [n["id"] for n in normalized],
        "duplicateIdsResolved": duplicates,
        "fieldMismatches": field_mismatches,
        "allPreserved": set(order) == set(result_by_id.keys()) and not field_mismatches,
    }
    return store, report


# =============================================================================
# TỰ ĐỘNG HẾT HẠN
# =============================================================================

def _push_status_history(n: Dict[str, Any], old: str, new: str, at_iso: str, actor: str, reason: Optional[str]):
    n.setdefault("statusHistory", []).append(
        {"from": old, "to": new, "at": at_iso, "by": actor, "reason": reason}
    )


def expire_due_notifications(store: Dict[str, Any], now_ts: Optional[float] = None) -> List[str]:
    """
    Chuyển mọi thông báo `active` có `expiresAtTimestamp < now` sang `expired`.
    Idempotent: thông báo đã expired không bị xử lý lại; `endedAt` = đúng mốc hạn chót.
    Không ảnh hưởng thông báo khác.
    """
    now_val = float(now_ts if now_ts is not None else time.time())
    expired_ids: List[str] = []
    for n in store.get("notifications", []):
        if n.get("status") != STATUS_ACTIVE:
            continue
        exp_ts = n.get("expiresAtTimestamp")
        if exp_ts is None or now_val <= float(exp_ts):
            continue
        end_iso = ts_to_vn_iso(exp_ts)
        # Tự động đóng băng tiến độ của đợt thu khi hết hạn
        try:
            try:
                from backend.contribution_store import freeze_campaign_progress_record
            except ImportError:
                from contribution_store import freeze_campaign_progress_record
            n["finalProgress"] = freeze_campaign_progress_record(n["id"], reason=AUTO_EXPIRE_REASON)
        except Exception:
            pass

        n["status"] = STATUS_EXPIRED
        n["endedAt"] = end_iso
        n["expiredAt"] = end_iso
        n["endReason"] = AUTO_EXPIRE_REASON
        n["statusChangedBy"] = SYSTEM_EXPIRE_ACTOR
        _push_status_history(n, STATUS_ACTIVE, STATUS_EXPIRED, end_iso, SYSTEM_EXPIRE_ACTOR, AUTO_EXPIRE_REASON)
        append_audit_event(store, "AUTO_EXPIRED", n, SYSTEM_EXPIRE_ACTOR, end_iso, {"expiresAt": end_iso})
        expired_ids.append(n["id"])
    if expired_ids:
        refresh_derived_views(store)
    return expired_ids


# =============================================================================
# THAO TÁC NGHIỆP VỤ
# =============================================================================

def find_notification(store: Dict[str, Any], notification_id: str) -> Optional[Dict[str, Any]]:
    for n in store.get("notifications", []):
        if n.get("id") == notification_id:
            return n
    return None


def resolve_target_id(store: Dict[str, Any], requested_id: Optional[str]) -> str:
    """
    Có id -> phải tồn tại. Không có id (client cũ) -> ưu tiên thông báo active mới nhất.
    """
    if requested_id is not None and str(requested_id).strip():
        nid = str(requested_id).strip()
        if find_notification(store, nid) is None:
            raise NotificationNotFoundError(f"Không tìm thấy thông báo id='{nid}'.", notificationId=nid)
        return nid
    actives = [n for n in store.get("notifications", []) if n.get("status") == STATUS_ACTIVE]
    if not actives:
        raise NotificationNotFoundError("Hiện không có thông báo nào đang hoạt động.")
    actives_sorted = sorted(actives, key=_sort_key_created, reverse=True)
    return actives_sorted[0]["id"]


def validate_notification_fields(fields: Dict[str, Any], partial: bool = False) -> Dict[str, Any]:
    clean: Dict[str, Any] = {}
    if not partial or "title" in fields:
        title = str(fields.get("title") or "").strip()
        if not title:
            raise NotificationValidationError("Tiêu đề không được để trống.")
        clean["title"] = title
    if not partial or "targetAmountEth" in fields:
        amount = str(fields.get("targetAmountEth") or "").strip()
        if not amount:
            raise NotificationValidationError("Mức đóng không được để trống.")
        try:
            if float(amount) <= 0:
                raise NotificationValidationError("Mức đóng phải lớn hơn 0 ETH.")
            eth_to_wei_str(amount)
        except ValueError as exc:
            raise NotificationValidationError("Mức đóng không hợp lệ.") from exc
        clean["targetAmountEth"] = amount
    if "deadline" in fields or not partial:
        clean["deadline"] = str(fields.get("deadline") or "Chưa xác định").strip()
    if "purpose" in fields:
        clean["purpose"] = str(fields.get("purpose") or "").strip()
    if "classSize" in fields:
        try:
            clean["classSize"] = int(fields.get("classSize"))
        except (TypeError, ValueError):
            pass
    if "autoCloseOnTarget" in fields:
        clean["autoCloseOnTarget"] = bool(fields.get("autoCloseOnTarget"))
    return clean


def generate_notification_id(store: Dict[str, Any], requested: Optional[str] = None) -> str:
    existing = {n.get("id") for n in store.get("notifications", [])}
    base = str(requested).strip() if requested else f"ann-{datetime.now(get_vn_tz()).strftime('%Y%m%d%H%M%S')}"
    if base not in existing:
        return base
    while True:
        cand = f"{base}-{secrets.token_hex(2)}"
        if cand not in existing:
            return cand


def create_notification(
    store: Dict[str, Any],
    fields: Dict[str, Any],
    actor: str,
    now_iso: Optional[str] = None,
    requested_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Thêm MỘT thông báo active mới. Không chạm vào bất kỳ thông báo nào khác."""
    now_iso = now_iso or now_vn_iso()
    clean = validate_notification_fields(fields, partial=False)
    raw = {
        "id": generate_notification_id(store, requested_id or fields.get("id")),
        "title": clean["title"],
        "targetAmountEth": clean["targetAmountEth"],
        "deadline": clean["deadline"],
        "purpose": clean.get("purpose", ""),
        "classSize": clean.get("classSize"),
        "autoCloseOnTarget": clean.get("autoCloseOnTarget", False),
        "status": STATUS_ACTIVE,
        "createdAt": now_iso,
        "createdBy": actor,
        "updatedAt": now_iso,
        "updatedBy": actor,
        "endedAt": None,
        "endReason": None,
    }
    n = normalize_notification(raw)
    _push_status_history(n, None, STATUS_ACTIVE, now_iso, actor, "Tạo thông báo")
    store.setdefault("notifications", []).append(n)
    append_audit_event(store, "CREATED", n, actor, now_iso)
    refresh_derived_views(store)
    return n


def edit_notification(
    store: Dict[str, Any],
    notification_id: Optional[str] = None,
    fields: Optional[Dict[str, Any]] = None,
    actor: Optional[str] = None,
    now_iso: Optional[str] = None,
    *,
    target_id: Optional[str] = None,
    updates: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Chỉ cập nhật đúng thông báo theo id, và chỉ khi thông báo đó còn active."""
    nid = notification_id or target_id
    flds = fields or updates or {}
    act = actor or kwargs.get("by", "system")
    now_iso = now_iso or now_vn_iso()
    n = find_notification(store, nid)
    if n is None:
        raise NotificationNotFoundError(f"Không tìm thấy thông báo id='{nid}'.")
    if n.get("status") != STATUS_ACTIVE:
        raise InvalidTransitionError(
            f"Thông báo '{nid}' đang ở trạng thái '{n.get('status')}', không thể chỉnh sửa.",
            currentStatus=n.get("status"),
        )
    clean = validate_notification_fields(flds, partial=True)
    changed = {}
    for k, v in clean.items():
        if n.get(k) != v:
            changed[k] = {"before": n.get(k), "after": v}
            n[k] = v
    n["updatedAt"] = now_iso
    n["updatedBy"] = act
    renormalized = normalize_notification(n)
    n.clear()
    n.update(renormalized)
    append_audit_event(store, "EDITED", n, act, now_iso, {"changedFields": sorted(changed.keys())})
    refresh_derived_views(store)
    return n


def transition_notification(
    store: Dict[str, Any],
    notification_id: Optional[str] = None,
    to_status: Optional[str] = None,
    actor: Optional[str] = None,
    reason: Optional[str] = None,
    now_iso: Optional[str] = None,
    *,
    target_id: Optional[str] = None,
    new_status: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Chuyển đúng một thông báo active sang archived hoặc revoked."""
    nid = notification_id or target_id
    status = to_status or new_status
    act = actor or kwargs.get("by", "system")
    if status not in (STATUS_ARCHIVED, STATUS_REVOKED, STATUS_COMPLETED):
        raise InvalidTransitionError(f"Trạng thái đích không hợp lệ: {status}.")
    now_iso = now_iso or now_vn_iso()
    n = find_notification(store, nid)
    if n is None:
        raise NotificationNotFoundError(f"Không tìm thấy thông báo id='{nid}'.")
    if n.get("status") != STATUS_ACTIVE:
        raise InvalidTransitionError(
            f"Thông báo '{nid}' đã ở trạng thái '{n.get('status')}', không thể chuyển sang '{status}'.",
            currentStatus=n.get("status"),
        )
    clean_reason = str(reason or "").strip()
    if status == STATUS_REVOKED and not clean_reason:
        raise NotificationValidationError("Thu hồi thông báo bắt buộc phải có lý do.")
    if not clean_reason:
        if status == STATUS_COMPLETED:
            clean_reason = "Đã hoàn thành mục tiêu đợt thu"
        else:
            clean_reason = "Ban cán sự chủ động kết thúc đợt thu"
    n["status"] = status
    n["endedAt"] = now_iso
    n["endReason"] = clean_reason
    n["updatedAt"] = now_iso
    n["updatedBy"] = act
    n["statusChangedBy"] = act
    if status == STATUS_REVOKED:
        n["revokedAt"] = now_iso
        n["revokedBy"] = act
    elif status == STATUS_COMPLETED:
        n["completedAt"] = now_iso
        n["completedBy"] = act
    else:
        n["archivedAt"] = now_iso
        n["archivedBy"] = act
    _push_status_history(n, STATUS_ACTIVE, status, now_iso, act, clean_reason)
    append_audit_event(store, status.upper(), n, act, now_iso, {"reason": clean_reason})
    refresh_derived_views(store)
    return n

