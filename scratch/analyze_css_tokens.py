import re

with open('web/index.html', encoding='utf-8') as f:
    content = f.read()

# Extract <style> block
style_match = re.search(r'<style>(.*?)</style>', content, re.DOTALL)
if style_match:
    css = style_match.group(1)
    
    # Check root variables
    root_match = re.search(r':root\s*\{(.*?)\}', css, re.DOTALL)
    if root_match:
        root_vars = [line.strip() for line in root_match.group(1).splitlines() if line.strip().startswith('--')]
        print(f"Total root variables: {len(root_vars)}")
        spacing_vars = [v for v in root_vars if 'space' in v or 'gap' in v or 'pad' in v]
        print(f"Spacing vars in :root: {spacing_vars}")
    
    # Check media queries
    media_queries = re.findall(r'@media[^{]+\{', css)
    print("\nMedia queries found:")
    for mq in set(media_queries):
        print(" ", mq.strip())

    # Find major class rules
    print("\nClasses defined for layout:")
    for cls in ['.container', '.app-content', '.section-header', '.card', '.btn', '.form-control', '.data-table', '.role-panel', '.dapp-hero-section', '.hero-section']:
        matches = [m.start() for m in re.finditer(re.escape(cls) + r'\b', css)]
        print(f"  {cls}: {len(matches)} occurrences")
