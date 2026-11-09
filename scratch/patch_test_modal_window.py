with open('scratch/test_modal_vm.js', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace(
    'context.currentVerifiedRole = "student";',
    'context.window.currentVerifiedRole = "student";'
)

with open('scratch/test_modal_vm.js', 'w', encoding='utf-8') as f:
    f.write(c)

