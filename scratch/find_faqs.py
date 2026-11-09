with open('web/index.html', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if 'faqData' in line or 'faqList' in line or 'const faqs' in line or 'var faqs' in line or 'let faqs' in line or 'renderFaq' in line:
            print(f'{idx}: {line.strip()[:100]}')

