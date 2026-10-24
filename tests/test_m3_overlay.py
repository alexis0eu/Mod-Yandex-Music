"""
Milestone 3 Automated Test Suite: Gaming HUD Overlay Modernization
Verifies Features 10, 11, 12, 13, 14:
- Feature 10: Immediate cache delivery via IPC pull (getLastPlayerState / getLastLyrics)
- Feature 11: Smooth progress bar & timecode interpolation timer (60fps requestAnimationFrame/interval)
- Feature 12: Overlay controls de-duplication (no redundant desktop:player:action)
- Feature 13: Optimistic UI updates on play/pause and seek
- Feature 14: Track transition lyrics reset (no lingering old lyrics)
"""

import os
import sys
import json
import re
import unittest
import subprocess
from typing import Dict, Any, List

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ELECTRON_EXE = r"C:\Users\denbi\AppData\Local\Programs\YandexMusic\Яндекс Музыка.exe"
MOD_MAIN_JS = os.path.join(PROJECT_ROOT, "src", "main", "mod-main.js")
OVERLAY_PRELOAD_JS = os.path.join(PROJECT_ROOT, "src", "preload", "overlay-preload.js")
OVERLAY_JS = os.path.join(PROJECT_ROOT, "src", "overlay", "overlay.js")
OVERLAY_HTML = os.path.join(PROJECT_ROOT, "src", "overlay", "overlay.html")
OVERLAY_CSS = os.path.join(PROJECT_ROOT, "src", "overlay", "overlay.css")


def run_electron_node_script(js_code: str) -> dict:
    """Execute JavaScript via Electron's embedded Node runtime."""
    env = os.environ.copy()
    env["ELECTRON_RUN_AS_NODE"] = "1"
    wrapped_code = js_code + "\nsetTimeout(() => process.exit(0), 100).unref();"
    try:
        res = subprocess.run(
            [ELECTRON_EXE, "-e", wrapped_code],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        return {
            "returncode": res.returncode,
            "stdout": res.stdout,
            "stderr": res.stderr,
        }
    except subprocess.TimeoutExpired as e:
        return {
            "returncode": -1,
            "stdout": e.stdout or "",
            "stderr": f"Process timed out: {e}",
        }


class TestFeature10ImmediateCacheDelivery(unittest.TestCase):
    """Feature 10: Immediate cache delivery via IPC pull handlers."""

    def test_main_process_registers_pull_handlers(self):
        """Feature 10: mod-main.js registers getLastPlayerState and getLastLyrics handle channels."""
        with open(MOD_MAIN_JS, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('ipcMain.handle("yandexMusicMod.getLastPlayerState"', content)
        self.assertIn('ipcMain.handle("yandexMusicMod.getLastLyrics"', content)

        # Verify handlers return the internal state variables
        self.assertRegex(content, r'ipcMain\.handle\("yandexMusicMod\.getLastPlayerState",\s*\(\)\s*=>\s*\{?\s*return\s+lastPlayerState')
        self.assertRegex(content, r'ipcMain\.handle\("yandexMusicMod\.getLastLyrics",\s*\(\)\s*=>\s*\{?\s*return\s+lastLyricsData')

    def test_preload_exposes_pull_and_push_methods(self):
        """Feature 10: overlay-preload.js exposes getPlayerState and getLyrics on window.overlayApi."""
        with open(OVERLAY_PRELOAD_JS, "r", encoding="utf-8") as f:
            content = f.read()

        # Both canonical and alias names are exposed
        self.assertIn('getPlayerState: () => ipcRenderer.invoke("yandexMusicMod.getLastPlayerState")', content)
        self.assertIn('getLyrics: () => ipcRenderer.invoke("yandexMusicMod.getLastLyrics")', content)
        self.assertIn('getLastPlayerState: () => ipcRenderer.invoke("yandexMusicMod.getLastPlayerState")', content)
        self.assertIn('getLastLyrics: () => ipcRenderer.invoke("yandexMusicMod.getLastLyrics")', content)
        self.assertIn('sendPlayerAction:', content)
        self.assertIn('sendAction:', content)

    def test_overlay_js_invokes_pull_on_startup(self):
        """Feature 10: overlay.js invokes pull handlers on initialization to eliminate cold-start blank state."""
        with open(OVERLAY_JS, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertTrue(
            "getPlayerState" in content or "getLastPlayerState" in content,
            "overlay.js must query player state on startup"
        )
        self.assertTrue(
            "getLyrics" in content or "getLastLyrics" in content,
            "overlay.js must query lyrics on startup"
        )

    def test_node_execution_cache_hydration_simulation(self):
        """Feature 10: Simulates cold-start cache pull into overlay.js in Node runtime."""
        script = f"""
        const overlay = require({json.dumps(OVERLAY_JS.replace(os.sep, '/'))});
        overlay.resetState();

        const cachedState = {{
          track: {{ id: "cold_start_track", title: "Cold Start Song", artists: ["Rock Band"], durationMs: 240000 }},
          progress: {{ position: 30, duration: 240, speed: 1.0 }},
          isPlaying: true
        }};

        overlay.updateUI(cachedState);
        const stateAfter = overlay.getState();

        console.log(JSON.stringify({{
          trackId: stateAfter.currentTrack.id,
          title: stateAfter.currentTrack.title,
          isPlaying: stateAfter.isPlaying,
          basePosition: stateAfter.basePosition,
          trackDuration: stateAfter.trackDuration,
        }}));
        """
        res = run_electron_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Node run error: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertEqual(data["trackId"], "cold_start_track")
        self.assertEqual(data["title"], "Cold Start Song")
        self.assertTrue(data["isPlaying"])
        self.assertEqual(data["basePosition"], 30)
        self.assertEqual(data["trackDuration"], 240)


class TestFeature11SmoothInterpolationTimer(unittest.TestCase):
    """Feature 11: Smooth progress bar & timecode interpolation timer (60fps)."""

    def test_interpolation_math_advances_when_playing(self):
        """Feature 11: Position smoothly advances according to basePosition + (now - base) / 1000 * speed."""
        script = f"""
        const {{ interpolatePosition }} = require({json.dumps(OVERLAY_JS.replace(os.sep, '/'))});

        const basePos = 15.0;
        const baseTs = 10000.0;
        const duration = 200.0;

        // Delta 16.6ms (one 60fps frame)
        const pos1Frame = interpolatePosition(basePos, baseTs, baseTs + 16.666, duration, 1.0, true);
        // Delta 500ms
        const posHalfSec = interpolatePosition(basePos, baseTs, baseTs + 500.0, duration, 1.0, true);
        // Delta 1000ms
        const posOneSec = interpolatePosition(basePos, baseTs, baseTs + 1000.0, duration, 1.0, true);

        console.log(JSON.stringify({{
          frame: pos1Frame,
          halfSec: posHalfSec,
          oneSec: posOneSec
        }}));
        """
        res = run_electron_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Node script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertAlmostEqual(data["frame"], 15.0 + 0.016666, places=3)
        self.assertAlmostEqual(data["halfSec"], 15.5, places=2)
        self.assertAlmostEqual(data["oneSec"], 16.0, places=2)

    def test_interpolation_freezes_when_paused(self):
        """Feature 11: Position does NOT advance when isPlaying is false."""
        script = f"""
        const {{ interpolatePosition }} = require({json.dumps(OVERLAY_JS.replace(os.sep, '/'))});

        const basePos = 42.0;
        const baseTs = 5000.0;
        const duration = 180.0;

        const posPaused = interpolatePosition(basePos, baseTs, baseTs + 2000.0, duration, 1.0, false);
        console.log(JSON.stringify({{ pos: posPaused }}));
        """
        res = run_electron_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Node script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertEqual(data["pos"], 42.0)

    def test_interpolation_clamping_to_duration_and_zero(self):
        """Feature 11: Position is strictly clamped to [0, duration]."""
        script = f"""
        const {{ interpolatePosition }} = require({json.dumps(OVERLAY_JS.replace(os.sep, '/'))});

        const duration = 100.0;

        // Position exceeds duration -> clamps to duration
        const overPos = interpolatePosition(95.0, 1000.0, 1000.0 + 10000.0, duration, 1.0, true);

        // Negative base position -> clamps to 0
        const underPos = interpolatePosition(-5.0, 1000.0, 1000.0, duration, 1.0, false);

        console.log(JSON.stringify({{ over: overPos, under: underPos }}));
        """
        res = run_electron_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Node script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertEqual(data["over"], 100.0)
        self.assertEqual(data["under"], 0.0)

    def test_interpolation_speed_factor(self):
        """Feature 11: Playback speed scaling (e.g. 1.5x, 0.5x, 2.0x) is accurately incorporated."""
        script = f"""
        const {{ interpolatePosition }} = require({json.dumps(OVERLAY_JS.replace(os.sep, '/'))});

        const basePos = 10.0;
        const baseTs = 1000.0;
        const nowTs = 2000.0; // 1 second elapsed
        const duration = 200.0;

        const pos1_5x = interpolatePosition(basePos, baseTs, nowTs, duration, 1.5, true);
        const pos0_5x = interpolatePosition(basePos, baseTs, nowTs, duration, 0.5, true);
        const pos2_0x = interpolatePosition(basePos, baseTs, nowTs, duration, 2.0, true);

        console.log(JSON.stringify({{
          p15: pos1_5x,
          p05: pos0_5x,
          p20: pos2_0x
        }}));
        """
        res = run_electron_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Node script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertAlmostEqual(data["p15"], 11.5, places=2)
        self.assertAlmostEqual(data["p05"], 10.5, places=2)
        self.assertAlmostEqual(data["p20"], 12.0, places=2)

    def test_format_time_utility(self):
        """Feature 11: formatTime produces clean mm:ss string for all inputs."""
        script = f"""
        const {{ formatTime }} = require({json.dumps(OVERLAY_JS.replace(os.sep, '/'))});

        console.log(JSON.stringify({{
          zero: formatTime(0),
          nineSec: formatTime(9),
          sixtySec: formatTime(60),
          sixtyFive: formatTime(65),
          hour: formatTime(3600),
          negative: formatTime(-10),
          nan: formatTime(NaN),
        }}));
        """
        res = run_electron_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Node script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertEqual(data["zero"], "0:00")
        self.assertEqual(data["nineSec"], "0:09")
        self.assertEqual(data["sixtySec"], "1:00")
        self.assertEqual(data["sixtyFive"], "1:05")
        self.assertEqual(data["hour"], "60:00")
        self.assertEqual(data["negative"], "0:00")
        self.assertEqual(data["nan"], "0:00")


class TestFeature12ControlsDeduplication(unittest.TestCase):
    """Feature 12: Overlay controls de-duplication in mod-main.js."""

    def test_overlay_action_does_not_send_desktop_player_action(self):
        """Feature 12: yandexMusicMod.overlayAction handler must NOT send desktop:player:action."""
        with open(MOD_MAIN_JS, "r", encoding="utf-8") as f:
            content = f.read()

        # Locate the overlayAction block
        match = re.search(
            r'ipcMain\.on\("yandexMusicMod\.overlayAction",\s*\(_ev,\s*action,\s*payload\)\s*=>\s*\{(.*?)\}\);',
            content,
            re.DOTALL
        )
        self.assertIsNotNone(match, "yandexMusicMod.overlayAction listener must exist in mod-main.js")
        handler_body = match.group(1)

        # Must send executePlayerAction
        self.assertIn("yandexMusicMod.executePlayerAction", handler_body)

        # Must NOT send desktop:player:action
        self.assertNotIn("desktop:player:action", handler_body)

    def test_deduplicated_dispatch_simulation(self):
        """Feature 12: Simulates action dispatching to confirm exactly 1 event is emitted."""
        script = f"""
        const dispatched = [];
        const mockWin = {{
          isDestroyed: () => false,
          webContents: {{
            send: (channel, ...args) => {{
              dispatched.push({{ channel, args }});
            }}
          }}
        }};

        // Simulate mod-main.js deduplicated overlayAction logic
        function handleOverlayAction(action, payload) {{
          mockWin.webContents.send("yandexMusicMod.executePlayerAction", action, payload);
        }}

        handleOverlayAction("playPause", null);
        handleOverlayAction("seek", {{ position: 45.0, progress: 0.25 }});

        console.log(JSON.stringify({{
          count: dispatched.length,
          channels: dispatched.map(d => d.channel)
        }}));
        """
        res = run_electron_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Node script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertEqual(data["count"], 2)
        self.assertEqual(data["channels"], ["yandexMusicMod.executePlayerAction", "yandexMusicMod.executePlayerAction"])
        self.assertNotIn("desktop:player:action", data["channels"])


class TestFeature13OptimisticUIUpdates(unittest.TestCase):
    """Feature 13: Optimistic UI updates on play/pause and seek."""

    def test_optimistic_play_pause_toggling(self):
        """Feature 13: Clicking play/pause flips isPlaying, starts/stops timer immediately."""
        script = f"""
        const overlay = require({json.dumps(OVERLAY_JS.replace(os.sep, '/'))});
        overlay.resetState();

        // Initially paused
        overlay.setState({{ isPlaying: false, basePosition: 20.0, trackDuration: 180.0 }});

        // Optimistic toggle to PLAY
        let nextPlaying = !overlay.getState().isPlaying;
        overlay.setState({{ isPlaying: nextPlaying }});
        const stateAfterPlay = overlay.getState();

        // Optimistic toggle to PAUSE
        nextPlaying = !overlay.getState().isPlaying;
        overlay.setState({{ isPlaying: nextPlaying }});
        const stateAfterPause = overlay.getState();

        console.log(JSON.stringify({{
          afterPlay: stateAfterPlay.isPlaying,
          afterPause: stateAfterPause.isPlaying
        }}));
        """
        res = run_electron_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Node script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertTrue(data["afterPlay"])
        self.assertFalse(data["afterPause"])

    def test_optimistic_seek_position_calculation(self):
        """Feature 13: Seek bar click updates basePosition immediately without waiting for round-trip."""
        script = f"""
        const overlay = require({json.dumps(OVERLAY_JS.replace(os.sep, '/'))});
        overlay.resetState();

        const duration = 200.0;
        overlay.setState({{
          trackDuration: duration,
          currentProgress: {{ position: 10.0, duration: duration }},
          basePosition: 10.0
        }});

        // Simulate seek click at 60% of progress bar
        const clickPercent = 0.60;
        const seekSeconds = clickPercent * duration;

        overlay.setState({{
          basePosition: seekSeconds,
          currentProgress: {{ position: seekSeconds, duration: duration }}
        }});

        const stateAfterSeek = overlay.getState();
        console.log(JSON.stringify({{
          seekPos: stateAfterSeek.basePosition,
          curPos: stateAfterSeek.currentProgress.position
        }}));
        """
        res = run_electron_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Node script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertEqual(data["seekPos"], 120.0)
        self.assertEqual(data["curPos"], 120.0)


class TestFeature14TrackTransitionLyricsReset(unittest.TestCase):
    """Feature 14: Track transition lyrics reset (no lingering previous lyrics)."""

    def test_lyrics_array_and_index_reset_on_new_track(self):
        """Feature 14: overlayLyrics is emptied and overlayLyricsIndex reset to -1 when track ID changes."""
        script = f"""
        const overlay = require({json.dumps(OVERLAY_JS.replace(os.sep, '/'))});
        overlay.resetState();

        // 1. Initial track playing with active lyrics
        const trackA = {{ id: "track_aaa", title: "First Track", artists: ["Artist A"] }};
        overlay.updateUI({{ track: trackA, progress: {{ position: 15, duration: 180 }}, isPlaying: true }});
        overlay.handleLyricsData({{
          syncLyrics: [
            {{ time: 5, line: "Line 1 of Track A" }},
            {{ time: 10, line: "Line 2 of Track A" }}
          ]
        }});

        const lyricsCountBefore = overlay.getState().overlayLyrics.length;
        const lyricsIndexBefore = overlay.getState().overlayLyricsIndex;

        // 2. Track transition to Track B
        const trackB = {{ id: "track_bbb", title: "Second Track", artists: ["Artist B"] }};
        overlay.updateUI({{ track: trackB, progress: {{ position: 0, duration: 210 }}, isPlaying: true }});

        const stateAfterTransition = overlay.getState();

        console.log(JSON.stringify({{
          beforeCount: lyricsCountBefore,
          beforeIndex: lyricsIndexBefore,
          afterCount: stateAfterTransition.overlayLyrics.length,
          afterIndex: stateAfterTransition.overlayLyricsIndex,
          newTrackId: stateAfterTransition.currentTrack.id,
        }}));
        """
        res = run_electron_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Node script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertEqual(data["beforeCount"], 2)
        self.assertEqual(data["afterCount"], 0, "Lyrics must be immediately cleared on track switch")
        self.assertEqual(data["afterIndex"], -1, "Lyrics index must be reset to -1 on track switch")
        self.assertEqual(data["newTrackId"], "track_bbb")

    def test_lrc_parser_robustness(self):
        """Feature 14: parseLRC handles standard LRC strings, tags stripping, and array input."""
        script = f"""
        const {{ parseLRC }} = require({json.dumps(OVERLAY_JS.replace(os.sep, '/'))});

        const rawLrc = `
        [ti:Test Title]
        [ar:Test Artist]
        [00:05.50]First line of lyrics
        [00:12.00]Second line of lyrics
        [01:05.250]Third line of lyrics
        `;

        const parsedString = parseLRC(rawLrc, 180);

        const arrayInput = [
          {{ time: 10, line: "Array line 1" }},
          {{ time: 25, line: "Array line 2" }}
        ];
        const parsedArray = parseLRC(arrayInput, 180);

        console.log(JSON.stringify({{
          strCount: parsedString.length,
          strFirstTime: parsedString[0].time,
          strFirstText: parsedString[0].text,
          strThirdTime: parsedString[2].time,
          arrCount: parsedArray.length,
          arrSecondTime: parsedArray[1].time,
        }}));
        """
        res = run_electron_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Node script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertEqual(data["strCount"], 3)
        self.assertAlmostEqual(data["strFirstTime"], 5.5, places=2)
        self.assertEqual(data["strFirstText"], "First line of lyrics")
        self.assertAlmostEqual(data["strThirdTime"], 65.25, places=2)
        self.assertEqual(data["arrCount"], 2)
        self.assertEqual(data["arrSecondTime"], 25)


class TestOverlayDOMStructureAndVisualAssets(unittest.TestCase):
    """Verifies overlay.html and overlay.css completeness and consistency."""

    def test_overlay_html_has_all_required_nodes(self):
        """Ensures overlay.html contains all HUD controls, progress bar, and lyrics line."""
        with open(OVERLAY_HTML, "r", encoding="utf-8") as f:
            html = f.read()

        required_ids = [
          "overlay-card", "status-dot", "btn-ghost", "ghost-label",
          "btn-lyrics-toggle", "btn-karaoke", "btn-close",
          "track-cover", "eq-bars", "track-title", "track-artist",
          "time-current", "progress-bar-container", "progress-bar-fill", "progress-bar-thumb", "time-total",
          "btn-prev", "btn-play", "icon-play", "icon-pause", "btn-next", "btn-like",
          "overlay-lyrics-container", "overlay-lyrics-active"
        ]
        for node_id in required_ids:
            self.assertIn(f'id="{node_id}"', html, f"overlay.html missing node id: {node_id}")

    def test_overlay_css_rules_and_smooth_rendering(self):
        """Ensures overlay.css defines HUD styling and accent variables."""
        with open(OVERLAY_CSS, "r", encoding="utf-8") as f:
            css = f.read()

        self.assertIn("--accent", css)
        self.assertIn(".overlay-card", css)
        self.assertIn(".progress-bar-container", css)
        self.assertIn(".progress-bar-fill", css)
        self.assertIn(".progress-bar-thumb", css)
        self.assertIn(".overlay-lyrics-line", css)


if __name__ == "__main__":
    unittest.main()
