import sys
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

im = Image.open('web/logo1.png')
w, h = im.size

# Sample corners and center
corners = [
    ("top-left (0,0)", im.getpixel((0, 0))),
    ("top-right", im.getpixel((w - 1, 0))),
    ("bottom-left", im.getpixel((0, h - 1))),
    ("bottom-right", im.getpixel((w - 1, h - 1))),
    ("center", im.getpixel((w // 2, h // 2)))
]

for name, col in corners:
    print(f"{name}: {col}")
