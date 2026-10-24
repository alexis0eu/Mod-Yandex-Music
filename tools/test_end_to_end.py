import os
import sys
import struct
import json
import hashlib
import re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=" * 60)
print("COMPREHENSIVE END-TO-END VERIFICATION")
print("=" * 60)

ASAR_PATH = r"C:\Users\denbi\AppData\Local\Programs\YandexMusic\resources\app.asar"
SRC_DIR = r"d:\Яндекс Музыка мод\src"

errors = []

# 1. Check local source files
print("\n[Check 1] Verifying core source modifications...")
with open(os.path.join(SRC_DIR, "renderer", "mod-renderer.js"), "r", encoding="utf-8") as f:
    renderer_code = f.read()

required_renderer_strings = [
    "VIBE_PLAYERBAR",
    "VIBE_PLAYERBAR_TRACK_NAME",
    "VIBE_ALBUM_COVER",
    "VIBE_PLAYERBAR_TIMECODE",
    "PLAYERBAR_DESKTOP",
    "TRACK_TITLE",
    "extractSonataStateFromFiber",
    "ym-mod-floating-trigger",
    "ym-mod-nav-item",
    "applyUiCleaner()",
    "cleaner/hideConcerts",
    "cleaner/hideKids",
    "cleaner/hidePodcasts",
    "KeyS",
    "F10"
]

for s in required_renderer_strings:
    if s in renderer_code:
        print(f"  [+] Found '{s}' in mod-renderer.js")
    else:
        print(f"  [-] MISSING '{s}' in mod-renderer.js")
        errors.append(f"Missing '{s}' in mod-renderer.js")

# 2. Check CSS styles
print("\n[Check 2] Verifying CSS styles for settings trigger...")
with open(os.path.join(SRC_DIR, "renderer", "mod-renderer.css"), "r", encoding="utf-8") as f:
    css_code = f.read()

required_css = [
    "#ym-mod-floating-trigger",
    "#ym-mod-nav-item",
    "#ym-mod-menu-btn"
]
for s in required_css:
    if s in css_code:
        print(f"  [+] Found '{s}' in mod-renderer.css")
    else:
        print(f"  [-] MISSING '{s}' in mod-renderer.css")
        errors.append(f"Missing '{s}' in mod-renderer.css")

# 3. Check Discord RPC and Lyrics in main
print("\n[Check 3] Verifying main process RPC & lyrics...")
with open(os.path.join(SRC_DIR, "main", "mod-main.js"), "r", encoding="utf-8") as f:
    main_code = f.read()

required_main = [
    "updateDiscordActivity",
    "openModSettings",
    "fetchLyrics",
    "lrclib.net"
]
for s in required_main:
    if s in main_code:
        print(f"  [+] Found '{s}' in mod-main.js")
    else:
        print(f"  [-] MISSING '{s}' in mod-main.js")
        errors.append(f"Missing '{s}' in mod-main.js")

# 4. Check ASAR in Yandex Music installation
print("\n[Check 4] Inspecting installed app.asar...")
if not os.path.exists(ASAR_PATH):
    print("  [-] app.asar NOT FOUND at", ASAR_PATH)
    errors.append("Target app.asar not found")
else:
    size = os.path.getsize(ASAR_PATH)
    print(f"  [+] Found app.asar ({size} bytes)")
    with open(ASAR_PATH, "rb") as f:
        u1, u2, u3, u4 = struct.unpack("<IIII", f.read(16))
        header = json.loads(f.read(u4).decode("utf-8"))
        base_offset = 8 + u2

        def find_file(node, cur=""):
            files = {}
            for k, v in node.get("files", {}).items():
                p = cur + "/" + k
                if "files" in v:
                    files.update(find_file(v, p))
                else:
                    files[p] = (int(v.get("offset", 0)), int(v.get("size", 0)))
            return files

        all_files = find_file(header)
        expected_injected = [
            "/app/yandexMusicMod/main.js",
            "/app/yandexMusicMod/renderer.js",
            "/app/yandexMusicMod/renderer.css",
            "/app/yandexMusicMod/discord-rpc.js",
            "/app/yandexMusicMod/overlay.html",
            "/app/yandexMusicMod/karaoke.html"
        ]
        for exp in expected_injected:
            if exp in all_files:
                off, sz = all_files[exp]
                print(f"  [+] ASAR verified file: {exp} ({sz} bytes)")
            else:
                print(f"  [-] ASAR missing file: {exp}")
                errors.append(f"ASAR missing file: {exp}")

        # Check renderer.js content inside ASAR
        if "/app/yandexMusicMod/renderer.js" in all_files:
            off, sz = all_files["/app/yandexMusicMod/renderer.js"]
            f.seek(base_offset + off)
            asar_renderer = f.read(sz).decode("utf-8", errors="replace")
            if "ym-mod-floating-trigger" in asar_renderer and "VIBE_PLAYERBAR" in asar_renderer:
                print("  [+] ASAR renderer.js confirmed to have latest Vibe & Floating badge code")
            else:
                print("  [-] ASAR renderer.js does NOT contain latest code!")
                errors.append("ASAR renderer.js is outdated")

print("\n" + "=" * 60)
if not errors:
    print("RESULT: ALL AUDIT CHECKS PASSED PERFECTLY (0 ERRORS)")
else:
    print(f"RESULT: FAILED WITH {len(errors)} ERRORS:")
    for e in errors:
        print("  -", e)
print("=" * 60)
