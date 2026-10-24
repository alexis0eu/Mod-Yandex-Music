"""
Milestone 1 Iteration 2 — Challenger Boundary & Edge Case Stress Test Suite
Author: Challenger Agent (Critic & Specialist)

Tests additional boundary dimensions:
1. CSS injection, escaping, and novel payload defenses in applyFont & optFontCustom.
2. Boundary floating-point arithmetic & NaN/Infinity resilience for font scaling.
3. Full Unicode, RTL, CJK, emoji, and zero-width font name handling.
4. Early-boot DOM null-head simulation across all style injectors.
5. High-volume rapid churn & memory/state-leak prevention.
"""

import math
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
JS_PATH = os.path.join(PROJECT_DIR, "src", "renderer", "mod-renderer.js")

class MockElement:
    def __init__(self, tag, elem_id=None):
        self.tagName = tag.upper()
        self.id = elem_id
        self.textContent = ""
        self.href = ""
        self.rel = ""
        self.parentNode = None
        self.children = []

    def removeChild(self, child):
        if child in self.children:
            self.children.remove(child)
        child.parentNode = None

    def remove(self):
        if self.parentNode:
            self.parentNode.removeChild(self)

class MockDOM:
    def __init__(self, head_is_null=False):
        self.documentElement = MockElement("HTML", "html-root")
        if head_is_null:
            self.head = None
        else:
            self.head = MockElement("HEAD", "head-root")
            self.head.parentNode = self.documentElement
            self.documentElement.children.append(self.head)

    def appendChild(self, target, element):
        if target is None:
            raise TypeError("Cannot read properties of null (reading 'appendChild')")
        element.parentNode = target
        target.children.append(element)
        return element

    def getElementById(self, elem_id):
        def _search(node):
            if node is None:
                return None
            if node.id == elem_id:
                return node
            for c in node.children:
                res = _search(c)
                if res:
                    return res
            return None
        return _search(self.documentElement)


def simulate_js_sanitize_font(font_name):
    # Matches L660:
    # fontFamily = String(fontFamily).replace(/["'{}<>;\\]/g, "").trim() || "JetBrains Mono";
    s = str(font_name if font_name is not None else "")
    sanitized = re.sub(r'["\'{}<>;\\]', '', s).strip()
    return sanitized if sanitized else "JetBrains Mono"


def simulate_js_font_scale(raw_value):
    # Matches L662-666:
    # const rawSizeScale = parseFloat(modSettings["font-changer/sizeScale"]);
    # let fontSizeScale = (!isNaN(rawSizeScale) && isFinite(rawSizeScale)) ? Math.max(0.5, Math.min(2.0, rawSizeScale)) : 1.0;
    # if (isNaN(fontSizeScale)) { fontSizeScale = 1.0; }
    try:
        if raw_value is None:
            raw_size_scale = float('nan')
        elif isinstance(raw_value, (int, float)):
            raw_size_scale = float(raw_value)
        else:
            # JavaScript parseFloat behavior
            match = re.match(r'^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)', str(raw_value))
            if match:
                raw_size_scale = float(match.group(1))
            else:
                raw_size_scale = float('nan')
    except (ValueError, TypeError):
        raw_size_scale = float('nan')

    if not math.isnan(raw_size_scale) and math.isfinite(raw_size_scale):
        font_size_scale = max(0.5, min(2.0, raw_size_scale))
    else:
        font_size_scale = 1.0

    if math.isnan(font_size_scale):
        font_size_scale = 1.0

    return font_size_scale


def simulate_apply_font(dom, font_name, enabled=True, settings=None):
    if settings is None:
        settings = {}

    FONT_STYLESHEET_ID = "ym-mod-custom-font-style"

    existing = dom.getElementById(FONT_STYLESHEET_ID)
    if existing:
        existing.remove()

    if not enabled:
        return None

    font_family = font_name or "JetBrains Mono"
    extra_css = ""
    if font_name in ("Terraria", "Andy Bold"):
        font_family = "Terraria"
        extra_css = "* { font-size-adjust: 0.66 !important; }"
    elif font_name == "Minecraft":
        font_family = "Minecraft"
        extra_css = "*:not(.UserID-Avatar-Image):not(img) { border-radius: 0 !important; } * { font-size-adjust: 0.55 !important; }"
    elif font_name == "Press Start 2P":
        font_family = "Press Start 2P"
        extra_css = "* { font-size-adjust: 0.50 !important; }"
    elif font_name == "VT323":
        font_family = "VT323"
        extra_css = "* { font-size-adjust: 0.85 !important; }"
    elif font_name == "Uncut Sans":
        font_family = "Uncut Sans"
        extra_css = "* { font-size-adjust: 0.75 !important; }"
    elif font_name == "JetBrains Mono":
        font_family = "JetBrains Mono"
        extra_css = "* { font-size-adjust: 0.72 !important; }"

    font_family = simulate_js_sanitize_font(font_family)
    font_size_scale = simulate_js_font_scale(settings.get("font-changer/sizeScale"))
    font_weight = settings.get("font-changer/weight", "normal")
    letter_spacing = settings.get("font-changer/letterSpacing", "normal")

    font_rule = (
        f'font-family: "{font_family}", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;'
        if (font_name and font_name != "Yandex Sans (Original)")
        else ""
    )
    size_rule = f"font-size: calc(1em * {font_size_scale}) !important;" if font_size_scale != 1.0 else ""
    weight_rule = f"font-weight: {font_weight} !important;" if font_weight != "normal" else ""
    spacing_rule = f"letter-spacing: {letter_spacing} !important;" if letter_spacing != "normal" else ""

    style = MockElement("STYLE", FONT_STYLESHEET_ID)
    style.textContent = f"""
      * {{
        {font_rule}
        {size_rule}
        {weight_rule}
        {spacing_rule}
      }}
      *, *::before, *::after,
      html, body,
      button, input, select, textarea,
      [class*="Typography_"],
      [class*="Font_"],
      [class*="Text_"],
      [class*="title"],
      [class*="artist"],
      div, span, p, a, h1, h2, h3, h4, h5, h6 {{
        {font_rule}
      }}
      {extra_css}
    """

    target = dom.head if dom.head else dom.documentElement
    dom.appendChild(target, style)
    return style


def run_boundary_stress_tests():
    passed = 0
    failed = 0
    findings = []

    def check(condition, desc):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  [PASS] {desc}")
        else:
            failed += 1
            print(f"  [FAIL] {desc}")
            findings.append(desc)

    print("=" * 70)
    print("CHALLENGER ITERATION 2 — DEEP BOUNDARY & STRESS TESTS")
    print("=" * 70)

    # ---------------------------------------------------------
    # SUITE 1: CSS Injection & Special Character Attacks
    # ---------------------------------------------------------
    print("\n--- [Suite 1] CSS Injection & Breakout Vectors ---")
    attack_vectors = [
        ('Breakout with close brace', 'Test"; } body { background: red; } /*'),
        ('Single quote breakout', "Test'; } * { color: green; } /*"),
        ('HTML style tag close', '</style><script>alert(1)</script>'),
        ('Backslash escape attack', 'Font\\"; } div { opacity: 0; } /*'),
        ('Nested braces', '{{{bad_css}}}'),
        ('Semicolon chaining', 'Arial; color: blue; border: none;'),
        ('All forbidden characters only', '"\'{}<>;\\'),
        ('Forbidden characters with whitespace', '  "  {  }  <  >  ;  \\  '),
    ]

    for name, attack in attack_vectors:
        sanitized = simulate_js_sanitize_font(attack)
        # Verify forbidden characters are completely gone
        has_forbidden = any(c in sanitized for c in ['"', "'", '{', '}', '<', '>', ';', '\\'])
        check(not has_forbidden, f"Attack '{name}': forbidden chars stripped -> '{sanitized}'")

    # Empty and whitespace fallback
    check(simulate_js_sanitize_font("") == "JetBrains Mono", "Empty string falls back to 'JetBrains Mono'")
    check(simulate_js_sanitize_font("   ") == "JetBrains Mono", "Whitespace-only falls back to 'JetBrains Mono'")
    check(simulate_js_sanitize_font("\t\n\r") == "JetBrains Mono", "Control whitespace falls back to 'JetBrains Mono'")
    check(simulate_js_sanitize_font(None) == "JetBrains Mono", "None falls back to 'JetBrains Mono'")

    # ---------------------------------------------------------
    # SUITE 2: Unicode, RTL, CJK & International Font Families
    # ---------------------------------------------------------
    print("\n--- [Suite 2] International, Unicode & RTL Font Names ---")
    unicode_fonts = [
        ("Cyrillic", "Шрифт Привет Яндекса"),
        ("Arabic RTL", "خط النسخ العربي"),
        ("Hebrew RTL", "גופן עברי מודרני"),
        ("Simplified Chinese", "思源黑体"),
        ("Traditional Chinese", "思源黑體"),
        ("Japanese Hiragana/Katakana", "メイリオ メディア"),
        ("Korean Hangul", "나눔고딕"),
        ("Emoji & Symbols", "Font 🎵 🎧 🎸 123!@#$%^&*()_+="),
        ("Accented Latin", "Éléphant Cañón Über"),
        ("Zero-width space included", "Hidden\u200BFont\u200CName"),
        ("RTL Mark", "\u202EFontReverse\u202C"),
    ]

    for label, ufont in unicode_fonts:
        sanitized = simulate_js_sanitize_font(ufont)
        dom = MockDOM()
        style = simulate_apply_font(dom, ufont, enabled=True)
        # Check that unicode chars remain intact and style content contains properly quoted name
        check(sanitized == ufont, f"Preserves valid Unicode for {label}: '{ufont}'")
        check(f'font-family: "{sanitized}"' in style.textContent, f"CSS rule properly quotes {label} font name")

    # ---------------------------------------------------------
    # SUITE 3: Floating Point & Font Scale Boundaries
    # ---------------------------------------------------------
    print("\n--- [Suite 3] Font Scale Clamping & Float Extremes ---")
    scale_matrix = [
        # (input_value, expected_output, test_name)
        (0.5, 0.5, "Exact lower bound 0.5"),
        (2.0, 2.0, "Exact upper bound 2.0"),
        (1.0, 1.0, "Exact identity 1.0"),
        (0.4999999, 0.5, "Sub-boundary 0.4999999 -> clamped to 0.5"),
        (2.0000001, 2.0, "Super-boundary 2.0000001 -> clamped to 2.0"),
        (0.0, 0.5, "Zero scale 0.0 -> clamped to 0.5"),
        (-0.0, 0.5, "Negative zero -0.0 -> clamped to 0.5"),
        (-1.5, 0.5, "Negative scale -1.5 -> clamped to 0.5"),
        (-1000.0, 0.5, "Extreme negative -1000.0 -> clamped to 0.5"),
        (100.0, 2.0, "Extreme positive 100.0 -> clamped to 2.0"),
        (1e20, 2.0, "Huge float 1e20 -> clamped to 2.0"),
        ("0.75", 0.75, "String '0.75' parsed -> 0.75"),
        ("1.8", 1.8, "String '1.8' parsed -> 1.8"),
        ("0.5px", 0.5, "String with units '0.5px' -> 0.5"),
        ("NaN", 1.0, "String 'NaN' -> fallback 1.0"),
        ("Infinity", 1.0, "String 'Infinity' -> fallback 1.0"),
        ("-Infinity", 1.0, "String '-Infinity' -> fallback 1.0"),
        ("", 1.0, "Empty string scale -> fallback 1.0"),
        (None, 1.0, "None / undefined scale -> fallback 1.0"),
        ("corrupted_text_123", 1.0, "Corrupted alphabetic string -> fallback 1.0"),
        (float('nan'), 1.0, "Float NaN -> fallback 1.0"),
        (float('inf'), 1.0, "Float +Inf -> fallback 1.0"),
        (float('-inf'), 1.0, "Float -Inf -> fallback 1.0"),
    ]

    for val, expected, desc in scale_matrix:
        res = simulate_js_font_scale(val)
        check(abs(res - expected) < 1e-6, f"{desc}: input {repr(val)} -> {res} (expected {expected})")

    # ---------------------------------------------------------
    # SUITE 4: Early-Boot Null document.head Simulation
    # ---------------------------------------------------------
    print("\n--- [Suite 4] Null document.head Early-Boot Resilience ---")
    null_head_dom = MockDOM(head_is_null=True)
    check(null_head_dom.head is None, "Confirmed mock DOM head is null")
    
    # Try applying font into null-head DOM
    try:
        style = simulate_apply_font(null_head_dom, "Minecraft", enabled=True)
        check(style is not None and style.parentNode == null_head_dom.documentElement,
              "applyFont successfully falls back to documentElement when head is null")
        check(null_head_dom.getElementById("ym-mod-custom-font-style") is not None,
              "Style element indexed in DOM under documentElement")
    except Exception as e:
        check(False, f"applyFont crashed on null head: {e}")

    # Inspect mod-renderer.js source to verify all document.head.appendChild occurrences
    with open(JS_PATH, "r", encoding="utf-8") as f:
        src = f.read()

    unsafe_matches = re.findall(r'document\.head\.appendChild\b', src)
    safe_matches = re.findall(r'\(document\.head\s*\|\|\s*document\.documentElement\)\.appendChild', src)
    check(len(unsafe_matches) == 0, f"Zero unsafe document.head.appendChild occurrences (found {len(unsafe_matches)})")
    check(len(safe_matches) >= 5, f"All dynamic styles use safe fallback syntax (found {len(safe_matches)} occurrences)")

    # ---------------------------------------------------------
    # SUITE 5: High-Volume Rapid Churn & Clean Teardown
    # ---------------------------------------------------------
    print("\n--- [Suite 5] High-Volume Churn (10,000 Operations) ---")
    churn_dom = MockDOM()
    cycle = ["Minecraft", "Andy Bold", "Terraria", "JetBrains Mono", "Press Start 2P", "VT323", "Uncut Sans", "Yandex Sans (Original)"]
    
    for i in range(10000):
        font = cycle[i % len(cycle)]
        enabled = (i % 7 != 0) # periodic toggle off
        simulate_apply_font(churn_dom, font, enabled=enabled)
        # Exactly 0 or 1 custom-font-style element should ever exist in head
        tag_count = sum(1 for c in churn_dom.head.children if c.id == "ym-mod-custom-font-style")
        if tag_count > 1:
            check(False, f"DOM pollution detected at iteration {i}: {tag_count} style tags present")
            break
    else:
        check(True, "10,000 rapid switches executed without DOM element leak or pollution")

    # Final disable
    simulate_apply_font(churn_dom, "Minecraft", enabled=False)
    check(churn_dom.getElementById("ym-mod-custom-font-style") is None, "Final disabled state cleanly removes style tag")

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------
    print("\n" + "=" * 70)
    print(f"BOUNDARY STRESS SUMMARY: {passed} PASSED, {failed} FAILED")
    print("=" * 70)
    return failed == 0

if __name__ == "__main__":
    success = run_boundary_stress_tests()
    sys.exit(0 if success else 1)
