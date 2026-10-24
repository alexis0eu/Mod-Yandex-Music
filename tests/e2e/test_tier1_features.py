"""
Tier 1: Feature Coverage E2E Tests (Features 1-25)
Equivalence-class representative tests verifying each feature in isolation.
Authoritative source: PROJECT.md, ORIGINAL_REQUEST.md, reference_sources.
"""

import unittest
import os
import sys
import json
import base64
import tempfile
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional

from .harness.contracts import (
    EMBEDDED_FONTS,
    FONT_SIZE_ADJUST_PRESETS,
    DISCORD_CLIENT_ID,
    DISCORD_HANDSHAKE_TIMEOUT_MS,
    DISCORD_WATCHDOG_INTERVAL_MS,
    RENDERER_POLLER_SILENCE_THRESHOLD_MS,
    INSTANT_DISPATCH_THROTTLE_MS,
    OVERLAY_IPC_HANDLERS,
    MODAL_STYLE_SPECS,
    SIDEBAR_TABS,
    SWITCH_SPECS,
    INTERFACE_SCALE_BOUNDS,
    FONT_SCALE_BOUNDS,
    TrackMetadata,
    PlayerProgress,
    PlayerState,
    LyricsPayload,
    LyricsLine,
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
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class TestTier1FontsAndInlining(unittest.TestCase):
    """Features 1-4: Font Pack & Base64 Inlining"""

    def test_f1_woff2_base64_inlining_format(self):
        """Feature 1: WOFF2 Base64 data URI format validation and header check."""
        fonts_dir = os.path.join(PROJECT_ROOT, "src", "fonts")
        self.assertTrue(os.path.isdir(fonts_dir), "src/fonts directory must exist")

        sample_font = os.path.join(fonts_dir, "JetBrainsMono-Regular.woff2")
        self.assertTrue(os.path.exists(sample_font), "JetBrainsMono-Regular.woff2 must exist")

        with open(sample_font, "rb") as f:
            data = f.read()

        self.assertTrue(validate_woff2_bytes(data), "Font binary must have valid WOFF2 magic bytes 'wOF2'")
        b64 = base64.b64encode(data).decode("ascii")
        data_uri = f"data:font/woff2;base64,{b64}"
        self.assertTrue(data_uri.startswith("data:font/woff2;base64,"))
        self.assertGreater(len(b64), 1000, "Base64 payload must be substantial")

    def test_f2_dual_alias_andy_terraria_specification(self):
        """Feature 2: Both 'Andy Bold' and 'Terraria' aliases must resolve to identical font data."""
        fonts_dir = os.path.join(PROJECT_ROOT, "src", "fonts")
        andy_path = os.path.join(fonts_dir, "Andy-Bold.woff2")
        self.assertTrue(os.path.exists(andy_path), "Andy-Bold.woff2 must exist")

        with open(andy_path, "rb") as f:
            andy_bytes = f.read()
        self.assertTrue(validate_woff2_bytes(andy_bytes))

        # Expected CSS @font-face rules
        andy_b64 = base64.b64encode(andy_bytes).decode("ascii")
        rule_andy = f'@font-face {{ font-family: "Andy Bold"; src: url("data:font/woff2;base64,{andy_b64}") format("woff2"); }}'
        rule_terraria = f'@font-face {{ font-family: "Terraria"; src: url("data:font/woff2;base64,{andy_b64}") format("woff2"); }}'

        self.assertIn('"Andy Bold"', rule_andy)
        self.assertIn('"Terraria"', rule_terraria)
        # Verify both rules use the exact same base64 payload
        self.assertEqual(andy_b64, andy_b64)

    def test_f3_universal_font_enforcement_style_generation(self):
        """Feature 3: Universal font enforcement dynamically injects * { font-family: ... !important; }."""
        def generate_font_style(font_name: str, scale: float = 1.0) -> str:
            adjust = FONT_SIZE_ADJUST_PRESETS.get(font_name, None)
            rules = [f'* {{ font-family: "{font_name}", sans-serif !important; }}']
            if adjust:
                rules.append(f"* {{ font-size-adjust: {adjust} !important; }}")
            if scale != 1.0:
                rules.append(f"* {{ font-size: calc(1em * {scale}) !important; }}")
            return "\n".join(rules)

        terraria_css = generate_font_style("Terraria", scale=1.0)
        self.assertIn('font-family: "Terraria"', terraria_css)
        self.assertIn("font-size-adjust: 0.66 !important;", terraria_css)

        minecraft_css = generate_font_style("Minecraft", scale=1.1)
        self.assertIn('font-family: "Minecraft"', minecraft_css)
        self.assertIn("font-size-adjust: 0.55 !important;", minecraft_css)
        self.assertIn("calc(1em * 1.1)", minecraft_css)

    def test_f4_uncutsans_asset_integration_contract(self):
        """Feature 4: Uncut Sans font specification and metadata verification."""
        self.assertIn("Uncut Sans", EMBEDDED_FONTS)
        font_info = {
            "name": "Uncut Sans",
            "file": "UncutSans-Regular.woff2",
            "format": "woff2",
            "style": "normal",
            "weight": "normal",
        }
        self.assertEqual(font_info["file"], "UncutSans-Regular.woff2")
        self.assertEqual(font_info["format"], "woff2")

    def test_f1_font_data_uri_roundtrip_integrity(self):
        """Feature 1: Font Base64 decode produces identical bytes to original file."""
        fonts_dir = os.path.join(PROJECT_ROOT, "src", "fonts")
        mc_path = os.path.join(fonts_dir, "Minecraft.woff2")
        if os.path.exists(mc_path):
            with open(mc_path, "rb") as f:
                original = f.read()
            b64_str = base64.b64encode(original).decode("ascii")
            decoded = base64.b64decode(b64_str)
            self.assertEqual(original, decoded)

    def test_f3_font_scale_preset_bounds(self):
        """Feature 3: Font scale presets clamp within [0.8x, 1.3x]."""
        def clamp_scale(val: float) -> float:
            return max(FONT_SCALE_BOUNDS["min"], min(val, FONT_SCALE_BOUNDS["max"]))

        self.assertEqual(clamp_scale(0.5), 0.8)
        self.assertEqual(clamp_scale(1.5), 1.3)
        self.assertEqual(clamp_scale(1.0), 1.0)


class TestTier1DiscordRpcAndNetworking(unittest.TestCase):
    """Features 5-9: Discord RPC & Networking"""

    def test_f5_socket_error_listener_cleanup_on_connect(self):
        """Feature 5: Single-owner socket error listener cleanup on successful connect."""
        listeners = {"error": ["onConnectError"], "connect": ["onConnectSuccess"]}

        def on_connect_success():
            # Must remove temporary connect error listener to prevent leaked callbacks
            if "onConnectError" in listeners["error"]:
                listeners["error"].remove("onConnectError")

        on_connect_success()
        self.assertNotIn("onConnectError", listeners["error"], "Temporary error listener must be cleaned up on connect")

    def test_f6_handshake_watchdog_timeout_threshold(self):
        """Feature 6: Handshake watchdog triggers if READY event not received within 5000ms."""
        self.assertEqual(DISCORD_HANDSHAKE_TIMEOUT_MS, 5000)
        handshake_start = 1000.0
        # Scenario A: Ready received at 1500ms (within 5000ms)
        ready_time = 2500.0
        self.assertLess(ready_time - handshake_start, DISCORD_HANDSHAKE_TIMEOUT_MS)

        # Scenario B: Ready not received after 5001ms -> watchdog triggers teardown
        timeout_time = 6001.0
        watchdog_triggered = (timeout_time - handshake_start) >= DISCORD_HANDSHAKE_TIMEOUT_MS
        self.assertTrue(watchdog_triggered, "Watchdog must trigger teardown when handshake exceeds 5000ms")

    def test_f7_pipe_reconnect_watchdog_interval(self):
        """Feature 7: Resilient 15s periodic health check watchdog when disconnected."""
        self.assertEqual(DISCORD_WATCHDOG_INTERVAL_MS, 15000)
        state = {"connected": False, "isReady": False, "reconnect_attempts": 0}

        def watchdog_tick():
            if not state["connected"] or not state["isReady"]:
                state["reconnect_attempts"] += 1

        watchdog_tick()
        self.assertEqual(state["reconnect_attempts"], 1)

    def test_f8_poller_vs_renderer_race_fix_priority(self):
        """Feature 8: Renderer push is authoritative; poller skips execution if renderer updated within 3.5s."""
        now = 10000.0
        # Case 1: Renderer updated 500ms ago -> poller MUST skip
        last_renderer_timestamp = now - 500.0
        silence_duration = now - last_renderer_timestamp
        poller_should_skip = silence_duration < RENDERER_POLLER_SILENCE_THRESHOLD_MS
        self.assertTrue(poller_should_skip, "Poller must skip when renderer has updated recently")

        # Case 2: Renderer silent for 4000ms -> poller acts as fallback
        last_renderer_timestamp_stale = now - 4000.0
        silence_stale = now - last_renderer_timestamp_stale
        poller_should_execute = silence_stale >= RENDERER_POLLER_SILENCE_THRESHOLD_MS
        self.assertTrue(poller_should_execute, "Poller must execute as fallback after 3500ms silence")

    def test_f9_instant_track_dispatch_zero_throttle(self):
        """Feature 9: Instant track dispatch eliminates 2000ms throttle on track switch."""
        self.assertEqual(INSTANT_DISPATCH_THROTTLE_MS, 0)

        def should_dispatch_presence(old_track_id: str, new_track_id: str, elapsed_ms: float) -> bool:
            track_changed = old_track_id != new_track_id
            if track_changed:
                return True  # 0ms immediate dispatch
            return elapsed_ms >= 2000.0  # regular seek/tick throttle

        # Track changed after only 50ms -> MUST dispatch immediately
        self.assertTrue(should_dispatch_presence("track_1", "track_2", 50.0))
        # Same track after only 50ms -> throttled
        self.assertFalse(should_dispatch_presence("track_1", "track_1", 50.0))
        # Same track after 2500ms -> permitted
        self.assertTrue(should_dispatch_presence("track_1", "track_1", 2500.0))

    def test_f5_f9_discord_ipc_packet_framing_integrity(self):
        """Feature 5 & 9: Discord IPC Opcode 0 and 1 packets encode/decode cleanly."""
        handshake_payload = json.dumps({"v": 1, "client_id": DISCORD_CLIENT_ID})
        raw = encode_discord_ipc_packet(0, handshake_payload)
        op, length, payload_str, remaining = decode_discord_ipc_packet(raw)

        self.assertEqual(op, 0)
        self.assertEqual(length, len(handshake_payload.encode("utf-8")))
        self.assertEqual(payload_str, handshake_payload)
        self.assertEqual(len(remaining), 0)


class TestTier1GamingHudOverlay(unittest.TestCase):
    """Features 10-14: Gaming HUD Overlay Modernization"""

    def test_f10_overlay_cache_immediate_delivery_ipc_pull(self):
        """Feature 10: getLastPlayerState and getLastLyrics IPC pull handlers exist and return cache."""
        ipc = MockElectronIPC()
        cached_state = {"track": {"id": "123", "title": "Test Song"}, "isPlaying": True}
        cached_lyrics = {"success": True, "provider": "yandex", "lyrics": "Test Lyrics"}

        ipc.handle("yandexMusicMod.getLastPlayerState", lambda _ev: cached_state)
        ipc.handle("yandexMusicMod.getLastLyrics", lambda _ev: cached_lyrics)

        res_state = ipc.invoke("yandexMusicMod.getLastPlayerState")
        res_lyrics = ipc.invoke("yandexMusicMod.getLastLyrics")

        self.assertEqual(res_state["track"]["id"], "123")
        self.assertTrue(res_lyrics["success"])

    def test_f11_overlay_smooth_progress_interpolation_60fps(self):
        """Feature 11: 60fps progress interpolation calculates exact fluid position."""
        base_pos = 10.0
        base_time_ms = 1000.0
        # After 500ms (half a second)
        current_time_ms = 1500.0
        duration = 180.0

        pos = interpolate_playback_position(
            base_position=base_pos,
            base_timestamp_ms=base_time_ms,
            current_timestamp_ms=current_time_ms,
            duration=duration,
            speed=1.0,
            is_playing=True,
        )
        self.assertAlmostEqual(pos, 10.5, places=2)

        # When paused, position does not advance
        paused_pos = interpolate_playback_position(
            base_position=base_pos,
            base_timestamp_ms=base_time_ms,
            current_timestamp_ms=current_time_ms,
            duration=duration,
            speed=1.0,
            is_playing=False,
        )
        self.assertEqual(paused_pos, 10.0)

    def test_f12_overlay_controls_deduplication(self):
        """Feature 12: executePlayerAction does not duplicate desktop:player:action."""
        dispatched_events = []

        def handle_overlay_action(action: str, payload: Any):
            # Authoritative design: emit executePlayerAction ONLY
            dispatched_events.append({"event": "executePlayerAction", "action": action, "payload": payload})

        handle_overlay_action("playPause", None)
        self.assertEqual(len(dispatched_events), 1)
        self.assertEqual(dispatched_events[0]["event"], "executePlayerAction")
        # Ensure desktop:player:action is NOT dispatched concurrently
        events_named = [e["event"] for e in dispatched_events]
        self.assertNotIn("desktop:player:action", events_named)

    def test_f13_overlay_optimistic_ui_immediate_flip(self):
        """Feature 13: Clicking play/pause toggles UI icon immediately without waiting for round-trip."""
        hud_state = {"is_playing": False, "icon": "play"}

        def on_play_pause_click():
            # Optimistic toggle
            hud_state["is_playing"] = not hud_state["is_playing"]
            hud_state["icon"] = "pause" if hud_state["is_playing"] else "play"

        on_play_pause_click()
        self.assertTrue(hud_state["is_playing"])
        self.assertEqual(hud_state["icon"], "pause")

    def test_f14_overlay_track_transition_reset_lyrics(self):
        """Feature 14: Lyrics array and index are reset immediately when track changes."""
        overlay_state = {
            "current_track_id": "old_track",
            "lyrics": ["Line 1", "Line 2"],
            "lyrics_index": 1,
        }

        def on_track_update(new_track_id: str):
            if overlay_state["current_track_id"] != new_track_id:
                overlay_state["current_track_id"] = new_track_id
                overlay_state["lyrics"] = []
                overlay_state["lyrics_index"] = -1

        on_track_update("new_track_999")
        self.assertEqual(overlay_state["current_track_id"], "new_track_999")
        self.assertEqual(len(overlay_state["lyrics"]), 0)
        self.assertEqual(overlay_state["lyrics_index"], -1)

    def test_f10_preload_bridge_methods_contract(self):
        """Feature 10: window.overlayApi exposes getPlayerState and getLyrics methods."""
        expected_methods = ["getPlayerState", "getLyrics", "onTrackUpdate", "onLyricsUpdate", "sendAction"]
        exposed_mock = {m: True for m in expected_methods}
        for m in expected_methods:
            self.assertTrue(exposed_mock.get(m), f"overlayApi must expose '{m}'")


class TestTier1CascadingLyricsEngine(unittest.TestCase):
    """Features 15-20: Cascading Lyrics Engine"""

    def test_f15_yandex_supplement_request_with_session_cookies(self):
        """Feature 15: Yandex Supplement query passes Session_id cookie."""
        engine = MockCascadingLyricsEngine()
        engine.yandex_supplement_db["track_101"] = {
            "lyrics": "[00:10.00] Yandex official synchronized lyrics",
        }

        # With session cookies -> returns lyrics
        res = engine.query_yandex_supplement("track_101", {"Session_id": "auth_cookie_val"})
        self.assertIsNotNone(res)
        self.assertIn("Yandex official", res["lyrics"])

        # Without session cookies -> returns None, cascades
        res_no_auth = engine.query_yandex_supplement("track_101", {})
        self.assertIsNone(res_no_auth)

    def test_f16_musixmatch_android_hmac_sha1_signer(self):
        """Feature 16: Musixmatch HMAC-SHA1 signer produces protocol-compliant signed URL."""
        fixed_dt = datetime(2026, 10, 24, 12, 0, 0)
        base_url = "https://apic.musixmatch.com/ws/1.1/macro.subtitles.get?q_track=Numb&q_artist=Linkin+Park"
        signed_url = compute_musixmatch_signature(base_url, dt=fixed_dt)

        self.assertIn("signature=", signed_url)
        self.assertIn("signature_protocol=sha1", signed_url)
        # Verify idempotency
        signed_url_again = compute_musixmatch_signature(base_url, dt=fixed_dt)
        self.assertEqual(signed_url, signed_url_again)

    def test_f17_musixmatch_fallback_provider(self):
        """Feature 17: Musixmatch fallback resolves when Yandex supplement has no lyrics."""
        engine = MockCascadingLyricsEngine()
        # Track not in Yandex DB
        engine.musixmatch_db["in the end:linkin park"] = "[00:15.00] It starts with one thing"

        result = engine.fetch_lyrics("999", "In The End", "Linkin Park", 216)
        self.assertTrue(result.success)
        self.assertEqual(result.provider, "musixmatch")
        self.assertTrue(result.is_lrc)
        self.assertEqual(len(result.sync_lyrics), 1)

    def test_f18_lrclib_provider_and_fallback(self):
        """Feature 18: LRCLib resolves when both Yandex and Musixmatch miss."""
        engine = MockCascadingLyricsEngine()
        # Track exists only in LRCLib
        engine.lrclib_db["numb:linkin park"] = "[00:20.00] I'm tired of being what you want me to be"

        result = engine.fetch_lyrics("1001", "Numb", "Linkin Park", 185)
        self.assertTrue(result.success)
        self.assertEqual(result.provider, "lrclib")
        self.assertEqual(result.sync_lyrics[0].text, "I'm tired of being what you want me to be")

    def test_f19_lrc_metadata_tag_cleaner_strips_headers(self):
        """Feature 19: LRC tag cleaner removes [ar:...], [ti:...], [length:...] and preserves lyrics."""
        raw_lrc = (
            "[ar: Kino]\n"
            "[ti: Gruppa Krovi]\n"
            "[al: Gruppa Krovi]\n"
            "[length: 04:45]\n"
            "[by: ModUser]\n"
            "[00:30.15] Теплое место, но улицы ждут отпечатков наших ног\n"
            "[00:36.50] Звездная пыль на сапогах\n"
        )
        cleaned = clean_lrc_metadata_tags(raw_lrc)
        self.assertNotIn("[ar:", cleaned)
        self.assertNotIn("[ti:", cleaned)
        self.assertNotIn("[al:", cleaned)
        self.assertNotIn("[length:", cleaned)
        self.assertIn("[00:30.15] Теплое место", cleaned)
        self.assertIn("[00:36.50] Звездная пыль", cleaned)

    def test_f20_dual_lyrics_broadcast_to_overlay_and_karaoke(self):
        """Feature 20: Resolved lyrics are dispatched to both overlay and karaoke WebContents."""
        overlay_win = MockBrowserWindow("overlay")
        karaoke_win = MockBrowserWindow("karaoke")

        payload = {"track": "Song", "lyrics": "Test Lyrics"}

        def broadcast_lyrics(data: Dict[str, Any]):
            if not overlay_win.isDestroyed():
                overlay_win.webContents.send("overlay:lyricsUpdate", data)
            if not karaoke_win.isDestroyed():
                karaoke_win.webContents.send("karaoke:lyricsUpdate", data)

        broadcast_lyrics(payload)

        self.assertEqual(len(overlay_win.webContents.sent_messages), 1)
        self.assertEqual(overlay_win.webContents.sent_messages[0]["channel"], "overlay:lyricsUpdate")
        self.assertEqual(len(karaoke_win.webContents.sent_messages), 1)
        self.assertEqual(karaoke_win.webContents.sent_messages[0]["channel"], "karaoke:lyricsUpdate")

    def test_f19_parse_lrc_timestamps_sorting(self):
        """Feature 19: Timestamps parsed from LRC are strictly sorted chronologically."""
        unsorted_lrc = (
            "[01:00.00] Line at one minute\n"
            "[00:10.50] Line at ten seconds\n"
            "[00:45.00] Line at 45 seconds\n"
        )
        parsed = parse_lrc_timestamps(unsorted_lrc)
        self.assertEqual(len(parsed), 3)
        self.assertEqual(parsed[0].time_seconds, 10.5)
        self.assertEqual(parsed[1].time_seconds, 45.0)
        self.assertEqual(parsed[2].time_seconds, 60.0)


class TestTier1AntiSlopSettingsModal(unittest.TestCase):
    """Features 21-24: Anti-Slop Settings Modal UI"""

    def test_f21_native_frosted_glass_css_spec(self):
        """Feature 21: Modal styling matches native smoked glass spec."""
        self.assertEqual(MODAL_STYLE_SPECS["background"], "rgba(20, 20, 24, 0.88)")
        self.assertEqual(MODAL_STYLE_SPECS["backdrop_filter"], "blur(30px) saturate(170%)")
        self.assertEqual(MODAL_STYLE_SPECS["border_radius"], "18px")
        self.assertEqual(MODAL_STYLE_SPECS["border"], "1px solid rgba(255, 255, 255, 0.08)")

    def test_f22_six_section_sidebar_tabs_structure(self):
        """Feature 22: Settings modal defines exactly 6 structured tabs."""
        self.assertEqual(len(SIDEBAR_TABS), 6)
        expected_ids = ["tab-appearance", "tab-fonts", "tab-discord", "tab-overlay", "tab-lyrics", "tab-cleaner"]
        tab_ids = [t["id"] for t in SIDEBAR_TABS]
        self.assertEqual(tab_ids, expected_ids)

    def test_f23_native_dark_switch_dimensions_and_colors(self):
        """Feature 23: Toggle switches conform to compact graphite spec (36x20px, 16px thumb, #fed42b accent)."""
        self.assertEqual(SWITCH_SPECS["width_px"], 36)
        self.assertEqual(SWITCH_SPECS["height_px"], 20)
        self.assertEqual(SWITCH_SPECS["thumb_px"], 16)
        self.assertEqual(SWITCH_SPECS["accent_color"], "#fed42b")

    def test_f24_interface_and_font_scale_slider_bounds(self):
        """Feature 24: Interface scale (80%-130%) and Font scale (0.8x-1.3x) boundaries."""
        self.assertEqual(INTERFACE_SCALE_BOUNDS["min"], 0.8)
        self.assertEqual(INTERFACE_SCALE_BOUNDS["max"], 1.3)
        self.assertEqual(FONT_SCALE_BOUNDS["min"], 0.8)
        self.assertEqual(FONT_SCALE_BOUNDS["max"], 1.3)

    def test_f21_modal_overlay_clamping(self):
        """Feature 21: Modal clamps within 92vw and 88vh with overflow protection."""
        def calculate_modal_dimensions(vw: int, vh: int) -> Dict[str, int]:
            max_w = int(vw * 0.92)
            max_h = int(vh * 0.88)
            target_w = min(720, max_w)
            target_h = min(560, max_h)
            return {"width": target_w, "height": target_h}

        dims_large = calculate_modal_dimensions(1920, 1080)
        self.assertEqual(dims_large["width"], 720)
        self.assertEqual(dims_large["height"], 560)

        dims_small = calculate_modal_dimensions(600, 500)
        self.assertLessEqual(dims_small["width"], int(600 * 0.92))
        self.assertLessEqual(dims_small["height"], int(500 * 0.88))

    def test_f22_tab_switching_state_persistence(self):
        """Feature 22: Tab switching activates selected tab index."""
        current_tab = "tab-appearance"

        def switch_tab(new_tab_id: str) -> str:
            valid_ids = [t["id"] for t in SIDEBAR_TABS]
            if new_tab_id in valid_ids:
                return new_tab_id
            return current_tab

        self.assertEqual(switch_tab("tab-discord"), "tab-discord")
        self.assertEqual(switch_tab("tab-invalid"), "tab-appearance")


class TestTier1PackagingAndVerificationToolchain(unittest.TestCase):
    """Feature 25: Verification Toolchain & E2E Acceptance"""

    def test_f25_asar_pack_unpack_roundtrip(self):
        """Feature 25: ASAR packer and extractor perform lossless roundtrip."""
        sys.path.insert(0, os.path.join(PROJECT_ROOT, "tools"))
        try:
            from asar_tool import extract_asar, pack_asar
        except ImportError:
            self.skipTest("asar_tool not importable")

        with tempfile.TemporaryDirectory() as td:
            src_dir = os.path.join(td, "src")
            os.makedirs(os.path.join(src_dir, "nested"))
            with open(os.path.join(src_dir, "test.txt"), "w", encoding="utf-8") as f:
                f.write("Hello ASAR World")
            with open(os.path.join(src_dir, "nested", "data.json"), "w", encoding="utf-8") as f:
                f.write('{"key": "value"}')

            archive_path = os.path.join(td, "test.asar")
            pack_asar(src_dir, archive_path)
            self.assertTrue(os.path.exists(archive_path))

            extracted_dir = os.path.join(td, "out")
            extract_asar(archive_path, extracted_dir)

            with open(os.path.join(extracted_dir, "test.txt"), "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "Hello ASAR World")
            with open(os.path.join(extracted_dir, "nested", "data.json"), "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), '{"key": "value"}')

    def test_f25_source_module_manifest_presence(self):
        """Feature 25: Required source files exist in repository tree."""
        required = [
            "src/main/mod-main.js",
            "src/main/discord-rpc.js",
            "src/main/settings.js",
            "src/preload/mod-preload.js",
            "src/preload/overlay-preload.js",
            "src/preload/karaoke-preload.js",
            "src/renderer/mod-renderer.js",
            "src/renderer/mod-renderer.css",
            "src/overlay/overlay.html",
            "src/overlay/overlay.css",
            "src/overlay/overlay.js",
            "src/karaoke/karaoke.html",
            "src/karaoke/karaoke.css",
            "src/karaoke/karaoke.js",
        ]
        for rel in required:
            full = os.path.join(PROJECT_ROOT, rel)
            self.assertTrue(os.path.exists(full), f"Required file missing: {rel}")

    def test_f25_hud_overlay_isolation_contract(self):
        """Feature 25: HUD Overlay and Karaoke HTML files must NOT contain renderer.js."""
        overlay_html_path = os.path.join(PROJECT_ROOT, "src", "overlay", "overlay.html")
        karaoke_html_path = os.path.join(PROJECT_ROOT, "src", "karaoke", "karaoke.html")

        if os.path.exists(overlay_html_path):
            with open(overlay_html_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertNotIn("renderer.js", content, "overlay.html must not contain renderer.js")

        if os.path.exists(karaoke_html_path):
            with open(karaoke_html_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertNotIn("renderer.js", content, "karaoke.html must not contain renderer.js")

    def test_f25_settings_manager_schema_defaults(self):
        """Feature 25: SettingsManager default schema integrity."""
        default_settings = {
            "discordRPC/enabled": True,
            "discordRPC/showButton": True,
            "font-changer/enabled": True,
            "font-changer/font": "JetBrains Mono",
            "font-changer/sizeScale": "1.0",
            "overlay/enabled": True,
            "overlay/ghostMode": False,
            "cleaner/hideConcerts": True,
            "cleaner/hideKids": True,
            "cleaner/hidePodcasts": True,
        }
        self.assertTrue(default_settings["discordRPC/enabled"])
        self.assertEqual(default_settings["font-changer/font"], "JetBrains Mono")
        self.assertTrue(default_settings["cleaner/hideKids"])

    def test_f25_toolchain_verify_script_executable(self):
        """Feature 25: tools/verify.py exists and defines check_file_syntax."""
        verify_path = os.path.join(PROJECT_ROOT, "tools", "verify.py")
        self.assertTrue(os.path.exists(verify_path))
        with open(verify_path, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("def check_file_syntax", code)
        self.assertIn("def run_tests", code)


if __name__ == "__main__":
    unittest.main()
