# -*- coding: utf-8 -*-
"""
Bộ kiểm thử toàn diện V4.5.2: Sửa lỗi tạo thông báo đợt thu mới
Bao gồm:
- Nhóm 1: Unit Test (Kiểm tra logic cô lập)
- Nhóm 2: API Integration Test (Kiểm thử tương tác HTTP thực tế với Server Testbed)
"""
import sys
import os
import json
import time
import shutil
import tempfile
import threading
import urllib.request
import urllib.error
from pathlib import Path
from http.server import HTTPServer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from backend.accounting_engine import (
    AtomicStorageError,
    DualLayerFileLock,
    safe_load_json,
    atomic_write_json,
    validate_concurrency_and_idempotency,
    record_mutation_commit
)
from backend.notification_store import (
    create_notification,
    validate_notification_fields,
    NotificationValidationError,
    build_views
)
from backend.server import (
    AIChatRequestHandler,
    _is_real_data_write_blocked,
    DEFAULT_ANNOUNCEMENT_FILE,
    ACTIVE_SESSIONS,
    AUTH_MUTEX
)

def run_unit_tests():
    print("=" * 60)
    print("NHÓM 1: UNIT TESTS (KIỂM THỬ ĐƠN VỊ CÔ LẬP)")
    print("=" * 60)
    
    # Unit Test 1: Khóa bảo vệ file thật hoạt động đúng
    is_blocked_default = _is_real_data_write_blocked(DEFAULT_ANNOUNCEMENT_FILE)
    assert is_blocked_default is True, "Unit Test 1 thất bại: File dữ liệu thật phải bị chặn ghi khi ALLOW_REAL_DATA_MUTATION != 1"
    print("  [PASS] Unit Test 1: Khóa bảo vệ dữ liệu thật _is_real_data_write_blocked hoạt động chính xác (Trả về True).")

    # Unit Test 2: File tạm không bị chặn
    temp_path = Path(tempfile.gettempdir()) / "test_ann.json"
    assert _is_real_data_write_blocked(temp_path) is False, "Unit Test 2 thất bại: File tạm không được bị chặn ghi"
    print("  [PASS] Unit Test 2: File tạm ngoài đường dẫn sản xuất được phép ghi bình thường (Trả về False).")

    # Unit Test 3: validate_notification_fields bắt lỗi khi tiêu đề hoặc số tiền rỗng / âm
    try:
        validate_notification_fields({"title": "", "targetAmountEth": "0.01"})
        assert False, "Phải ném NotificationValidationError khi tiêu đề rỗng"
    except NotificationValidationError:
        pass

    try:
        validate_notification_fields({"title": "Test", "targetAmountEth": "-0.5"})
        assert False, "Phải ném NotificationValidationError khi mức nộp âm"
    except NotificationValidationError:
        pass
    print("  [PASS] Unit Test 3: validate_notification_fields từ chối dữ liệu không hợp lệ (tiêu đề rỗng, mức nộp âm).")

    # Unit Test 4: validate_notification_fields chuẩn hóa dữ liệu hợp lệ
    clean = validate_notification_fields({
        "title": "Quỹ kiến tập Q4",
        "targetAmountEth": "0.02",
        "deadline": "31/12/2026",
        "purpose": "Học tập thực tế"
    })
    assert clean["title"] == "Quỹ kiến tập Q4"
    assert clean["targetAmountEth"] == "0.02"
    print("  [PASS] Unit Test 4: validate_notification_fields chuẩn hóa dữ liệu hợp lệ thành công.")


def run_api_integration_tests():
    print("\n" + "=" * 60)
    print("NHÓM 2: API INTEGRATION TESTS (KIỂM THỬ TƯƠNG TÁC HTTP)")
    print("=" * 60)

    # Khởi tạo Test Server trên cổng ngẫu nhiên trong tiến trình này để chia sẻ ACTIVE_SESSIONS
    test_server = HTTPServer(("127.0.0.1", 0), AIChatRequestHandler)
    port = test_server.server_port
    server_thread = threading.Thread(target=test_server.serve_forever, daemon=True)
    server_thread.start()
    server_url = f"http://127.0.0.1:{port}"

    # Lấy 1 ví BCS từ class_roster
    roster_file = PROJECT_ROOT / "backend" / "class_roster.json"
    roster = json.loads(roster_file.read_text(encoding="utf-8"))
    bcs_info = next(item for item in roster if item.get("role") == "bcs")
    bcs_wallet = bcs_info["wallet"]

    bcs_token = f"test_bcs_token_{int(time.time())}"
    student_token = f"test_student_token_{int(time.time())}"

    with AUTH_MUTEX:
        ACTIVE_SESSIONS[bcs_token] = {
            "token": bcs_token,
            "address": bcs_wallet.lower(),
            "role": "bcs",
            "isAdvisor": False,
            "isBcs": True,
            "expires_at": time.time() + 1800,
            "created_at": time.time()
        }
        ACTIVE_SESSIONS[student_token] = {
            "token": student_token,
            "address": "0x2222222222222222222222222222222222222222",
            "role": "student",
            "isAdvisor": False,
            "isBcs": False,
            "expires_at": time.time() + 1800,
            "created_at": time.time()
        }

    try:
        # API Test 1: BCS có session nhưng storage bị khóa (DEFAULT_ANNOUNCEMENT_FILE khi ALLOW_REAL_DATA_MUTATION != 1)
        # Kỳ vọng: Trả về HTTP 503 với code: "STORAGE_PROTECTED", không làm sập server!
        payload = {
            "mode": "create",
            "title": "Quỹ lớp Tháng 11 Kiểm thử Storage Khóa",
            "targetAmountEth": "0.01",
            "classSize": 7,
            "deadline": "30/11/2026",
            "purpose": "Kiểm thử khóa an toàn"
        }
        req_body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{server_url}/api/announcement",
            data=req_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {bcs_token}"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req) as resp:
                assert False, "Lẽ ra phải trả về HTTP 503 vì storage đang bị khóa"
        except urllib.error.HTTPError as err:
            assert err.code == 503, f"Mã HTTP phải là 503, nhưng nhận được {err.code}"
            err_data = json.loads(err.read().decode("utf-8"))
            assert err_data.get("code") == "STORAGE_PROTECTED", "Code lỗi phải là STORAGE_PROTECTED"
            assert err_data.get("success") is False
            print(f"  [PASS] API Test 1: Khi storage bị khóa, Server phản hồi sạch JSON HTTP 503 (code={err_data.get('code')}) an toàn.")

        # API Test 2: Sinh viên gửi request tạo thông báo
        # Kỳ vọng: Trả về HTTP 403 Forbidden
        req_student = urllib.request.Request(
            f"{server_url}/api/announcement",
            data=req_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {student_token}"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req_student) as resp:
                assert False, "Lẽ ra phải trả về HTTP 403 Forbidden đối với Sinh viên"
        except urllib.error.HTTPError as err:
            assert err.code == 403, f"Mã HTTP phải là 403, nhưng nhận được {err.code}"
            print("  [PASS] API Test 2: Sinh viên gửi request tạo thông báo bị từ chối với HTTP 403 Forbidden.")

        # API Test 3: Không có Authorization token hoặc token không hợp lệ
        req_no_auth = urllib.request.Request(
            f"{server_url}/api/announcement",
            data=req_body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req_no_auth) as resp:
                assert False, "Lẽ ra phải trả về HTTP 403 Forbidden khi thiếu token"
        except urllib.error.HTTPError as err:
            assert err.code == 403, f"Mã HTTP phải là 403, nhưng nhận được {err.code}"
            print("  [PASS] API Test 3: Yêu cầu không có Authorization Bearer token bị từ chối với HTTP 403 Forbidden.")

        # API Test 4: Gửi dữ liệu không hợp lệ (Mức nộp = 0 hoặc âm)
        invalid_body = json.dumps({
            "mode": "create",
            "title": "Sai định dạng",
            "targetAmountEth": "-0.01"
        }).encode("utf-8")
        req_invalid = urllib.request.Request(
            f"{server_url}/api/announcement",
            data=invalid_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {bcs_token}"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req_invalid) as resp:
                assert False, "Lẽ ra phải trả về HTTP 400 Bad Request"
        except urllib.error.HTTPError as err:
            assert err.code == 400, f"Mã HTTP phải là 400, nhưng nhận được {err.code}"
            print("  [PASS] API Test 4: Dữ liệu không hợp lệ (tiền âm) bị Backend từ chối với HTTP 400 Bad Request.")

        # API Test 5: Tạo thông báo thành công trong môi trường cho phép ghi (File test cô lập)
        temp_dir = tempfile.mkdtemp()
        test_ann_file = Path(temp_dir) / "test_announcements.json"
        
        initial_store = {
            "schemaVersion": 3,
            "revision": 1,
            "notifications": [
                {
                    "id": "TB-01",
                    "title": "Thông báo cũ 1",
                    "targetAmountEth": "0.01",
                    "status": "active",
                    "deadline": "31/12/2026",
                    "classSize": 7
                }
            ],
            "auditLog": [],
            "mutationCommits": []
        }
        test_ann_file.write_text(json.dumps(initial_store, indent=2), encoding="utf-8")

        old_env = os.environ.get("ANNOUNCEMENT_FILE_PATH")
        try:
            os.environ["ANNOUNCEMENT_FILE_PATH"] = str(test_ann_file)
            from backend.server import load_announcements_store, save_announcements_store
            
            store = load_announcements_store()
            new_item = create_notification(
                store,
                {
                    "title": "Đợt thu dã ngoại K57",
                    "targetAmountEth": "0.025",
                    "classSize": 7,
                    "deadline": "15/12/2026",
                    "purpose": "Chi phí dã ngoại cuối năm"
                },
                actor=bcs_wallet
            )
            save_announcements_store(store)
            
            reloaded = load_announcements_store()
            views = build_views(reloaded)
            active_ids = [n["id"] for n in views["activeNotifications"]]
            assert new_item["id"] in active_ids, "Thông báo mới phải xuất hiện trong activeNotifications"
            assert len(reloaded["notifications"]) == 2, "Tổng số thông báo phải là 2 (TB-01 cũ và TB mới)"
            print(f"  [PASS] API Test 5: Tạo thông báo mới thành công trong file test: ID={new_item['id']}, Tiêu đề='{new_item['title']}'.")
            print(f"  [PASS] API Test 6: Kiểm tra tính bền vững sau khi tải lại từ đĩa: Thông báo mới tồn tại, thông báo cũ được bảo toàn.")

            # API Test 7: Kiểm tra Chống tạo trùng (Idempotency)
            client_req_id = "req_unique_12345"
            is_replay, _ = validate_concurrency_and_idempotency(
                store,
                client_request_id=client_req_id,
                action="create_announcement",
                actor=bcs_wallet
            )
            assert is_replay is False, "Lần đầu không phải là replay"
            
            record_mutation_commit(
                store,
                action="create_announcement",
                actor=bcs_wallet,
                client_request_id=client_req_id,
                response_payload={"announcementId": new_item["id"]}
            )
            
            is_replay_2, saved_payload = validate_concurrency_and_idempotency(
                store,
                client_request_id=client_req_id,
                action="create_announcement",
                actor=bcs_wallet
            )
            assert is_replay_2 is True, "Lần 2 phải được phát hiện là replay trùng lặp"
            assert saved_payload["announcementId"] == new_item["id"]
            print("  [PASS] API Test 7: Chống tạo trùng lặp (Idempotency) bằng clientRequestId hoạt động chính xác.")

        finally:
            if old_env is not None:
                os.environ["ANNOUNCEMENT_FILE_PATH"] = old_env
            else:
                os.environ.pop("ANNOUNCEMENT_FILE_PATH", None)
            shutil.rmtree(temp_dir, ignore_errors=True)

        # API Test 8: Kiểm tra tính toàn vẹn của file backup ban đầu
        backup_path = PROJECT_ROOT / "backend" / "announcements.json.pre_fix_backup"
        assert backup_path.exists(), "File announcements.json.pre_fix_backup phải tồn tại nguyên vẹn"
        backup_data = json.loads(backup_path.read_text(encoding="utf-8"))
        total_items = (1 if backup_data.get("active") else 0) + len(backup_data.get("history", []))
        assert total_items == 2, f"File backup phải chứa đúng 2 thông báo ban đầu (1 active, 1 history), tìm thấy: {total_items}"
        print(f"  [PASS] API Test 8: File backup 'announcements.json.pre_fix_backup' được bảo toàn nguyên vẹn 100% (chứa {total_items} thông báo gốc: 1 active, 1 history).")

    finally:
        test_server.shutdown()
        test_server.server_close()

if __name__ == "__main__":
    run_unit_tests()
    run_api_integration_tests()
    print("\n" + "=" * 60)
    print("TẤT CẢ CÁC BÀI TEST UNIT VÀ API INTEGRATION ĐỀU ĐẠT (ALL PASS)!")
    print("=" * 60)
