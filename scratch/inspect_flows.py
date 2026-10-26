import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("web/index.html", "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find('class="flow-steps-grid"')
end_pos = text.find('</div>', text.find('</div>', text.find('</div>', text.find('</div>', pos)))) + 100
print("=== FLOW STEPS GRID ===")
print(text[pos:pos+2500])

pos2 = text.find('class="flow-balance-grid"')
print("\n=== FLOW BALANCE GRID ===")
print(text[pos2:pos2+1800])
