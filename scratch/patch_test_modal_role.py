with open('scratch/test_modal_vm.js', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace(
    'context.openActionModal(\'deposit\');',
    'context.currentVerifiedRole = "student";\n  context.openActionModal(\'deposit\');'
)

with open('scratch/test_modal_vm.js', 'w', encoding='utf-8') as f:
    f.write(c)

