# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import py_compile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
server_path = PROJECT_ROOT / "backend" / "server.py"
content = server_path.read_text(encoding="utf-8")

# 1. Add NotificationValidationError to imports if not present
if "NotificationValidationError" not in content:
    content = content.replace(
        "        build_views,\n    )\nexcept ImportError:",
        "        build_views,\n        NotificationValidationError,\n    )\nexcept ImportError:"
    )
    content = content.replace(
        "        build_views,\n    )\n\ntry:",
        "        build_views,\n        NotificationValidationError,\n    )\n\ntry:"
    )

# 2. Add _safe_save_announcements helper method to AIChatRequestHandler
helper_method = '''    def _safe_save_announcements(self, store: dict) -> bool:
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

'''

if "def _safe_save_announcements" not in content:
    # Insert before def do_POST
    do_post_marker = "    def do_POST(self):"
    if do_post_marker in content:
        content = content.replace(do_post_marker, helper_method + do_post_marker, 1)
        print("Inserted _safe_save_announcements helper")

# 3. Replace save_announcements_store in close announcement
old_close_save = """                    save_announcements_store(store)
                    self._send_json(200, resp_payload)
                    return

                # 2. Thao tác thu hồi đợt thu (revoke)"""

new_close_save = """                    if not self._safe_save_announcements(store):
                        return
                    self._send_json(200, resp_payload)
                    return

                # 2. Thao tác thu hồi đợt thu (revoke)"""

if old_close_save in content:
    content = content.replace(old_close_save, new_close_save, 1)
    print("Replaced close save")

# 4. Replace save_announcements_store in revoke announcement
old_revoke_save = """                    save_announcements_store(store)
                    self._send_json(200, resp_payload)
                    return

                # 3. Thao tác chỉnh sửa (mode="edit") hoặc tạo mới (mode="create")"""

new_revoke_save = """                    if not self._safe_save_announcements(store):
                        return
                    self._send_json(200, resp_payload)
                    return

                # 3. Thao tác chỉnh sửa (mode="edit") hoặc tạo mới (mode="create")"""

if old_revoke_save in content:
    content = content.replace(old_revoke_save, new_revoke_save, 1)
    print("Replaced revoke save")

# 5. Replace create_notification with try...except NotificationValidationError
old_create_block = """                else:
                    # mode == "create": Thêm mới độc lập, KHÔNG đóng hay ảnh hưởng bất kỳ thông báo cũ nào!
                    announcement_data = create_notification(
                        store,
                        req_data,
                        actor=session["address"],
                        client_request_id=client_request_id,
                    )
                    action_name = "create_announcement" """

new_create_block = """                else:
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

if old_create_block in content:
    content = content.replace(old_create_block, new_create_block, 1)
    print("Replaced create_notification")
else:
    # Try without trailing space
    old_create_block_2 = """                else:
                    # mode == "create": Thêm mới độc lập, KHÔNG đóng hay ảnh hưởng bất kỳ thông báo cũ nào!
                    announcement_data = create_notification(
                        store,
                        req_data,
                        actor=session["address"],
                        client_request_id=client_request_id,
                    )
                    action_name = "create_announcement"\n"""
    if old_create_block_2 in content:
        content = content.replace(old_create_block_2, new_create_block.rstrip() + "\n", 1)
        print("Replaced create_notification (variant 2)")

# 6. Replace save_announcements_store in create / edit
old_create_save = """                save_announcements_store(store)
                self._send_json(200, resp_payload)"""

new_create_save = """                if not self._safe_save_announcements(store):
                    return
                self._send_json(200, resp_payload)"""

if old_create_save in content:
    content = content.replace(old_create_save, new_create_save, 1)
    print("Replaced create/edit save")

server_path.write_text(content, encoding="utf-8")
print("Saved server.py, testing py_compile...")
py_compile.compile(str(server_path), doraise=True)
print("SUCCESS: server.py compiled cleanly with zero errors!")

