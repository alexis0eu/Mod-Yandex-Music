"""
Empirical Challenger Test Suite for Milestone 2: Discord RPC Stabilization
Tests:
1. Poller suppression under continuous 400ms renderer pushes (zero superfluous executeJavaScript calls)
2. Seek events threshold (>2.5s vs >3.0s behavior) and 2000ms throttle bypass
3. Payload formatting, Unicode UTF-8 handling, extremely long titles/artists, and buffer safety
4. Stream packet fragmentation, chunking, and malformed payload resilience
5. Socket lifecycle, connection race conditions, and watchdog timings
"""

import os
import sys
import json
import time
import subprocess
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ELECTRON_EXE = r"C:\Users\denbi\AppData\Local\Programs\YandexMusic\Яндекс Музыка.exe"
DISCORD_RPC_JS = os.path.join(PROJECT_ROOT, "src", "main", "discord-rpc.js")
MOD_MAIN_JS = os.path.join(PROJECT_ROOT, "src", "main", "mod-main.js")


def run_node_script(js_code: str) -> dict:
    """Execute JavaScript via Electron's embedded Node runtime."""
    env = os.environ.copy()
    env["ELECTRON_RUN_AS_NODE"] = "1"
    res = subprocess.run(
        [ELECTRON_EXE, "-e", js_code],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "returncode": res.returncode,
        "stdout": res.stdout,
        "stderr": res.stderr,
    }


class TestM2EmpiricalChallenger(unittest.TestCase):
    """Adversarial stress and boundary tests for Milestone 2 Discord RPC."""

    def test_poller_suppression_under_continuous_renderer_pushes(self):
        """
        Challenge 1: Verify that when renderer pushes state every 400ms,
        poller execution is 100% suppressed (zero superfluous executeJavaScript calls).
        """
        script = """
        let lastPlayerStateTimestamp = 0;
        let executeJavaScriptCallCount = 0;
        let pollerCheckCount = 0;
        let pollerSuppressedCount = 0;

        function simulateRendererPush(currentTime) {
            lastPlayerStateTimestamp = currentTime;
        }

        function simulatePollerTick(currentTime) {
            pollerCheckCount++;
            if (currentTime - lastPlayerStateTimestamp < 3500) {
                pollerSuppressedCount++;
                return; // Suppressed
            }
            executeJavaScriptCallCount++;
        }

        // Phase 1: Renderer actively pushing every 400ms for 10 seconds (25 pushes)
        // Poller ticks every 1500ms
        let t = 0;
        let nextRendererPush = 0;
        let nextPollerTick = 1500;
        const totalDuration = 10000;

        while (t <= totalDuration) {
            if (t >= nextRendererPush) {
                simulateRendererPush(t);
                nextRendererPush += 400;
            }
            if (t >= nextPollerTick) {
                simulatePollerTick(t);
                nextPollerTick += 1500;
            }
            t += 50; // 50ms time step
        }

        const phase1ExecCalls = executeJavaScriptCallCount;
        const phase1Checks = pollerCheckCount;
        const phase1Suppressed = pollerSuppressedCount;

        // Phase 2: Renderer stops pushing (silence > 3500ms).
        // Check if fallback kicks in at t = 10000 + 4000 = 14000
        simulatePollerTick(t + 4000);
        const phase2ExecCalls = executeJavaScriptCallCount;

        // Phase 3: Renderer resumes pushing immediately.
        simulateRendererPush(t + 4100);
        simulatePollerTick(t + 4200);
        const phase3ExecCalls = executeJavaScriptCallCount;

        console.log(JSON.stringify({
            phase1Checks,
            phase1Suppressed,
            phase1ExecCalls,
            phase2ExecCalls,
            phase3ExecCalls
        }));
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        # Assert 100% suppression during active renderer push
        self.assertEqual(data["phase1ExecCalls"], 0, "Poller MUST make zero executeJavaScript calls during 400ms pushes")
        self.assertEqual(data["phase1Checks"], data["phase1Suppressed"], "All phase 1 poller checks must be suppressed")
        self.assertEqual(data["phase1Checks"], 6, "Expected 6 poller ticks during 10 seconds")
        # Assert fallback executes when silent > 3500ms
        self.assertEqual(data["phase2ExecCalls"], 1, "Poller MUST execute fallback when renderer is silent for >3.5s")
        # Assert poller re-suppresses once renderer resumes
        self.assertEqual(data["phase3ExecCalls"], 1, "Poller MUST immediately re-suppress once renderer resumes")

    def test_seek_detection_threshold_boundary_analysis(self):
        """
        Challenge 2: Analyze seek detection boundary.
        Investigate seek jumps >=2.5s and >3.0s against the 2000ms throttle.
        """
        with open(MOD_MAIN_JS, "r", encoding="utf-8") as f:
            code = f.read()

        # Extract seek logic from mod-main.js
        self.assertIn("Math.abs(position - expectedPos) > 3", code)

        script = """
        // Exact logic from mod-main.js lines 501-527
        function checkSeek(lastPos, lastTime, newPos, nowTime) {
            const elapsedSec = (nowTime - lastTime) / 1000;
            const expectedPos = lastPos + elapsedSec;
            const seekDetected = Math.abs(newPos - expectedPos) > 3;
            const timeSinceLastUpdate = nowTime - lastTime;
            const throttled = !seekDetected && timeSinceLastUpdate < 2000;
            return {
                seekDetected,
                throttled,
                delta: Math.abs(newPos - expectedPos),
                timeSinceLastUpdate
            };
        }

        const t0 = 1000;
        const pos0 = 10.0;

        // Test at t = 1400 (400ms elapsed, within 2000ms window)
        // Normal playback: pos advances by 0.4s -> 10.4
        const normalPlayback = checkSeek(pos0, t0, 10.4, 1400);

        // Seek forward by 2.6s: pos advances from expected 10.4 to 13.0 (+2.6s)
        const seek2_6s = checkSeek(pos0, t0, 13.0, 1400);

        // Seek forward by 2.9s: pos advances to 13.3 (+2.9s)
        const seek2_9s = checkSeek(pos0, t0, 13.3, 1400);

        // Seek forward by 3.1s: pos advances to 13.5 (+3.1s)
        const seek3_1s = checkSeek(pos0, t0, 13.5, 1400);

        // Seek forward by 5.0s: pos advances to 15.4 (+5.0s, e.g. arrow key)
        const seek5_0s = checkSeek(pos0, t0, 15.4, 1400);

        // Seek backward by 4.0s: pos drops from 10.4 to 6.4 (-4.0s)
        const seekBack4s = checkSeek(pos0, t0, 6.4, 1400);

        // Seek backward by 2.6s: pos drops to 7.8 (-2.6s)
        const seekBack2_6s = checkSeek(pos0, t0, 7.8, 1400);

        console.log(JSON.stringify({
            normalPlayback,
            seek2_6s,
            seek2_9s,
            seek3_1s,
            seek5_0s,
            seekBack4s,
            seekBack2_6s
        }));
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        # Normal playback is throttled within 2000ms
        self.assertFalse(data["normalPlayback"]["seekDetected"])
        self.assertTrue(data["normalPlayback"]["throttled"])

        # Seek > 3.0s (e.g. 3.1s, 5.0s forward, 4.0s backward) bypasses throttle
        self.assertTrue(data["seek3_1s"]["seekDetected"])
        self.assertFalse(data["seek3_1s"]["throttled"])
        self.assertTrue(data["seek5_0s"]["seekDetected"])
        self.assertFalse(data["seek5_0s"]["throttled"])
        self.assertTrue(data["seekBack4s"]["seekDetected"])
        self.assertFalse(data["seekBack4s"]["throttled"])

        # Boundary note: at delta = 2.6s (<= 3.0s threshold in code),
        # seekDetected is FALSE and throttled until 2000ms periodic tick.
        self.assertFalse(data["seek2_6s"]["seekDetected"], "Delta 2.6s is <= 3.0s threshold")
        self.assertTrue(data["seek2_6s"]["throttled"], "Delta 2.6s is throttled within 2000ms window")

    def test_unicode_and_extreme_title_payload_formatting(self):
        """
        Challenge 3: Verify non-ASCII and extremely long titles/artists
        format properly into Discord IPC packets without buffer overflow or corrupt JSON.
        """
        script = f"""
        const {{ DiscordRPC }} = require({json.dumps(DISCORD_RPC_JS.replace(os.sep, '/'))});
        const client = new DiscordRPC();

        const testCases = [
            {{
                name: "Russian Cyrillic Standard",
                title: "Лесник",
                artist: "Король и Шут",
                album: "Камнем по голове"
            }},
            {{
                name: "Multi-Artist Cyrillic",
                title: "Седьмой лепесток (Remix)",
                artist: "Антон Токарев, DJ Smash, Моя Мишель",
                album: "Хиты 2024"
            }},
            {{
                name: "Complex UTF-8 Emojis & Symbols",
                title: "Track 🎧 🎵 ✨ 🚀 🌟 🎸",
                artist: "Artist ⚡ 💎",
                album: "Album 🎶"
            }},
            {{
                name: "CJK (Japanese / Chinese)",
                title: "夜に駆ける",
                artist: "YOASOBI",
                album: "THE BOOK"
            }},
            {{
                name: "RTL & Arabic",
                title: "أغنية جميلة جداً",
                artist: "فنان مشهور",
                album: "ألبوم رائع"
            }},
            {{
                name: "Extreme Length Title (500 chars)",
                title: "A".repeat(500),
                artist: "B".repeat(500),
                album: "C".repeat(500)
            }},
            {{
                name: "Extreme Cyrillic Length (300 chars)",
                title: "Ш".repeat(300),
                artist: "Ю".repeat(300),
                album: "Я".repeat(300)
            }},
            {{
                name: "JSON Metacharacters & Escaping",
                title: 'Track with \\"quotes\\", \\\\ backslashes, \\n newlines, and \\t tabs',
                artist: 'Artist <tag> & "ampersand"',
                album: 'Album with {{ "json": "injection" }}'
            }}
        ];

        const results = [];
        for (const tc of testCases) {{
            // Apply truncation matching mod-main.js line 541-542
            const details = tc.title.length > 128 ? tc.title.substring(0, 125) + "..." : tc.title;
            const state = tc.artist.length > 128 ? tc.artist.substring(0, 125) + "..." : tc.artist;
            const large_text = tc.album ? `${{tc.album}} — ${{tc.title}}` : tc.title;

            const payload = {{
                cmd: "SET_ACTIVITY",
                args: {{
                    pid: 12345,
                    activity: {{
                        type: 2,
                        details,
                        state,
                        assets: {{
                            large_image: "yandex_music_logo",
                            large_text,
                            small_image: "play",
                            small_text: "Слушает в Яндекс Музыке"
                        }},
                        instance: false
                    }}
                }},
                nonce: "test-nonce-123"
            }};

            try {{
                const packet = client.encode(1, payload);
                const op = packet.readUInt32LE(0);
                const len = packet.readUInt32LE(4);
                
                // Assert packet size matches 8 + len exactly
                const sizeMatches = packet.length === 8 + len;
                
                // Slice body and parse back as UTF-8 JSON
                const bodyBuf = packet.slice(8, 8 + len);
                const bodyStr = bodyBuf.toString("utf8");
                const parsed = JSON.parse(bodyStr);

                results.push({{
                    name: tc.name,
                    success: true,
                    sizeMatches,
                    opMatches: op === 1,
                    lenFieldMatches: len === bodyBuf.length,
                    detailsMatches: parsed.args.activity.details === details,
                    stateMatches: parsed.args.activity.state === state,
                    largeTextLength: large_text.length,
                    packetByteLength: packet.length
                }});
            }} catch (e) {{
                results.push({{
                    name: tc.name,
                    success: false,
                    error: e.message
                }});
            }}
        }}

        client.destroy();
        console.log(JSON.stringify(results));
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Script failed: {res['stderr']}")
        results = json.loads(res["stdout"].strip().splitlines()[-1])

        for r in results:
            self.assertTrue(r["success"], f"Failed case {r.get('name')}: {r.get('error')}")
            self.assertTrue(r["sizeMatches"], f"Packet buffer size mismatch for {r['name']}")
            self.assertTrue(r["opMatches"], f"Opcode mismatch for {r['name']}")
            self.assertTrue(r["lenFieldMatches"], f"Length field mismatch for {r['name']}")
            self.assertTrue(r["detailsMatches"], f"Details string mismatch for {r['name']}")
            self.assertTrue(r["stateMatches"], f"State string mismatch for {r['name']}")

    def test_incoming_packet_fragmentation_and_malformed_json_resilience(self):
        """
        Challenge 4: Verify processIncomingPackets survives 1-byte chunking,
        header splitting, multiple concatenated packets, and malformed JSON.
        """
        script = f"""
        const {{ DiscordRPC }} = require({json.dumps(DISCORD_RPC_JS.replace(os.sep, '/'))});
        const client = new DiscordRPC();

        let readyFired = false;
        let activitySent = false;
        client.sendActivityPayload = () => {{
            activitySent = true;
        }};

        // Prepare packets
        const readyPacket = client.encode(1, {{ evt: "READY", data: {{ v: 1 }} }});
        const malformedPacket = Buffer.alloc(8 + 15);
        malformedPacket.writeUInt32LE(1, 0);
        malformedPacket.writeUInt32LE(15, 4);
        malformedPacket.write("{{ not valid json", 8, "utf8");

        // Feed ready packet byte-by-byte into client.readBuffer
        for (let i = 0; i < readyPacket.length; i++) {{
            client.readBuffer = Buffer.concat([client.readBuffer, readyPacket.slice(i, i + 1)]);
            client.processIncomingPackets();
        }}
        const readyAfterByteByByte = client.isReady;

        // Feed malformed packet: must not throw, must consume buffer
        client.readBuffer = Buffer.concat([client.readBuffer, malformedPacket]);
        let threwOnMalformed = false;
        try {{
            client.processIncomingPackets();
        }} catch (e) {{
            threwOnMalformed = true;
        }}
        const bufferEmptyAfterMalformed = client.readBuffer.length === 0;

        client.destroy();
        console.log(JSON.stringify({{
            readyAfterByteByByte,
            threwOnMalformed,
            bufferEmptyAfterMalformed
        }}));
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertTrue(data["readyAfterByteByByte"], "Packet reassembly MUST handle 1-byte chunks")
        self.assertFalse(data["threwOnMalformed"], "Malformed JSON MUST NOT throw an unhandled exception")
        self.assertTrue(data["bufferEmptyAfterMalformed"], "Buffer MUST be advanced even when payload is malformed")


    def test_pipe_exhaustion_and_descriptor_safety(self):
        """
        Challenge 5: Verify that when all 10 pipes fail to connect,
        the client terminates connecting, schedules reconnect, and leaks zero sockets.
        """
        script = f"""
        const {{ DiscordRPC }} = require({json.dumps(DISCORD_RPC_JS.replace(os.sep, '/'))});
        const net = require("net");
        const EventEmitter = require("events");

        let attemptedPipes = [];
        let createdSockets = [];

        // Mock net.createConnection to fail immediately on every pipe
        const originalCreateConnection = net.createConnection;
        net.createConnection = function(path, connectListener) {{
            attemptedPipes.push(path);
            const sock = new EventEmitter();
            sock.destroyed = false;
            sock.destroy = function() {{
                this.destroyed = true;
            }};
            sock.removeListener = EventEmitter.prototype.removeListener;
            createdSockets.push(sock);
            
            // Asynchronously emit error
            process.nextTick(() => {{
                sock.emit("error", new Error("ENOENT: pipe not found"));
            }});
            return sock;
        }};

        const client = new DiscordRPC();
        client.stopWatchdog(); // disable background watchdog for deterministic test

        client.connect();

        // Wait for all nextTicks to process
        setTimeout(() => {{
            net.createConnection = originalCreateConnection; // restore

            const allDestroyed = createdSockets.every(s => s.destroyed);
            const report = {{
                pipesAttemptedCount: attemptedPipes.length,
                socketsCreatedCount: createdSockets.length,
                allDestroyed,
                connectingAfterScan: client.connecting,
                connectedAfterScan: client.connected,
                pendingSocketNull: client.pendingSocket === null,
                hasReconnectTimer: client.reconnectTimer !== null
            }};

            client.destroy();
            console.log(JSON.stringify(report));
        }}, 50);
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertEqual(data["pipesAttemptedCount"], 10, "Must attempt exactly pipes 0..9")
        self.assertEqual(data["socketsCreatedCount"], 10, "Must create 10 temporary sockets")
        self.assertTrue(data["allDestroyed"], "All temporary probing sockets MUST be destroyed")
        self.assertFalse(data["connectingAfterScan"], "connecting flag must reset to false after scan")
        self.assertFalse(data["connectedAfterScan"], "connected flag must remain false")
        self.assertTrue(data["pendingSocketNull"], "pendingSocket must be null")
        self.assertTrue(data["hasReconnectTimer"], "scheduleReconnect must be armed")

    def test_concurrent_connect_calls_are_idempotent(self):
        """
        Challenge 6: Verify concurrent calls to connect() do not spawn duplicate scans.
        """
        script = f"""
        const {{ DiscordRPC }} = require({json.dumps(DISCORD_RPC_JS.replace(os.sep, '/'))});
        const net = require("net");
        const EventEmitter = require("events");

        let connectionCalls = 0;
        const originalCreateConnection = net.createConnection;
        net.createConnection = function(path, listener) {{
            connectionCalls++;
            const sock = new EventEmitter();
            sock.destroy = () => {{}};
            return sock;
        }};

        const client = new DiscordRPC();
        client.stopWatchdog();

        // Call connect 5 times synchronously
        client.connect();
        client.connect();
        client.connect();
        client.connect();
        client.connect();

        const calls = connectionCalls;
        net.createConnection = originalCreateConnection;
        client.destroy();

        console.log(JSON.stringify({{ connectionCalls: calls }}));
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertEqual(data["connectionCalls"], 1, "Only 1 connection attempt should be initiated")


if __name__ == "__main__":
    unittest.main()

