from PIL import Image

trans_im = Image.open('web/logo.png')
w, h = trans_im.size
side = max(w, h)
sq_trans = Image.new('RGBA', (side, side), (0, 0, 0, 0))
sq_trans.paste(trans_im, ((side - w) // 2, (side - h) // 2))
sq_trans.save('web/logo.png', 'PNG')

# Also overwrite web/logo.jpg with a clean version so both logo.png and logo.jpg exist and look great!
sq_white = Image.new('RGB', (side, side), (255, 255, 255))
sq_white.paste(trans_im, ((side - w) // 2, (side - h) // 2), trans_im)
sq_white.save('web/logo.jpg', 'JPEG', quality=95)

print(f"Updated web/logo.png (square transparent {sq_trans.size}) and web/logo.jpg (clean square {sq_white.size})")
