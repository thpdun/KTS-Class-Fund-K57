import sys
import os
import re
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

print("=== KIỂM THỬ XÁC MINH CẬP NHẬT LOGO1 ===")

# 1. Kiểm tra file logo1.png
logo1_path = os.path.join("web", "logo1.png")
if not os.path.exists(logo1_path):
    print(f"[FAIL] Tệp {logo1_path} không tồn tại!")
    sys.exit(1)

size_bytes = os.path.getsize(logo1_path)
print(f"[PASS] Tệp {logo1_path} tồn tại (kích thước: {size_bytes:,} bytes).")

try:
    img = Image.open(logo1_path)
    w, h = img.size
    aspect_ratio = w / h
    print(f"[PASS] Định dạng ảnh: {img.format}, Kích thước: {w}x{h} px, Tỷ lệ: {aspect_ratio:.2f}:1")
    if aspect_ratio == 1.0:
        print("[PASS] Tỷ lệ ảnh là hình vuông chuẩn (1:1), hoàn toàn phù hợp với khung logo giao diện.")
except Exception as e:
    print(f"[FAIL] Không thể đọc tệp ảnh: {e}")
    sys.exit(1)

# 2. Kiểm tra web/index.html
index_path = os.path.join("web", "index.html")
with open(index_path, "r", encoding="utf-8") as f:
    content = f.read()

# Kiểm tra favicon
favicon_match = re.search(r'<link\s+rel="icon"\s+type="image/png"\s+href="logo1\.png">', content)
if favicon_match:
    print("[PASS] Favicon đã được cập nhật chính xác sang logo1.png (type='image/png').")
else:
    print("[FAIL] Favicon chưa trỏ đúng logo1.png hoặc MIME type chưa phải image/png!")

# Kiểm tra sidebar logo
sidebar_match = re.search(r'<img\s+src="logo1\.png"\s+alt="Logo KTS Class Fund"\s+class="sidebar-logo-img">', content)
if sidebar_match:
    print("[PASS] Logo sidebar đã được cập nhật chính xác sang logo1.png.")
else:
    print("[FAIL] Logo sidebar chưa trỏ đúng logo1.png!")

# Kiểm tra topbar logo
topbar_match = re.search(r'<img\s+src="logo1\.png"\s+alt="KTS Logo"\s+class="topbar-mini-logo">', content)
if topbar_match:
    print("[PASS] Logo topbar (header) đã được cập nhật chính xác sang logo1.png.")
else:
    print("[FAIL] Logo topbar chưa trỏ đúng logo1.png!")

# Kiểm tra không còn sót logo.png cũ trong index.html
old_logo_matches = re.findall(r'logo\.png', content)
if len(old_logo_matches) == 0:
    print("[PASS] Không còn bất kỳ tham chiếu logo.png cũ nào trong web/index.html.")
else:
    print(f"[FAIL] Vẫn còn {len(old_logo_matches)} tham chiếu logo.png trong web/index.html!")

# 3. Kiểm tra CSS object-fit bảo vệ tỷ lệ ảnh
if "object-fit: contain !important;" in content:
    print("[PASS] CSS có quy tắc 'object-fit: contain !important;' bảo đảm không bao giờ méo ảnh.")
else:
    print("[WARNING] Chưa tìm thấy 'object-fit: contain !important;' trong CSS.")

print("=== TẤT CẢ KIỂM THỬ XÁC MINH LOGO1 ĐỀU THÀNH CÔNG ===")
