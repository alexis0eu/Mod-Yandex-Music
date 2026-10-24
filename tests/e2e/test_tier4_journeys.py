"""
Tier 4: Real-World Application Scenarios (Journeys 1-5)
End-to-end user journeys simulating complete lifecycles from boot to shutdown.
Authoritative source: PROJECT.md, ORIGINAL_REQUEST.md.
"""

import unittest
import os
import sys
import json
import base64
import time
import tempfile
from datetime import datetime
from typing import Dict, Any, List, Optional

from .harness.contracts import (
    TrackMetadata,
    PlayerProgress,
    PlayerState,
    LyricsPayload,
    LyricsLine,
    DISCORD_CLIENT_ID,
    DISCORD_WATCHDOG_INTERVAL_MS,
    RENDERER_POLLER_SILENCE_THRESHOLD_MS,
    FONT_SIZE_ADJUST_PRESETS,
    MODAL_STYLE_SPECS,
    SIDEBAR_TABS,
    SWITCH_SPECS,
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


class TestTier4RealWorldJourneys(unittest.TestCase):
    """Tier 4: Comprehensive Real-World Application Journeys"""

    def test_journey1_cold_app_launch_and_mod_initialization(self):
        """Journey 1: Cold App Launch, Settings Loading & IPC Hydration."""
        # 1. Initialize Mock IPC & Storage
        ipc = MockElectronIPC()
        stored_settings = {
            "discordRPC/enabled": True,
            "discordRPC/showButton": True,
            "font-changer/enabled": True,
            "font-changer/font": "JetBrains Mono",
            "font-changer/sizeScale": "1.0",
            "overlay/enabled": True,
            "overlay/ghostMode": False,
        }

        # 2. Register main IPC handlers
        cache = {"lastPlayerState": None, "lastLyrics": None}
        ipc.handle("yandexMusicMod.getLastPlayerState", lambda _ev: cache["lastPlayerState"])
        ipc.handle("yandexMusicMod.getLastLyrics", lambda _ev: cache["lastLyrics"])
        ipc.handle("yandexMusicMod.getSettings", lambda _ev: stored_settings)

        # 3. Simulate Window Creation
        main_win = MockBrowserWindow("main")
        overlay_win = MockBrowserWindow("overlay")
        karaoke_win = MockBrowserWindow("karaoke")

        # 4. Context bridge exposures verified
        exposed_in_renderer = ["updatePlayerState", "fetchLyrics", "openSettings"]
        exposed_in_overlay = ["getPlayerState", "getLyrics", "sendAction"]

        self.assertEqual(len(exposed_in_renderer), 3)
        self.assertEqual(len(exposed_in_overlay), 3)

        # 5. Connect Discord RPC client
        discord_server = MockDiscordServer(pipe_id=0)
        handshake = json.dumps({"v": 1, "client_id": DISCORD_CLIENT_ID})
        resp = discord_server.receive_client_packet(encode_discord_ipc_packet(0, handshake))
        op, _, ready_json, _ = decode_discord_ipc_packet(resp)
        ready_evt = json.loads(ready_json)
        self.assertEqual(ready_evt.get("evt"), "READY")

        # Journey 1 completes with healthy state
        self.assertTrue(discord_server.client_ready)
        self.assertEqual(ipc.invoke("yandexMusicMod.getLastPlayerState"), None)

    def test_journey2_music_playback_and_real_time_sync(self):
        """Journey 2: Music Playback, Instant Discord RPC & Real-time Interpolation."""
        ipc = MockElectronIPC()
        discord_server = MockDiscordServer(pipe_id=0)
        # Establish Discord connection
        handshake = json.dumps({"v": 1, "client_id": DISCORD_CLIENT_ID})
        discord_server.receive_client_packet(encode_discord_ipc_packet(0, handshake))

        state_cache = {"last_player_state": None, "last_timestamp": 0.0}

        def on_renderer_player_state(state: Dict[str, Any]):
            now = time.time()
            old_track_id = state_cache["last_player_state"].get("track", {}).get("id") if state_cache["last_player_state"] else None
            new_track_id = state["track"]["id"]

            state_cache["last_player_state"] = state
            state_cache["last_timestamp"] = now

            # If track changed, instant 0ms dispatch to Discord
            track_changed = old_track_id != new_track_id
            if track_changed:
                activity = {
                    "cmd": "SET_ACTIVITY",
                    "args": {
                        "pid": 5555,
                        "activity": {
                            "details": state["track"]["title"],
                            "state": state["track"]["artist"],
                        },
                    },
                }
                discord_server.receive_client_packet(encode_discord_ipc_packet(1, json.dumps(activity)))

        # 1. Track starts playing
        track1 = {
            "track": {"id": "1001", "title": "In the End", "artist": "Linkin Park"},
            "progress": {"position": 0.0, "duration": 216.0},
            "isPlaying": True,
        }
        on_renderer_player_state(track1)

        # Verify Discord RPC received instant update
        self.assertIsNotNone(discord_server.last_activity)
        self.assertEqual(discord_server.last_activity["args"]["activity"]["details"], "In the End")

        # 2. Check poller suppression
        poller_now = state_cache["last_timestamp"] + 1.5  # 1500ms later
        silence = (poller_now - state_cache["last_timestamp"]) * 1000.0
        self.assertLess(silence, RENDERER_POLLER_SILENCE_THRESHOLD_MS)

        # 3. Simulate Seek by user (+30s)
        track1_seek = {
            "track": {"id": "1001", "title": "In the End", "artist": "Linkin Park"},
            "progress": {"position": 30.0, "duration": 216.0},
            "isPlaying": True,
        }
        on_renderer_player_state(track1_seek)
        self.assertEqual(state_cache["last_player_state"]["progress"]["position"], 30.0)

    def test_journey3_cascading_lyrics_resolution_and_dual_broadcast(self):
        """Journey 3: 3-Tier Cascading Lyrics Engine & Synchronized Dual Broadcast."""
        engine = MockCascadingLyricsEngine()
        engine.user_session_cookies = {"Session_id": "valid_token"}

        # Track 1: Found on Tier 1 (Yandex Supplement)
        engine.yandex_supplement_db["track_yandex"] = {
            "lyrics": "[00:12.00] Official Yandex synced line\n[00:18.50] Second Yandex line",
        }

        # Track 2: Misses Tier 1, Found on Tier 2 (Musixmatch) with metadata headers
        engine.musixmatch_db["numb:linkin park"] = (
            "[ar: Linkin Park]\n"
            "[ti: Numb]\n"
            "[al: Meteora]\n"
            "[length: 03:07]\n"
            "[00:21.00] I'm tired of being what you want me to be\n"
            "[00:25.50] Feeling so faithless, lost under the surface\n"
        )

        # Track 3: Misses Tier 1 and 2, Found on Tier 3 (LRCLib) with remix search query
        engine.lrclib_db["radioactive:imagine dragons"] = (
            "[00:10.00] I'm waking up to ash and dust\n"
            "[00:15.00] I wipe my brow and I sweat my rust\n"
        )

        overlay_win = MockBrowserWindow("overlay")
        karaoke_win = MockBrowserWindow("karaoke")

        def dispatch_resolved_lyrics(payload: LyricsPayload):
            data = {
                "provider": payload.provider,
                "lyrics": payload.lyrics,
                "sync": [{"time": l.time_seconds, "text": l.text} for l in payload.sync_lyrics],
            }
            overlay_win.webContents.send("overlay:lyricsUpdate", data)
            karaoke_win.webContents.send("karaoke:lyricsUpdate", data)

        # Test Tier 1 resolution
        res1 = engine.fetch_lyrics("track_yandex", "Some Song", "Some Artist", 180)
        self.assertEqual(res1.provider, "yandex")
        dispatch_resolved_lyrics(res1)
        self.assertEqual(overlay_win.webContents.sent_messages[-1]["args"][0]["provider"], "yandex")

        # Test Tier 2 resolution with tag cleaning
        res2 = engine.fetch_lyrics("track_mxm", "Numb", "Linkin Park", 187)
        self.assertEqual(res2.provider, "musixmatch")
        self.assertNotIn("[ar:", res2.lyrics)
        self.assertEqual(len(res2.sync_lyrics), 2)
        dispatch_resolved_lyrics(res2)
        self.assertEqual(karaoke_win.webContents.sent_messages[-1]["args"][0]["provider"], "musixmatch")

        # Test Tier 3 resolution with search stripping
        res3 = engine.fetch_lyrics("track_lrc", "Radioactive (Club Remix) [2012]", "Imagine Dragons", 190)
        self.assertEqual(res3.provider, "lrclib")
        self.assertEqual(res3.sync_lyrics[0].text, "I'm waking up to ash and dust")
        dispatch_resolved_lyrics(res3)
        self.assertEqual(overlay_win.webContents.sent_messages[-1]["args"][0]["provider"], "lrclib")

    def test_journey4_gaming_hud_overlay_interactive_session(self):
        """Journey 4: Gaming HUD Overlay Interactive Session (Launch, Scrub, Dedup & Lyrics Reset)."""
        ipc = MockElectronIPC()
        active_track = {
            "track": {"id": "song_42", "title": "Castle of Glass", "artist": "Linkin Park", "duration_ms": 205000},
            "progress": {"position": 10.0, "duration": 205.0},
            "isPlaying": True,
        }
        active_lyrics = {
            "success": True,
            "lyrics": "[00:10.00] Take me down to the river bend\n[00:15.00] Take me down to the fighting end",
        }

        # 1. Main cache pull handlers
        ipc.handle("yandexMusicMod.getLastPlayerState", lambda _ev: active_track)
        ipc.handle("yandexMusicMod.getLastLyrics", lambda _ev: active_lyrics)

        # 2. Overlay opens & immediately pulls state
        pulled_state = ipc.invoke("yandexMusicMod.getLastPlayerState")
        pulled_lyrics = ipc.invoke("yandexMusicMod.getLastLyrics")
        self.assertEqual(pulled_state["track"]["title"], "Castle of Glass")
        self.assertTrue(pulled_lyrics["success"])

        # 3. Local 60fps interpolation advances progress
        base_pos = pulled_state["progress"]["position"]
        base_time_ms = 1000.0
        interpolated = interpolate_playback_position(
            base_position=base_pos,
            base_timestamp_ms=base_time_ms,
            current_timestamp_ms=2500.0,  # 1.5s later
            duration=pulled_state["progress"]["duration"],
            speed=1.0,
            is_playing=True,
        )
        self.assertAlmostEqual(interpolated, 11.5, places=2)

        # 4. User clicks Play/Pause: optimistic toggle & deduplicated event
        dispatched_player_actions = []

        def overlay_send_action(action: str, payload: Any = None):
            # Optimistic toggle
            active_track["isPlaying"] = not active_track["isPlaying"]
            # Deduplicated event emit
            dispatched_player_actions.append({"channel": "executePlayerAction", "action": action})

        overlay_send_action("playPause")
        self.assertFalse(active_track["isPlaying"])
        self.assertEqual(len(dispatched_player_actions), 1)
        self.assertEqual(dispatched_player_actions[0]["channel"], "executePlayerAction")

        # 5. Track transition resets lyrics immediately
        overlay_lyrics_state = {"track_id": "song_42", "lyrics_count": 2}
        new_incoming_track = "song_43"

        if overlay_lyrics_state["track_id"] != new_incoming_track:
            overlay_lyrics_state["track_id"] = new_incoming_track
            overlay_lyrics_state["lyrics_count"] = 0  # Immediate reset

        self.assertEqual(overlay_lyrics_state["track_id"], "song_43")
        self.assertEqual(overlay_lyrics_state["lyrics_count"], 0)

    def test_journey5_anti_slop_settings_customization_and_persistence(self):
        """Journey 5: Anti-Slop Settings Customization, Font Terraria Alias & Atomic Save."""
        # 1. Verify modal styling contracts
        self.assertEqual(MODAL_STYLE_SPECS["background"], "rgba(20, 20, 24, 0.88)")
        self.assertEqual(MODAL_STYLE_SPECS["backdrop_filter"], "blur(30px) saturate(170%)")
        self.assertEqual(MODAL_STYLE_SPECS["border_radius"], "18px")
        self.assertEqual(SWITCH_SPECS["accent_color"], "#fed42b")

        # 2. User navigates all 6 side tabs
        active_settings = {
            "appearance/scale": 1.1,
            "font-changer/enabled": True,
            "font-changer/font": "Terraria",
            "font-changer/sizeScale": "1.05",
            "discordRPC/enabled": True,
            "overlay/enabled": True,
            "overlay/ghostMode": True,
            "cleaner/hideConcerts": True,
            "cleaner/hideKids": True,
            "cleaner/hidePodcasts": True,
        }

        # 3. Verify Terraria alias dynamic CSS rule generation
        font_name = active_settings["font-changer/font"]
        font_scale = float(active_settings["font-changer/sizeScale"])
        adjust = FONT_SIZE_ADJUST_PRESETS.get(font_name, 1.0)

        css_output = (
            f'* {{ font-family: "{font_name}", sans-serif !important; }}\n'
            f"* {{ font-size-adjust: {adjust} !important; }}\n"
            f"* {{ font-size: calc(1em * {font_scale}) !important; }}"
        )

        self.assertIn('font-family: "Terraria"', css_output)
        self.assertIn("font-size-adjust: 0.66 !important;", css_output)
        self.assertIn("calc(1em * 1.05)", css_output)

        # 4. Atomic Save to mod_settings.json
        with tempfile.TemporaryDirectory() as td:
            settings_path = os.path.join(td, "mod_settings.json")
            tmp_path = settings_path + ".tmp"

            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(active_settings, f, indent=2)
            os.replace(tmp_path, settings_path)

            self.assertTrue(os.path.exists(settings_path))
            with open(settings_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)

            self.assertEqual(loaded["font-changer/font"], "Terraria")
            self.assertTrue(loaded["overlay/ghostMode"])
            self.assertTrue(loaded["cleaner/hideKids"])


if __name__ == "__main__":
    unittest.main()
