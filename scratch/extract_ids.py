import re

with open('web/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find script part
script_match = re.search(r'<script>(.*)</script>', content, re.DOTALL)
if script_match:
    script_text = script_match.group(1)
    
    # find getElementById
    by_id = set(re.findall(r'getElementById\([\'"]([^\'"]+)[\'"]\)', script_text))
    # find querySelector with #
    by_qs = set(re.findall(r'querySelector(?:All)?\([\'"]#([a-zA-Z0-9_\-]+)[\'"]\)', script_text))
    
    all_ids = sorted(list(by_id | by_qs))
    print(f"Total IDs used in JS: {len(all_ids)}")
    with open('scratch/js_ids.txt', 'w', encoding='utf-8') as out:
        for item in all_ids:
            out.write(item + '\n')
    print("Saved to scratch/js_ids.txt")
