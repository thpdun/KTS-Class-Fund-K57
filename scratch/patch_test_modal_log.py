with open('scratch/test_modal_vm.js', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace(
    "if (secDep.style.display !== 'block') {",
    "console.log('secDep style.display is:', secDep.style.display);\n  if (secDep.style.display !== 'block') {"
)

with open('scratch/test_modal_vm.js', 'w', encoding='utf-8') as f:
    f.write(c)

