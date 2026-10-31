const electron = require("electron");
const { app, BrowserWindow, ipcMain, globalShortcut, dialog, shell, screen } = electron;
const path = require("path");
const fs = require("fs");
const https = require("https");
const { SettingsManager } = require("./settings");
const appFolder = app ? app.getPath("userData") : path.join(process.env.APPDATA || "", "YandexMusic");
const { DiscordRPC } = require("./discord-rpc");

let settingsManager = null;
let discordRPC = null;
let overlayWindow = null;
let karaokeWindow = null;
let lastPlayerState = null;
let lastPlayerStateTimestamp = 0;
let lastLyricsData = null;

function resolvePreloadPath(scriptName) {
  // In packaged app.asar, mod-main.js is in /app/yandexMusicMod/main.js
  const localDir = path.join(__dirname, scriptName);
  if (fs.existsSync(localDir)) return localDir;

  const parentPreload = path.join(__dirname, "../preload", scriptName);
  if (fs.existsSync(parentPreload)) return parentPreload;

  const rootPreload = path.join(__dirname, "../../preload", scriptName);
  if (fs.existsSync(rootPreload)) return rootPreload;

  return localDir;
}

function initModMain() {
  if (settingsManager) return; // already initialized
  settingsManager = new SettingsManager();

  // 0. Disable official Yandex Music Auto-Updater to prevent overwriting the mod
  try {
    const electronUpdater = require("electron-updater");
    if (electronUpdater && electronUpdater.autoUpdater) {
      electronUpdater.autoUpdater.autoDownload = false;
      electronUpdater.autoUpdater.autoInstallOnAppQuit = false;
      electronUpdater.autoUpdater.checkForUpdates = async () => null;
      electronUpdater.autoUpdater.checkForUpdatesAndNotify = async () => null;
      electronUpdater.autoUpdater.downloadUpdate = async () => null;
      electronUpdater.autoUpdater.quitAndInstall = () => {};
    }
  } catch (e) {}

  // 1. Discord RPC
  const initialAppTitle = settingsManager.get("discordRPC/appTitle", "ru");
  const initialClientId = initialAppTitle === "en" ? "1269807014393942046" : "1269826362399522849";
  discordRPC = new DiscordRPC(initialClientId);
  const rpcEnabled = settingsManager.get("discordRPC/enabled", true);
  discordRPC.enabled = rpcEnabled;
  if (rpcEnabled) {
    discordRPC.connect();
  }

  settingsManager.onChange((key, value) => {
    if (key === "discordRPC/appTitle") {
      const newCid = value === "en" ? "1269807014393942046" : "1269826362399522849";
      if (discordRPC) {
        discordRPC.setClientId(newCid);
        if (lastPlayerState) updateDiscordActivity(lastPlayerState);
      }
    }
    if (key === "discordRPC/enabled") {
      discordRPC.enabled = !!value;
      if (value) {
        discordRPC.startWatchdog();
        discordRPC.connect();
        if (lastPlayerState) updateDiscordActivity(lastPlayerState);
      } else {
        discordRPC.stopWatchdog();
        discordRPC.clearActivity();
        discordRPC.cleanupSocket();
      }
    }

    // Broadcast settings update to all open windows
    BrowserWindow.getAllWindows().forEach((win) => {
      if (!win.isDestroyed()) {
        try {
          win.webContents.send("yandexMusicMod.storageValueUpdated", key, value);
        } catch (e) {}
      }
    });
  });

  // 2. Setup IPC Handlers
  setupIpcHandlers();
  startPlayerStatePolling();

  // 3. Register devtools shortcuts & console logger on every window
  function attachToWindow(win) {
    if (!win || win.isDestroyed()) return;

    const consoleLogPath = path.join(appFolder, "mod-renderer-console.log");

    win.webContents.on("console-message", (_event, level, message, line, sourceId) => {
      const entry = `[LVL ${level}] ${message} (${sourceId}:${line})\n`;
      try {
        fs.appendFileSync(consoleLogPath, entry, "utf8");
      } catch (e) {}
    });

    win.webContents.on("did-fail-load", (_ev, errorCode, errorDescription, validatedURL) => {
      const entry = `[FAIL LOAD] Code: ${errorCode}, Desc: ${errorDescription}, URL: ${validatedURL}\n`;
      try {
        fs.appendFileSync(consoleLogPath, entry, "utf8");
      } catch (e) {}
    });

    const dumpState = async () => {
      try {
        const domDump = await win.webContents.executeJavaScript(`
          (() => {
            const getElInfo = (el) => {
              if (!el) return null;
              const r = el.getBoundingClientRect();
              const s = window.getComputedStyle(el);
              return {
                tag: el.tagName,
                id: el.id,
                cls: el.className,
                rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
                display: s.display,
                visibility: s.visibility,
                opacity: s.opacity,
                zIndex: s.zIndex,
                bg: s.backgroundColor,
                color: s.color,
                overflow: s.overflow
              };
            };

            
            const asideLinks = Array.from(document.querySelectorAll('aside a, [data-test-id="NAVBAR"] a')).map(a => ({
              href: a.getAttribute("href"),
              text: a.innerText.trim(),
              testId: a.getAttribute("data-test-id") || (a.parentElement ? a.parentElement.getAttribute("data-test-id") : null)
            }));

            const pointCenter = document.elementFromPoint(Math.round(window.innerWidth / 2), Math.round(window.innerHeight / 2));
            const pointSidebar = document.elementFromPoint(50, 150);
            const pointTop = document.elementFromPoint(100, 20);

            return JSON.stringify({
              windowSize: { w: window.innerWidth, h: window.innerHeight },
              elementsAtPoints: {
                top: pointTop ? { tag: pointTop.tagName, id: pointTop.id, cls: pointTop.className } : null,
                sidebar: pointSidebar ? { tag: pointSidebar.tagName, id: pointSidebar.id, cls: pointSidebar.className } : null,
                center: pointCenter ? { tag: pointCenter.tagName, id: pointCenter.id, cls: pointCenter.className } : null,
                sidebarLinks: asideLinks
              },
              nodes: {
                body: getElInfo(document.body),
                modalBackdrop: getElInfo(document.getElementById("ym-mod-modal-backdrop")),
                withTopBanner: getElInfo(document.querySelector('div[class*="WithTopBanner_root"]')),
                withTopBannerContent: getElInfo(document.querySelector('div[class*="WithTopBanner_content"]')),
                defaultLayout: getElInfo(document.querySelector('div[class*="DefaultLayout_root"]')),
                navbar: getElInfo(document.querySelector('aside[data-test-id="NAVBAR"], aside, nav')),
                sidebarBtn: getElInfo(document.getElementById("ym-mod-menu-btn")),
                floatingTrigger: getElInfo(document.getElementById("ym-mod-floating-trigger"))
              },
              errors: window.__ymLastErrors || []
            }, null, 2);
          })()
        `);
        fs.appendFileSync(consoleLogPath, `[DEEP DOM DUMP] ${domDump}\n`, "utf8");

        const screenshotPath = path.join(appFolder, "mod-screen-capture.png");
        try {
          const image = await win.webContents.capturePage();
          fs.writeFileSync(screenshotPath, image.toPNG());
          fs.appendFileSync(consoleLogPath, `[SCREENSHOT SAVED] ${screenshotPath} (${image.getSize().width}x${image.getSize().height})\n`, "utf8");
        } catch (scErr) {
          fs.appendFileSync(consoleLogPath, `[SCREENSHOT ERROR] ${scErr.message}\n`, "utf8");
        }
      } catch (e) {
        fs.appendFileSync(consoleLogPath, `[DUMP ERROR] ${e.message}\n`, "utf8");
      }
    };

    win.webContents.on("did-finish-load", () => {
      setTimeout(dumpState, 1500);
    });
    setTimeout(dumpState, 1000);

    win.webContents.on("before-input-event", (event, input) => {
      if (input.type === "keyDown") {
        const isF12 = input.key === "F12";
        const isCtrlShiftI = (input.control || input.meta) && input.shift && input.key && input.key.toLowerCase() === "i";
        if (isF12 || isCtrlShiftI) {
          if (settingsManager.get("devtools/enabled", true)) {
            win.webContents.toggleDevTools();
            event.preventDefault();
          }
        }
      }
    });
  }

  let mainWindow = null;

  function trackMainWindow(win) {
    if (!win || win.isDestroyed()) return;
    if (win === overlayWindow || win === karaokeWindow) return;

    mainWindow = win;

    win.on("closed", () => {
      if (mainWindow === win) {
        mainWindow = null;
      }
      if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
      }
      if (discordRPC) {
        try { discordRPC.destroy(); } catch (e) {}
      }
      if (overlayWindow && !overlayWindow.isDestroyed()) {
        try { overlayWindow.destroy(); } catch (e) {}
        overlayWindow = null;
      }
      if (karaokeWindow && !karaokeWindow.isDestroyed()) {
        try { karaokeWindow.destroy(); } catch (e) {}
        karaokeWindow = null;
      }
      // Force immediate process exit so no zombie tasks linger in Task Manager
      try { app.exit(0); } catch (e) { app.quit(); }
    });
  }

  // Attach to existing windows immediately
  BrowserWindow.getAllWindows().forEach((win) => {
    attachToWindow(win);
    trackMainWindow(win);
  });

  // Attach to future windows
  app.on("browser-window-created", (_ev, win) => {
    attachToWindow(win);
    trackMainWindow(win);
  });

  // Handle second instance launch: bring main window to front
  app.on("second-instance", () => {
    const wins = BrowserWindow.getAllWindows();
    for (const win of wins) {
      if (!win.isDestroyed() && win !== overlayWindow && win !== karaokeWindow) {
        if (win.isMinimized()) win.restore();
        win.show();
        win.setSkipTaskbar(false);
        win.focus();
        return;
      }
    }
  });

  // 4. Register Global Shortcuts when App is ready
  if (app.isReady()) {
    onAppReady();
  } else {
    app.whenReady().then(onAppReady);
  }
}

function onAppReady() {
  registerGlobalShortcuts();
}

function registerGlobalShortcuts() {
  try {
    // Overlay toggle hotkey
    const overlayHotkey = settingsManager.get("overlay/hotkey", "CommandOrControl+Shift+O");
    globalShortcut.register(overlayHotkey, () => {
      toggleOverlayWindow();
    });

    // Karaoke toggle hotkey
    const karaokeHotkey = settingsManager.get("karaoke/hotkey", "CommandOrControl+Shift+L");
    globalShortcut.register(karaokeHotkey, () => {
      toggleKaraokeWindow();
    });

    // Ghost mode toggle hotkey (Ctrl+Shift+G)
    globalShortcut.register("CommandOrControl+Shift+G", () => {
      toggleOverlayGhostMode();
    });

    // Settings modal hotkey (Ctrl+Shift+S)
    globalShortcut.register("CommandOrControl+Shift+S", () => {
      openSettingsInMainWindow();
    });

    // Global DevTools hotkey
    globalShortcut.register("CommandOrControl+Shift+I", () => {
      toggleFocusedDevTools();
    });
    globalShortcut.register("F12", () => {
      toggleFocusedDevTools();
    });
  } catch (e) {
    console.error("[Mod Main] Failed to register global shortcuts:", e);
  }
}

function toggleFocusedDevTools() {
  const focused = BrowserWindow.getFocusedWindow();
  if (focused && !focused.isDestroyed()) {
    focused.webContents.toggleDevTools();
  }
}

function openSettingsInMainWindow() {
  BrowserWindow.getAllWindows().forEach((win) => {
    if (win !== overlayWindow && win !== karaokeWindow && !win.isDestroyed()) {
      try {
        win.webContents.send("yandexMusicMod.openSettingsModal");
        if (win.isMinimized()) win.restore();
        win.focus();
      } catch (e) {}
    }
  });
}

// ==========================================
// STEAM / DISCORD STYLE OVERLAY WINDOW
// ==========================================
function getOrCreateOverlayWindow() {
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    return overlayWindow;
  }

  const primaryDisplay = screen.getPrimaryDisplay();
  const { width } = primaryDisplay.workAreaSize;
  const overlayWidth = 380;
  const overlayHeight = 175;
  const posX = width - overlayWidth - 30;
  const posY = 40;

  const preloadScript = resolvePreloadPath("overlay-preload.js");

  overlayWindow = new BrowserWindow({
    width: overlayWidth,
    height: overlayHeight,
    x: posX,
    y: posY,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: true,
    hasShadow: false,
    show: false,
    backgroundColor: "#00000000",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false,
      preload: preloadScript,
    },
  });

  overlayWindow.setAlwaysOnTop(true, "screen-saver");
  overlayWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });

  const clickThrough = settingsManager.get("overlay/clickThrough", false);
  if (clickThrough) {
    overlayWindow.setIgnoreMouseEvents(true, { forward: true });
  }

  // Load overlay.html via standard music-application protocol
  overlayWindow.loadURL("music-application://desktop/yandexMusicMod/overlay.html");

  overlayWindow.webContents.on("did-finish-load", () => {
    if (lastPlayerState) {
      try {
        overlayWindow.webContents.send("overlay:trackUpdate", lastPlayerState);
      } catch (e) {}
    }
    if (lastLyricsData) {
      try {
        overlayWindow.webContents.send("overlay:lyricsUpdate", lastLyricsData);
      } catch (e) {}
    }
  });

  overlayWindow.on("closed", () => {
    overlayWindow = null;
  });

  return overlayWindow;
}

function toggleOverlayWindow() {
  const win = getOrCreateOverlayWindow();
  if (win.isVisible()) {
    win.hide();
  } else {
    win.show();
    if (lastPlayerState) {
      try {
        win.webContents.send("overlay:trackUpdate", lastPlayerState);
      } catch (e) {}
    }
    if (lastLyricsData) {
      try {
        win.webContents.send("overlay:lyricsUpdate", lastLyricsData);
      } catch (e) {}
    }
  }
}

function toggleOverlayGhostMode() {
  const current = settingsManager.get("overlay/clickThrough", false);
  const updated = !current;
  settingsManager.set("overlay/clickThrough", updated);
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    overlayWindow.setIgnoreMouseEvents(updated, { forward: true });
    try {
      overlayWindow.webContents.send("overlay:ghostModeToggled", updated);
    } catch (e) {}
  }
}

// ==========================================
// FLOATING KARAOKE WINDOW
// ==========================================
function getOrCreateKaraokeWindow() {
  if (karaokeWindow && !karaokeWindow.isDestroyed()) {
    return karaokeWindow;
  }

  const primaryDisplay = screen.getPrimaryDisplay();
  const { width, height } = primaryDisplay.workAreaSize;
  const karaokeWidth = 680;
  const karaokeHeight = 90;
  const posX = Math.round((width - karaokeWidth) / 2);
  const posY = height - karaokeHeight - 35;

  const preloadScript = resolvePreloadPath("karaoke-preload.js");

  karaokeWindow = new BrowserWindow({
    width: karaokeWidth,
    height: karaokeHeight,
    x: posX,
    y: posY,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: true,
    hasShadow: false,
    show: false,
    backgroundColor: "#00000000",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false,
      preload: preloadScript,
    },
  });

  karaokeWindow.setAlwaysOnTop(true, "screen-saver");
  karaokeWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  karaokeWindow.setIgnoreMouseEvents(true, { forward: true });

  karaokeWindow.loadURL("music-application://desktop/yandexMusicMod/karaoke.html");

  karaokeWindow.webContents.on("did-finish-load", () => {
    if (lastPlayerState) {
      try {
        karaokeWindow.webContents.send("karaoke:trackUpdate", lastPlayerState);
      } catch (e) {}
    }
    if (lastLyricsData) {
      try {
        karaokeWindow.webContents.send("karaoke:lyricsUpdate", lastLyricsData);
      } catch (e) {}
    }
  });

  karaokeWindow.on("closed", () => {
    karaokeWindow = null;
  });

  return karaokeWindow;
}

function toggleKaraokeWindow() {
  const win = getOrCreateKaraokeWindow();
  if (win.isVisible()) {
    win.hide();
  } else {
    win.show();
    if (lastPlayerState) {
      try {
        win.webContents.send("karaoke:trackUpdate", lastPlayerState);
      } catch (e) {}
    }
    if (lastLyricsData) {
      try {
        win.webContents.send("karaoke:lyricsUpdate", lastLyricsData);
      } catch (e) {}
    }
  }
}

// ==========================================
// DISCORD RICH PRESENCE UPDATE
// ==========================================
let rpcLastSentState = {
  trackId: null,
  isPlaying: null,
  position: 0,
  timestamp: 0,
};

function updateDiscordActivity(state) {
  if (!discordRPC || !discordRPC.enabled) return;
  if (!state) {
    if (rpcLastSentState.trackId !== null) {
      rpcLastSentState = { trackId: null, isPlaying: null, position: 0, timestamp: 0 };
      discordRPC.clearActivity();
    }
    return;
  }

  // Handle all player state shapes: state.track (renderer), state.trackMeta (IPC), or flat state
  const track = state.track || state.trackMeta || state;
  const isPlaying = state.isPlaying !== undefined 
    ? !!state.isPlaying 
    : (state.playback ? !!state.playback.isPlaying : false);
  const position = (state.progress && state.progress.position) 
    || (state.playback && state.playback.position) 
    || state.position 
    || 0;
  const duration = (state.progress && state.progress.duration) 
    || (state.playback && state.playback.duration) 
    || state.duration 
    || 0;

  const rawTitle = track.title || "";
  let rawArtist = "";
  if (Array.isArray(track.artists)) {
    rawArtist = track.artists.map((a) => (typeof a === "object" ? (a.name || "") : String(a))).join(", ");
  } else {
    rawArtist = track.artists || track.artist || "";
  }
  const album = (track.albums && track.albums[0] && track.albums[0].title) || track.album || "";

  if (!rawTitle) {
    if (rpcLastSentState.trackId !== null) {
      rpcLastSentState = { trackId: null, isPlaying: null, position: 0, timestamp: 0 };
      discordRPC.clearActivity();
    }
    return;
  }

  const trackId = track.id ? String(track.id) : `${rawTitle}-${rawArtist}`;
  const now = Math.floor(Date.now() / 1000);
  const trackChanged = rpcLastSentState.trackId !== trackId;
  const playStateChanged = rpcLastSentState.isPlaying !== isPlaying;

  let seekDetected = false;
  if (isPlaying && rpcLastSentState.isPlaying && rpcLastSentState.timestamp > 0) {
    const elapsedSec = now - rpcLastSentState.timestamp;
    const expectedPos = rpcLastSentState.position + elapsedSec;
    if (Math.abs(position - expectedPos) > 4) {
      seekDetected = true;
    }
  }

  const timeSinceLastUpdate = now - rpcLastSentState.timestamp;

  // Discord allows at most 1 update every ~15 seconds without rate-limiting.
  // Bypass throttle ONLY on track change, play/pause toggle, or seek (> 4s).
  if (!trackChanged && !playStateChanged && !seekDetected && timeSinceLastUpdate < 15) {
    return;
  }

  rpcLastSentState = {
    trackId,
    isPlaying,
    position,
    timestamp: now,
  };

  const isEn = settingsManager && settingsManager.get("discordRPC/appTitle", "ru") === "en";

  const cleanTitle = (rawTitle || "").trim();
  const cleanArtist = (rawArtist || "").trim();
  const safeTitle = (cleanTitle.length === 1 ? cleanTitle + "\u200b" : cleanTitle).substring(0, 128) || (isEn ? "Music" : "Музыка");
  const safeArtist = (cleanArtist.length === 1 ? cleanArtist + "\u200b" : cleanArtist).substring(0, 128) || (isEn ? "Yandex Music" : "Яндекс Музыка");

  let validCover = track.coverUrl || track.coverUri || (track.ogImage ? "https://" + track.ogImage.replace("%%", "400x400") : "");
  if (validCover && validCover.startsWith("//")) {
    validCover = "https:" + validCover;
  }
  if (validCover && validCover.includes("%%")) {
    validCover = validCover.replace("%%", "400x400");
  }
  if (!validCover || !validCover.startsWith("http")) {
    validCover = "https://music.yandex.ru/favicon.ico";
  }

  const activity = {
    details: safeTitle,
    state: safeArtist,
    assets: {
      large_image: validCover,
      large_text: album ? `${album} — ${safeTitle}`.substring(0, 128) : safeTitle,
      small_image: isPlaying 
        ? "https://raw.githubusercontent.com/FozerG/WinYandexMusicRPC/main/assets/Playing.png" 
        : "https://raw.githubusercontent.com/FozerG/WinYandexMusicRPC/main/assets/Paused.png",
      small_text: isPlaying 
        ? (isEn ? "Listening to Yandex Music" : "Слушает в Яндекс Музыке")
        : (isEn ? "Paused" : "На паузе"),
    },
    instance: false,
  };

  if (isPlaying && duration > 0) {
    activity.timestamps = {
      start: now - Math.floor(position || 0),
      end: now - Math.floor(position || 0) + Math.floor(duration),
    };
  }

  if (trackId && !trackId.includes("-") && trackId !== "0" && String(trackId).match(/^\d+$/)) {
    activity.buttons = [
      {
        label: isEn ? "🎵 Listen on Yandex Music" : "🎵 Слушать в Яндекс Музыке",
        url: `https://music.yandex.ru/track/${trackId}`,
      },
    ];
  }

  discordRPC.setActivity(activity);
}

// Active polling fallback for Discord RPC & Overlay (Stephanzion standard)
let pollingInterval = null;
function startPlayerStatePolling() {
  if (pollingInterval) return;
  setTimeout(() => { if (pollingInterval && typeof pollingInterval.unref === 'function') pollingInterval.unref(); }, 100);
  pollingInterval = setInterval(async () => {
    try {
      // Feature 8: Eliminate poller vs. renderer race condition.
      // Renderer push is authoritative. If renderer updated within 3500ms, skip poller entirely.
      if (Date.now() - lastPlayerStateTimestamp < 3500) {
        return;
      }

      const wins = BrowserWindow.getAllWindows();
      const mainWin = wins.find((w) => !w.isDestroyed() && w !== overlayWindow && w !== karaokeWindow);
      if (mainWin && !mainWin.isDestroyed()) {
        const pState = await mainWin.webContents.executeJavaScript(`
          (() => {
            return typeof window.__getPlayerState === "function" ? window.__getPlayerState() : null;
          })()
        `).catch(() => null);

        if (pState && pState.data) {
          if (!lastPlayerState || lastPlayerState.track?.id !== pState.data.trackMeta?.id || lastPlayerState.isPlaying !== pState.data.isPlaying) {
            updateDiscordActivity(pState.data);
          }
        }
      }
    } catch (e) {}
  }, 1500);
}

// ==========================================
// SETUP IPC HANDLERS
// ==========================================
function setupIpcHandlers() {
  // Prevent any official update installation from quitting and executing updater
  try {
    ipcMain.removeAllListeners("desktop:application:install-update");
    ipcMain.on("desktop:application:install-update", () => {
      console.warn("[Mod Main] Blocked official update installation request.");
    });
  } catch (e) {}
  // Storage API
  ipcMain.handle("yandexMusicMod.getStorageValue", (_ev, key) => {
    return settingsManager.get(key);
  });

  ipcMain.on("yandexMusicMod.setStorageValue", (_ev, key, value) => {
    settingsManager.set(key, value);
  });

  ipcMain.handle("yandexMusicMod.getAllSettings", () => {
    return settingsManager.getAll();
  });

  // DevTools
  ipcMain.on("yandexMusicMod.openDevTools", (event) => {
    const win = BrowserWindow.fromWebContents(event.sender);
    if (win && !win.isDestroyed()) {
      win.webContents.openDevTools({ mode: "detach" });
    }
  });

  // Settings Modal
  ipcMain.on("yandexMusicMod.openModSettings", () => {
    openSettingsInMainWindow();
  });

  // Overlay Windows Controls
  ipcMain.on("yandexMusicMod.toggleOverlay", () => {
    toggleOverlayWindow();
  });

  ipcMain.on("yandexMusicMod.toggleKaraoke", () => {
    toggleKaraokeWindow();
  });

  ipcMain.on("yandexMusicMod.setOverlayClickThrough", (_ev, enabled) => {
    settingsManager.set("overlay/clickThrough", !!enabled);
    if (overlayWindow && !overlayWindow.isDestroyed()) {
      overlayWindow.setIgnoreMouseEvents(!!enabled, { forward: true });
    }
  });

  ipcMain.on("yandexMusicMod.setOverlayIgnoreMouseEvents", (_ev, ignore, forward) => {
    if (overlayWindow && !overlayWindow.isDestroyed()) {
      overlayWindow.setIgnoreMouseEvents(!!ignore, { forward: forward !== false });
    }
  });

  // Pull Handlers for immediate cache hydration
  ipcMain.handle("yandexMusicMod.getLastPlayerState", () => {
    return lastPlayerState;
  });

  ipcMain.handle("yandexMusicMod.getLastLyrics", () => {
    return lastLyricsData;
  });

  // Action executed from Overlay -> forward to Main App Window (deduplicated: executePlayerAction only)
  ipcMain.on("yandexMusicMod.overlayAction", (_ev, action, payload) => {
    BrowserWindow.getAllWindows().forEach((win) => {
      if (win !== overlayWindow && win !== karaokeWindow && !win.isDestroyed()) {
        try {
          win.webContents.send("yandexMusicMod.executePlayerAction", action, payload);
        } catch (e) {}
      }
    });
  });

  // Player State updated from Main App Window -> forward to Overlay, Karaoke, Discord
  ipcMain.on("yandexMusicMod.updatePlayerState", (_ev, state) => {
    lastPlayerState = state;
    lastPlayerStateTimestamp = Date.now();

    // 1. Forward to Overlay
    if (overlayWindow && !overlayWindow.isDestroyed()) {
      try {
        overlayWindow.webContents.send("overlay:trackUpdate", state);
      } catch (e) {}
    }

    // 2. Forward to Karaoke
    if (karaokeWindow && !karaokeWindow.isDestroyed()) {
      try {
        karaokeWindow.webContents.send("karaoke:trackUpdate", state);
      } catch (e) {}
    }

    // 3. Discord RPC
    updateDiscordActivity(state);
  });

  // Resize Overlay dynamically (e.g. expanding for Apple Music full lyrics view)
  ipcMain.on("yandexMusicMod.resizeOverlay", (_ev, width, height) => {
    if (overlayWindow && !overlayWindow.isDestroyed()) {
      try {
        const [curW, curH] = overlayWindow.getSize();
        const targetW = Math.max(380, Math.round(width || curW));
        const targetH = Math.max(160, Math.round(height || curH));
        overlayWindow.setSize(targetW, targetH);
      } catch (e) {}
    }
  });

  // Open external URL in system browser
  ipcMain.on("yandexMusicMod.openExternal", (_ev, url) => {
    try {
      if (url && typeof url === "string" && (url.startsWith("http://") || url.startsWith("https://"))) {
        shell.openExternal(url);
      }
    } catch (e) {
      console.error("[Mod Main] openExternal error:", e);
    }
  });

  // Lyrics forward to Karaoke and Overlay
  ipcMain.on("yandexMusicMod.updateLyrics", (_ev, lyricsData) => {
    lastLyricsData = lyricsData;
    if (karaokeWindow && !karaokeWindow.isDestroyed()) {
      try {
        karaokeWindow.webContents.send("karaoke:lyricsUpdate", lyricsData);
      } catch (e) {}
    }
    if (overlayWindow && !overlayWindow.isDestroyed()) {
      try {
        overlayWindow.webContents.send("overlay:lyricsUpdate", lyricsData);
      } catch (e) {}
    }
  });

  // Multi-Tier Cascading Lyrics Fetcher (Yandex Supplement -> LRCLib Direct -> LRCLib Search)
  ipcMain.handle("yandexMusicMod.fetchLyrics", async (_ev, trackTitle, trackArtist, trackId = null, oauthToken = null) => {
    if (!trackTitle && !trackId) return null;
    try {
      const cleanTitle = (trackTitle || "").trim();
      const cleanArtist = (trackArtist || "").trim();

      const fetchJson = (url, extraHeaders = {}) => {
        return new Promise((resolve) => {
          const req = https.get(
            url,
            {
              headers: {
                "User-Agent": "YandexMusicMod/1.3.8 (Windows NT 10.0; Win64; x64)",
                "Accept": "application/json, text/plain, */*",
                ...extraHeaders,
              },
              timeout: 4000,
            },
            (res) => {
              let data = "";
              res.on("data", (chunk) => (data += chunk));
              res.on("end", () => {
                try {
                  if (res.statusCode >= 200 && res.statusCode < 300) {
                    resolve(JSON.parse(data));
                  } else {
                    resolve(null);
                  }
                } catch (e) {
                  resolve(null);
                }
              });
            }
          );
          req.on("error", () => resolve(null));
          req.on("timeout", () => {
            req.destroy();
            resolve(null);
          });
        });
      };

      let plainLyricsFallback = null;

      // 1. Tier 1: Official Yandex Music Track Supplement (Zero-latency native synced lyrics)
      if (trackId && String(trackId).match(/^\d+$/)) {
        try {
          const ymHeaders = {
            "User-Agent": "YandexMusicDesktopAppWindows/5.124.1",
            "X-Yandex-Music-Client": "YandexMusicDesktopAppWindows/5.124.1",
            "X-Yandex-Music-Frontend": "new",
          };
          if (oauthToken) ymHeaders["Authorization"] = oauthToken;
          const yandexData = await fetchJson(`https://api.music.yandex.net/tracks/${trackId}/supplement`, ymHeaders);

          if (yandexData && yandexData.result && yandexData.result.lyrics) {
            const lyricsObj = yandexData.result.lyrics;
            if (Array.isArray(lyricsObj.syncLyrics) && lyricsObj.syncLyrics.length > 0) {
              const lrcLines = lyricsObj.syncLyrics.map((item) => {
                const totalSec = (item.timestamp || item.offset || 0) / 1000;
                const m = Math.floor(totalSec / 60);
                const s = Math.floor(totalSec % 60);
                const cs = Math.floor((totalSec % 1) * 100);
                const timeTag = `[${m < 10 ? "0" : ""}${m}:${s < 10 ? "0" : ""}${s}.${cs < 10 ? "0" : ""}${cs}]`;
                return `${timeTag} ${item.line || item.text || ""}`;
              });
              return lrcLines.join("\n");
            } else if (lyricsObj.fullLyrics) {
              plainLyricsFallback = lyricsObj.fullLyrics;
            }
          }
        } catch (e) {}
      }

      // 2. Tier 2: LRCLib Direct Match with modern browser headers (prefer syncedLyrics)
      if (cleanTitle) {
        const query = new URLSearchParams({
          track_name: cleanTitle,
          artist_name: cleanArtist,
        }).toString();
        const direct = await fetchJson(`https://lrclib.net/api/get?${query}`);
        if (direct && direct.syncedLyrics) {
          return direct.syncedLyrics;
        }
        if (direct && direct.plainLyrics && !plainLyricsFallback) {
          plainLyricsFallback = direct.plainLyrics;
        }

        // 3. Tier 3: LRCLib Cleaned Search Fallback (strip feat., remix, remaster)
        const strippedTitle = cleanTitle
          .replace(/\s*[\(\[][^\)\]]*(?:feat|ft|remix|edit|version|prod|remaster|soundtrack|live|official)[^\)\]]*[\)\]]/gi, "")
          .trim();
        const primaryArtist = cleanArtist.split(/[,&/]/)[0].trim();

        if (strippedTitle !== cleanTitle || primaryArtist !== cleanArtist) {
          const strippedQuery = new URLSearchParams({
            track_name: strippedTitle,
            artist_name: primaryArtist,
          }).toString();
          const directStripped = await fetchJson(`https://lrclib.net/api/get?${strippedQuery}`);
          if (directStripped && directStripped.syncedLyrics) {
            return directStripped.syncedLyrics;
          }
          if (directStripped && directStripped.plainLyrics && !plainLyricsFallback) {
            plainLyricsFallback = directStripped.plainLyrics;
          }
        }

        const searchQuery = encodeURIComponent(`${strippedTitle} ${primaryArtist}`.trim());
        const searchRes = await fetchJson(`https://lrclib.net/api/search?q=${searchQuery}`);
        if (Array.isArray(searchRes) && searchRes.length > 0) {
          const synced = searchRes.find((x) => x.syncedLyrics);
          if (synced && synced.syncedLyrics) return synced.syncedLyrics;
          const plain = searchRes.find((x) => x.plainLyrics);
          if (plain && plain.plainLyrics && !plainLyricsFallback) plainLyricsFallback = plain.plainLyrics;
        }
      }

      if (plainLyricsFallback) {
        return plainLyricsFallback;
      }

      return null;
    } catch (err) {
      return null;
    }
  });

  // Directory pickers
  ipcMain.handle("yandexMusicMod.selectDownloadFolder", async (_ev) => {
    const result = await dialog.showOpenDialog({
      properties: ["openDirectory"],
      title: "Выберите папку для сохранения музыки",
    });
    if (!result.canceled && result.filePaths.length > 0) {
      settingsManager.set("downloadFolderPath", result.filePaths[0]);
      return result.filePaths[0];
    }
    return null;
  });

  ipcMain.on("yandexMusicMod.openDownloadDirectory", () => {
    const folder = settingsManager.get("downloadFolderPath", app.getPath("downloads"));
    shell.openPath(folder);
  });

  ipcMain.handle("yandexMusicMod.openFolder", (_ev, folderPath) => {
    if (folderPath) {
      shell.openPath(folderPath);
      return { success: true };
    }
    return { success: false };
  });
}

// Auto-run initialization
initModMain();

module.exports = {
  initModMain,
  getOrCreateOverlayWindow,
  getOrCreateKaraokeWindow,
  toggleOverlayWindow,
  toggleKaraokeWindow,
  toggleOverlayGhostMode,
};
