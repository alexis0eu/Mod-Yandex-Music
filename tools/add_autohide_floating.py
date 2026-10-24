import os

css_file = r"src\renderer\mod-renderer.css"
with open(css_file, "r", encoding="utf-8") as f:
    c = f.read()

rule = """
/* Auto-hide floating trigger when sidebar button is mounted in DOM */
body:has(#ym-mod-menu-btn) #ym-mod-floating-trigger {
  display: none !important;
}
"""

if "body:has(#ym-mod-menu-btn)" not in c:
    c += "\n" + rule
    with open(css_file, "w", encoding="utf-8") as f:
        f.write(c)
    print("Added body:has(#ym-mod-menu-btn) auto-hide rule to mod-renderer.css")
else:
    print("Rule already present")
