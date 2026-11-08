import re

with open('backend/server.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace hardcoded 7 fallbacks
old_1 = """    roster_len = len(load_roster())
    actual_size = roster_len if roster_len > 0 else 7"""
new_1 = """    roster_len = len(load_roster())
    actual_size = roster_len if roster_len > 0 else None"""
assert old_1 in text, 'old_1 not found'
text = text.replace(old_1, new_1)

old_2 = """        "classSize": len(load_roster()) or 7,"""
new_2 = """        "classSize": len(load_roster()) or None,"""
assert old_2 in text, 'old_2 not found'
text = text.replace(old_2, new_2)

old_6 = """            roster_len = len(load_roster())
            effective_class_sz = roster_len if roster_len > 0 else 7
            target_eth_val = notif_rec.get("targetAmountEth") if notif_rec else None"""
new_6 = """            roster_len = len(load_roster())
            effective_class_sz = (notif_rec.get("classSize") if notif_rec and notif_rec.get("classSize") else None) or (roster_len if roster_len > 0 else None)
            target_eth_val = notif_rec.get("targetAmountEth") if notif_rec else None"""
assert old_6 in text, 'old_6 not found'
text = text.replace(old_6, new_6)

old_3 = """            roster_len = len(load_roster())
            effective_class_sz = roster_len if roster_len > 0 else 7"""
new_3 = """            roster_len = len(load_roster())
            effective_class_sz = roster_len if roster_len > 0 else None"""
text = text.replace(old_3, new_3)

old_4 = """resp_payload["progress"] = get_campaign_progress_view(target_nid, class_size=roster_len or 7)"""
new_4 = """resp_payload["progress"] = get_campaign_progress_view(target_nid, class_size=roster_len or None)"""
assert old_4 in text, 'old_4 not found'
text = text.replace(old_4, new_4)

old_5 = """                roster_len = len(load_roster())
                actual_class_size = roster_len if roster_len > 0 else int(req_data.get("classSize", 7))"""
new_5 = """                roster_len = len(load_roster())
                req_class_size = req_data.get("classSize")
                if req_class_size is not None and int(req_class_size) > 0:
                    actual_class_size = int(req_class_size)
                elif roster_len > 0:
                    actual_class_size = roster_len
                else:
                    self._send_json(400, {"success": False, "error": "Không thể xác định sĩ số từ danh sách lớp (Roster rỗng hoặc không hợp lệ)."})
                    return"""
assert old_5 in text, 'old_5 not found'
text = text.replace(old_5, new_5)

with open('backend/server.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('Updated server.py successfully!')
