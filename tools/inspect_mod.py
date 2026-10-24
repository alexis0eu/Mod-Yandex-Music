import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open(r'd:\Яндекс Музыка мод\src\renderer\mod-renderer.js', 'r', encoding='utf-8') as f:
    c = f.read()

print("File length:", len(c))

panes = re.findall(r'<div class="ym-tab-pane[^"]*"\s+id="([^"]+)">', c)
print("Panes found:", panes)

for p in panes:
    idx = c.find(f'id="{p}"')
    print(f"\n=== PANE {p} (at {idx}) ===")
    print(c[idx:idx+350])
