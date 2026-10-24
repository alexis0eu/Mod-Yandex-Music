import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

RENDERER_JS = r"d:\Яндекс Музыка мод\src\renderer\mod-renderer.js"
RENDERER_CSS = r"d:\Яндекс Музыка мод\src\renderer\mod-renderer.css"

with open(RENDERER_JS, "r", encoding="utf-8") as f:
    js_content = f.read()

print(f"Current mod-renderer.js length: {len(js_content)} characters")
