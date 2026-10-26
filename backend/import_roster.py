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

# Đảm bảo in tiếng Việt chuẩn trên Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROSTER_FILE = Path(__file__).parent / "class_roster.json"


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
        if result["invalid_rows"]:
            print("⚠️ Cảnh báo các dòng không hợp lệ:")
            for warn in result["invalid_rows"]:
                print(f"   - {warn}")
    else:
        print(f"❌ Thất bại: {result['error']}")
    print("=" * 60)
