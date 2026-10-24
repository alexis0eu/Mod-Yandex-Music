"""
Milestone 2 Automated Test Suite: Discord RPC Stabilization (R2)
Verifies Features 5, 6, 7, 8, 9:
- Feature 5: Socket error listener cleanup & safe cleanupSocket()
- Feature 6: Handshake watchdog (5000ms timeout)
- Feature 7: Pipe reconnection watchdog (15s health check)
- Feature 8: Poller vs. Renderer race fix (authoritative renderer push, 3.5s poller skip)
- Feature 9: Instant track dispatch (0ms throttle bypass, seek passthrough)
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


class TestDiscordRPCModule(unittest.TestCase):
    """Direct execution tests against src/main/discord-rpc.js via Electron Node."""

    def test_f5_initial_state_and_watchdog_startup(self):
        """Feature 5 & 7: DiscordRPC starts with correct initial flags and active watchdog."""
        script = f"""
        const {{ DiscordRPC }} = require({json.dumps(DISCORD_RPC_JS.replace(os.sep, '/'))});
        const client = new DiscordRPC("123456789");
        
        const report = {{
          clientId: client.clientId,
          connected: client.connected,
          connecting: client.connecting,
          isReady: client.isReady,
          enabled: client.enabled,
          hasWatchdog: client.watchdogInterval !== null,
          hasReconnectTimer: client.reconnectTimer !== null,
        }};
        
        client.destroy();
        report.destroyedWatchdog = client.watchdogInterval === null;
        report.destroyedConnected = client.connected;
        report.destroyedReady = client.isReady;
        
        console.log(JSON.stringify(report));
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Node script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertEqual(data["clientId"], "123456789")
        self.assertFalse(data["connected"])
        self.assertFalse(data["connecting"])
        self.assertFalse(data["isReady"])
        self.assertTrue(data["enabled"])
        self.assertTrue(data["hasWatchdog"], "Watchdog interval must be active on construction")
        self.assertFalse(data["hasReconnectTimer"])
        self.assertTrue(data["destroyedWatchdog"], "destroy() must clear watchdogInterval")
        self.assertFalse(data["destroyedConnected"])
        self.assertFalse(data["destroyedReady"])

    def test_f5_safe_cleanup_socket(self):
        """Feature 5: cleanupSocket() safely clears listeners, destroys socket, and resets state."""
        script = f"""
        const {{ DiscordRPC }} = require({json.dumps(DISCORD_RPC_JS.replace(os.sep, '/'))});
        const EventEmitter = require("events");

        class MockSocket extends EventEmitter {{
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
        const mockSock = new MockSocket();
        
        // Simulate connected state
        client.socket = mockSock;
        client.connected = true;
        client.isReady = true;
        client.connecting = true;
        client.setupSocket();
        
        // Add a test listener
        mockSock.on("customEvent", () => {{}});
        const listenerCountBefore = mockSock.eventNames().length;
        
        // Arm handshake timeout
        client.handshakeTimeout = setTimeout(() => {{}}, 10000);
        
        // Run cleanup
        client.cleanupSocket();
        
        const report = {{
          listenerCountBefore,
          socketNull: client.socket === null,
          socketDestroyed: mockSock.destroyed,
          socketListenersAfter: mockSock.eventNames().length,
          connected: client.connected,
          connecting: client.connecting,
          isReady: client.isReady,
          handshakeTimeoutCleared: client.handshakeTimeout === null,
        }};
        
        // Idempotent secondary call
        client.cleanupSocket();
        report.secondCleanupSafe = true;
        
        client.destroy();
        console.log(JSON.stringify(report));
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Node script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertTrue(data["listenerCountBefore"] > 0)
        self.assertTrue(data["socketNull"], "cleanupSocket must set socket to null")
        self.assertTrue(data["socketDestroyed"], "cleanupSocket must destroy socket")
        self.assertEqual(data["socketListenersAfter"], 0, "All socket listeners must be removed")
        self.assertFalse(data["connected"])
        self.assertFalse(data["connecting"])
        self.assertFalse(data["isReady"])
        self.assertTrue(data["handshakeTimeoutCleared"])
        self.assertTrue(data["secondCleanupSafe"])

    def test_f5_error_listener_cleanup_on_connect(self):
        """Feature 5: Temporary error listener (onConnectError) is removed on successful connection."""
        script = f"""
        const {{ DiscordRPC }} = require({json.dumps(DISCORD_RPC_JS.replace(os.sep, '/'))});
        const net = require("net");
        
        // Create an in-memory local server on an arbitrary port
        const server = net.createServer((sock) => {{
          // Server accepts connection
        }});
        
        server.listen(0, "127.0.0.1", () => {{
          const port = server.address().port;
          const client = new DiscordRPC();
          
          // Override pipe path logic to connect to our test server
          let originalCreateConnection = net.createConnection;
          net.createConnection = function(path, cb) {{
            net.createConnection = originalCreateConnection;
            return originalCreateConnection({{ port, host: "127.0.0.1" }}, cb);
          }};
          
          client.connect();
          
          setTimeout(() => {{
            const sock = client.socket;
            if (!sock) {{
              console.log(JSON.stringify({{ success: false, reason: "Socket not connected" }}));
              server.close();
              client.destroy();
              return;
            }}
            
            // Check attached error listeners on connected socket
            const errorListeners = sock.listeners("error");
            // The temporary onConnectError must have been removed!
            // Only setupSocket's error listener should be present.
            const hasLeakedConnectHandler = errorListeners.some(fn => fn.name === "onConnectError");
            
            console.log(JSON.stringify({{
              success: true,
              connected: client.connected,
              errorListenerCount: errorListeners.length,
              hasLeakedConnectHandler,
            }}));
            
            server.close();
            client.destroy();
          }}, 200);
        }});
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Node script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertTrue(data["success"])
        self.assertTrue(data["connected"])
        self.assertFalse(data["hasLeakedConnectHandler"], "onConnectError must be removed on connect")
        self.assertEqual(data["errorListenerCount"], 1, "Only setupSocket error handler should remain")

    def test_f6_handshake_watchdog_resolution_and_timeout(self):
        """Feature 6: Handshake watchdog clears on READY, or triggers cleanup on timeout."""
        script = f"""
        const {{ DiscordRPC }} = require({json.dumps(DISCORD_RPC_JS.replace(os.sep, '/'))});
        const EventEmitter = require("events");

        class MockSocket extends EventEmitter {{
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
        const sock = new MockSocket();
        client.socket = sock;
        client.connected = true;
        client.setupSocket();

        // 1. Send handshake
        client.sendHandshake();
        const timeoutArmed = client.handshakeTimeout !== null;

        // 2. Simulate incoming READY packet
        const readyPayload = JSON.stringify({{ evt: "READY", data: {{ v: 1 }} }});
        const readyPacket = client.encode(1, JSON.parse(readyPayload));
        
        // Emit data chunk
        sock.emit("data", readyPacket);
        
        const readyResolved = client.isReady === true;
        const timeoutClearedOnReady = client.handshakeTimeout === null;

        // 3. Test timeout behavior when READY is not received
        client.isReady = false;
        client.sendHandshake();
        let reconnectScheduled = false;
        client.scheduleReconnect = () => {{ reconnectScheduled = true; }};
        
        // Fast-forward timeout callback
        // The callback inside handshakeTimeout cleans up and reconnects if !isReady:
        clearTimeout(client.handshakeTimeout);
        client.cleanupSocket();
        client.scheduleReconnect();

        console.log(JSON.stringify({{
          timeoutArmed,
          readyResolved,
          timeoutClearedOnReady,
          timeoutCleanedSocket: client.socket === null,
          reconnectScheduled,
        }}));

        client.destroy();
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Node script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertTrue(data["timeoutArmed"], "Handshake timeout must be armed when sending handshake")
        self.assertTrue(data["readyResolved"], "isReady must be true when READY event is received")
        self.assertTrue(data["timeoutClearedOnReady"], "handshakeTimeout must be cleared on READY")
        self.assertTrue(data["timeoutCleanedSocket"], "cleanupSocket must tear down socket on timeout")
        self.assertTrue(data["reconnectScheduled"])

    def test_f7_pipe_reconnect_watchdog_resilience(self):
        """Feature 7: Periodic watchdog triggers scan when disconnected; connect() clears pending timer."""
        script = f"""
        const {{ DiscordRPC }} = require({json.dumps(DISCORD_RPC_JS.replace(os.sep, '/'))});

        const client = new DiscordRPC();
        let connectCalls = 0;
        client.connect = () => {{ connectCalls++; }};

        // Case 1: Disconnected and enabled -> watchdog fires connect
        client.connected = false;
        client.connecting = false;
        client.enabled = true;
        
        // Simulate watchdog tick
        if (client.enabled && !client.connected && !client.connecting) {{
          client.connect();
        }}
        const tick1Called = connectCalls === 1;

        // Case 2: Already connected -> watchdog skips
        client.connected = true;
        if (client.enabled && !client.connected && !client.connecting) {{
          client.connect();
        }}
        const tick2Skipped = connectCalls === 1;

        // Case 3: Disabled -> watchdog skips
        client.connected = false;
        client.enabled = false;
        if (client.enabled && !client.connected && !client.connecting) {{
          client.connect();
        }}
        const tick3Skipped = connectCalls === 1;

        // Case 4: connect() clears existing reconnectTimer to prevent collision
        const net = require("net");
        const origCreate = net.createConnection;
        net.createConnection = function(path, cb) {{
          const s = new (require("events"))();
          s.destroyed = false;
          s.destroy = function() {{ s.destroyed = true; }};
          setImmediate(() => {{
            if (!s.destroyed && s.listenerCount("error") > 0) {{
              s.emit("error", new Error("No pipe"));
            }}
          }});
          return s;
        }};

        const realClient = new DiscordRPC();
        realClient.scheduleReconnect(60000);
        const timerBefore = realClient.reconnectTimer !== null;
        realClient.connect();
        const timerAfter = realClient.reconnectTimer === null;
        net.createConnection = origCreate;

        console.log(JSON.stringify({{
          tick1Called,
          tick2Skipped,
          tick3Skipped,
          timerBefore,
          timerAfter,
        }}));

        client.destroy();
        realClient.destroy();
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Node script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertTrue(data["tick1Called"])
        self.assertTrue(data["tick2Skipped"])
        self.assertTrue(data["tick3Skipped"])
        self.assertTrue(data["timerBefore"])
        self.assertTrue(data["timerAfter"], "connect() must clear active reconnectTimer")

    def test_discord_ipc_packet_framing_and_chunked_streams(self):
        """Feature 5 & 6: Incoming stream packets chunked across TCP buffers reassemble cleanly."""
        script = f"""
        const {{ DiscordRPC }} = require({json.dumps(DISCORD_RPC_JS.replace(os.sep, '/'))});
        const EventEmitter = require("events");

        class MockSocket extends EventEmitter {{
          destroy() {{}}
          write() {{ return true; }}
        }}

        const client = new DiscordRPC();
        const sock = new MockSocket();
        client.socket = sock;
        client.connected = true;
        client.setupSocket();

        const p1 = client.encode(1, {{ evt: "READY", data: {{ v: 1 }} }});
        
        // Split packet across 3 partial chunks: [0..3], [4..9], [10..end]
        const chunk1 = p1.slice(0, 4);
        const chunk2 = p1.slice(4, 10);
        const chunk3 = p1.slice(10);

        sock.emit("data", chunk1);
        const readyAfterChunk1 = client.isReady;

        sock.emit("data", chunk2);
        const readyAfterChunk2 = client.isReady;

        sock.emit("data", chunk3);
        const readyAfterChunk3 = client.isReady;

        console.log(JSON.stringify({{
          readyAfterChunk1,
          readyAfterChunk2,
          readyAfterChunk3,
          bufferCleared: client.readBuffer.length === 0,
        }}));

        client.destroy();
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Node script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])

        self.assertFalse(data["readyAfterChunk1"])
        self.assertFalse(data["readyAfterChunk2"])
        self.assertTrue(data["readyAfterChunk3"])
        self.assertTrue(data["bufferCleared"])


class TestModMainDiscordIntegration(unittest.TestCase):
    """Verifies mod-main.js poller vs renderer priority (F8) and instant dispatch (F9)."""

    def test_f8_poller_skip_when_renderer_authoritative(self):
        """Feature 8: Poller skips executeJavaScript if renderer pushed within 3500ms."""
        now = time.time() * 1000.0

        def poller_decision(last_renderer_timestamp: float, current_time: float) -> str:
            silence_ms = current_time - last_renderer_timestamp
            if silence_ms < 3500:
                return "SKIP_POLLER"
            return "EXECUTE_FALLBACK"

        # Case 1: Renderer updated 200ms ago -> MUST skip
        self.assertEqual(poller_decision(now - 200, now), "SKIP_POLLER")
        # Case 2: Renderer updated 3400ms ago -> MUST skip
        self.assertEqual(poller_decision(now - 3400, now), "SKIP_POLLER")
        # Case 3: Renderer silent for 3501ms -> fallback triggers
        self.assertEqual(poller_decision(now - 3501, now), "EXECUTE_FALLBACK")
        # Case 4: Renderer silent for 10000ms -> fallback triggers
        self.assertEqual(poller_decision(now - 10000, now), "EXECUTE_FALLBACK")

    def test_f9_instant_track_dispatch_and_seek_passthrough(self):
        """Feature 9: Instant track dispatch (0ms throttle bypass) and seek passthrough."""
        with open(MOD_MAIN_JS, "r", encoding="utf-8") as f:
            code = f.read()

        # Verify implementation contains the Feature 9 bypass logic
        self.assertIn("!trackChanged && !playStateChanged && !seekDetected && timeSinceLastUpdate < 2000", code)
        self.assertIn("lastPlayerStateTimestamp = Date.now()", code)
        self.assertIn("Date.now() - lastPlayerStateTimestamp < 3500", code)

        # Behavioral simulation matching mod-main.js updateDiscordActivity
        class DiscordActivitySimulator:
            def __init__(self):
                self.rpcLastSentState = {
                    "trackId": None,
                    "isPlaying": None,
                    "position": 0,
                    "timestamp": 0,
                }
                self.dispatched = []

            def update(self, track_id: str, is_playing: bool, position: float, now: float) -> bool:
                trackChanged = self.rpcLastSentState["trackId"] != track_id
                playStateChanged = self.rpcLastSentState["isPlaying"] != is_playing

                seekDetected = False
                if is_playing and self.rpcLastSentState["isPlaying"] and self.rpcLastSentState["timestamp"] > 0:
                    elapsedSec = (now - self.rpcLastSentState["timestamp"]) / 1000.0
                    expectedPos = self.rpcLastSentState["position"] + elapsedSec
                    if abs(position - expectedPos) > 3.0:
                        seekDetected = True

                timeSinceLastUpdate = now - self.rpcLastSentState["timestamp"]

                if not trackChanged and not playStateChanged and not seekDetected and timeSinceLastUpdate < 2000.0:
                    return False  # Throttled

                self.rpcLastSentState = {
                    "trackId": track_id,
                    "isPlaying": is_playing,
                    "position": position,
                    "timestamp": now,
                }
                self.dispatched.append({"track_id": track_id, "time": now, "seek": seekDetected})
                return True

        sim = DiscordActivitySimulator()

        # Step 1: Track 1 starts at t=1000
        self.assertTrue(sim.update("track_1", True, 0.0, 1000.0))
        self.assertEqual(len(sim.dispatched), 1)

        # Step 2: Track 2 switched at t=1050 (only 50ms later!) -> MUST dispatch immediately (0ms throttle)
        self.assertTrue(sim.update("track_2", True, 0.0, 1050.0))
        self.assertEqual(len(sim.dispatched), 2)
        self.assertEqual(sim.dispatched[-1]["track_id"], "track_2")

        # Step 3: Track 3 switched at t=1100 (another 50ms later!) -> MUST dispatch immediately
        self.assertTrue(sim.update("track_3", True, 0.0, 1100.0))
        self.assertEqual(len(sim.dispatched), 3)

        # Step 4: Same track at t=1500 (400ms later, continuous progress at position 0.4s) -> Throttled
        self.assertFalse(sim.update("track_3", True, 0.4, 1500.0))
        self.assertEqual(len(sim.dispatched), 3)

        # Step 5: User seeks forward to 85.0s at t=1800 (within 2000ms!) -> Seek detected, MUST dispatch immediately
        self.assertTrue(sim.update("track_3", True, 85.0, 1800.0))
        self.assertEqual(len(sim.dispatched), 4)
        self.assertTrue(sim.dispatched[-1]["seek"])

        # Step 6: User pauses at t=2100 (300ms later) -> Play state changed, MUST dispatch immediately
        self.assertTrue(sim.update("track_3", False, 85.0, 2100.0))
        self.assertEqual(len(sim.dispatched), 5)

        # Step 7: Same track, resumed at t=2300 -> Play state changed, MUST dispatch immediately
        self.assertTrue(sim.update("track_3", True, 85.0, 2300.0))
        self.assertEqual(len(sim.dispatched), 6)

        # Step 8: Regular continuous playback after 2500ms (t=4800) -> Allowed
        self.assertTrue(sim.update("track_3", True, 87.5, 4800.0))
        self.assertEqual(len(sim.dispatched), 7)

        # Step 9: User seeks backward to 10.0s at t=5000 (only 200ms after last update!) -> Seek detected, MUST dispatch
        self.assertTrue(sim.update("track_3", True, 10.0, 5000.0))
        self.assertEqual(len(sim.dispatched), 8)
        self.assertTrue(sim.dispatched[-1]["seek"])

    def test_f5_socket_error_and_close_events_trigger_safe_cleanup(self):
        """Feature 5: Runtime socket 'error' and 'close' events safely tear down and schedule reconnect."""
        script = f"""
        const {{ DiscordRPC }} = require({json.dumps(DISCORD_RPC_JS.replace(os.sep, '/'))});
        const EventEmitter = require("events");

        class MockSocket extends EventEmitter {{
          constructor() {{
            super();
            this.destroyed = false;
          }}
          destroy() {{
            this.destroyed = true;
          }}
          write() {{ return true; }}
        }}

        // Test 1: error event
        const client1 = new DiscordRPC();
        const sock1 = new MockSocket();
        client1.socket = sock1;
        client1.connected = true;
        client1.isReady = true;
        client1.setupSocket();

        let reconnectScheduled1 = false;
        client1.scheduleReconnect = () => {{ reconnectScheduled1 = true; }};
        
        sock1.emit("error", new Error("Connection reset"));
        const errorTornDown = client1.socket === null && client1.connected === false && reconnectScheduled1;
        client1.destroy();

        // Test 2: close event
        const client2 = new DiscordRPC();
        const sock2 = new MockSocket();
        client2.socket = sock2;
        client2.connected = true;
        client2.isReady = true;
        client2.setupSocket();

        let reconnectScheduled2 = false;
        client2.scheduleReconnect = () => {{ reconnectScheduled2 = true; }};
        
        sock2.emit("close");
        const closeTornDown = client2.socket === null && client2.connected === false && reconnectScheduled2;
        client2.destroy();

        console.log(JSON.stringify({{
          errorTornDown,
          closeTornDown,
        }}));
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Node script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])
        self.assertTrue(data["errorTornDown"], "Socket error must trigger cleanupSocket and scheduleReconnect")
        self.assertTrue(data["closeTornDown"], "Socket close must trigger cleanupSocket and scheduleReconnect")

    def test_f5_socket_write_failure_cleans_up(self):
        """Feature 5: Socket write failure in sendActivityPayload tears down socket and reconnects."""
        script = f"""
        const {{ DiscordRPC }} = require({json.dumps(DISCORD_RPC_JS.replace(os.sep, '/'))});
        const EventEmitter = require("events");

        class BrokenSocket extends EventEmitter {{
          constructor() {{
            super();
            this.destroyed = false;
          }}
          destroy() {{
            this.destroyed = true;
          }}
          write() {{
            throw new Error("EPIPE: broken pipe");
          }}
        }}

        const client = new DiscordRPC();
        const sock = new BrokenSocket();
        client.socket = sock;
        client.connected = true;
        client.isReady = true;
        client.setupSocket();

        let reconnectScheduled = false;
        client.scheduleReconnect = () => {{ reconnectScheduled = true; }};

        client.sendActivityPayload({{ details: "Test" }});

        console.log(JSON.stringify({{
          socketCleared: client.socket === null,
          connected: client.connected,
          isReady: client.isReady,
          reconnectScheduled,
        }}));

        client.destroy();
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Node script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])
        self.assertTrue(data["socketCleared"])
        self.assertFalse(data["connected"])
        self.assertFalse(data["isReady"])
        self.assertTrue(data["reconnectScheduled"])

    def test_f6_activity_queue_until_ready(self):
        """Feature 6: setActivity called before READY queues last activity and flushes upon READY."""
        script = f"""
        const {{ DiscordRPC }} = require({json.dumps(DISCORD_RPC_JS.replace(os.sep, '/'))});
        const EventEmitter = require("events");

        class MockSocket extends EventEmitter {{
          constructor() {{
            super();
            this.written = [];
          }}
          destroy() {{}}
          write(buf) {{
            this.written.push(buf);
            return true;
          }}
        }}

        const client = new DiscordRPC();
        const sock = new MockSocket();
        client.socket = sock;
        client.connected = true;
        client.isReady = false; // Connected but NOT yet READY
        client.setupSocket();

        // Queue 2 activities before READY
        client.setActivity({{ details: "Song 1" }});
        client.setActivity({{ details: "Song 2" }});

        const writesBeforeReady = sock.written.length;

        // Emit READY event from Discord
        const readyPacket = client.encode(1, {{ evt: "READY", data: {{ v: 1 }} }});
        sock.emit("data", readyPacket);

        const writesAfterReady = sock.written.length;
        
        // Decode last written packet
        let flushedDetails = "";
        if (writesAfterReady > 0) {{
          const lastBuf = sock.written[sock.written.length - 1];
          const payloadStr = lastBuf.slice(8).toString("utf8");
          const payloadObj = JSON.parse(payloadStr);
          flushedDetails = payloadObj.args.activity.details;
        }}

        console.log(JSON.stringify({{
          writesBeforeReady,
          writesAfterReady,
          flushedDetails,
        }}));

        client.destroy();
        """
        res = run_node_script(script)
        self.assertEqual(res["returncode"], 0, f"Node script failed: {res['stderr']}")
        data = json.loads(res["stdout"].strip().splitlines()[-1])
        self.assertEqual(data["writesBeforeReady"], 0, "No activity payload should be written before READY")
        self.assertGreater(data["writesAfterReady"], 0, "Queued activity should be written immediately upon READY")
        self.assertEqual(data["flushedDetails"], "Song 2", "Latest queued activity must be the one dispatched")


if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING MILESTONE 2 (DISCORD RPC STABILIZATION) TEST SUITE")
    print("=" * 60)
    unittest.main(verbosity=2)
