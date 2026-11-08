with open('web/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. DEFAULT_ANNOUNCEMENT
old_1 = """    const DEFAULT_ANNOUNCEMENT = {
      title: "Hiện chưa có thông báo kêu gọi nộp quỹ",
      targetAmountEth: "0",
      deadline: "Không có",
      classSize: 7,"""
new_1 = """    const DEFAULT_ANNOUNCEMENT = {
      title: "Hiện chưa có thông báo kêu gọi nộp quỹ",
      targetAmountEth: "0",
      deadline: "Không có",
      classSize: 0,"""
assert old_1 in text, 'old_1 not found'
text = text.replace(old_1, new_1)

# 2. getDynamicClassSize
old_2 = """    function getDynamicClassSize(ann) {
      if (classRoster && classRoster.length > 0) return classRoster.length;
      if (ann && ann.classSize) return Number(ann.classSize);
      return 7;
    }"""
new_2 = """    function getDynamicClassSize(ann) {
      if (ann && ann.classSize && Number(ann.classSize) > 0) return Number(ann.classSize);
      if (classRoster && classRoster.length > 0) return classRoster.length;
      return 0;
    }"""
assert old_2 in text, 'old_2 not found'
text = text.replace(old_2, new_2)

# 3. viewAnnouncementDetail: Sĩ số
old_3 = """`Sĩ số: ${item.classSize || 7} sinh viên\\n`"""
new_3 = """`Sĩ số: ${getDynamicClassSize(item) || 'Chưa xác định'} sinh viên\\n`"""
assert old_3 in text, 'old_3 not found'
text = text.replace(old_3, new_3)

# 4. viewAnnouncementDetail: item.progress.classSize
old_4 = """${item.progress.classSize || 7} ví"""
new_4 = """${(item.progress.classSize || getDynamicClassSize(item))} ví"""
assert old_4 in text, 'old_4 not found'
text = text.replace(old_4, new_4)

# 5. History card rendering: cSize fallback
old_5 = """const cSize = fp.classSize || 7;"""
new_5 = """const cSize = fp.classSize || getDynamicClassSize(item);"""
assert old_5 in text, 'old_5 not found'
text = text.replace(old_5, new_5)

# 6. renderMultipleProgressCards
old_6 = """const dynamicClassSize = (classRoster && classRoster.length > 0) ? classRoster.length : 7;"""
new_6 = """const dynamicClassSize = (classRoster && classRoster.length > 0) ? classRoster.length : 0;"""
assert old_6 in text, 'old_6 not found'
text = text.replace(old_6, new_6)

# 7. formAnnClassSize input in create mode
old_7 = """document.getElementById("formAnnClassSize").value = classRoster ? classRoster.length : 7;"""
new_7 = """document.getElementById("formAnnClassSize").value = (classRoster && classRoster.length > 0) ? classRoster.length : "";"""
assert old_7 in text, 'old_7 not found'
text = text.replace(old_7, new_7)

# 8. btnSave in modal
old_8 = """const classSize = classRoster ? classRoster.length : 7;"""
new_8 = """const classSize = (classRoster && classRoster.length > 0) ? classRoster.length : null;"""
assert old_8 in text, 'old_8 not found'
text = text.replace(old_8, new_8)

# 9. rosterCountBadge
old_9 = """<span>📋</span> Quản lý Danh bạ K57 (<span id="rosterCountBadge">7</span>)"""
new_9 = """<span>📋</span> Quản lý Danh bạ K57 (<span id="rosterCountBadge">--</span>)"""
assert old_9 in text, 'old_9 not found'
text = text.replace(old_9, new_9)

with open('web/index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('Updated web/index.html successfully!')

