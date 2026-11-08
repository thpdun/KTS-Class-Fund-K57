with open('backend/notification_store.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace hardcoded 7 fallbacks
old_1 = """    try:
        n["classSize"] = int(item.get("classSize", 7))
    except (TypeError, ValueError):
        n["classSize"] = 7"""

new_1 = """    req_sz = item.get("classSize")
    if req_sz is not None:
        try:
            n["classSize"] = max(1, int(req_sz))
        except (TypeError, ValueError):
            n["classSize"] = None
    else:
        n["classSize"] = None"""

assert old_1 in text, 'old_1 not found'
text = text.replace(old_1, new_1)

old_2 = """        "classSize": clean.get("classSize", 7),"""
new_2 = """        "classSize": clean.get("classSize"),"""
assert old_2 in text, 'old_2 not found'
text = text.replace(old_2, new_2)

with open('backend/notification_store.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('Updated notification_store.py successfully!')

