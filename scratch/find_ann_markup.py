with open('web/index.html', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if 'id="annTitle"' in line:
            print(f'annTitle at line {idx}')
        if 'id="announcementModal"' in line:
            print(f'modal at line {idx}')
        if 'btnOpenAnnModal' in line:
            print(f'btnOpenAnnModal at line {idx}')
