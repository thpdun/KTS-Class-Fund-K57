import sys
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

img = Image.open('web/logo1.png')
print(f"Format: {img.format}")
print(f"Size: {img.size}")
print(f"Mode: {img.mode}")
print(f"Info: {img.info}")

old_img = Image.open('web/logo.png')
print(f"Old Logo Format: {old_img.format}")
print(f"Old Logo Size: {old_img.size}")
print(f"Old Logo Mode: {old_img.mode}")
