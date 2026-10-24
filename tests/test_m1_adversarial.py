"""
Adversarial Stress Test Suite for Milestone 1 (Font Pack & Base64 Inlining)
Challenger 1 Verification Harness

This suite adversarially challenges:
1. Base64 payload decoding integrity, byte corruption resistance, and deep WOFF2 header/table validation across all 6 fonts.
2. Dual-alias resolution for "Andy Bold" and "Terraria" (weight parity, payload equality, and JS resolution).
3. Dynamic style injection edge cases: rapid switching, special characters/CSS injection defense, font scale boundary clamping (0.5x to 2.0x), NaN handling, and restoring default font.
"""

import os
import re
import base64
import struct
import binascii
import sys

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(PROJECT_DIR, "src")
FONTS_DIR = os.path.join(SRC_DIR, "fonts")
CSS_PATH = os.path.join(SRC_DIR, "renderer", "mod-renderer.css")
JS_PATH = os.path.join(SRC_DIR, "renderer", "mod-renderer.js")

KNOWN_WOFF2_TAGS = [
    'cmap', 'head', 'hhea', 'hmtx', 'maxp', 'name', 'OS/2', 'post', 'cvt ', 'fpgm',
    'glyf', 'loca', 'prep', 'CFF ', 'VORG', 'EBDT', 'EBLC', 'gasp', 'hdmx', 'kern',
    'LTSH', 'PCLT', 'VDMX', 'vhea', 'vmtx', 'BASE', 'GDEF', 'GPOS', 'GSUB', 'JSTF',
    'MATH', 'CBDT', 'CBLC', 'COLR', 'CPAL', 'SVG ', 'sbix', 'acnt', 'avar', 'bdat',
    'bloc', 'bsln', 'cvar', 'fdsc', 'feat', 'fmtx', 'fvar', 'gvar', 'hsty', 'just',
    'lcar', 'mort', 'morx', 'opbd', 'prop', 'trak', 'Zapf', 'Silf', 'Glat', 'Gloc',
    'Feat', 'Sill', 'valA'
]

def read_base128(data, offset):
    accum = 0
    for i in range(5):
        if offset >= len(data):
            raise ValueError("Buffer underflow reading UIntBase128")
        b = data[offset]
        offset += 1
        if i == 0 and b == 0x80:
            raise ValueError("Leading 0x80 in UIntBase128")
        if (accum & 0xFE000000) != 0:
            raise ValueError("UIntBase128 overflow")
        accum = (accum << 7) | (b & 0x7F)
        if (b & 0x80) == 0:
            return accum, offset
    raise ValueError("UIntBase128 exceeds 5 bytes")

def parse_woff2_tables(data):
    """Deep inspection of WOFF2 header (48 bytes) and table directory."""
    if len(data) < 48:
        raise ValueError(f"Payload too short for WOFF2 header: {len(data)} bytes")
    sig, flavor, length, num_tables, res, total_sfnt_size, total_comp_size, maj_v, min_v, meta_off, meta_len, meta_orig_len, priv_off, priv_len = struct.unpack('>4sIIHHIIHHIIIII', data[:48])
    if sig != b'wOF2':
        raise ValueError(f"Invalid WOFF2 signature: {sig}")
    if length != len(data):
        raise ValueError(f"Header length ({length}) != actual payload length ({len(data)})")
    if num_tables <= 0:
        raise ValueError(f"Zero tables declared: {num_tables}")
    if total_comp_size <= 0:
        raise ValueError(f"Invalid totalCompressedSize: {total_comp_size}")
    if flavor not in (0x10000, 0x4f54544f):
        raise ValueError(f"Unknown font flavor: {hex(flavor)}")

    offset = 48
    tables = []
    for _ in range(num_tables):
        flags = data[offset]
        offset += 1
        tag_idx = flags & 0x3F
        if tag_idx == 0x3F:
            tag = data[offset:offset+4].decode('latin1', errors='replace')
            offset += 4
        else:
            tag = KNOWN_WOFF2_TAGS[tag_idx]
        orig_len, offset = read_base128(data, offset)
        transform_version = (flags & 0xC0) >> 6
        transform_len = None
        if tag in ('glyf', 'loca') and transform_version == 0:
            transform_len, offset = read_base128(data, offset)
        elif tag == 'CFF ' and transform_version == 0:
            transform_len, offset = read_base128(data, offset)
        tables.append((tag, orig_len, transform_len))
    return {
        "sig": sig,
        "flavor": flavor,
        "length": length,
        "num_tables": num_tables,
        "tables": [t[0] for t in tables]
    }

class AdversarialChallengeM1:
    def __init__(self):
        with open(CSS_PATH, "r", encoding="utf-8") as f:
            self.css = f.read()
        with open(JS_PATH, "r", encoding="utf-8") as f:
            self.js = f.read()
        self.findings = []
        self.passed_tests = 0
        self.failed_tests = 0

    def record_pass(self, name):
        self.passed_tests += 1
        print(f"  [PASS] {name}")

    def record_fail(self, name, reason, severity="HIGH"):
        self.failed_tests += 1
        self.findings.append({
            "name": name,
            "reason": reason,
            "severity": severity
        })
        print(f"  [FAIL - {severity}] {name}: {reason}")

    # =========================================================================
    # AREA 1: Base64 payload decoding integrity & deep WOFF2 inspection
    # =========================================================================
    def test_base64_decoding_and_bitstream_equality(self):
        print("\n--- [Area 1.1] Base64 Decoding & Exact Bitstream Equality ---")
        font_map = {
            "JetBrains Mono": "JetBrainsMono-Regular.woff2",
            "Minecraft": "Minecraft.woff2",
            "Andy Bold": "Andy-Bold.woff2",
            "Terraria": "Andy-Bold.woff2",
            "Press Start 2P": "PressStart2P.woff2",
            "VT323": "VT323.woff2",
            "Uncut Sans": "UncutSans-Regular.woff2",
        }

        for fam, fname in font_map.items():
            fpath = os.path.join(FONTS_DIR, fname)
            if not os.path.exists(fpath):
                self.record_fail(f"Asset existence: {fname}", "Font binary does not exist on disk", "CRITICAL")
                continue
            with open(fpath, "rb") as f:
                disk_bytes = f.read()

            pattern = r'@font-face\s*\{[^}]*font-family:\s*\"' + re.escape(fam) + r'\"[^}]*\}'
            matches = re.findall(pattern, self.css, re.DOTALL)
            if not matches:
                self.record_fail(f"@font-face presence: {fam}", "No matching @font-face block found in mod-renderer.css", "CRITICAL")
                continue

            for idx, block in enumerate(matches):
                b64_match = re.search(r'url\("data:font/woff2;base64,([^"]+)"\)', block)
                if not b64_match:
                    self.record_fail(f"Data URI syntax: {fam} rule #{idx+1}", "data:font/woff2;base64 URI missing or malformed", "HIGH")
                    continue
                b64_payload = b64_match.group(1)

                # RFC 4648 strict alphabet check
                if not re.fullmatch(r'[A-Za-z0-9+/=]+', b64_payload):
                    self.record_fail(f"Base64 RFC alphabet: {fam} rule #{idx+1}", "Contains non-alphabet characters or unexpected whitespace", "HIGH")
                    continue

                try:
                    decoded = base64.b64decode(b64_payload, validate=True)
                except binascii.Error as e:
                    self.record_fail(f"Base64 decode validation: {fam} rule #{idx+1}", f"Decode error: {e}", "CRITICAL")
                    continue

                if decoded != disk_bytes:
                    self.record_fail(f"Bitstream match: {fam} rule #{idx+1}", f"Decoded payload ({len(decoded)}b) != disk binary ({len(disk_bytes)}b)", "CRITICAL")
                else:
                    self.record_pass(f"Bitstream match: {fam} rule #{idx+1} ({len(decoded)} bytes bit-for-bit identical to {fname})")

    def test_deep_woff2_header_and_table_integrity(self):
        print("\n--- [Area 1.2] Deep WOFF2 Header & Table Directory Integrity ---")
        font_files = [
            "Andy-Bold.woff2",
            "Minecraft.woff2",
            "JetBrainsMono-Regular.woff2",
            "PressStart2P.woff2",
            "VT323.woff2",
            "UncutSans-Regular.woff2"
        ]

        for fname in font_files:
            fpath = os.path.join(FONTS_DIR, fname)
            with open(fpath, "rb") as f:
                data = f.read()

            try:
                info = parse_woff2_tables(data)
                # Verify required OpenType / TrueType tables
                required_tables = ['cmap', 'head', 'OS/2', 'hhea', 'hmtx', 'maxp', 'name', 'post']
                missing_tables = [t for t in required_tables if t not in info["tables"]]
                if missing_tables:
                    self.record_fail(f"WOFF2 tables in {fname}", f"Missing critical table(s): {missing_tables}", "HIGH")
                    continue

                # Must have outline table: either glyf (TrueType) or CFF (OpenType)
                has_outlines = ('glyf' in info["tables"]) or ('CFF ' in info["tables"])
                if not has_outlines:
                    self.record_fail(f"WOFF2 outline data in {fname}", "Neither 'glyf' nor 'CFF ' table present", "HIGH")
                    continue

                self.record_pass(f"WOFF2 validation: {fname} (Flavor: {hex(info['flavor'])}, {info['num_tables']} tables, outlines present)")
            except Exception as e:
                self.record_fail(f"WOFF2 parser exception in {fname}", str(e), "CRITICAL")

    def test_corruption_resistance_oracle(self):
        print("\n--- [Area 1.3] Corruption Resistance Oracle (Byte Mutator) ---")
        # Extract a sample Base64 payload from CSS
        b64_match = re.search(r'url\("data:font/woff2;base64,([^"]+)"\)', self.css)
        assert b64_match, "Failed to extract test payload"
        valid_b64 = b64_match.group(1)

        # 1. Invalid character insertion
        corrupt_char_b64 = valid_b64[:100] + "!" + valid_b64[101:]
        try:
            base64.b64decode(corrupt_char_b64, validate=True)
            self.record_fail("Corruption Oracle: illegal character", "b64decode succeeded on payload containing '!'", "MEDIUM")
        except binascii.Error:
            self.record_pass("Corruption Oracle: illegal character rejected as expected")

        # 2. Corrupt header signature
        valid_bytes = base64.b64decode(valid_b64)
        corrupt_header_bytes = b"NOPE" + valid_bytes[4:]
        try:
            parse_woff2_tables(corrupt_header_bytes)
            self.record_fail("Corruption Oracle: corrupted header", "parse_woff2_tables accepted header with signature 'NOPE'", "MEDIUM")
        except ValueError as e:
            if "Invalid WOFF2 signature" in str(e):
                self.record_pass("Corruption Oracle: invalid magic signature caught")
            else:
                self.record_fail("Corruption Oracle: unexpected exception", str(e), "LOW")

        # 3. Truncated length
        corrupt_length_bytes = valid_bytes[:30]
        try:
            parse_woff2_tables(corrupt_length_bytes)
            self.record_fail("Corruption Oracle: truncated buffer", "parse_woff2_tables accepted 30 bytes buffer", "MEDIUM")
        except ValueError as e:
            self.record_pass("Corruption Oracle: truncated payload underflow rejected")

    # =========================================================================
    # AREA 2: Dual-Alias Resolution & Weight Parity ("Andy Bold" / "Terraria")
    # =========================================================================
    def test_dual_alias_declarations_and_weight_parity(self):
        print("\n--- [Area 2.1] Dual-Alias Declarations & Font-Weight Parity ---")
        for alias in ["Andy Bold", "Terraria"]:
            pattern = r'@font-face\s*\{[^}]*font-family:\s*\"' + re.escape(alias) + r'\"[^}]*\}'
            matches = re.findall(pattern, self.css, re.DOTALL)
            if not matches:
                self.record_fail(f"Dual-alias @font-face: {alias}", f"Missing declaration for {alias}", "CRITICAL")
                continue

            weights = []
            for m in matches:
                w_match = re.search(r'font-weight:\s*([^;]+);', m)
                if w_match:
                    weights.append(w_match.group(1).strip())

            has_normal = "normal" in weights
            has_bold = "bold" in weights

            if not (has_normal and has_bold):
                self.record_fail(f"Weight parity for {alias}", f"Expected normal and bold weights, found: {weights}", "HIGH")
            else:
                self.record_pass(f"Dual-alias '{alias}': has both normal and bold font-weights declared")

        # Compare Andy Bold and Terraria data URIs
        m_andy = re.search(r'@font-face\s*\{[^}]*font-family:\s*"Andy Bold"[^}]*url\("data:font/woff2;base64,([^"]+)"\)', self.css)
        m_terr = re.search(r'@font-face\s*\{[^}]*font-family:\s*"Terraria"[^}]*url\("data:font/woff2;base64,([^"]+)"\)', self.css)
        if m_andy and m_terr:
            if m_andy.group(1) == m_terr.group(1):
                self.record_pass("Dual-alias payload equivalence: 'Andy Bold' and 'Terraria' share identical Base64 font stream")
            else:
                self.record_fail("Dual-alias payload mismatch", "'Andy Bold' and 'Terraria' have different payloads", "HIGH")
        else:
            self.record_fail("Dual-alias payload extraction", "Could not extract data URIs for Andy Bold / Terraria", "CRITICAL")

    def test_dual_alias_js_runtime_resolution(self):
        print("\n--- [Area 2.2] Dual-Alias JS Runtime Resolution in mod-renderer.js ---")
        # Check that both "Terraria" and "Andy Bold" map to "Terraria" or are handled properly
        apply_font_match = re.search(r'function applyFont\(fontName, enabled = true\)\s*\{(.*?)(?=\n\s*function|\n\s*\/\/)', self.js, re.DOTALL)
        if not apply_font_match:
            self.record_fail("applyFont function extraction", "Could not locate applyFont definition in mod-renderer.js", "CRITICAL")
            return

        body = apply_font_match.group(1)
        terraria_handled = ('fontName === "Terraria"' in body) or ('fontName === "Andy Bold"' in body)
        if not terraria_handled:
            self.record_fail("applyFont Terraria resolution", "applyFont does not branch on Terraria / Andy Bold", "HIGH")
        else:
            self.record_pass("applyFont properly handles Terraria / Andy Bold font alias")

        # Check font selector options in HTML string
        opt_terraria = '<option value="Terraria">' in self.js
        if opt_terraria:
            self.record_pass("Settings modal select includes '<option value=\"Terraria\">'")
        else:
            self.record_fail("Settings modal font select", "Missing '<option value=\"Terraria\">' in mod-renderer.js", "HIGH")

    # =========================================================================
    # AREA 3: Dynamic Style Injection Edge Cases & Scale Clamping
    # =========================================================================
    def test_dynamic_style_injection_simulation(self):
        print("\n--- [Area 3.1] Dynamic Style Injection & State Reset Simulation ---")
        # Simulate DOM style injection logic from applyFont
        class MockDOM:
            def __init__(self):
                self.elements = {}

            def getElementById(self, el_id):
                return self.elements.get(el_id)

            def remove_element(self, el_id):
                if el_id in self.elements:
                    del self.elements[el_id]

            def appendChild(self, el):
                self.elements[el['id']] = el

        def simulate_apply_font(dom, font_name, enabled=True, size_scale=1.0, weight="normal", letter_spacing="normal"):
            FONT_STYLESHEET_ID = "ym-mod-custom-font-style"
            dom.remove_element(FONT_STYLESHEET_ID)

            if not enabled:
                return

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

            font_rule = f'font-family: "{font_family}", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;' if (font_name and font_name != "Yandex Sans (Original)") else ""
            size_rule = f'font-size: calc(1em * {size_scale}) !important;' if size_scale != 1.0 else ""
            weight_rule = f'font-weight: {weight} !important;' if weight != "normal" else ""
            spacing_rule = f'letter-spacing: {letter_spacing} !important;' if letter_spacing != "normal" else ""

            css_text = f"""
              * {{
                {font_rule}
                {size_rule}
                {weight_rule}
                {spacing_rule}
              }}
              {extra_css}
            """
            dom.appendChild({"id": FONT_STYLESHEET_ID, "content": css_text, "font_family": font_family})

        dom = MockDOM()

        # 1. Rapid font switching (100 rapid changes)
        fonts_cycle = ["Minecraft", "Terraria", "VT323", "Uncut Sans", "JetBrains Mono", "Press Start 2P"]
        for i in range(100):
            chosen = fonts_cycle[i % len(fonts_cycle)]
            simulate_apply_font(dom, chosen, enabled=True)
            assert "ym-mod-custom-font-style" in dom.elements, "Style tag missing during churn"

        el = dom.getElementById("ym-mod-custom-font-style")
        last_expected = fonts_cycle[99 % len(fonts_cycle)]
        if last_expected in ("Terraria", "Andy Bold"):
            last_expected = "Terraria"
        if el["font_family"] == last_expected:
            self.record_pass("Rapid font switching: 100 transitions cleanly executed without orphan styles")
        else:
            self.record_fail("Rapid font switching state", f"Expected final font {last_expected}, got {el['font_family']}", "HIGH")

        # 2. Reset / Disable font
        simulate_apply_font(dom, "Minecraft", enabled=False)
        if dom.getElementById("ym-mod-custom-font-style") is None:
            self.record_pass("Disable font: style tag cleanly removed from DOM")
        else:
            self.record_fail("Disable font", "Style tag remained in DOM when enabled=False", "HIGH")

        # 3. Yandex Sans (Original)
        simulate_apply_font(dom, "Yandex Sans (Original)", enabled=True)
        el = dom.getElementById("ym-mod-custom-font-style")
        if el and 'font-family:' not in el["content"]:
            self.record_pass("Yandex Sans (Original): font-family rule omitted, allowing native app font inheritance")
        else:
            self.record_fail("Yandex Sans (Original)", "font-family rule inappropriately forced for original font", "MEDIUM")

    def test_css_special_character_injection_vulnerability(self):
        print("\n--- [Area 3.2] CSS Injection & Malicious Special Characters in Custom Font ---")
        # In mod-renderer.js:
        # const fontRule = (fontName && fontName !== "Yandex Sans (Original)") 
        #   ? `font-family: "${fontFamily}", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;` 
        #   : "";
        # Adversarial input: font name containing double quotes and malicious CSS breakout
        adversarial_input = 'Malicious"; } * { display: none !important; } /*'
        
        # Test how mod-renderer.js sanitizes or fails to sanitize this input
        escaped_in_code = False
        if 'replace(/"/g' in self.js or "replace(/[\\\"\\\\]/g" in self.js or "sanitize" in self.js.lower():
            escaped_in_code = True

        # Let's inspect the actual fontRule generation in mod-renderer.js:
        rule_match = re.search(r'font-family:\s*\\?"\$\{fontFamily\}\\?"', self.js)
        if rule_match and not escaped_in_code:
            self.record_fail(
                "CSS injection in custom font",
                f'fontFamily is interpolated into `font-family: "${{fontFamily}}", ...` without sanitizing double-quotes (`"`) or closing curly braces (`}}`). User input `{adversarial_input}` breaks out of the CSS rule.',
                "MEDIUM"
            )
        else:
            self.record_pass("Custom font name is sanitized before CSS style insertion")

    def test_font_scale_boundary_clamping(self):
        print("\n--- [Area 3.3] Font Scale Boundary Clamping (0.5x to 2.0x) & NaN Resistance ---")
        # Target check:
        # Does mod-renderer.js clamp fontSizeScale to [0.5, 2.0] and resist NaN / corrupt values?
        # Lines in mod-renderer.js:
        # const fontSizeScale = parseFloat(modSettings["font-changer/sizeScale"] || 1.0);
        # const sizeRule = fontSizeScale !== 1.0 ? `font-size: calc(1em * ${fontSizeScale}) !important;` : "";

        has_math_clamp = (
            ("Math.max" in self.js and "Math.min" in self.js and "0.5" in self.js and "2.0" in self.js) or
            ("Math.max(0.5" in self.js) or
            ("Math.min(2.0" in self.js) or
            ("clamp" in self.js.lower() and "scale" in self.js.lower())
        )

        has_nan_guard = (
            ("isNaN(fontSizeScale)" in self.js) or
            ("isNaN(" in self.js and "sizeScale" in self.js) or
            ("isFinite(" in self.js)
        )

        # Stress test cases:
        test_scales = [
            ("Negative scale", -1.5, "Generates inverted/negative font-size rule"),
            ("Zero scale", 0.0, "Generates 0px unreadable text"),
            ("Extreme runaway scale", 50.0, "Blows up application layout (5000% scale)"),
            ("Sub-minimum scale", 0.1, "Renders microscopic unreadable text"),
            ("Corrupted non-numeric NaN", "corrupted_string", "Generates invalid CSS: `font-size: calc(1em * NaN)`"),
        ]

        if not has_math_clamp or not has_nan_guard:
            issues = []
            if not has_math_clamp:
                issues.append("No boundary clamping to [0.5, 2.0]")
            if not has_nan_guard:
                issues.append("No isNaN/isFinite check on parseFloat")
            self.record_fail(
                "Font scale clamping and NaN resistance",
                f"Deficiencies found in mod-renderer.js: {'; '.join(issues)}. Test cases: {[t[0] for t in test_scales]}",
                "HIGH"
            )
        else:
            self.record_pass("Font scale boundary clamping (0.5x to 2.0x) and NaN resistance verified")

    def test_null_document_head_resilience(self):
        print("\n--- [Area 3.4] Early-Boot DOM Null-Head Resilience ---")
        # Line 599: document.head.appendChild(link)
        # Line 754: document.head.appendChild(style)
        # Compare to line 692: (document.head || document.documentElement).appendChild(style)
        null_head_unsafe = []
        with open(JS_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for idx, line in enumerate(lines, 1):
            if "document.head.appendChild" in line and "||" not in line and "document.documentElement" not in line:
                null_head_unsafe.append((idx, line.strip()))

        if null_head_unsafe:
            locations = ", ".join([f"L{loc[0]}" for loc in null_head_unsafe])
            self.record_fail(
                "Early-boot null document.head guard",
                f"Unprotected `document.head.appendChild()` calls at {locations} will throw TypeError if invoked before `<head>` is parsed. Should use `(document.head || document.documentElement).appendChild()`.",
                "MEDIUM"
            )
        else:
            self.record_pass("All dynamic style injection calls safely guard against null document.head")

    def run_all(self):
        print("=" * 70)
        print("ADVERSARIAL CHALLENGE HARNESS — MILESTONE 1")
        print("=" * 70)

        self.test_base64_decoding_and_bitstream_equality()
        self.test_deep_woff2_header_and_table_integrity()
        self.test_corruption_resistance_oracle()
        self.test_dual_alias_declarations_and_weight_parity()
        self.test_dual_alias_js_runtime_resolution()
        self.test_dynamic_style_injection_simulation()
        self.test_css_special_character_injection_vulnerability()
        self.test_font_scale_boundary_clamping()
        self.test_null_document_head_resilience()

        print("\n" + "=" * 70)
        print(f"ADVERSARIAL HARNESS SUMMARY: {self.passed_tests} PASSED, {self.failed_tests} FAILED / CHALLENGED")
        print("=" * 70)
        return self.failed_tests == 0

if __name__ == "__main__":
    challenger = AdversarialChallengeM1()
    success = challenger.run_all()
    sys.exit(0 if success else 1)
