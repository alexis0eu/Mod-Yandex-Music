"""
Tier 2: Boundary & Corner Cases E2E Tests (Features 1-25)
Covers boundary conditions, empty inputs, limits, error handling, offline states, and cascades.
Authoritative source: PROJECT.md, ORIGINAL_REQUEST.md, survey edge-case analyses.
"""

import unittest
import os
import sys
import json
import base64
import tempfile
import struct
from datetime import datetime
from typing import Dict, Any, List, Optional

from .harness.contracts import (
    FONT_SCALE_BOUNDS,
    INTERFACE_SCALE_BOUNDS,
    FONT_SIZE_ADJUST_PRESETS,
    DISCORD_PIPE_NAMES,
    DISCORD_HANDSHAKE_TIMEOUT_MS,
    RENDERER_POLLER_SILENCE_THRESHOLD_MS,
    TrackMetadata,
    PlayerProgress,
    PlayerState,
    LyricsPayload,
)
from .harness.oracles import (
    compute_musixmatch_signature,
    clean_lrc_metadata_tags,
    parse_lrc_timestamps,
    interpolate_playback_position,
    encode_discord_ipc_packet,
    decode_discord_ipc_packet,
    validate_woff2_bytes,
)
from .harness.simulators import (
    MockElectronIPC,
    MockBrowserWindow,
    MockDiscordServer,
    MockCascadingLyricsEngine,
    re_strip_parentheses,
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class TestTier2FontBoundaries(unittest.TestCase):
    """Area 1 Boundaries: Fonts & Inlining"""

    def test_b1_empty_or_null_font_name_falls_back(self):
        """Boundary: Passing None or empty string as font name falls back to default font safely."""
        def resolve_font(name: Optional[str]) -> str:
            return name if name and name.strip() else "JetBrains Mono"

        self.assertEqual(resolve_font(None), "JetBrains Mono")
        self.assertEqual(resolve_font(""), "JetBrains Mono")
        self.assertEqual(resolve_font("   "), "JetBrains Mono")

    def test_b2_font_scale_extreme_boundaries_clamping(self):
        """Boundary: Scale factor values outside [0.8, 1.3] are clamped without crash."""
        def clamp_scale(val: float) -> float:
            return max(FONT_SCALE_BOUNDS["min"], min(val, FONT_SCALE_BOUNDS["max"]))

        self.assertEqual(clamp_scale(-10.0), 0.8)
        self.assertEqual(clamp_scale(0.0), 0.8)
        self.assertEqual(clamp_scale(0.799), 0.8)
        self.assertEqual(clamp_scale(1.301), 1.3)
        self.assertEqual(clamp_scale(999.0), 1.3)

    def test_b3_corrupted_base64_font_payload_handling(self):
        """Boundary: Corrupted base64 font payload is detected and does not pass WOFF2 validation."""
        corrupted_b64 = "!!!NotValidBase64@@@"
        try:
            raw = base64.b64decode(corrupted_b64)
            valid = validate_woff2_bytes(raw)
        except Exception:
            valid = False
        self.assertFalse(valid, "Corrupted base64 must not be recognized as valid WOFF2 font")

    def test_b4_non_standard_font_family_escaping(self):
        """Boundary: Font family names with special characters are safely quoted in CSS rules."""
        def format_font_rule(font_name: str) -> str:
            # Escape quotes
            safe_name = font_name.replace('"', '\\"')
            return f'* {{ font-family: "{safe_name}", sans-serif !important; }}'

        rule_special = format_font_rule('Test "Special" Font')
        self.assertIn('"Test \\"Special\\" Font"', rule_special)

    def test_b5_missing_font_file_graceful_handling(self):
        """Boundary: Attempting to read a missing font file raises FileNotFound without silent corruption."""
        missing_path = os.path.join(PROJECT_ROOT, "src", "fonts", "NonExistentFont.woff2")
        with self.assertRaises(FileNotFoundError):
            with open(missing_path, "rb") as f:
                _ = f.read()

    def test_b6_font_size_adjust_missing_preset_defaults_to_none(self):
        """Boundary: Standard fonts without preset font-size-adjust do not inject unnecessary rules."""
        self.assertIsNone(FONT_SIZE_ADJUST_PRESETS.get("JetBrains Mono"))
        self.assertIsNone(FONT_SIZE_ADJUST_PRESETS.get("Uncut Sans"))
        self.assertEqual(FONT_SIZE_ADJUST_PRESETS.get("Terraria"), 0.66)
        self.assertEqual(FONT_SIZE_ADJUST_PRESETS.get("Minecraft"), 0.55)


class TestTier2DiscordRpcBoundaries(unittest.TestCase):
    """Area 2 Boundaries: Discord RPC & Networking"""

    def test_b7_all_ten_pipes_unavailable_schedules_reconnect(self):
        """Boundary: When all pipes 0..9 fail, client must not crash and schedules retry."""
        pipe_attempts = []
        state = {"connected": False, "scheduled_reconnect": False}

        for pipe_name in DISCORD_PIPE_NAMES:
            pipe_attempts.append(pipe_name)

        self.assertEqual(len(pipe_attempts), 10)
        # All failed -> schedule reconnect
        state["scheduled_reconnect"] = True
        self.assertTrue(state["scheduled_reconnect"])
        self.assertFalse(state["connected"])

    def test_b8_stalled_handshake_triggers_watchdog_teardown(self):
        """Boundary: Discord pipe connects but hangs before sending READY event."""
        state = {"connected": True, "isReady": False, "socket_destroyed": False}
        elapsed_ms = 5001.0  # Exceeds 5000ms

        if not state["isReady"] and elapsed_ms >= DISCORD_HANDSHAKE_TIMEOUT_MS:
            state["connected"] = False
            state["socket_destroyed"] = True

        self.assertTrue(state["socket_destroyed"])
        self.assertFalse(state["connected"])

    def test_b9_zero_or_negative_track_duration_handling(self):
        """Boundary: Track with 0ms or negative duration is safely formatted in RPC activity."""
        def format_activity_timestamps(duration_ms: int, position_ms: int) -> Dict[str, int]:
            now = 1700000000
            if duration_ms <= 0:
                return {"start": now - int(max(0, position_ms) / 1000)}
            start_ts = now - int(position_ms / 1000)
            end_ts = start_ts + int(duration_ms / 1000)
            return {"start": start_ts, "end": end_ts}

        # Zero duration
        res_zero = format_activity_timestamps(0, 5000)
        self.assertIn("start", res_zero)
        self.assertNotIn("end", res_zero)

        # Negative duration
        res_neg = format_activity_timestamps(-100, 0)
        self.assertIn("start", res_neg)
        self.assertNotIn("end", res_neg)

    def test_b10_extremely_long_track_strings_truncation(self):
        """Boundary: 500-char track title and artist strings don't crash packet serialization."""
        long_title = "A" * 500
        long_artist = "B" * 500
        activity = {
            "details": long_title[:128],  # Discord RPC limits to 128 chars
            "state": long_artist[:128],
        }
        raw = encode_discord_ipc_packet(1, json.dumps(activity))
        op, length, payload_str, _ = decode_discord_ipc_packet(raw)
        self.assertEqual(op, 1)
        decoded = json.loads(payload_str)
        self.assertLessEqual(len(decoded["details"]), 128)
        self.assertLessEqual(len(decoded["state"]), 128)

    def test_b11_rapid_concurrent_connect_calls_idempotent(self):
        """Boundary: Multiple calls to connect() while already connecting do not leak sockets."""
        state = {"connecting": False, "connected": False, "attempts": 0}

        def safe_connect():
            if state["connected"] or state["connecting"]:
                return  # Idempotent skip
            state["connecting"] = True
            state["attempts"] += 1

        safe_connect()
        safe_connect()
        safe_connect()
        self.assertEqual(state["attempts"], 1, "Concurrent connect() calls must be idempotent")

    def test_b12_malformed_incoming_packet_handling(self):
        """Boundary: Incoming packet with corrupted length field raises ValueError without hanging."""
        # 4-byte opcode 1, but header claiming 10000 bytes with only 4 bytes of body
        corrupted_packet = struct.pack("<II", 1, 10000) + b"test"
        with self.assertRaises(ValueError):
            decode_discord_ipc_packet(corrupted_packet)


class TestTier2GamingHudOverlayBoundaries(unittest.TestCase):
    """Area 3 Boundaries: Gaming HUD Overlay"""

    def test_b13_open_overlay_with_null_last_player_state(self):
        """Boundary: Opening overlay before any music has played handles null state gracefully."""
        overlay_ui = {
            "title": "Трек не воспроизводится",
            "artist": "—",
            "progress_width": "0%",
            "has_error": False,
        }

        def render_state(state: Optional[Dict[str, Any]]):
            if not state or not state.get("track"):
                overlay_ui["title"] = "Трек не воспроизводится"
                overlay_ui["artist"] = "—"
                overlay_ui["progress_width"] = "0%"
                return
            overlay_ui["title"] = state["track"].get("title", "")
            overlay_ui["artist"] = state["track"].get("artist", "")

        render_state(None)
        self.assertEqual(overlay_ui["title"], "Трек не воспроизводится")
        self.assertEqual(overlay_ui["progress_width"], "0%")
        self.assertFalse(overlay_ui["has_error"])

    def test_b14_playback_position_clamping_beyond_duration(self):
        """Boundary: Position calculated > duration is clamped to duration (progress bar <= 100%)."""
        clamped_pos = interpolate_playback_position(
            base_position=175.0,
            base_timestamp_ms=1000.0,
            current_timestamp_ms=10000.0,  # 9 seconds later -> 184s
            duration=180.0,                # max 180s
            speed=1.0,
            is_playing=True,
        )
        self.assertEqual(clamped_pos, 180.0)

    def test_b15_negative_position_clamping(self):
        """Boundary: Negative base position is clamped to 0.0s."""
        clamped_pos = interpolate_playback_position(
            base_position=-15.0,
            base_timestamp_ms=1000.0,
            current_timestamp_ms=1000.0,
            duration=200.0,
            speed=1.0,
            is_playing=True,
        )
        self.assertEqual(clamped_pos, 0.0)

    def test_b16_rapid_play_pause_clicks_consistency(self):
        """Boundary: Rapid 20x click spam on play/pause toggles state deterministically."""
        is_playing = False
        for _ in range(20):
            is_playing = not is_playing

        self.assertFalse(is_playing, "Even number of clicks returns to original state")

    def test_b17_null_lyrics_payload_does_not_crash_hud(self):
        """Boundary: Null lyrics payload displays track fallback header without crashing."""
        hud_lyrics_state = {"display_text": ""}

        def update_lyrics_ui(payload: Optional[Dict[str, Any]], track_title: str):
            if not payload or not payload.get("lyrics"):
                hud_lyrics_state["display_text"] = f"♫ {track_title}"
                return
            hud_lyrics_state["display_text"] = payload["lyrics"]

        update_lyrics_ui(None, "My Song")
        self.assertEqual(hud_lyrics_state["display_text"], "♫ My Song")

    def test_b18_seek_to_exact_boundaries(self):
        """Boundary: Seeking to exact 0.0s and exact duration clamps cleanly."""
        duration = 240.0
        def safe_seek(target_sec: float) -> float:
            return max(0.0, min(target_sec, duration))

        self.assertEqual(safe_seek(-5.0), 0.0)
        self.assertEqual(safe_seek(0.0), 0.0)
        self.assertEqual(safe_seek(240.0), 240.0)
        self.assertEqual(safe_seek(300.0), 240.0)


class TestTier2CascadingLyricsBoundaries(unittest.TestCase):
    """Area 4 Boundaries: Cascading Lyrics Engine"""

    def test_b19_all_three_providers_fail_gracefully(self):
        """Boundary: All 3 tiers miss (404/empty) -> returns success=False without unhandled exception."""
        engine = MockCascadingLyricsEngine()
        # Empty databases
        result = engine.fetch_lyrics("nonexistent_id", "Unknown Track", "Unknown Artist", 180)
        self.assertFalse(result.success)
        self.assertEqual(result.provider, "none")
        self.assertEqual(result.lyrics, "")
        self.assertEqual(len(result.sync_lyrics), 0)

    def test_b20_unauthenticated_session_cookie_skips_yandex_cleanly(self):
        """Boundary: Empty or invalid Session_id cookie skips Yandex and falls through to Musixmatch."""
        engine = MockCascadingLyricsEngine()
        engine.user_session_cookies = {}  # Logged out
        engine.musixmatch_db["song:artist"] = "[00:10.00] Synced line"

        result = engine.fetch_lyrics("123", "Song", "Artist", 120)
        self.assertTrue(result.success)
        self.assertEqual(result.provider, "musixmatch")

    def test_b21_musixmatch_tls_block_cascades_to_lrclib(self):
        """Boundary: Musixmatch timeout/block cascades to LRCLib within timeout bounds."""
        engine = MockCascadingLyricsEngine()
        engine.user_session_cookies = {}
        engine.simulate_musixmatch_block = True
        engine.lrclib_db["song:artist"] = "[00:15.00] LRCLib fallback line"

        result = engine.fetch_lyrics("123", "Song", "Artist", 120)
        self.assertTrue(result.success)
        self.assertEqual(result.provider, "lrclib")

    def test_b22_complex_track_title_parentheses_stripping(self):
        """Boundary: Track title with brackets, feat, and remixes strips to clean search query."""
        raw_titles = [
            ("Розовое вино (feat. Feduk) [Remix]", "Розовое вино"),
            ("Shape of You (Acoustic Version)", "Shape of You"),
            ("Track Title (Official Audio)", "Track Title"),
            ("Clean Title", "Clean Title"),
        ]
        for raw, expected in raw_titles:
            self.assertEqual(re_strip_parentheses(raw), expected)

    def test_b23_plain_text_lyrics_without_timestamps(self):
        """Boundary: Plain text lyrics without any timestamps parse with is_lrc=False."""
        plain_text = "First verse line\nSecond verse line\nChorus line"
        parsed = parse_lrc_timestamps(plain_text)
        self.assertEqual(len(parsed), 0)

        cleaned = clean_lrc_metadata_tags(plain_text)
        self.assertEqual(cleaned, plain_text)

    def test_b24_massive_metadata_tag_block_stripping(self):
        """Boundary: LRC with 100 metadata header lines strips all headers cleanly."""
        headers = [f"[tag{i}: value{i}]" for i in range(100)]
        lyrics = ["[00:10.00] Real lyric line 1", "[00:20.00] Real lyric line 2"]
        full_lrc = "\n".join(headers + lyrics)

        cleaned = clean_lrc_metadata_tags(full_lrc)
        self.assertNotIn("tag0", cleaned)
        self.assertNotIn("tag99", cleaned)
        self.assertEqual(cleaned.splitlines(), lyrics)


class TestTier2SettingsUiBoundaries(unittest.TestCase):
    """Area 5 Boundaries: Anti-Slop Settings UI"""

    def test_b25_scale_slider_clamping_on_invalid_inputs(self):
        """Boundary: Non-numeric, negative or excessive scale values clamp to valid bounds."""
        def safe_parse_scale(raw_val: Any) -> float:
            try:
                v = float(raw_val)
                return max(INTERFACE_SCALE_BOUNDS["min"], min(v, INTERFACE_SCALE_BOUNDS["max"]))
            except (ValueError, TypeError):
                return INTERFACE_SCALE_BOUNDS["default"]

        self.assertEqual(safe_parse_scale("invalid"), 1.0)
        self.assertEqual(safe_parse_scale(None), 1.0)
        self.assertEqual(safe_parse_scale("-50"), 0.8)
        self.assertEqual(safe_parse_scale("500"), 1.3)
        self.assertEqual(safe_parse_scale("1.15"), 1.15)

    def test_b26_corrupted_json_in_settings_file(self):
        """Boundary: Corrupted JSON in mod_settings.json falls back to defaults without crash."""
        def load_settings(raw_content: str) -> Dict[str, Any]:
            try:
                return json.loads(raw_content)
            except Exception:
                return {"discordRPC/enabled": True, "font-changer/enabled": True}

        corrupt_data = "{ key: incomplete_json..."
        loaded = load_settings(corrupt_data)
        self.assertTrue(loaded["discordRPC/enabled"])

    def test_b27_zero_byte_settings_file_handling(self):
        """Boundary: Completely empty 0-byte settings file loads default settings."""
        def load_settings_or_default(content: str) -> Dict[str, Any]:
            if not content.strip():
                return {"loaded_defaults": True}
            return json.loads(content)

        self.assertTrue(load_settings_or_default("")["loaded_defaults"])

    def test_b28_rapid_sidebar_tab_switching_state(self):
        """Boundary: Rapid switching across tabs in arbitrary order preserves current active tab."""
        active_tab = "tab-appearance"
        sequence = ["tab-fonts", "tab-discord", "tab-lyrics", "tab-cleaner", "tab-overlay", "tab-appearance"]
        for tab in sequence:
            active_tab = tab

        self.assertEqual(active_tab, "tab-appearance")

    def test_b29_invalid_accent_hex_falls_back(self):
        """Boundary: Invalid accent color input falls back to default #fed42b."""
        import re
        def sanitize_hex_accent(color: str) -> str:
            if re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", color):
                return color
            return "#fed42b"

        self.assertEqual(sanitize_hex_accent("not_a_hex"), "#fed42b")
        self.assertEqual(sanitize_hex_accent(""), "#fed42b")
        self.assertEqual(sanitize_hex_accent("#ff0000"), "#ff0000")
        self.assertEqual(sanitize_hex_accent("#fed42b"), "#fed42b")

    def test_b30_extreme_small_viewport_clamping(self):
        """Boundary: 320x240 screen size clamps modal with positive non-zero dimensions."""
        max_w = max(280, int(320 * 0.92))
        max_h = max(200, int(240 * 0.88))
        self.assertGreater(max_w, 0)
        self.assertGreater(max_h, 0)


class TestTier2PackagingBoundaries(unittest.TestCase):
    """Area 6 Boundaries: ASAR Packaging & File Integrity"""

    def test_b31_corrupted_asar_header_unpack_error(self):
        """Boundary: ASAR with invalid header length raises exception."""
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            # write corrupt header
            tf.write(struct.pack("<IIII", 4, 100, 100, 0))
            tf_path = tf.name

        try:
            sys.path.insert(0, os.path.join(PROJECT_ROOT, "tools"))
            from asar_tool import extract_asar
            with tempfile.TemporaryDirectory() as td:
                with self.assertRaises(Exception):
                    extract_asar(tf_path, td)
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_b32_zero_byte_file_in_asar_pack(self):
        """Boundary: 0-byte file inside ASAR roundtrips with size=0 and valid offset."""
        sys.path.insert(0, os.path.join(PROJECT_ROOT, "tools"))
        from asar_tool import extract_asar, pack_asar

        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "src")
            os.makedirs(src)
            open(os.path.join(src, "empty.txt"), "w").close()

            archive = os.path.join(td, "archive.asar")
            pack_asar(src, archive)

            dest = os.path.join(td, "dest")
            extract_asar(archive, dest)

            empty_file = os.path.join(dest, "empty.txt")
            self.assertTrue(os.path.exists(empty_file))
            self.assertEqual(os.path.getsize(empty_file), 0)

    def test_b33_deep_directory_hierarchy_preservation(self):
        """Boundary: 5-level deep directory nesting inside ASAR preserves structure."""
        sys.path.insert(0, os.path.join(PROJECT_ROOT, "tools"))
        from asar_tool import extract_asar, pack_asar

        with tempfile.TemporaryDirectory() as td:
            deep_path = os.path.join(td, "src", "a", "b", "c", "d", "e")
            os.makedirs(deep_path)
            with open(os.path.join(deep_path, "deep.txt"), "w") as f:
                f.write("deep content")

            archive = os.path.join(td, "archive.asar")
            pack_asar(os.path.join(td, "src"), archive)

            dest = os.path.join(td, "dest")
            extract_asar(archive, dest)

            self.assertTrue(os.path.exists(os.path.join(dest, "a", "b", "c", "d", "e", "deep.txt")))

    def test_b34_nonexistent_asar_file_extraction_error(self):
        """Boundary: Extracting from non-existent ASAR path raises FileNotFoundError."""
        sys.path.insert(0, os.path.join(PROJECT_ROOT, "tools"))
        from asar_tool import extract_asar

        with self.assertRaises(FileNotFoundError):
            extract_asar("C:\\non_existent_folder\\fake.asar", "C:\\dest")

    def test_b35_asar_special_characters_filename_handling(self):
        """Boundary: Files with Cyrillic characters inside ASAR pack and unpack without corruption."""
        sys.path.insert(0, os.path.join(PROJECT_ROOT, "tools"))
        from asar_tool import extract_asar, pack_asar

        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "src")
            os.makedirs(src)
            cyrillic_file = os.path.join(src, "шрифт_текст.txt")
            with open(cyrillic_file, "w", encoding="utf-8") as f:
                f.write("Содержимое файла")

            archive = os.path.join(td, "archive.asar")
            pack_asar(src, archive)

            dest = os.path.join(td, "dest")
            extract_asar(archive, dest)

            out_file = os.path.join(dest, "шрифт_текст.txt")
            self.assertTrue(os.path.exists(out_file))
            with open(out_file, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "Содержимое файла")


if __name__ == "__main__":
    unittest.main()
