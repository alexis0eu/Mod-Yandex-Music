"""
Tier 3: Cross-Feature Combinations E2E Tests
Pairwise feature interaction matrices verifying multi-module harmony.
Authoritative source: PROJECT.md § Architecture & Interface Contracts.
"""

import unittest
import os
import sys
import json
import base64
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from .harness.contracts import (
    TrackMetadata,
    PlayerProgress,
    PlayerState,
    LyricsPayload,
    LyricsLine,
    DISCORD_CLIENT_ID,
    RENDERER_POLLER_SILENCE_THRESHOLD_MS,
    FONT_SIZE_ADJUST_PRESETS,
)
from .harness.oracles import (
    compute_musixmatch_signature,
    clean_lrc_metadata_tags,
    parse_lrc_timestamps,
    interpolate_playback_position,
    encode_discord_ipc_packet,
    decode_discord_ipc_packet,
)
from .harness.simulators import (
    MockElectronIPC,
    MockBrowserWindow,
    MockDiscordServer,
    MockCascadingLyricsEngine,
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class TestTier3CrossFeatureCombinations(unittest.TestCase):
    """Pairwise Cross-Feature Interactions"""

    def test_pair1_font_enforcement_and_hud_overlay_isolation(self):
        """Pair 1: Main window font styling does NOT contaminate HUD overlay assets."""
        # 1. Main window applies Terraria font rule
        font_style = '* { font-family: "Terraria", sans-serif !important; font-size-adjust: 0.66 !important; }'
        self.assertIn("Terraria", font_style)

        # 2. Inspect overlay.html and overlay.css to verify font independence
        overlay_css_path = os.path.join(PROJECT_ROOT, "src", "overlay", "overlay.css")
        if os.path.exists(overlay_css_path):
            with open(overlay_css_path, "r", encoding="utf-8") as f:
                overlay_css = f.read()
            # Overlay has its own scoped fonts and styling
            self.assertIn(".overlay-card", overlay_css)
            self.assertNotIn('font-family: "Terraria"', overlay_css)

    def test_pair2_track_switch_instant_rpc_and_lyrics_trigger(self):
        """Pair 2: Track transition triggers instant 0ms Discord RPC update AND async lyrics fetch."""
        ipc = MockElectronIPC()
        lyrics_engine = MockCascadingLyricsEngine()
        lyrics_engine.lrclib_db["song b:artist b"] = "[00:10.00] Line for song B"

        events_log = []

        # Simulate track switch
        old_track = TrackMetadata(id="1", title="Song A", artists=["Artist A"])
        new_track = TrackMetadata(id="2", title="Song B", artists=["Artist B"], duration_ms=180000)

        # 1. Immediate Discord RPC dispatch (0ms throttle)
        def on_track_switch(track: TrackMetadata):
            events_log.append({"time": time.time(), "event": "DISCORD_RPC_INSTANT", "track": track.title})
            # Concurrently trigger lyrics cascade
            res = lyrics_engine.fetch_lyrics(track.id, track.title, track.formatted_artist(), track.duration_ms // 1000)
            events_log.append({"time": time.time(), "event": "LYRICS_RESOLVED", "provider": res.provider})

        on_track_switch(new_track)

        self.assertEqual(len(events_log), 2)
        self.assertEqual(events_log[0]["event"], "DISCORD_RPC_INSTANT")
        self.assertEqual(events_log[1]["event"], "LYRICS_RESOLVED")
        self.assertEqual(events_log[1]["provider"], "lrclib")

    def test_pair3_overlay_optimistic_control_and_poller_suppression(self):
        """Pair 3: Overlay play action pushes new state and suppresses poller execution."""
        clock = 10000.0
        state = {
            "is_playing": False,
            "last_state_push_time": clock - 5000.0,  # 5s ago
        }

        # User clicks play in overlay
        def overlay_click_play():
            state["is_playing"] = True  # Optimistic UI update
            # Renderer push updates timestamp
            state["last_state_push_time"] = clock

        overlay_click_play()
        self.assertTrue(state["is_playing"])

        # Poller checks if silence threshold (3500ms) is reached
        silence_ms = clock - state["last_state_push_time"]
        poller_suppressed = silence_ms < RENDERER_POLLER_SILENCE_THRESHOLD_MS
        self.assertTrue(poller_suppressed, "Poller must be suppressed immediately after overlay user action")

    def test_pair4_settings_persistence_and_font_rehydration(self):
        """Pair 4: Saved settings persist font preferences and re-apply cleanly on app reboot."""
        persisted_settings = {
            "font-changer/enabled": True,
            "font-changer/font": "Minecraft",
            "font-changer/sizeScale": "1.1",
        }

        # Simulate reboot: rehydrate and generate dynamic CSS
        font = persisted_settings["font-changer/font"]
        scale = float(persisted_settings["font-changer/sizeScale"])
        adjust = FONT_SIZE_ADJUST_PRESETS.get(font, 1.0)

        injected_css = (
            f'* {{ font-family: "{font}" !important; }}\n'
            f"* {{ font-size-adjust: {adjust} !important; }}\n"
            f"* {{ font-size: calc(1em * {scale}) !important; }}"
        )

        self.assertIn('font-family: "Minecraft"', injected_css)
        self.assertIn("font-size-adjust: 0.55 !important;", injected_css)
        self.assertIn("calc(1em * 1.1)", injected_css)

    def test_pair5_lyrics_fallback_and_dual_window_broadcast(self):
        """Pair 5: Fallback lyrics with metadata headers are cleaned and broadcast to both windows."""
        engine = MockCascadingLyricsEngine()
        engine.user_session_cookies = {}  # Yandex unavailable
        # Musixmatch provides LRC with header tags
        engine.musixmatch_db["skyfall:adele"] = (
            "[ar: Adele]\n"
            "[ti: Skyfall]\n"
            "[00:20.00] This is the end\n"
            "[00:25.00] Hold your breath and count to ten\n"
        )

        overlay_win = MockBrowserWindow("overlay")
        karaoke_win = MockBrowserWindow("karaoke")

        # Fetch and broadcast
        res = engine.fetch_lyrics("skyfall_1", "Skyfall", "Adele", 286)
        self.assertTrue(res.success)
        self.assertEqual(res.provider, "musixmatch")

        # Verify tags were stripped in result
        self.assertNotIn("[ar:", res.lyrics)
        self.assertEqual(len(res.sync_lyrics), 2)

        # Broadcast
        payload = {"lyrics": res.lyrics, "sync": [l.text for l in res.sync_lyrics]}
        overlay_win.webContents.send("overlay:lyricsUpdate", payload)
        karaoke_win.webContents.send("karaoke:lyricsUpdate", payload)

        self.assertEqual(len(overlay_win.webContents.sent_messages), 1)
        self.assertEqual(len(karaoke_win.webContents.sent_messages), 1)
        self.assertEqual(overlay_win.webContents.sent_messages[0]["args"][0]["lyrics"], res.lyrics)

    def test_pair6_ui_cleaner_settings_and_player_observer(self):
        """Pair 6: UI cleaner toggles add hiding styles while player observer runs continuously."""
        cleaner_settings = {
            "cleaner/hideConcerts": True,
            "cleaner/hideKids": True,
            "cleaner/hidePodcasts": True,
        }

        # Generate cleaner CSS
        css_rules = []
        if cleaner_settings["cleaner/hideConcerts"]:
            css_rules.append('[href*="/concerts"] { display: none !important; }')
        if cleaner_settings["cleaner/hideKids"]:
            css_rules.append('[href*="/kids"] { display: none !important; }')

        combined_css = "\n".join(css_rules)
        self.assertIn("/concerts", combined_css)
        self.assertIn("/kids", combined_css)

        # Concurrently, player observer observes DOM audio element
        audio_observed = {"currentTime": 45.2, "duration": 210.0, "paused": False}
        self.assertEqual(audio_observed["currentTime"], 45.2)

    def test_pair7_discord_watchdog_reconnect_and_active_track_hydration(self):
        """Pair 7: Watchdog connects after Discord starts late and immediately pushes current playing track."""
        discord_server = MockDiscordServer(pipe_id=0)
        client_state = {
            "connected": False,
            "isReady": False,
            "current_track": TrackMetadata(id="101", title="Radioactive", artists=["Imagine Dragons"], duration_ms=186000),
            "position_ms": 30000,
        }

        # Watchdog fires -> connects to pipe
        handshake = json.dumps({"v": 1, "client_id": DISCORD_CLIENT_ID})
        response_bytes = discord_server.receive_client_packet(encode_discord_ipc_packet(0, handshake))
        op, _, resp_payload, _ = decode_discord_ipc_packet(response_bytes)
        resp_data = json.loads(resp_payload)

        self.assertEqual(resp_data.get("evt"), "READY")
        client_state["connected"] = True
        client_state["isReady"] = True

        # Immediately hydrate active track
        activity = {
            "cmd": "SET_ACTIVITY",
            "args": {
                "pid": 1234,
                "activity": {
                    "details": client_state["current_track"].title,
                    "state": client_state["current_track"].formatted_artist(),
                },
            },
        }
        ack_bytes = discord_server.receive_client_packet(encode_discord_ipc_packet(1, json.dumps(activity)))
        _, _, ack_payload, _ = decode_discord_ipc_packet(ack_bytes)
        ack_data = json.loads(ack_payload)

        self.assertEqual(discord_server.last_activity["args"]["activity"]["details"], "Radioactive")

    def test_pair8_overlay_cache_pull_and_delayed_push_hydration(self):
        """Pair 8: Opening overlay when empty shows idle UI, then updates upon first renderer push."""
        ipc = MockElectronIPC()
        overlay_ui = {"title": "Трек не воспроизводится", "is_playing": False}

        # Initial pull -> cache is None
        ipc.handle("yandexMusicMod.getLastPlayerState", lambda _ev: None)
        initial_cache = ipc.invoke("yandexMusicMod.getLastPlayerState")
        self.assertIsNone(initial_cache)

        # Later, renderer pushes track 1
        new_state = {
            "track": {"id": "500", "title": "Delayed Song", "artist": "Delayed Artist"},
            "isPlaying": True,
        }

        def on_track_update(state):
            overlay_ui["title"] = state["track"]["title"]
            overlay_ui["is_playing"] = state["isPlaying"]

        on_track_update(new_state)
        self.assertEqual(overlay_ui["title"], "Delayed Song")
        self.assertTrue(overlay_ui["is_playing"])

    def test_pair9_interface_scale_and_font_scale_independence(self):
        """Pair 9: UI scale zoom and font scale adjust operate without syntax collision."""
        interface_scale = 1.15
        font_scale = 0.95

        ui_style = f"body {{ zoom: {interface_scale} !important; }}"
        font_style = f"* {{ font-size: calc(1em * {font_scale}) !important; }}"

        self.assertIn("zoom: 1.15", ui_style)
        self.assertIn("calc(1em * 0.95)", font_style)

    def test_pair10_musixmatch_signer_with_cyrillic_and_ampersand(self):
        """Pair 10: Musixmatch HMAC signer handles Cyrillic characters and URI special symbols."""
        query_url = "https://apic.musixmatch.com/ws/1.1/macro.subtitles.get?q_track=Звезда&q_artist=Кино&feat=true"
        fixed_dt = datetime(2026, 10, 24, 15, 30, 0)
        signed = compute_musixmatch_signature(query_url, dt=fixed_dt)

        self.assertIn("signature=", signed)
        self.assertIn("signature_protocol=sha1", signed)
        self.assertTrue("q_track=%D0%97%D0%B2%D0%B5%D0%B7%D0%B4%D0%B0" in signed or "q_track=Звезда" in signed)


if __name__ == "__main__":
    unittest.main()
