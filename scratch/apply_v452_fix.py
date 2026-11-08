# -*- coding: utf-8 -*-
"""
Script áp dụng bản sửa lỗi V4.5.2 một cách chính xác vào backend/server.py và web/index.html
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def patch_backend_server():
    server_path = PROJECT_ROOT / "backend" / "server.py"
    raw_content = server_path.read_text(encoding="utf-8")
    is_crlf = "\r\n" in raw_content
    content = raw_content.replace("\r\n", "\n")

    # 1. Thêm NotificationValidationError vào import
    target_import_1 = "        build_views,\n    )\nexcept ImportError:\n    from notification_store import ("
    replacement_import_1 = "        build_views,\n        NotificationValidationError,\n    )\nexcept ImportError:\n    from notification_store import ("
    
    target_import_2 = "        build_views,\n    )\n\ntry:\n    from backend.campaign_progress import"
    replacement_import_2 = "        build_views,\n        NotificationValidationError,\n    )\n\ntry:\n    from backend.campaign_progress import"

    if target_import_1 in content:
        content = content.replace(target_import_1, replacement_import_1, 1)
        print("Patched import 1 in server.py")

    if target_import_2 in content:
        content = content.replace(target_import_2, replacement_import_2, 1)
        print("Patched import 2 in server.py")

    # 2. Bắt NotificationValidationError ở create_notification
    old_create = """                else:
                    # mode == "create": Thêm mới độc lập, KHÔNG đóng hay ảnh hưởng bất kỳ thông báo cũ nào!
                    announcement_data = create_notification(
                        store,
                        req_data,
                        actor=session["address"],
                        client_request_id=client_request_id,
                    )
                    action_name = "create_announcement" """

    new_create = """                else:
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
                    action_name = "create_announcement" """

    if old_create in content:
        content = content.replace(old_create, new_create, 1)
        print("Patched create_notification in server.py")
    else:
        old_create_2 = """                else:
                    # mode == "create": Thêm mới độc lập, KHÔNG đóng hay ảnh hưởng bất kỳ thông báo cũ nào!
                    announcement_data = create_notification(
                        store,
                        req_data,
                        actor=session["address"],
                        client_request_id=client_request_id,
                    )
                    action_name = "create_announcement"\n"""
        if old_create_2 in content:
            content = content.replace(old_create_2, new_create.rstrip() + "\n", 1)
            print("Patched create_notification (variant 2) in server.py")
        else:
            print("ERROR: old_create not found in server.py")

    # 3. Bọc save_announcements_store ở cả 3 vị trí (close, revoke, create/edit)
    safe_save = """                    try:
                        save_announcements_store(store)
                    except AtomicStorageError as ase:
                        logger.warning("Thao tác lưu trữ bị từ chối do bảo vệ dữ liệu: %s", ase)
                        self._send_json(503, {
                            "success": False,
                            "code": "STORAGE_PROTECTED",
                            "error": "Hệ thống lưu trữ đang ở chế độ bảo vệ dữ liệu (Read-Only). Vui lòng cấu hình cho phép ghi dữ liệu trên máy chủ triển khai.",
                        })
                        return
                    except Exception as ex:
                        logger.error("Lỗi hệ thống khi lưu thông báo: %s", ex, exc_info=True)
                        self._send_json(500, {
                            "success": False,
                            "code": "INTERNAL_SERVER_ERROR",
                            "error": "Đã xảy ra lỗi nội bộ trên máy chủ khi lưu thông báo. Vui lòng liên hệ quản trị viên.",
                        })
                        return"""

    target_save_create = """                if client_request_id:
                    resp_payload["clientRequestId"] = str(client_request_id).strip()
                save_announcements_store(store)
                self._send_json(200, resp_payload)"""

    replacement_save_create = """                if client_request_id:
                    resp_payload["clientRequestId"] = str(client_request_id).strip()
""" + safe_save + """
                self._send_json(200, resp_payload)"""

    if target_save_create in content:
        content = content.replace(target_save_create, replacement_save_create, 1)
        print("Patched save_announcements_store in create/edit")
    else:
        print("ERROR: target_save_create not found!")

    target_save_close = """                    if client_request_id:
                        resp_payload["clientRequestId"] = str(client_request_id).strip()
                    save_announcements_store(store)
                    self._send_json(200, resp_payload)
                    return

                # 2. Thao tác thu hồi đợt thu (revoke)"""

    replacement_save_close = """                    if client_request_id:
                        resp_payload["clientRequestId"] = str(client_request_id).strip()
""" + safe_save + """
                    self._send_json(200, resp_payload)
                    return

                # 2. Thao tác thu hồi đợt thu (revoke)"""

    if target_save_close in content:
        content = content.replace(target_save_close, replacement_save_close, 1)
        print("Patched save_announcements_store in close")
    else:
        print("ERROR: target_save_close not found!")

    target_save_revoke = """                    if client_request_id:
                        resp_payload["clientRequestId"] = str(client_request_id).strip()
                    save_announcements_store(store)
                    self._send_json(200, resp_payload)
                    return

                # 3. Thao tác chỉnh sửa (mode="edit") hoặc tạo mới (mode="create")"""

    replacement_save_revoke = """                    if client_request_id:
                        resp_payload["clientRequestId"] = str(client_request_id).strip()
""" + safe_save + """
                    self._send_json(200, resp_payload)
                    return

                # 3. Thao tác chỉnh sửa (mode="edit") hoặc tạo mới (mode="create")"""

    if target_save_revoke in content:
        content = content.replace(target_save_revoke, replacement_save_revoke, 1)
        print("Patched save_announcements_store in revoke")
    else:
        print("ERROR: target_save_revoke not found!")

    if is_crlf:
        content = content.replace("\n", "\r\n")

    server_path.write_text(content, encoding="utf-8")
    print("Saved server.py successfully.")

if __name__ == "__main__":
    patch_backend_server()
