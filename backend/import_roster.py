#!/usr/bin/env python3
"""
Công cụ nhập dữ liệu Danh bạ Sinh viên K57 (Class Roster Importer)
Tuân thủ quy ước AGENTS.md:
- Python 3.10+
- Kiểm tra tính hợp lệ của dữ liệu trước khi xử lý
"""

import csv
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from eth_utils import keccak

# Đảm bảo in tiếng Việt chuẩn trên Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROSTER_FILE = Path(__file__).parent / "class_roster.json"

# =============================================================================
# CHUẨN HÓA VÀ BĂM DANH BẠ SINH VIÊN (Phase 3 / Mục D)
# =============================================================================
# Thuật toán băm được chọn: KECCAK-256 (EVM standard keccak256)
# Lý do lựa chọn:
# 1. Native bytes32 on-chain: Keccak-256 là hàm băm gốc của máy ảo Ethereum (EVM),
#    khớp hoàn toàn với kiểu `bytes32 public rosterHash` trong `ProjectCore.sol` và
#    hàm `ethers.keccak256(ethers.toUtf8Bytes(...))` ở Frontend Web3 DApp.
# 2. Không nhầm lẫn tiêu chuẩn: Tránh rủi ro sai lệch padding giữa NIST SHA3-256 (FIPS-202)
#    và Ethereum Keccak-256 (keccak / keccak256).
# 3. Tính sẵn có và nhất quán: Thư viện `eth_utils.keccak` đã được cài đặt và sử dụng
#    xuyên suốt trong dự án (`backend/blockchain_indexer.py`).
# 4. Bảo vệ quyền riêng tư: Chỉ đưa mã băm 32 byte lên chuỗi qua commitRoster(bytes32),
#    tuyệt đối không đưa Họ tên, MSSV hoặc thông tin định danh cá nhân lên blockchain.
ROSTER_HASH_ALGORITHM = "keccak256"
ROSTER_CANONICAL_VERSION = "roster-canonical-v1"
ROSTER_CANONICAL_SPEC = "sorted(mssv, wallet.lower()) + json(sort_keys=True, ensure_ascii=False, separators=(',', ':')) + utf8 + keccak256"


def normalize_roster_entry(entry: Any) -> Dict[str, str]:
    """
    Chuẩn hóa cấu trúc của một phần tử trong danh bạ để đảm bảo tính xác định (determinism):
    - mssv: chuỗi ký tự đã cắt khoảng trắng đầu/cuối.
    - name: chuỗi họ tên đã cắt khoảng trắng đầu/cuối.
    - wallet: chuỗi địa chỉ ví chuyển về chữ thường (lowercase) để tránh phân biệt hoa/thường EIP-55.
    - role: vai trò chuẩn hóa chữ thường ('bcs', 'student', ...).
    - roleTitle: chức danh tương ứng.
    """
    if not isinstance(entry, dict):
        raise ValueError("Mỗi phần tử trong danh bạ phải là một từ điển (dict).")

    mssv = str(entry.get("mssv", "")).strip()
    name = str(entry.get("name", "")).strip()
    wallet = str(entry.get("wallet", "")).strip().lower()
    role_raw = str(entry.get("role", "student")).strip().lower()
    role = "bcs" if role_raw == "bcs" else ("advisor" if role_raw == "advisor" else (role_raw or "student"))
    role_title = str(entry.get("roleTitle", "")).strip()
    if not role_title:
        role_title = "Ban cán sự" if role == "bcs" else ("Cố vấn học tập" if role == "advisor" else "Sinh viên")

    if not mssv:
        raise ValueError("Phần tử danh bạ thiếu MSSV hợp lệ.")

    return {
        "mssv": mssv,
        "name": name,
        "wallet": wallet,
        "role": role,
        "roleTitle": role_title,
    }


def normalize_roster_for_hash(roster: List[Any]) -> List[Dict[str, str]]:
    """
    Chuẩn hóa và sắp xếp toàn bộ danh bạ theo thứ tự xác định:
    Sắp xếp tăng dần theo (mssv, wallet, name) để hoán vị thứ tự các dòng
    trong file lưu trữ vẫn tạo ra chuỗi chuẩn hóa và mã băm giống hệt nhau.
    """
    if not isinstance(roster, list):
        raise ValueError("Danh bạ sinh viên phải là danh sách (list).")

    normalized = [normalize_roster_entry(item) for item in roster]
    normalized.sort(key=lambda s: (s["mssv"], s["wallet"], s["name"]))
    return normalized


def serialize_canonical_roster(roster: List[Any]) -> str:
    """
    Tuần tự hóa danh bạ sang JSON chuẩn hóa (RFC 8785 subset):
    - sort_keys=True
    - ensure_ascii=False (giữ nguyên tiếng Việt UTF-8 không mã hóa escape)
    - separators=(',', ':') (loại bỏ mọi khoảng trắng dư thừa giữa các token)
    """
    normalized = normalize_roster_for_hash(roster)
    return json.dumps(normalized, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def compute_roster_hash(roster: List[Any]) -> str:
    """
    Tính mã băm keccak256 chuẩn hóa cho danh bạ sinh viên.
    Trả về chuỗi hex 66 ký tự có tiền tố '0x' (bytes32 tương thích Solidity).
    Từ chối danh bạ rỗng để tránh commit mã băm vô nghĩa lên chuỗi.
    """
    if not roster:
        raise ValueError("Danh bạ lớp rỗng, không thể tạo mã băm rosterHash hợp lệ.")

    canonical_json = serialize_canonical_roster(roster)
    raw_digest = keccak(canonical_json.encode("utf-8"))
    return "0x" + raw_digest.hex()


def build_roster_hash_payload(roster: List[Any]) -> Dict[str, Any]:
    """
    Xây dựng payload phản hồi chứa mã băm và siêu dữ liệu cho API GET /api/roster/hash:
    TUYỆT ĐỐI KHÔNG chứa dữ liệu cá nhân (PII như họ tên, mssv, danh sách ví).
    """
    normalized = normalize_roster_for_hash(roster)
    if not normalized:
        raise ValueError("Danh bạ lớp rỗng, không thể tạo mã băm rosterHash hợp lệ.")

    digest_hex = compute_roster_hash(roster)
    wallet_count = sum(1 for s in normalized if validate_wallet(s["wallet"]))

    return {
        "rosterHash": digest_hex,
        "algorithm": ROSTER_HASH_ALGORITHM,
        "canonicalVersion": ROSTER_CANONICAL_VERSION,
        "canonicalSpec": ROSTER_CANONICAL_SPEC,
        "count": len(normalized),
        "classSize": len(normalized),
        "walletCount": wallet_count,
    }


def compute_roster_hash_from_file(roster_path: Path = ROSTER_FILE) -> Dict[str, Any]:
    """Đọc file danh bạ từ đường dẫn và tính toán payload mã băm chuẩn hóa."""
    p = Path(roster_path)
    if not p.exists():
        raise FileNotFoundError(f"Không tìm thấy file danh bạ: {p}")
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    return build_roster_hash_payload(data)


def validate_wallet(wallet: str) -> bool:
    """Kiểm tra địa chỉ ví Ethereum hợp lệ (42 ký tự, bắt đầu bằng 0x)"""
    if not wallet or not isinstance(wallet, str):
        return False
    w = wallet.strip()
    return w.startswith("0x") and len(w) == 42


def import_from_csv(csv_path: Path) -> dict:
    """Đọc dữ liệu sinh viên từ file CSV và hợp nhất vào class_roster.json"""
    if not csv_path.exists():
        return {"success": False, "error": f"Không tìm thấy file: {csv_path}"}

    # Đọc danh bạ hiện có
    existing_roster = []
    if ROSTER_FILE.exists():
        try:
            with open(ROSTER_FILE, "r", encoding="utf-8") as f:
                existing_roster = json.load(f)
        except Exception:
            existing_roster = []

    roster_map = {item.get("mssv"): item for item in existing_roster if item.get("mssv")}

    added_count = 0
    updated_count = 0
    invalid_rows = []

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=2):
            mssv = str(row.get("mssv", "")).strip()
            name = str(row.get("name", "")).strip()
            wallet = str(row.get("wallet", "")).strip()
            role = str(row.get("role", "student")).strip().lower()
            role_title = str(row.get("roleTitle", "")).strip()

            if not mssv or not name:
                invalid_rows.append(f"Dòng {idx}: Thiếu MSSV hoặc Họ tên.")
                continue

            if wallet and not validate_wallet(wallet):
                invalid_rows.append(f"Dòng {idx} ({name}): Địa chỉ ví '{wallet}' không hợp lệ (cần 42 ký tự, bắt đầu bằng 0x).")
                continue

            if not role_title:
                role_title = "Ban cán sự" if role == "bcs" else "Sinh viên"

            entry = {
                "mssv": mssv,
                "name": name,
                "wallet": wallet,
                "role": role,
                "roleTitle": role_title
            }

            if mssv in roster_map:
                roster_map[mssv] = entry
                updated_count += 1
            else:
                roster_map[mssv] = entry
                added_count += 1

    updated_roster = list(roster_map.values())
    with open(ROSTER_FILE, "w", encoding="utf-8") as f:
        json.dump(updated_roster, f, ensure_ascii=False, indent=2)

    return {
        "success": True,
        "added": added_count,
        "updated": updated_count,
        "total": len(updated_roster),
        "invalid_rows": invalid_rows
    }


if __name__ == "__main__":
    target_csv = Path(__file__).parent / "sample_roster.csv"
    if len(sys.argv) > 1:
        target_csv = Path(sys.argv[1])

    print("=" * 60)
    print(f"📥 Đang nạp danh bạ từ: {target_csv}")
    result = import_from_csv(target_csv)
    if result["success"]:
        print(f"✅ Thành công! Đã thêm mới: {result['added']}, Đã cập nhật: {result['updated']}")
        print(f"   Tổng số sinh viên hiện có trong danh bạ: {result['total']}")
        try:
            hash_info = compute_roster_hash_from_file(ROSTER_FILE)
            print(f"   Mã băm danh bạ on-chain (rosterHash): {hash_info['rosterHash']}")
            print(f"   Thuật toán: {hash_info['algorithm']} ({hash_info['canonicalVersion']})")
        except Exception as he:
            print(f"   ⚠️ Không thể tính rosterHash: {he}")
        if result["invalid_rows"]:
            print("⚠️ Cảnh báo các dòng không hợp lệ:")
            for warn in result["invalid_rows"]:
                print(f"   - {warn}")
    else:
        print(f"❌ Thất bại: {result['error']}")
    print("=" * 60)
