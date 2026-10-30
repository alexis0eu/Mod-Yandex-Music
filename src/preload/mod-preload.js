// === Yandex Music Mod Preload Integration ===
(function () {
  try {
    const electron = require("electron");

    // 1. Intercept & neutralize official Yandex Music app update listeners and install commands
    try {
      const originalOn = electron.ipcRenderer.on.bind(electron.ipcRenderer);
      electron.ipcRenderer.on = function (channel, listener) {
        if (channel === "desktop:application:update-available") {
          // Drop update-available listener so UI never receives update notice
          return this;
        }
        return originalOn(channel, listener);
      };

      const originalSend = electron.ipcRenderer.send.bind(electron.ipcRenderer);
      electron.ipcRenderer.send = function (channel, ...args) {
        if (channel === "desktop:application:install-update") {
          console.warn("[Mod Preload] Prevented install-update IPC invocation to protect mod");
          return;
        }
        return originalSend(channel, ...args);
      };
    } catch (hookErr) {
      console.error("[Mod Preload Hook Error]", hookErr);
    }

    electron.contextBridge.exposeInMainWorld("yandexMusicMod", {
      getStorageValue: (key) => electron.ipcRenderer.invoke("yandexMusicMod.getStorageValue", key),
      setStorageValue: (key, value) => electron.ipcRenderer.send("yandexMusicMod.setStorageValue", key, value),
      getAllSettings: () => electron.ipcRenderer.invoke("yandexMusicMod.getAllSettings"),
      onStorageChanged: (callback) => {
        const listener = (_e, key, value) => callback(key, value);
        electron.ipcRenderer.on("yandexMusicMod.storageValueUpdated", listener);
        return () => electron.ipcRenderer.removeListener("yandexMusicMod.storageValueUpdated", listener);
      },
      updatePlayerState: (state) => electron.ipcRenderer.send("yandexMusicMod.updatePlayerState", state),
      updateLyrics: (lyricsData) => electron.ipcRenderer.send("yandexMusicMod.updateLyrics", lyricsData),
      fetchLyrics: (track, artist, trackId) => electron.ipcRenderer.invoke("yandexMusicMod.fetchLyrics", track, artist, trackId),
      onExecutePlayerAction: (callback) => {
        const listener = (_e, action, payload) => callback(action, payload);
        electron.ipcRenderer.on("yandexMusicMod.executePlayerAction", listener);
        return () => electron.ipcRenderer.removeListener("yandexMusicMod.executePlayerAction", listener);
      },
      toggleOverlay: () => electron.ipcRenderer.send("yandexMusicMod.toggleOverlay"),
      toggleKaraoke: () => electron.ipcRenderer.send("yandexMusicMod.toggleKaraoke"),
      setOverlayClickThrough: (enabled) => electron.ipcRenderer.send("yandexMusicMod.setOverlayClickThrough", enabled),
      setOverlayIgnoreMouseEvents: (ignore, forward) => electron.ipcRenderer.send("yandexMusicMod.setOverlayIgnoreMouseEvents", ignore, forward),
      openDevTools: () => electron.ipcRenderer.send("yandexMusicMod.openDevTools"),
      selectDownloadFolder: () => electron.ipcRenderer.invoke("yandexMusicMod.selectDownloadFolder"),
      openDownloadDirectory: () => electron.ipcRenderer.send("yandexMusicMod.openDownloadDirectory"),
      openFolder: (path) => electron.ipcRenderer.invoke("yandexMusicMod.openFolder", path),
      openExternal: (url) => electron.ipcRenderer.send("yandexMusicMod.openExternal", url),
      onOpenSettings: (callback) => {
        const listener = () => callback();
        electron.ipcRenderer.on("yandexMusicMod.openSettingsModal", listener);
        return () => electron.ipcRenderer.removeListener("yandexMusicMod.openSettingsModal", listener);
      },
    });
  } catch (e) {
    console.error("[Mod Preload Error]", e);
  }
})();
