with open('web/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

grid_idx = text.find('home-layout-grid')
rail_idx = text.find('home-right-rail')
footer_idx = text.find('<footer')
print(f'grid_idx: {grid_idx}, rail_idx: {rail_idx}, footer_idx: {footer_idx}')

