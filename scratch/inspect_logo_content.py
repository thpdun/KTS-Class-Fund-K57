from PIL import Image
import numpy as np

im = Image.open('web/logo.jpg').convert('RGB')
arr = np.array(im)

# Find pixels that are NOT white (threshold e.g. < 245 in any channel)
non_white = np.any(arr < 245, axis=-1)

# Find bounding box
rows = np.any(non_white, axis=1)
cols = np.any(non_white, axis=0)

rmin, rmax = np.where(rows)[0][[0, -1]]
cmin, cmax = np.where(cols)[0][[0, -1]]

print(f"Original size: {im.size}")
print(f"Content bbox: left={cmin}, top={rmin}, right={cmax}, bottom={rmax}")
print(f"Content width: {cmax - cmin}, height: {rmax - rmin}")
print(f"Padding: top={rmin}, bottom={im.height - rmax}, left={cmin}, right={im.width - cmax}")
