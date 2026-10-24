import re
import os

RENDERER_JS = r"d:\Яндекс Музыка мод\src\renderer\mod-renderer.js"
RENDERER_CSS = r"d:\Яндекс Музыка мод\src\renderer\mod-renderer.css"

with open(RENDERER_JS, "r", encoding="utf-8") as f:
    js_content = f.read()

# Let's inspect where tabs are defined
tabs_start = js_content.find('<div class="ym-modal-tabs">')
tabs_end = js_content.find('</div>', tabs_start) + 6
print("Found tabs:", js_content[tabs_start:tabs_end])
