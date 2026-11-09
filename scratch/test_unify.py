with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

checks = [
    'announcementModal',
    'formAnnSyncOnchain',
    'formAnnDays',
    'updateFormDeadlineFromDays',
    'createCollection',
    'closeCollection'
]
for c in checks:
    print(c, c in html)

