const net = require("net");
const process = require("process");

const CLIENT_ID = "1283109459463377011";

class DiscordRPC {
  constructor(clientId = CLIENT_ID) {
    this.clientId = clientId;
    this.socket = null;
    this.pendingSocket = null;
    this.connected = false;
    this.connecting = false;
    this.isReady = false;
    this.enabled = true;
    this.reconnectTimer = null;
    this.handshakeTimeout = null;
    this.watchdogInterval = null;
    this.lastActivity = null;
    this.readBuffer = Buffer.alloc(0);

    this.startWatchdog();
  }

  setClientId(newId) {
    if (!newId || this.clientId === newId) return;
    this.clientId = newId;
    this.cleanupSocket();
    if (this.enabled) {
      this.connect();
    }
  }

  startWatchdog() {
    if (this.watchdogInterval) return;
    this.watchdogInterval = setInterval(() => {
      if (this.enabled && !this.connected && !this.connecting) {
        this.connect();
      }
    }, 15000);
    if (this.watchdogInterval && typeof this.watchdogInterval.unref === "function") {
      this.watchdogInterval.unref();
    }
  }

  stopWatchdog() {
    if (this.watchdogInterval) {
      clearInterval(this.watchdogInterval);
      this.watchdogInterval = null;
    }
  }

  clearHandshakeTimeout() {
    if (this.handshakeTimeout) {
      clearTimeout(this.handshakeTimeout);
      this.handshakeTimeout = null;
    }
  }

  cleanupSocket() {
    this.clearHandshakeTimeout();
    if (this.pendingSocket) {
      try {
        this.pendingSocket.removeAllListeners();
        this.pendingSocket.destroy();
      } catch (e) {}
      this.pendingSocket = null;
    }
    if (this.socket) {
      try {
        this.socket.removeAllListeners();
        this.socket.destroy();
      } catch (e) {}
      this.socket = null;
    }
    this.connected = false;
    this.connecting = false;
    this.isReady = false;
    this.readBuffer = Buffer.alloc(0);
  }

  connect() {
    if (!this.enabled) return;
    if (this.connected || this.connecting) return;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.connecting = true;
    this.isReady = false;

    let pipeIndex = 0;
    const tryNextPipe = () => {
      if (!this.connecting) return;

      if (pipeIndex > 9) {
        this.connecting = false;
        this.scheduleReconnect();
        return;
      }

      const pipePath =
        process.platform === "win32"
          ? `\\\\.\\pipe\\discord-ipc-${pipeIndex}`
          : `${process.env.XDG_RUNTIME_DIR || process.env.TMPDIR || process.env.TMP || "/tmp"}/discord-ipc-${pipeIndex}`;

      pipeIndex++;

      let sock = null;
      const onConnectError = () => {
        if (this.pendingSocket === sock) {
          this.pendingSocket = null;
        }
        if (sock) {
          try {
            sock.removeListener("error", onConnectError);
            sock.destroy();
          } catch (e) {}
        }
        tryNextPipe();
      };

      sock = net.createConnection(pipePath, () => {
        if (this.pendingSocket === sock) {
          this.pendingSocket = null;
        }
        sock.removeListener("error", onConnectError);
        this.socket = sock;
        this.connected = true;
        this.connecting = false;
        this.readBuffer = Buffer.alloc(0);
        this.setupSocket();
        this.sendHandshake();
      });

      this.pendingSocket = sock;
      sock.once("error", onConnectError);
    };

    tryNextPipe();
  }

  scheduleReconnect(delayMs = 10000) {
    if (!this.enabled) return;
    if (this.connected || this.connecting) return;
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delayMs);
    if (this.reconnectTimer && typeof this.reconnectTimer.unref === "function") {
      this.reconnectTimer.unref();
    }
  }

  setupSocket() {
    if (!this.socket) return;

    this.socket.on("close", () => {
      this.cleanupSocket();
      this.scheduleReconnect();
    });

    this.socket.on("error", () => {
      this.cleanupSocket();
      this.scheduleReconnect();
    });

    this.socket.on("data", (chunk) => {
      this.readBuffer = Buffer.concat([this.readBuffer, chunk]);
      this.processIncomingPackets();
    });
  }

  processIncomingPackets() {
    while (this.readBuffer.length >= 8) {
      const op = this.readBuffer.readUInt32LE(0);
      const len = this.readBuffer.readUInt32LE(4);
      const totalLen = 8 + len;

      if (this.readBuffer.length < totalLen) {
        break; // Wait for full packet
      }

      const payloadBuf = this.readBuffer.slice(8, totalLen);
      this.readBuffer = this.readBuffer.slice(totalLen);

      try {
        const jsonStr = payloadBuf.toString("utf8");
        const data = JSON.parse(jsonStr);

        if (data.evt === "READY") {
          this.clearHandshakeTimeout();
          this.isReady = true;
          // If we had pending activity queued, send it immediately
          if (this.lastActivity) {
            this.sendActivityPayload(this.lastActivity);
          }
        }
      } catch (e) {}
    }
  }

  encode(op, payload) {
    const jsonStr = JSON.stringify(payload);
    const len = Buffer.byteLength(jsonStr, "utf8");
    const packet = Buffer.alloc(8 + len);
    packet.writeUInt32LE(op, 0);
    packet.writeUInt32LE(len, 4);
    packet.write(jsonStr, 8, len, "utf8");
    return packet;
  }

  sendHandshake() {
    if (!this.socket || !this.connected) return;

    this.clearHandshakeTimeout();
    this.handshakeTimeout = setTimeout(() => {
      this.handshakeTimeout = null;
      if (!this.isReady) {
        this.cleanupSocket();
        this.scheduleReconnect();
      }
    }, 5000);

    const payload = {
      v: 1,
      client_id: this.clientId,
    };
    try {
      this.socket.write(this.encode(0, payload));
    } catch (e) {
      this.cleanupSocket();
      this.scheduleReconnect();
    }
  }

  setActivity(activity) {
    this.lastActivity = activity;
    if (!this.socket || !this.connected) {
      this.connect();
      return;
    }
    if (!this.isReady) {
      // Waiting for Discord READY event, packet will be sent as soon as READY arrives
      return;
    }
    this.sendActivityPayload(activity);
  }

  sendActivityPayload(activity) {
    if (!this.socket || !this.connected) return;
    const payload = {
      cmd: "SET_ACTIVITY",
      args: {
        pid: process.pid,
        activity: activity || null,
      },
      nonce: Math.random().toString(36).substring(2),
    };

    try {
      this.socket.write(this.encode(1, payload));
    } catch (e) {
      this.cleanupSocket();
      this.scheduleReconnect();
    }
  }

  clearActivity() {
    this.lastActivity = null;
    this.setActivity(null);
  }

  destroy() {
    this.stopWatchdog();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.clearHandshakeTimeout();
    if (this.socket && this.connected && this.isReady) {
      try {
        this.sendActivityPayload(null);
      } catch (e) {}
    }
    this.cleanupSocket();
    this.lastActivity = null;
  }
}

module.exports = { DiscordRPC };
