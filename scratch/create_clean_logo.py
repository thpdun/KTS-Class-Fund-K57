from PIL import Image
import numpy as np

im = Image.open('web/logo.jpg').convert('RGBA')
arr = np.array(im)

# Content bbox from previous step:
# left=776, top=642, right=1249, bottom=1453
# Let's add a small padding, say 25px
pad = 25
left = max(0, 776 - pad)
top = max(0, 642 - pad)
right = min(im.width, 1249 + pad)
bottom = min(im.height, 1453 + pad)

cropped = im.crop((left, top, right, bottom))
cropped_arr = np.array(cropped)

# Make pure/near white pixels transparent:
# If R > 240 and G > 240 and B > 240 -> alpha = 0, with smooth antialiasing
r, g, b, a = cropped_arr[:,:,0], cropped_arr[:,:,1], cropped_arr[:,:,2], cropped_arr[:,:,3]
# Compute distance from white (255, 255, 255)
dist_from_white = np.sqrt((255 - r.astype(float))**2 + (255 - g.astype(float))**2 + (255 - b.astype(float))**2)

# Transparent mask
alpha = np.clip((dist_from_white / 30.0) * 255, 0, 255).astype(np.uint8)
cropped_arr[:,:,3] = alpha

transparent_logo = Image.fromarray(cropped_arr)
transparent_logo.save('web/logo.png', 'PNG')

# Also create a tightly cropped square JPG version if needed
# Square crop centered on content
c_w = right - left
c_h = bottom - top
side = max(c_w, c_h)
square_im = Image.new('RGB', (side, side), (255, 255, 255))
offset_x = (side - c_w) // 2
offset_y = (side - c_h) // 2
square_im.paste(cropped.convert('RGB'), (offset_x, offset_y))
square_im.save('web/logo_cropped.jpg', 'JPEG', quality=95)

print(f"Generated web/logo.png (transparent, size {transparent_logo.size}) and web/logo_cropped.jpg (square {square_im.size})")
