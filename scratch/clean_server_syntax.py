# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import py_compile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
server_path = PROJECT_ROOT / "backend" / "server.py"
lines = server_path.read_text(encoding="utf-8").splitlines(keepends=True)

# 1. Clean up lines 1118-1123
# Find line with 'ann_file = get_announcement_file()'
ann_idx = None
for idx, l in enumerate(lines):
    if "ann_file = get_announcement_file()" in l and idx > 1100:
        ann_idx = idx
        break

print("ann_idx:", ann_idx)

# Check next lines
print("line ann_idx+1:", repr(lines[ann_idx+1]))
print("line ann_idx+2:", repr(lines[ann_idx+2]))

# If line ann_idx+1 is '            try:\n', remove it!
if "try:" in lines[ann_idx+1].strip():
    del lines[ann_idx+1]
    print("Removed stray try at ann_idx+1")

# Make sure with DualLayerFileLock(ann_file) is indented with 12 spaces
lines[ann_idx+1] = "            with DualLayerFileLock(ann_file):\n"
lines[ann_idx+2] = "                try:\n"
lines[ann_idx+3] = "                    store = load_announcements_store()\n"

# 2. Clean up lines around line 1345-1365 (remove stray except block at bottom if it exists)
stray_except_idx = None
for idx in range(ann_idx+10, len(lines)):
    if "except AtomicStorageError as ase:" in lines[idx] and lines[idx].startswith("            except"):
        stray_except_idx = idx
        break

if stray_except_idx is not None:
    print("Found stray except at:", stray_except_idx)
    # find where this except block ends (before # 4. Thêm / Chỉnh sửa danh bạ)
    end_idx = stray_except_idx
    while end_idx < len(lines) and not ("# 4. Thêm" in lines[end_idx] or "elif path == \"/api/roster/register\":" in lines[end_idx]):
        end_idx += 1
    print("Removing stray except lines from", stray_except_idx, "to", end_idx)
    del lines[stray_except_idx:end_idx]

server_path.write_text("".join(lines), encoding="utf-8")
print("Saved cleaned server.py, testing py_compile...")
py_compile.compile(str(server_path), doraise=True)
print("SUCCESS: py_compile passed without errors!")

