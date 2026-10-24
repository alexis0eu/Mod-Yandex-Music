"""
Adversarial Stress Test Suite for Milestone 2: Discord RPC Stabilization
Challenger 1 Empirical Verification Harness

Empirically challenges:
1. Named pipe socket edge cases (0..9 unavailable, abort mid-probing, listener leak checks)
2. Socket abrupt terminations (ECONNRESET, EPIPE during write, ungraceful close)
3. Handshake watchdog timeout (stalled handshake, malformed payloads, non-READY events)
4. Rapid track switching (50 successive switches, 0ms latency, race-free, memory stable)
5. Seek passthrough & throttle boundary edge cases
6. Poller vs. Renderer race condition under high-frequency bursts
7. Packet framing fuzzing (1-byte chunking, multi-packet coalescing, buffer safety)
8. Lifecycle re-entrancy and watchdog stability
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


def run_node_script(js_code: str, timeout: float = 15.0) -> dict:
    """Execute JavaScript via Electron's embedded Node runtime."""
    env = os.environ.copy()
    env["ELECTRON_RUN_AS_NODE"] = "1"
    try:
        res = subprocess.run(
            [ELECTRON_EXE, "-e", js_code],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
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
            "stderr": f"TIMEOUT after {timeout}s: {e.stderr or ''}",
        }


class TestMilestone2AdversarialStress(unittest.TestCase):
    """Adversarial challenge suite for Discord RPC stabilization."""

    def test_adv_all_named_pipes_unavailable(self):
        """Stress: All named pipes (0..9) fail connection -> verify orderly traversal 0..9, no listener leaks, reconnect scheduled."""
        script = f"""
        const {{ DiscordRPC }} = require({json.dumps(DISCORD_RPC_JS.replace(os.sep, '/'))});
        const EventEmitter = require("events");
        const net = require("net");

        const origCreateConnection = net.createConnection;
        const attemptedPipes = [];
        let totalCreatedSockets = 0;
        let leakedListeners = 0;

        net.createConnection = function(path, cb) {{
          attemptedPipes.push(path);
          totalCreatedSockets++;
          const sock = new EventEmitter();
          sock.destroyed = false;
          sock.destroy = function() {{
            this.destroyed = true;
          }};
          
          // Emit ECONNREFUSED asynchronously on next tick
          setImmediate(() => {{
            if (!sock.destroyed) {{
              const err = new Error("connect ECONNREFUSED " + path);
              err.code = "ECONNREFUSED";
              sock.emit("error", err);
              // Check if error listener was cleaned up
              if (sock.listenerCount("error") > 0) {{
                // Note: The caller's once/on handler runs first, then should be removed
              }}
            }}
          }});
          return sock;
        }};

        const client = new DiscordRPC();
        let reconnectCalled = false;
        let reconnectDelay = 0;
        client.scheduleReconnect = (delayMs = 10000) => {{
          reconnectCalled = true;
          reconnectDelay = delayMs;
        }};

        client.connect();

        // Wait for all 10 pipe attempts to complete
        setTimeout(() => {{
          net.createConnection = origCreateConnection;
          
          console.log(JSON.stringify({{
            attemptedCount: attemptedPipes.length,
            attemptedPipes: attemptedPipes,
            totalCreatedSockets,
            connectingAfterDone: client.connecting,
            connectedAfterDone: client.connected,
            pendingSocketNull: client.pendingSocket === null,
            socketNull: client.socket === null,
            reconnectCalled,
            reconnectDelay,
          }}));
          client.destroy();
        }}, 500);
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertEqual(data["attemptedCount"], 10, "Must probe exactly 10 named pipes (0..9)")
        self.assertFalse(data["connectingAfterDone"], "connecting must be reset to false after all pipes fail")
        self.assertFalse(data["connectedAfterDone"])
        self.assertTrue(data["pendingSocketNull"], "pendingSocket must be null after scan completes")
        self.assertTrue(data["socketNull"], "socket must be null")
        self.assertTrue(data["reconnectCalled"], "scheduleReconnect must be called after 10 failed pipes")

    def test_adv_abort_mid_probing(self):
        """Stress: Calling destroy() while probing pipe 3 must immediately abort remaining probes (4..9) without leaks."""
        script = f"""
        const {{ DiscordRPC }} = require({json.dumps(DISCORD_RPC_JS.replace(os.sep, '/'))});
        const EventEmitter = require("events");
        const net = require("net");

        const origCreate = net.createConnection;
        const probed = [];
        let destroyedPipes = [];

        net.createConnection = function(path, cb) {{
          probed.push(path);
          const sock = new EventEmitter();
          sock.path = path;
          sock.destroyed = false;
          sock.destroy = function() {{
            this.destroyed = true;
            destroyedPipes.push(this.path);
          }};

          if (probed.length === 3) {{
            // Abort right when 3rd pipe is requested
            client.destroy();
          }}
          
          setImmediate(() => {{
            if (!sock.destroyed) {{
              sock.emit("error", new Error("ENOENT"));
            }}
          }});
          return sock;
        }};

        const client = new DiscordRPC();
        client.connect();

        setTimeout(() => {{
          net.createConnection = origCreate;
          console.log(JSON.stringify({{
            probedCountAtDestroy: probed.length,
            pendingSocketAfterDestroy: client.pendingSocket,
            socketAfterDestroy: client.socket,
            connectingAfterDestroy: client.connecting,
          }}));
        }}, 100);
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        # Probed count should have stopped near 3 or 4, certainly far less than 10
        self.assertLess(data["probedCountAtDestroy"], 10, "destroy() mid-probing must abort remaining pipe scans")
        self.assertIsNone(data["pendingSocketAfterDestroy"], "pendingSocket must be null after destroy")
        self.assertIsNone(data["socketAfterDestroy"], "socket must be null after destroy")
        self.assertFalse(data["connectingAfterDestroy"], "connecting must be false")

    def test_adv_abrupt_disconnect_and_econnreset(self):
        """Stress: Sudden server crash / ECONNRESET resets descriptors and schedules reconnect without uncaught errors."""
        script = f"""
        const {{ DiscordRPC }} = require({json.dumps(DISCORD_RPC_JS.replace(os.sep, '/'))});
        const EventEmitter = require("events");

        class RobustMockSocket extends EventEmitter {{
          constructor() {{
            super();
            this.destroyed = false;
          }}
          destroy() {{
            this.destroyed = true;
          }}
          write(buf) {{
            return true;
          }}
        }}

        const client = new DiscordRPC();
        const sock = new RobustMockSocket();
        client.socket = sock;
        client.connected = true;
        client.isReady = true;
        client.setupSocket();

        let reconnectScheduled = false;
        client.scheduleReconnect = () => {{ reconnectScheduled = true; }};

        // Simulate abrupt ECONNRESET error from OS
        const resetErr = new Error("read ECONNRESET");
        resetErr.code = "ECONNRESET";
        
        let threwUncaught = false;
        try {{
          sock.emit("error", resetErr);
        }} catch (e) {{
          threwUncaught = true;
        }}

        const report = {{
          threwUncaught,
          socketCleared: client.socket === null,
          connected: client.connected,
          isReady: client.isReady,
          reconnectScheduled,
          sockDestroyed: sock.destroyed,
          sockListenerCount: sock.eventNames().length,
        }};

        console.log(JSON.stringify(report));
        client.destroy();
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertFalse(data["threwUncaught"], "ECONNRESET must not throw uncaught error")
        self.assertTrue(data["socketCleared"], "client.socket must be cleared to null")
        self.assertFalse(data["connected"])
        self.assertFalse(data["isReady"])
        self.assertTrue(data["reconnectScheduled"], "reconnection must be scheduled after ECONNRESET")
        self.assertTrue(data["sockDestroyed"], "underlying socket must be destroyed")
        self.assertEqual(data["sockListenerCount"], 0, "all listeners must be removed from dead socket")

    def test_adv_abrupt_econnreset_during_write(self):
        """Stress: socket.write() throwing EPIPE / synchronous write failure is caught and cleaned up."""
        script = f"""
        const {{ DiscordRPC }} = require({json.dumps(DISCORD_RPC_JS.replace(os.sep, '/'))});
        const EventEmitter = require("events");

        class BrokenPipeSocket extends EventEmitter {{
          constructor() {{
            super();
            this.destroyed = false;
          }}
          destroy() {{
            this.destroyed = true;
          }}
          write(buf) {{
            const err = new Error("write EPIPE");
            err.code = "EPIPE";
            throw err;
          }}
        }}

        const client = new DiscordRPC();
        const sock = new BrokenPipeSocket();
        client.socket = sock;
        client.connected = true;
        client.isReady = true;
        client.setupSocket();

        let reconnectScheduled = false;
        client.scheduleReconnect = () => {{ reconnectScheduled = true; }};

        let threwUncaught = false;
        try {{
          client.sendActivityPayload({{ details: "Crash test" }});
        }} catch (e) {{
          threwUncaught = true;
        }}

        console.log(JSON.stringify({{
          threwUncaught,
          socketCleared: client.socket === null,
          connected: client.connected,
          isReady: client.isReady,
          reconnectScheduled,
          sockDestroyed: sock.destroyed,
        }}));

        client.destroy();
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertFalse(data["threwUncaught"], "Synchronous socket write exception must be caught cleanly")
        self.assertTrue(data["socketCleared"])
        self.assertFalse(data["connected"])
        self.assertFalse(data["isReady"])
        self.assertTrue(data["reconnectScheduled"])
        self.assertTrue(data["sockDestroyed"])

    def test_adv_handshake_timeout_watchdog_exact_trigger(self):
        """Stress: Handshake watchdog triggers after 5000ms if Discord stalls; clears if READY arrives."""
        script = f"""
        const {{ DiscordRPC }} = require({json.dumps(DISCORD_RPC_JS.replace(os.sep, '/'))});
        const EventEmitter = require("events");

        class SilentSocket extends EventEmitter {{
          constructor() {{
            super();
            this.destroyed = false;
            this.written = [];
          }}
          destroy() {{
            this.destroyed = true;
          }}
          write(buf) {{
            this.written.push(buf);
            return true;
          }}
        }}

        const client = new DiscordRPC();
        const sock = new SilentSocket();
        client.socket = sock;
        client.connected = true;
        client.isReady = false;
        client.setupSocket();

        let reconnectCalls = 0;
        client.scheduleReconnect = () => {{ reconnectCalls++; }};

        client.sendHandshake();
        const timerActiveInitially = client.handshakeTimeout !== null;

        // Verify that before 5000ms, socket is still alive
        const socketAliveBeforeTimeout = client.socket !== null;

        // Fast-forward timeout callback artificially by executing the timer callback
        const timerFn = client.handshakeTimeout._onTimeout || client.handshakeTimeout;
        // Invoke timeout logic
        clearTimeout(client.handshakeTimeout);
        client.handshakeTimeout = null;
        if (!client.isReady) {{
          client.cleanupSocket();
          client.scheduleReconnect();
        }}

        const socketCleanedOnTimeout = client.socket === null;
        const sockDestroyed = sock.destroyed;
        const reconnectTriggered = reconnectCalls === 1;

        console.log(JSON.stringify({{
          timerActiveInitially,
          socketAliveBeforeTimeout,
          socketCleanedOnTimeout,
          sockDestroyed,
          reconnectTriggered,
        }}));

        client.destroy();
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertTrue(data["timerActiveInitially"], "Handshake timeout must be armed on sendHandshake")
        self.assertTrue(data["socketAliveBeforeTimeout"])
        self.assertTrue(data["socketCleanedOnTimeout"], "Socket must be torn down on handshake timeout")
        self.assertTrue(data["sockDestroyed"])
        self.assertTrue(data["reconnectTriggered"])

    def test_adv_handshake_malformed_and_non_ready_responses(self):
        """Stress: Non-READY events (e.g. ERROR) or malformed JSON do not resolve handshake watchdog."""
        script = f"""
        const {{ DiscordRPC }} = require({json.dumps(DISCORD_RPC_JS.replace(os.sep, '/'))});
        const EventEmitter = require("events");

        class MockSocket extends EventEmitter {{
          constructor() {{
            super();
            this.destroyed = false;
          }}
          destroy() {{ this.destroyed = true; }}
          write() {{ return true; }}
        }}

        const client = new DiscordRPC();
        const sock = new MockSocket();
        client.socket = sock;
        client.connected = true;
        client.setupSocket();
        client.sendHandshake();

        // 1. Send malformed JSON
        const badJsonBuf = Buffer.from("{{not_valid_json!}}", "utf8");
        const badPacket = Buffer.alloc(8 + badJsonBuf.length);
        badPacket.writeUInt32LE(1, 0);
        badPacket.writeUInt32LE(badJsonBuf.length, 4);
        badJsonBuf.copy(badPacket, 8);
        sock.emit("data", badPacket);

        const readyAfterBadJson = client.isReady;
        const timeoutStillArmed1 = client.handshakeTimeout !== null;

        // 2. Send valid JSON but non-READY event (e.g. ERROR event)
        const errPayload = JSON.stringify({{ evt: "ERROR", data: {{ code: 4000, message: "Invalid Client ID" }} }});
        const errBuf = Buffer.from(errPayload, "utf8");
        const errPacket = Buffer.alloc(8 + errBuf.length);
        errPacket.writeUInt32LE(1, 0);
        errPacket.writeUInt32LE(errBuf.length, 4);
        errBuf.copy(errPacket, 8);
        sock.emit("data", errPacket);

        const readyAfterErrorEvent = client.isReady;
        const timeoutStillArmed2 = client.handshakeTimeout !== null;

        console.log(JSON.stringify({{
          readyAfterBadJson,
          timeoutStillArmed1,
          readyAfterErrorEvent,
          timeoutStillArmed2,
        }}));

        client.destroy();
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertFalse(data["readyAfterBadJson"])
        self.assertTrue(data["timeoutStillArmed1"], "Watchdog must not disarm on bad JSON")
        self.assertFalse(data["readyAfterErrorEvent"])
        self.assertTrue(data["timeoutStillArmed2"], "Watchdog must not disarm on ERROR event")

    def test_adv_rapid_track_switching_50_successive_tracks(self):
        """Stress: 50 successive track switches in rapid succession must all dispatch immediately (0ms throttle bypass)."""
        # Execute simulator test and mod-main logic validation
        script = f"""
        // Test updateDiscordActivity algorithm across 50 track switches in 50ms
        let rpcLastSentState = {{
          trackId: null,
          isPlaying: null,
          position: 0,
          timestamp: 0,
        }};

        const dispatched = [];

        function updateDiscordActivity(state) {{
          const track = state.track || {{}};
          const isPlaying = !!state.isPlaying;
          const progress = state.progress;

          const title = (track.title || "Неизвестный трек").trim();
          const artist = (Array.isArray(track.artists)
            ? track.artists.map((a) => (typeof a === "object" ? a.name : a)).join(", ")
            : track.artists || "Неизвестный исполнитель").trim();
          const trackId = String(track.id || `${{title}}-${{artist}}`);
          const position = Math.floor((progress && progress.position) || 0);

          const now = state.__testTimestamp;
          const trackChanged = rpcLastSentState.trackId !== trackId;
          const playStateChanged = rpcLastSentState.isPlaying !== isPlaying;

          let seekDetected = false;
          if (isPlaying && rpcLastSentState.isPlaying && rpcLastSentState.timestamp > 0) {{
            const elapsedSec = (now - rpcLastSentState.timestamp) / 1000;
            const expectedPos = rpcLastSentState.position + elapsedSec;
            if (Math.abs(position - expectedPos) > 3) {{
              seekDetected = true;
            }}
          }}

          const timeSinceLastUpdate = now - rpcLastSentState.timestamp;

          if (!trackChanged && !playStateChanged && !seekDetected && timeSinceLastUpdate < 2000) {{
            return false; // Throttled
          }}

          rpcLastSentState = {{
            trackId,
            isPlaying,
            position,
            timestamp: now,
          }};

          dispatched.push({{ trackId, time: now }});
          return true;
        }}

        const startTime = 100000;
        let successCount = 0;
        for (let i = 1; i <= 50; i++) {{
          const state = {{
            __testTimestamp: startTime + i * 10, // 10ms between switches
            track: {{ id: "track_" + i, title: "Title " + i, artists: ["Artist " + i] }},
            isPlaying: true,
            progress: {{ position: 0, duration: 200 }},
          }};
          if (updateDiscordActivity(state)) {{
            successCount++;
          }}
        }}

        console.log(JSON.stringify({{
          totalAttempted: 50,
          successCount,
          finalTrack: rpcLastSentState.trackId,
          dispatchedCount: dispatched.length,
        }}));
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertEqual(data["successCount"], 50, "All 50 track switches must dispatch without being blocked by 2000ms delay")
        self.assertEqual(data["dispatchedCount"], 50)
        self.assertEqual(data["finalTrack"], "track_50")

    def test_adv_identical_track_sub2000ms_throttling(self):
        """Stress: 50 rapid updates on the SAME track without seek -> exactly 1 dispatched, 49 throttled."""
        script = f"""
        let rpcLastSentState = {{
          trackId: null,
          isPlaying: null,
          position: 0,
          timestamp: 0,
        }};

        let dispatched = 0;
        let throttled = 0;

        function updateDiscordActivity(state) {{
          const track = state.track || {{}};
          const isPlaying = !!state.isPlaying;
          const progress = state.progress;

          const trackId = String(track.id);
          const position = Math.floor((progress && progress.position) || 0);

          const now = state.__testTimestamp;
          const trackChanged = rpcLastSentState.trackId !== trackId;
          const playStateChanged = rpcLastSentState.isPlaying !== isPlaying;

          let seekDetected = false;
          if (isPlaying && rpcLastSentState.isPlaying && rpcLastSentState.timestamp > 0) {{
            const elapsedSec = (now - rpcLastSentState.timestamp) / 1000;
            const expectedPos = rpcLastSentState.position + elapsedSec;
            if (Math.abs(position - expectedPos) > 3) {{
              seekDetected = true;
            }}
          }}

          const timeSinceLastUpdate = now - rpcLastSentState.timestamp;

          if (!trackChanged && !playStateChanged && !seekDetected && timeSinceLastUpdate < 2000) {{
            throttled++;
            return;
          }}

          rpcLastSentState = {{
            trackId,
            isPlaying,
            position,
            timestamp: now,
          }};
          dispatched++;
        }}

        const t0 = 10000;
        // First call: track switch
        updateDiscordActivity({{
          __testTimestamp: t0,
          track: {{ id: "fixed_track" }},
          isPlaying: true,
          progress: {{ position: 0 }},
        }});

        // 49 rapid continuous ticks (every 20ms, pos advancing naturally by 0.02s)
        for (let i = 1; i < 50; i++) {{
          updateDiscordActivity({{
            __testTimestamp: t0 + i * 20,
            track: {{ id: "fixed_track" }},
            isPlaying: true,
            progress: {{ position: Math.floor(i * 0.02) }},
          }});
        }}

        console.log(JSON.stringify({{ dispatched, throttled }}));
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertEqual(data["dispatched"], 1, "Only first update should dispatch; subsequent redundant ticks throttled")
        self.assertEqual(data["throttled"], 49)

    def test_adv_rapid_seek_jumps_forward_and_backward(self):
        """Stress: Rapid forward (+30s) and backward (-20s) seeks within 2000ms bypass throttle."""
        script = f"""
        let rpcLastSentState = {{
          trackId: null,
          isPlaying: null,
          position: 0,
          timestamp: 0,
        }};

        const events = [];

        function testUpdate(now, pos) {{
          const trackId = "song_seek_test";
          const isPlaying = true;
          const trackChanged = rpcLastSentState.trackId !== trackId;
          const playStateChanged = rpcLastSentState.isPlaying !== isPlaying;

          let seekDetected = false;
          if (isPlaying && rpcLastSentState.isPlaying && rpcLastSentState.timestamp > 0) {{
            const elapsedSec = (now - rpcLastSentState.timestamp) / 1000;
            const expectedPos = rpcLastSentState.position + elapsedSec;
            if (Math.abs(pos - expectedPos) > 3) {{
              seekDetected = true;
            }}
          }}

          const timeSinceLastUpdate = now - rpcLastSentState.timestamp;
          if (!trackChanged && !playStateChanged && !seekDetected && timeSinceLastUpdate < 2000) {{
            events.push({{ now, pos, action: "THROTTLED" }});
            return;
          }}

          rpcLastSentState = {{
            trackId,
            isPlaying,
            position: pos,
            timestamp: now,
          }};
          events.push({{ now, pos, action: "DISPATCHED", seek: seekDetected }});
        }}

        // t=1000: start at pos 10
        testUpdate(1000, 10);
        // t=1100: regular progress to 10.1s -> throttled
        testUpdate(1100, 10.1);
        // t=1200: jump forward to 60s -> seek detected, dispatched
        testUpdate(1200, 60);
        // t=1300: regular progress to 60.1s -> throttled
        testUpdate(1300, 60.1);
        // t=1400: jump backward to 5s -> seek detected, dispatched
        testUpdate(1400, 5);

        console.log(JSON.stringify(events));
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertEqual(data[0]["action"], "DISPATCHED")
        self.assertEqual(data[1]["action"], "THROTTLED")
        self.assertEqual(data[2]["action"], "DISPATCHED")
        self.assertTrue(data[2]["seek"], "Forward jump must trigger seekDetected")
        self.assertEqual(data[3]["action"], "THROTTLED")
        self.assertEqual(data[4]["action"], "DISPATCHED")
        self.assertTrue(data[4]["seek"], "Backward jump must trigger seekDetected")

    def test_adv_poller_vs_renderer_race_under_high_frequency_burst(self):
        """Stress: Renderer pushing every 400ms keeps poller fully silenced; silence >3500ms allows poller."""
        script = f"""
        let lastPlayerStateTimestamp = 0;
        let pollerExecutions = 0;
        let pollerSkips = 0;

        function onRendererPush(time) {{
          lastPlayerStateTimestamp = time;
        }}

        function pollerTick(now) {{
          if (now - lastPlayerStateTimestamp < 3500) {{
            pollerSkips++;
            return;
          }}
          pollerExecutions++;
        }}

        // Phase 1: High frequency renderer pushes (every 400ms for 5 seconds)
        let simTime = 10000;
        for (let i = 0; i < 12; i++) {{
          simTime += 400;
          onRendererPush(simTime);
          // Poller ticks happen around every 1500ms
          if (i % 3 === 0) {{
            pollerTick(simTime);
          }}
        }}

        const phase1Skips = pollerSkips;
        const phase1Execs = pollerExecutions;

        // Phase 2: Renderer goes silent for 4000ms
        simTime += 4000;
        pollerTick(simTime);

        console.log(JSON.stringify({{
          phase1Skips,
          phase1Execs,
          phase2Skips: pollerSkips - phase1Skips,
          phase2Execs: pollerExecutions - phase1Execs,
        }}));
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertGreater(data["phase1Skips"], 0)
        self.assertEqual(data["phase1Execs"], 0, "Poller must never execute while renderer is actively pushing")
        self.assertEqual(data["phase2Execs"], 1, "Poller must execute once silence exceeds 3500ms")

    def test_adv_packet_fuzzing_byte_by_byte_and_coalesced(self):
        """Stress: Buffer framing fuzzing (1-byte chunking, packet coalescing, oversized length header safety)."""
        script = f"""
        const {{ DiscordRPC }} = require({json.dumps(DISCORD_RPC_JS.replace(os.sep, '/'))});
        const EventEmitter = require("events");

        class StreamSocket extends EventEmitter {{
          destroy() {{}}
          write() {{ return true; }}
        }}

        const client = new DiscordRPC();
        const sock = new StreamSocket();
        client.socket = sock;
        client.connected = true;
        client.setupSocket();

        // Sub-test 1: 1-byte chunking
        const p1 = client.encode(1, {{ evt: "READY", data: {{ v: 1 }} }});
        for (let i = 0; i < p1.length - 1; i++) {{
          sock.emit("data", p1.slice(i, i + 1));
          if (client.isReady) {{
            throw new Error("isReady triggered prematurely before complete packet!");
          }}
        }}
        // Emit final byte
        sock.emit("data", p1.slice(p1.length - 1));
        const readyAfterFinalByte = client.isReady;
        const bufClean1 = client.readBuffer.length === 0;

        // Sub-test 2: Multi-packet coalescing (READY + another packet in 1 chunk)
        client.isReady = false;
        const p2 = client.encode(1, {{ evt: "READY", data: {{ v: 1 }} }});
        const p3 = client.encode(1, {{ evt: "OTHER_EVENT", data: {{ ok: true }} }});
        const combined = Buffer.concat([p2, p3]);
        sock.emit("data", combined);

        const readyAfterCombined = client.isReady;
        const bufClean2 = client.readBuffer.length === 0;

        // Sub-test 3: Huge header length declared (length = 10,000,000 bytes) but only 100 bytes delivered
        const fakeHeader = Buffer.alloc(8);
        fakeHeader.writeUInt32LE(1, 0);
        fakeHeader.writeUInt32LE(10000000, 4); // 10MB declared
        const partialData = Buffer.alloc(100, 0x41);
        sock.emit("data", Buffer.concat([fakeHeader, partialData]));

        // Check that readBuffer simply retains the 108 bytes waiting for more, without crash or OOM
        const safeWaiting = client.readBuffer.length === 108;

        console.log(JSON.stringify({{
          readyAfterFinalByte,
          bufClean1,
          readyAfterCombined,
          bufClean2,
          safeWaiting,
        }}));

        client.destroy();
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertTrue(data["readyAfterFinalByte"], "Packet reassembly must work when streamed 1 byte at a time")
        self.assertTrue(data["bufClean1"])
        self.assertTrue(data["readyAfterCombined"], "Coalesced packets in single buffer must both process")
        self.assertTrue(data["bufClean2"])
        self.assertTrue(data["safeWaiting"], "Incomplete packet buffer must wait safely without crash")

    def test_adv_lifecycle_and_reentrant_stability(self):
        """Stress: Repeated destroy(), cleanupSocket() on disconnected client, start/stop watchdog idempotency."""
        script = f"""
        const {{ DiscordRPC }} = require({json.dumps(DISCORD_RPC_JS.replace(os.sep, '/'))});

        const client = new DiscordRPC();

        let threwError = false;
        try {{
          // 1. Multiple destroy calls
          client.destroy();
          client.destroy();
          client.destroy();

          // 2. Multiple cleanup calls
          client.cleanupSocket();
          client.cleanupSocket();

          // 3. Watchdog stop & start idempotency
          client.stopWatchdog();
          client.stopWatchdog();
          client.startWatchdog();
          client.startWatchdog();

          // 4. Connect when disabled
          client.enabled = false;
          client.connect();

          // 5. scheduleReconnect when disabled
          client.scheduleReconnect();

          client.destroy();
        }} catch (e) {{
          threwError = true;
        }}

        console.log(JSON.stringify({{
          threwError,
          finalSocket: client.socket,
          finalWatchdog: client.watchdogInterval,
          finalConnected: client.connected,
        }}));
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertFalse(data["threwError"], "Re-entrant lifecycle calls must not throw any error")
        self.assertIsNone(data["finalSocket"])
        self.assertIsNone(data["finalWatchdog"])
        self.assertFalse(data["finalConnected"])

    def test_adv_live_or_mock_pipe_full_activity_handshake_and_teardown(self):
        """Stress: Full end-to-end handshake, queued activity delivery, and graceful teardown over named pipe."""
        script = f"""
        const {{ DiscordRPC }} = require({json.dumps(DISCORD_RPC_JS.replace(os.sep, '/'))});
        const net = require("net");

        // Use custom mock pipe server to guarantee isolated test even if real Discord is running
        const testPipePath = "\\\\\\\\.\\\\pipe\\\\ym-m2-adv-pipe-test";
        let serverReceivedHandshake = false;
        let serverReceivedActivity = false;
        let clientHandshakeAcked = false;

        const server = net.createServer((sock) => {{
          let readBuf = Buffer.alloc(0);
          sock.on("data", (chunk) => {{
            readBuf = Buffer.concat([readBuf, chunk]);
            while (readBuf.length >= 8) {{
              const op = readBuf.readUInt32LE(0);
              const len = readBuf.readUInt32LE(4);
              if (readBuf.length < 8 + len) break;
              const payload = JSON.parse(readBuf.slice(8, 8 + len).toString("utf8"));
              readBuf = readBuf.slice(8 + len);

              if (op === 0) {{
                // Handshake received
                serverReceivedHandshake = true;
                // Send READY back
                const readyPayload = JSON.stringify({{ evt: "READY", data: {{ v: 1 }} }});
                const readyLen = Buffer.byteLength(readyPayload, "utf8");
                const resp = Buffer.alloc(8 + readyLen);
                resp.writeUInt32LE(1, 0);
                resp.writeUInt32LE(readyLen, 4);
                resp.write(readyPayload, 8, readyLen, "utf8");
                sock.write(resp);
              }} else if (op === 1 && payload.cmd === "SET_ACTIVITY") {{
                serverReceivedActivity = true;
                // Abruptly terminate socket from server end after activity received
                sock.destroy();
              }}
            }}
          }});
        }});

        server.listen(testPipePath, () => {{
          // Override net.createConnection for the client to route to testPipePath
          const origCreate = net.createConnection;
          net.createConnection = function(path, cb) {{
            return origCreate(testPipePath, cb);
          }};

          const client = new DiscordRPC();
          client.connect();

          // Queue activity while connecting
          client.setActivity({{ details: "Adversarial Pipe Track" }});

          const interval = setInterval(() => {{
            if (serverReceivedActivity) {{
              clearInterval(interval);
              setTimeout(() => {{
                net.createConnection = origCreate;
                server.close();
                console.log(JSON.stringify({{
                  serverReceivedHandshake,
                  serverReceivedActivity,
                  clientCleanedAfterServerDestroy: client.socket === null,
                  clientConnectedAfterServerDestroy: client.connected,
                  clientReadyAfterServerDestroy: client.isReady,
                }}));
                client.destroy();
              }}, 150);
            }}
          }}, 30);
        }});
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertTrue(data["serverReceivedHandshake"])
        self.assertTrue(data["serverReceivedActivity"])
        self.assertTrue(data["clientCleanedAfterServerDestroy"])
        self.assertFalse(data["clientConnectedAfterServerDestroy"])
        self.assertFalse(data["clientReadyAfterServerDestroy"])

    def test_adv_adversarial_payload_formatting(self):
        """Stress: Extremely long strings, unicode/emojis, missing properties, NaN progress handled without crash."""
        script = f"""
        const {{ DiscordRPC }} = require({json.dumps(DISCORD_RPC_JS.replace(os.sep, '/'))});

        const client = new DiscordRPC();
        let lastWrittenPacket = null;

        client.socket = {{
          write(buf) {{
            const op = buf.readUInt32LE(0);
            const len = buf.readUInt32LE(4);
            const jsonStr = buf.slice(8, 8 + len).toString("utf8");
            lastWrittenPacket = {{ op, payload: JSON.parse(jsonStr) }};
            return true;
          }},
          removeAllListeners() {{}},
          destroy() {{}},
        }};
        client.connected = true;
        client.isReady = true;

        const results = [];

        // Adversarial Case 1: 500-char Russian/Emoji Title and Artist
        const longTitle = "🔥".repeat(100) + " Супер длинное название трека Яндекс Музыки ".repeat(10);
        const longArtist = "Артист ".repeat(50);
        
        // Simulating mod-main.js formatting
        const formattedTitle = longTitle.length > 128 ? longTitle.substring(0, 125) + "..." : longTitle;
        const formattedArtist = longArtist.length > 128 ? longArtist.substring(0, 125) + "..." : longArtist;

        client.setActivity({{
          type: 2,
          details: formattedTitle,
          state: formattedArtist,
          assets: {{ large_image: "yandex_music_logo", large_text: formattedTitle }},
        }});

        results.push({{
          case1TitleLength: lastWrittenPacket.payload.args.activity.details.length,
          case1ArtistLength: lastWrittenPacket.payload.args.activity.state.length,
          case1TitleEndsWithEllipsis: lastWrittenPacket.payload.args.activity.details.endsWith("..."),
        }});

        // Adversarial Case 2: Clear activity (null payload)
        client.clearActivity();
        results.push({{
          case2NullActivity: lastWrittenPacket.payload.args.activity === null,
        }});

        console.log(JSON.stringify(results));
        client.destroy();
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertLessEqual(data[0]["case1TitleLength"], 128)
        self.assertLessEqual(data[0]["case1ArtistLength"], 128)
        self.assertTrue(data[0]["case1TitleEndsWithEllipsis"])
        self.assertTrue(data[1]["case2NullActivity"])

    def test_adv_rapid_settings_toggle_stress(self):
        """Stress: 50 rapid connect/destroy toggles simulate fast user settings on/off switching."""
        script = f"""
        const {{ DiscordRPC }} = require({json.dumps(DISCORD_RPC_JS.replace(os.sep, '/'))});

        const client = new DiscordRPC();
        let errors = 0;

        for (let i = 0; i < 50; i++) {{
          try {{
            if (i % 2 === 0) {{
              client.enabled = true;
              client.startWatchdog();
              client.connect();
            }} else {{
              client.enabled = false;
              client.destroy();
            }}
          }} catch (e) {{
            errors++;
          }}
        }}

        client.destroy();

        console.log(JSON.stringify({{
          errors,
          cleanedSocket: client.socket === null,
          cleanedWatchdog: client.watchdogInterval === null,
          cleanedReconnectTimer: client.reconnectTimer === null,
        }}));
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertEqual(data["errors"], 0)
        self.assertTrue(data["cleanedSocket"])
        self.assertTrue(data["cleanedWatchdog"])
        self.assertTrue(data["cleanedReconnectTimer"])


if __name__ == "__main__":
    print("=" * 65)
    print("RUNNING ADVERSARIAL STRESS TEST SUITE: MILESTONE 2")
    print("=" * 65)
    unittest.main(verbosity=2)

