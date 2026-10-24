import os
import re
import base64
import sys

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CSS_PATH = os.path.join(PROJECT_DIR, "src", "renderer", "mod-renderer.css")
FONTS_DIR = os.path.join(PROJECT_DIR, "src", "fonts")
JS_PATH = os.path.join(PROJECT_DIR, "src", "renderer", "mod-renderer.js")

def test_fonts():
    print("=" * 60)
    print("TESTING MILESTONE 1: FONT PACK & BASE64 INLINING")
    print("=" * 60)

    # 1. Check font files in src/fonts
    print("\n[Step 1] Verifying all 6 font binaries in src/fonts/...")
    required_font_files = [
        "Andy-Bold.woff2",
        "Minecraft.woff2",
        "JetBrainsMono-Regular.woff2",
        "PressStart2P.woff2",
        "VT323.woff2",
        "UncutSans-Regular.woff2"
    ]
    for fname in required_font_files:
        fpath = os.path.join(FONTS_DIR, fname)
        assert os.path.exists(fpath), f"Missing font binary: {fname}"
        with open(fpath, "rb") as f:
            header = f.read(4)
        assert header == b"wOF2", f"Invalid WOFF2 signature in {fname}: {header}"
        size = os.path.getsize(fpath)
        print(f"  [+] {fname} ({size} bytes, signature: wOF2)")
    print("-> Step 1 PASSED!")

    # 2. Check CSS @font-face rules & Base64 data URIs
    print("\n[Step 2] Verifying Base64 inlining & dual-alias in mod-renderer.css...")
    with open(CSS_PATH, "r", encoding="utf-8") as f:
        css = f.read()

    font_families = [
        "JetBrains Mono",
        "Minecraft",
        "Andy Bold",
        "Terraria",
        "Press Start 2P",
        "VT323",
        "Uncut Sans"
    ]
    for fam in font_families:
        pattern = r'@font-face\s*\{[^}]*font-family:\s*"' + re.escape(fam) + r'"[^}]*\}'
        matches = re.findall(pattern, css, re.DOTALL)
        assert len(matches) > 0, f"Missing @font-face for {fam}"
        for m in matches:
            b64_match = re.search(r'url\("data:font/woff2;base64,([^"]+)"\)', m)
            assert b64_match, f"Missing Base64 data URI in @font-face for {fam}"
            decoded = base64.b64decode(b64_match.group(1))
            assert decoded[:4] == b"wOF2", f"Corrupt decoded WOFF2 data for {fam}"
        print(f"  [+] \"{fam}\": {len(matches)} @font-face rule(s) verified with valid wOF2 data URIs")
    print("-> Step 2 PASSED!")

    # 3. Check applyFont() and scale adjustments in mod-renderer.js
    print("\n[Step 3] Verifying applyFont() implementation in mod-renderer.js...")
    with open(JS_PATH, "r", encoding="utf-8") as f:
        js = f.read()

    assert "function applyFont(fontName, enabled = true)" in js, "Missing applyFont definition"
    assert 'font-size-adjust: 0.66' in js, "Missing Terraria font-size-adjust: 0.66"
    assert 'font-size-adjust: 0.55' in js, "Missing Minecraft font-size-adjust: 0.55"
    assert 'font-size-adjust: 0.50' in js, "Missing Press Start 2P font-size-adjust: 0.50"
    assert 'font-size-adjust: 0.85' in js, "Missing VT323 font-size-adjust: 0.85"
    assert 'font-size-adjust: 0.75' in js, "Missing Uncut Sans font-size-adjust: 0.75"
    assert 'font-size-adjust: 0.72' in js, "Missing JetBrains Mono font-size-adjust: 0.72"
    assert '* {' in js, "Missing universal wildcard selector * {"
    assert '!important' in js, "Missing !important enforcement"
    print("  [+] All 6 fonts handled with appropriate scale adjustments and universal * selector")
    print("-> Step 3 PASSED!")

    print("\n" + "=" * 60)
    print("ALL MILESTONE 1 VERIFICATION CHECKS PASSED (3/3)")
    print("=" * 60)

if __name__ == "__main__":
    test_fonts()
