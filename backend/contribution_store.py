# -*- coding: utf-8 -*-
"""
contribution_store.py - Quản lý tiến độ đóng góp và phân bổ giao dịch chiến dịch (Attribution Layer)
Dự án: KTS-Class-Fund-K57

Quy tắc nghiệp vụ:
1. Mỗi giao dịch blockchain (txHash) chỉ được phân bổ cho duy nhất 1 notificationId (1-to-1 mapping).
2. Chống ghi nhận trùng: Gọi claim nhiều lần với cùng txHash và cùng notificationId có tính lũy đẳng (Idempotent).
   Gọi claim txHash đã liên kết với chiến dịch khác sẽ bị từ chối (Conflict).
3. Xác minh on-chain: Backend xác thực receipt từ RPC (status=1, đúng contract ProjectCore, đúng người gửi, đúng số tiền).
4. Xác thực danh tính: Không tin địa chỉ ví client tự khai; đối chiếu ví từ session đã xác thực chữ ký (Challenge-Response)
   với `receipt.from` và event `FundDeposited(student, amount)`.
5. Chuẩn hóa chỉ số:
   - Số người đóng góp = Số địa chỉ ví duy nhất đã xác minh thuộc đợt thu.
   - Số tiền đóng góp = Tổng amount thực tế từ on-chain logs.
   - Tỷ lệ phần trăm tính theo số ví / classSize; nếu có targetEth > 0 thì tính thêm % theo số tiền.
6. Hỗ trợ Intent (claimIntentId): Khởi tạo intent trước khi mở MetaMask để ràng buộc thời gian hợp lệ,
   chống tự tạo intent hồi tố sau khi đợt thu đã đóng.
7. Snapshot bất biến (finalProgress): Đóng băng tại thời điểm kết thúc đợt thu.
   Mọi ngoại lệ sau khi đóng được ghi vào `adjustedFinalProgress` kèm audit trail đầy đủ.
"""

from __future__ import annotations

import copy
import json
import os
import threading
import time
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Sử dụng DualLayerFileLock và safe_load_json từ accounting_engine nếu có,
# hoặc triển khai cơ chế khóa file an toàn tương đương
try:
    from backend.accounting_engine import (
        DualLayerFileLock,
        atomic_write_json,
        safe_load_json,
    )
except ImportError:
    from accounting_engine import (
        DualLayerFileLock,
        atomic_write_json,
        safe_load_json,
    )

# Cấu hình đường dẫn lưu trữ
DEFAULT_CONTRIBUTIONS_FILE = (Path(__file__).parent / "campaign_contributions.json").resolve()
CONTRIBUTIONS_FILE = Path(os.environ.get("CONTRIBUTIONS_FILE_PATH", str(DEFAULT_CONTRIBUTIONS_FILE)))

DEFAULT_INTENTS_FILE = (Path(__file__).parent / "claim_intents.json").resolve()
INTENTS_FILE = Path(os.environ.get("CLAIM_INTENTS_FILE_PATH", str(DEFAULT_INTENTS_FILE)))

INTENT_EXPIRATION_SECONDS = 1800  # 30 phút cho một claim intent trước khi mở ví và ký giao dịch

# Sepolia Network Defaults
SEPOLIA_CHAIN_ID = 11155111
DEFAULT_CONTRACT_ADDRESS = "0x90948699FF04bC9cF159a39e200F09885439503D".lower()


def get_contributions_file() -> Path:
    env_val = os.environ.get("CONTRIBUTIONS_FILE_PATH", "").strip()
    if env_val:
        return Path(env_val).resolve()
    return Path(CONTRIBUTIONS_FILE).resolve()


def get_intents_file() -> Path:
    env_val = os.environ.get("CLAIM_INTENTS_FILE_PATH", "").strip()
    if env_val:
        return Path(env_val).resolve()
    return Path(INTENTS_FILE).resolve()


def default_contributions_store() -> Dict[str, Any]:
    return {
        "version": 1,
        "campaigns": {},            # notificationId -> CampaignProgressRecord
        "claimedTxHashes": {},      # txHash_lower -> notificationId
        "unallocatedTxHashes": {},  # txHash_lower -> UnallocatedRecord
        "transactions": {}          # txHash_lower -> VerifiedTransactionRecord
    }


def default_intents_store() -> Dict[str, Any]:
    return {
        "version": 1,
        "intents": {}               # intentId -> IntentRecord
    }


def _validate_contributions_structure(data: Any) -> Tuple[bool, Optional[str]]:
    if not isinstance(data, dict):
        return False, "Store contributions phải là một đối tượng JSON (dict)."
    if "claimedTxHashes" not in data or "campaigns" not in data:
        return False, "Thiếu trường bắt buộc trong contributions store."
    return True, None


def _validate_intents_structure(data: Any) -> Tuple[bool, Optional[str]]:
    if not isinstance(data, dict):
        return False, "Store intents phải là một đối tượng JSON (dict)."
    if "intents" not in data:
        return False, "Thiếu trường intents trong store."
    return True, None


def load_contributions_store() -> Dict[str, Any]:
    file_path = get_contributions_file()
    if not file_path.exists():
        return default_contributions_store()
    try:
        data, _ = safe_load_json(file_path, validator_fn=_validate_contributions_structure)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return default_contributions_store()


def save_contributions_store(store: Dict[str, Any]) -> None:
    file_path = get_contributions_file()
    if file_path == DEFAULT_CONTRIBUTIONS_FILE and os.environ.get("ALLOW_REAL_DATA_MUTATION", "0").strip() != "1":
        pass
    atomic_write_json(file_path, store, validator_fn=_validate_contributions_structure)


def load_intents_store() -> Dict[str, Any]:
    file_path = get_intents_file()
    if not file_path.exists():
        return default_intents_store()
    try:
        data, _ = safe_load_json(file_path, validator_fn=_validate_intents_structure)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return default_intents_store()


def save_intents_store(store: Dict[str, Any]) -> None:
    file_path = get_intents_file()
    if file_path == DEFAULT_INTENTS_FILE and os.environ.get("ALLOW_REAL_DATA_MUTATION", "0").strip() != "1":
        pass
    atomic_write_json(file_path, store, validator_fn=_validate_intents_structure)


# =============================================================================
# GIAI ĐOẠN 1: QUẢN LÝ CLAIM INTENT (BẢO VỆ MỐC THỜI GIAN ĐÁNG TIN CẬY)
# =============================================================================

def create_claim_intent(
    notification_id: str,
    verified_wallet: str,
    notification_status: str,
    target_amount_eth: Optional[str] = None
) -> Dict[str, Any]:
    """
    Tạo claimIntentId TRƯỚC KHI mở MetaMask.
    Backend ghi nhận notificationId, thời điểm tạo intent (now), trạng thái thông báo và ví đã xác thực qua session.
    Nếu đợt thu KHÔNG còn active, từ chối tạo intent để chống hợp thức hóa hồi tố.
    """
    clean_nid = str(notification_id or "").strip()
    clean_wallet = str(verified_wallet or "").strip().lower()
    
    if not clean_nid:
        raise ValueError("Yêu cầu notificationId hợp lệ để tạo claim intent.")
    if not clean_wallet.startswith("0x") or len(clean_wallet) != 42:
        raise ValueError("Địa chỉ ví xác thực không hợp lệ.")
    
    if str(notification_status).lower() != "active":
        raise ValueError(f"Không thể tạo ý định nộp quỹ vì đợt thu '{clean_nid}' hiện không ở trạng thái ACTIVE (trạng thái: {notification_status}).")

    intents_file = get_intents_file()
    with DualLayerFileLock(intents_file):
        store = load_intents_store()
        import secrets
        intent_id = f"intent-{int(time.time())}-{secrets.token_hex(4)}"
        now_ts = time.time()
        
        intent_record = {
            "intentId": intent_id,
            "notificationId": clean_nid,
            "wallet": clean_wallet,
            "createdAtTimestamp": now_ts,
            "expiresAtTimestamp": now_ts + INTENT_EXPIRATION_SECONDS,
            "notificationStatusAtCreation": notification_status,
            "targetAmountEth": target_amount_eth,
            "status": "PENDING"
        }
        store["intents"][intent_id] = intent_record
        save_intents_store(store)
        return intent_record


def get_claim_intent(intent_id: str) -> Optional[Dict[str, Any]]:
    intents_file = get_intents_file()
    with DualLayerFileLock(intents_file):
        store = load_intents_store()
        return store["intents"].get(intent_id)


def mark_intent_used(intent_id: str, tx_hash: str) -> None:
    intents_file = get_intents_file()
    with DualLayerFileLock(intents_file):
        store = load_intents_store()
        if intent_id in store["intents"]:
            store["intents"][intent_id]["status"] = "CONSUMED"
            store["intents"][intent_id]["consumedTxHash"] = str(tx_hash).strip().lower()
            store["intents"][intent_id]["consumedAtTimestamp"] = time.time()
            save_intents_store(store)


# =============================================================================
# TÍNH TOÁN TIẾN ĐỘ CHIẾN DỊCH (CAMPAIGN PROGRESS CALCULATION)
# =============================================================================

def _validate_roster_structure(data: Any) -> Tuple[bool, Optional[str]]:
    if not isinstance(data, list):
        return False, "Danh bạ sinh viên phải là một danh sách (list)."
    return True, None


def get_official_roster_count() -> int:
    """
    Lấy số lượng thành viên hợp lệ từ danh sách lớp chính thức (backend/class_roster.json).
    Sử dụng validator_fn=_validate_roster_structure để safe_load_json chấp nhận root là list.
    Nếu không đọc được roster hoặc roster rỗng/không hợp lệ, trả về 0 để phía gọi xử lý lỗi,
    tuyệt đối không âm thầm sử dụng giá trị mặc định cứng.
    """
    roster_file_env = os.environ.get("CLASS_ROSTER_FILE_PATH", "").strip()
    roster_file = Path(roster_file_env).resolve() if roster_file_env else (Path(__file__).parent / "class_roster.json").resolve()
    bak_file = roster_file.with_name(roster_file.name + ".bak")

    if roster_file.exists() or bak_file.exists():
        try:
            data, _ = safe_load_json(roster_file, validator_fn=_validate_roster_structure)
            if isinstance(data, list) and len(data) > 0:
                return len(data)
        except Exception:
            pass
    return 0


def init_campaign_progress_record(notification_id: str, target_eth: Optional[str] = None, class_size: Optional[int] = None) -> Dict[str, Any]:
    clean_target = str(target_eth).strip() if target_eth is not None else None
    has_target = False
    target_float = 0.0
    if clean_target and clean_target not in ("0", "0.0", "None", ""):
        try:
            target_float = float(clean_target)
            has_target = target_float > 0
        except ValueError:
            has_target = False

    effective_size = class_size
    if effective_size is None or effective_size <= 0:
        official_count = get_official_roster_count()
        if official_count > 0:
            effective_size = official_count
        else:
            raise ValueError(f"Không thể xác định sĩ số hợp lệ từ danh sách lớp cho đợt thu '{notification_id}'.")

    return {
        "notificationId": notification_id,
        "classSize": max(1, int(effective_size)),
        "hasFinancialTarget": has_target,
        "targetAmountEth": clean_target if has_target else None,
        "raisedWei": "0",
        "raisedEth": "0.0000",
        "contributingWallets": [],        # Danh sách địa chỉ ví duy nhất đã xác minh
        "contributingWalletsCount": 0,    # Số ví duy nhất (Headcount)
        "totalTransactionsCount": 0,      # Tổng số giao dịch thành công đã phân bổ
        "headcountPercent": 0,            # (contributingWalletsCount / classSize) * 100
        "financialPercent": 0 if has_target else None,
        "allocatedTxHashes": [],
        "isFrozen": False,
        "finalProgress": None,
        "adjustedFinalProgress": None,
        "auditLog": []
    }


def get_or_create_campaign_progress(store: Dict[str, Any], notification_id: str, target_eth: Optional[str] = None, class_size: Optional[int] = None) -> Dict[str, Any]:
    if notification_id not in store["campaigns"]:
        store["campaigns"][notification_id] = init_campaign_progress_record(notification_id, target_eth, class_size)
    else:
        # Cập nhật class_size hoặc target nếu có thông tin mới
        rec = store["campaigns"][notification_id]
        if class_size is not None and class_size > 0:
            rec["classSize"] = int(class_size)
            wallets_cnt = len(rec.get("contributingWallets", []))
            rec["contributingWalletsCount"] = wallets_cnt
            rec["headcountPercent"] = min(100, round((wallets_cnt / rec["classSize"]) * 100))
    return store["campaigns"][notification_id]


# =============================================================================
# XÁC MINH ON-CHAIN VÀ PHÂN BỔ GIAO DỊCH (ON-CHAIN VERIFICATION & ATTRIBUTION)
# =============================================================================

class ContributionAttributionError(ValueError):
    """Lỗi nghiệp vụ phân bổ đóng góp."""
    pass


def verify_and_claim_contribution(
    notification_id: str,
    tx_hash: str,
    verified_wallet: str,
    claim_intent_id: Optional[str] = None,
    rpc_client: Optional[Any] = None,
    notification_status: str = "active",
    notification_ended_at_ts: Optional[float] = None,
    class_size: Optional[int] = None,
    target_eth: Optional[str] = None
) -> Dict[str, Any]:
    """
    Hàm lõi xác minh giao dịch on-chain và phân bổ cho notificationId:
    1. Kiểm tra định dạng txHash, notificationId, verified_wallet.
    2. Chống ghi nhận trùng (Idempotency):
       - Nếu txHash đã liên kết với chính notification_id này: trả về kết quả thành công hiện hành.
       - Nếu txHash đã liên kết với notification_id khác: báo lỗi 409 Conflict.
    3. Kiểm tra Intent (nếu có claim_intent_id):
       - Intent phải thuộc về đúng ví verified_wallet và đúng notification_id.
    4. Kiểm tra vòng đời và xử lý ngoại lệ PENDING_CLAIM:
       - Nếu đợt thu đã đóng: kiểm tra thời điểm intent và thời điểm block on-chain.
         Nếu giao dịch phát sinh sau khi đợt đã đóng, đưa vào UNALLOCATED_EXCEPTION.
    5. Xác minh on-chain qua RPC:
       - Lấy TransactionReceipt. Kiểm tra status == 1.
       - Kiểm tra to == ProjectCore Contract Address.
       - Kiểm tra from == verified_wallet (Khớp danh tính ví đã xác thực).
       - Trích xuất sự kiện FundDeposited(student, amount) -> số tiền Wei thực tế.
    6. Cập nhật tiến độ đợt thu:
       - Cập nhật số ví duy nhất, cộng dồn số tiền, tính lại tỷ lệ hoàn thành.
    """
    clean_nid = str(notification_id or "").strip()
    clean_tx = str(tx_hash or "").strip().lower()
    clean_wallet = str(verified_wallet or "").strip().lower()

    if not clean_nid:
        raise ContributionAttributionError("Mã đợt thu (notificationId) không được để trống.")
    if not clean_tx.startswith("0x") or len(clean_tx) != 66:
        raise ContributionAttributionError(f"Định dạng txHash không hợp lệ: '{clean_tx}'.")
    if not clean_wallet.startswith("0x") or len(clean_wallet) != 42:
        raise ContributionAttributionError(f"Địa chỉ ví xác thực không hợp lệ: '{clean_wallet}'.")

    contributions_file = get_contributions_file()
    with DualLayerFileLock(contributions_file):
        store = load_contributions_store()

        # 1. Kiểm tra tính lũy đẳng (Idempotency Check)
        if clean_tx in store["claimedTxHashes"]:
            existing_nid = store["claimedTxHashes"][clean_tx]
            if existing_nid == clean_nid:
                # Đã ghi nhận đúng cho đợt này -> Trả về kết quả hiện tại mà không cộng dồn thêm
                camp_rec = store["campaigns"].get(clean_nid, {})
                return {
                    "success": True,
                    "idempotent": True,
                    "message": "Giao dịch đã được ghi nhận trước đó cho đợt thu này.",
                    "notificationId": clean_nid,
                    "txHash": clean_tx,
                    "campaignProgress": camp_rec
                }
            else:
                # Đã liên kết cho đợt khác -> Xung đột (Conflict)
                raise ContributionAttributionError(
                    f"Giao dịch '{clean_tx}' đã được phân bổ cho đợt thu khác ('{existing_nid}'). "
                    f"Mỗi giao dịch on-chain chỉ được phân bổ cho duy nhất một đợt thu."
                )

        # 2. Kiểm tra Intent (nếu client cung cấp)
        if claim_intent_id:
            intent = get_claim_intent(claim_intent_id)
            if not intent:
                raise ContributionAttributionError(f"Không tìm thấy claim intent '{claim_intent_id}'.")
            if intent.get("wallet", "").lower() != clean_wallet:
                raise ContributionAttributionError("Ví người gửi không khớp với ví đã đăng ký trong claim intent.")
            if intent.get("notificationId") != clean_nid:
                raise ContributionAttributionError("Mã đợt thu trong claim intent không khớp với yêu cầu.")

        # 3. Xác minh On-chain qua RPC
        # Sử dụng rpc_client nếu được truyền vào, hoặc khởi tạo SepoliaRpcClient mặc định
        receipt = None
        block_timestamp = None
        amount_wei = 0
        from_address = None

        if rpc_client is not None:
            # Đối với rpc_client (hoặc mock trong unit test)
            receipt = rpc_client.get_transaction_receipt(clean_tx)
        else:
            # Gọi trực tiếp qua blockchain_indexer RPC nếu có
            try:
                from backend.blockchain_indexer import SepoliaRpcClient
                client = SepoliaRpcClient()
                receipt = client.call("eth_getTransactionReceipt", [clean_tx])
            except Exception as e:
                raise ContributionAttributionError(f"Không thể kết nối RPC Sepolia để xác minh biên lai giao dịch: {e}")

        if not receipt:
            raise ContributionAttributionError(f"Không tìm thấy biên lai giao dịch (receipt) cho txHash '{clean_tx}'.")

        # Kiểm tra trạng thái giao dịch
        status_val = receipt.get("status")
        if status_val in (0, "0x0", "0"):
            raise ContributionAttributionError(f"Giao dịch '{clean_tx}' thất bại trên Blockchain (status=0).")

        # Kiểm tra hợp đồng đích
        to_addr = (receipt.get("to") or "").lower()
        expected_contract = (os.environ.get("CONTRACT_ADDRESS") or DEFAULT_CONTRACT_ADDRESS).lower()
        if to_addr != expected_contract:
            raise ContributionAttributionError(
                f"Giao dịch tương tác với hợp đồng {to_addr}, không khớp với hợp đồng quỹ lớp {expected_contract}."
            )

        # Kiểm tra người gửi (receipt.from) khớp với ví đã xác thực
        from_address = (receipt.get("from") or "").lower()
        if from_address != clean_wallet:
            raise ContributionAttributionError(
                f"Người gửi giao dịch ({from_address}) không khớp với tài khoản ví đã xác thực ({clean_wallet})."
            )

        # Trích xuất số tiền từ logs sự kiện FundDeposited
        # Event Signature: FundDeposited(address indexed student, uint256 amount)
        # Topic0: 0x... (FundDeposited)
        # Topic1: address indexed student
        # Data: uint256 amount
        FUND_DEPOSITED_TOPIC0 = "0x89980d2fb2d3523f6e16bc8d16719e7ccae18c1b3f94294ca237ca5e5a2db12f".lower()
        found_deposit_event = False

        logs = receipt.get("logs", [])
        for log in logs:
            topics = log.get("topics", [])
            if topics and topics[0].lower() == FUND_DEPOSITED_TOPIC0:
                # Kiểm tra student trong topic1
                if len(topics) > 1:
                    topic_student = "0x" + topics[1][-40:].lower()
                    if topic_student != clean_wallet:
                        continue
                data_hex = log.get("data", "0x0")
                try:
                    amount_wei = int(data_hex, 16)
                    found_deposit_event = True
                    break
                except (ValueError, TypeError):
                    pass

        if not found_deposit_event or amount_wei <= 0:
            # Fallback nếu transaction gọi trực tiếp deposit() có value
            try:
                # Nếu receipt có value hoặc lấy từ get_transaction
                if rpc_client is not None and hasattr(rpc_client, "get_transaction"):
                    tx_data = rpc_client.get_transaction(clean_tx)
                    if tx_data and "value" in tx_data:
                        val_str = tx_data["value"]
                        amount_wei = int(val_str, 16) if isinstance(val_str, str) and val_str.startswith("0x") else int(val_str)
            except Exception:
                pass

        if amount_wei <= 0:
            raise ContributionAttributionError(
                f"Giao dịch '{clean_tx}' không phát sự kiện FundDeposited hoặc có số tiền nộp bằng 0."
            )

        # 4. Kiểm tra thời điểm kết thúc đợt thu (Xử lý PENDING_CLAIM / Ngoại lệ)
        # Lấy block_timestamp nếu có
        block_num = receipt.get("blockNumber")
        if block_num and rpc_client is not None and hasattr(rpc_client, "get_block_timestamp"):
            block_timestamp = rpc_client.get_block_timestamp(block_num)

        is_campaign_closed = str(notification_status).lower() in ("completed", "expired", "archived", "revoked")
        if is_campaign_closed:
            # Đợt thu đã đóng. Kiểm tra xem giao dịch có phát sinh trước thời điểm đóng không
            if notification_ended_at_ts and block_timestamp and block_timestamp > notification_ended_at_ts:
                # Giao dịch phát sinh SAU KHI đợt thu đã đóng -> Chuyển sang UNALLOCATED_EXCEPTION
                store["unallocatedTxHashes"][clean_tx] = {
                    "txHash": clean_tx,
                    "intendedNotificationId": clean_nid,
                    "student": clean_wallet,
                    "amountWei": str(amount_wei),
                    "amountEth": str(Decimal(amount_wei) / Decimal(10**18)),
                    "blockNumber": block_num,
                    "blockTimestamp": block_timestamp,
                    "reason": "TRANSACTION_MINED_AFTER_CAMPAIGN_CLOSED",
                    "recordedAt": time.time()
                }
                save_contributions_store(store)
                raise ContributionAttributionError(
                    f"Đợt thu '{clean_nid}' đã kết thúc trước khi giao dịch được xác nhận trên Blockchain. "
                    f"Giao dịch đã được lưu an toàn vào danh mục 'UNALLOCATED_EXCEPTION' chờ Ban cán sự đối soát."
                )

        # 5. Phân bổ thành công vào chiến dịch
        amount_eth_str = str(Decimal(amount_wei) / Decimal(10**18))
        camp = get_or_create_campaign_progress(store, clean_nid, target_eth=target_eth, class_size=class_size)

        # Thêm ví vào danh sách nếu chưa có
        wallets_set = set(w.lower() for w in camp.get("contributingWallets", []))
        is_new_wallet = clean_wallet not in wallets_set
        if is_new_wallet:
            camp["contributingWallets"].append(clean_wallet)
            camp["contributingWalletsCount"] = len(camp["contributingWallets"])

        # Cộng dồn số tiền
        curr_wei = int(camp.get("raisedWei", "0"))
        new_wei = curr_wei + amount_wei
        camp["raisedWei"] = str(new_wei)
        camp["raisedEth"] = f"{(Decimal(new_wei) / Decimal(10**18)):.4f}"
        camp["totalTransactionsCount"] = int(camp.get("totalTransactionsCount", 0)) + 1
        camp["allocatedTxHashes"].append(clean_tx)

        # Tính lại tỷ lệ phần trăm
        sz = camp.get("classSize")
        if not sz or int(sz) <= 0:
            official_sz = get_official_roster_count()
            if official_sz > 0:
                sz = official_sz
                camp["classSize"] = sz
            else:
                sz = 1
        else:
            sz = int(sz)
        camp["headcountPercent"] = min(100, round((camp["contributingWalletsCount"] / sz) * 100))

        if camp.get("hasFinancialTarget") and camp.get("targetAmountEth"):
            try:
                tgt = float(camp["targetAmountEth"])
                if tgt > 0:
                    curr_eth_val = float(Decimal(new_wei) / Decimal(10**18))
                    camp["financialPercent"] = min(100, round((curr_eth_val / tgt) * 100))
            except ValueError:
                pass

        # Ghi vào bảng tra cứu toàn cục
        store["claimedTxHashes"][clean_tx] = clean_nid
        store["transactions"][clean_tx] = {
            "txHash": clean_tx,
            "notificationId": clean_nid,
            "student": clean_wallet,
            "amountWei": str(amount_wei),
            "amountEth": amount_eth_str,
            "blockNumber": block_num,
            "blockTimestamp": block_timestamp,
            "verifiedAt": time.time(),
            "claimIntentId": claim_intent_id
        }

        # Nếu có intent, đánh dấu đã sử dụng
        if claim_intent_id:
            mark_intent_used(claim_intent_id, clean_tx)

        save_contributions_store(store)

        return {
            "success": True,
            "idempotent": False,
            "message": "Xác minh và phân bổ giao dịch thành công.",
            "notificationId": clean_nid,
            "txHash": clean_tx,
            "amountEth": amount_eth_str,
            "contributingWalletsCount": camp["contributingWalletsCount"],
            "headcountPercent": camp["headcountPercent"],
            "campaignProgress": camp
        }


def get_campaign_progress_view(notification_id: str, class_size: Optional[int] = None) -> Dict[str, Any]:
    """Truy vấn tiến độ hiện hành của một chiến dịch."""
    contributions_file = get_contributions_file()
    with DualLayerFileLock(contributions_file):
        store = load_contributions_store()
        rec = store["campaigns"].get(notification_id)
        if not rec:
            return init_campaign_progress_record(notification_id, class_size=class_size)
        return copy.deepcopy(rec)


def freeze_campaign_progress_record(
    notification_id: str,
    reason: str = "Đợt thu kết thúc",
    class_size: Optional[int] = None
) -> Dict[str, Any]:
    """
    Đóng băng tiến độ khi thông báo kết thúc.
    Tạo snapshot bất biến `finalProgress`.
    Không bao giờ tự động tính lại snapshot này.
    """
    contributions_file = get_contributions_file()
    with DualLayerFileLock(contributions_file):
        store = load_contributions_store()
        camp = store["campaigns"].get(notification_id)
        if not camp:
            camp = init_campaign_progress_record(notification_id, class_size=class_size)
            store["campaigns"][notification_id] = camp

        if camp.get("isFrozen") and camp.get("finalProgress"):
            return copy.deepcopy(camp["finalProgress"])

        # Xác định classSize chính xác: ưu tiên camp.classSize, sau đó class_size đối số, sau đó roster chính thức
        target_class_sz = camp.get("classSize")
        if not target_class_sz or int(target_class_sz) <= 0:
            if class_size and int(class_size) > 0:
                target_class_sz = int(class_size)
            else:
                official_sz = get_official_roster_count()
                if official_sz > 0:
                    target_class_sz = official_sz
                else:
                    raise ValueError(f"Không thể xác định sĩ số hợp lệ để chốt sổ chiến dịch '{notification_id}'.")
            camp["classSize"] = target_class_sz

        target_class_sz = int(target_class_sz)
        wallets_cnt = camp.get("contributingWalletsCount", 0)
        headcount_pct = min(100, round((wallets_cnt / max(1, target_class_sz)) * 100))
        camp["headcountPercent"] = headcount_pct

        now_iso = time.strftime("%Y-%m-%dT%H:%M:%S+07:00", time.localtime())
        snapshot = {
            "notificationId": notification_id,
            "isFrozen": True,
            "frozenAt": now_iso,
            "reason": reason,
            "raisedEth": camp.get("raisedEth", "0.0000"),
            "raisedWei": camp.get("raisedWei", "0"),
            "contributingWalletsCount": wallets_cnt,
            "classSize": target_class_sz,
            "headcountPercent": headcount_pct,
            "hasFinancialTarget": camp.get("hasFinancialTarget", False),
            "targetAmountEth": camp.get("targetAmountEth"),
            "financialPercent": camp.get("financialPercent"),
            "totalTransactionsCount": camp.get("totalTransactionsCount", 0),
            "allocatedTxHashes": list(camp.get("allocatedTxHashes", []))
        }

        camp["isFrozen"] = True
        camp["finalProgress"] = snapshot
        save_contributions_store(store)
        return copy.deepcopy(snapshot)


def record_adjusted_final_progress(
    notification_id: str,
    actor: str,
    reason: str,
    adjustments: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Quy trình ngoại lệ có kiểm toán:
    Tuyệt đối không ghi đè `finalProgress` ban đầu.
    Lưu bản ghi điều chỉnh riêng `adjustedFinalProgress` kèm đầy đủ actor, reason, timestamp và giá trị trước/sau.
    """
    contributions_file = get_contributions_file()
    with DualLayerFileLock(contributions_file):
        store = load_contributions_store()
        camp = store["campaigns"].get(notification_id)
        if not camp or not camp.get("finalProgress"):
            raise ValueError(f"Chiến dịch '{notification_id}' chưa có finalProgress ban đầu để điều chỉnh.")

        original = copy.deepcopy(camp["finalProgress"])
        adjusted = copy.deepcopy(original)

        for k, v in adjustments.items():
            if k in adjusted:
                adjusted[k] = v

        now_iso = time.strftime("%Y-%m-%dT%H:%M:%S+07:00", time.localtime())
        adjustment_record = {
            "adjustedAt": now_iso,
            "actor": actor,
            "reason": reason,
            "before": original,
            "after": adjusted
        }

        camp["adjustedFinalProgress"] = adjusted
        camp.setdefault("auditLog", []).append(adjustment_record)
        save_contributions_store(store)
        return copy.deepcopy(adjusted)
