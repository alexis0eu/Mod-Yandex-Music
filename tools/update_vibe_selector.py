import os

target = r"src\renderer\mod-renderer.js"
with open(target, "r", encoding="utf-8") as f:
    c = f.read()

old_s = '    if (modSettings["cleaner/hideVibe"]) {\n      css += `div[data-test-id="VIBE_BLOCK"], div[class*="VibeBlock"] { display: none !important; }\\n`;\n    }'
new_s = '    if (modSettings["cleaner/hideVibe"]) {\n      css += `div[data-test-id="VIBE_BLOCK"], div[class*="VibeBlock"], aside li:has([data-test-id="NAVBAR_NAVIGATION_ITEM_HOME"]) { display: none !important; }\\n`;\n    }'

c_norm = c.replace("\r\n", "\n")
old_norm = old_s.replace("\r\n", "\n")
new_norm = new_s.replace("\r\n", "\n")

if old_norm in c_norm:
    c_norm = c_norm.replace(old_norm, new_norm)
    with open(target, "w", encoding="utf-8") as f:
        f.write(c_norm)
    print("Updated cleaner/hideVibe selector")
else:
    print("Could not match old cleaner/hideVibe")
