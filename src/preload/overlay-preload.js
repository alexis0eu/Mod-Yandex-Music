const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("overlayApi", {
  onTrackUpdate: (callback) => {
    const listener = (_e, state) => callback(state);
    ipcRenderer.on("overlay:trackUpdate", listener);
    return () => ipcRenderer.removeListener("overlay:trackUpdate", listener);
  },
  onLyricsUpdate: (callback) => {
    const listener = (_e, lyrics) => callback(lyrics);
    ipcRenderer.on("overlay:lyricsUpdate", listener);
    return () => ipcRenderer.removeListener("overlay:lyricsUpdate", listener);
  },
  sendPlayerAction: (action, payload) => {
    ipcRenderer.send("yandexMusicMod.overlayAction", action, payload);
  },
  sendAction: (action, payload) => {
    ipcRenderer.send("yandexMusicMod.overlayAction", action, payload);
  },
  setClickThrough: (enabled) => {
    ipcRenderer.send("yandexMusicMod.setOverlayClickThrough", enabled);
  },
  setIgnoreMouseEvents: (ignore, forward) => {
    ipcRenderer.send("yandexMusicMod.setOverlayIgnoreMouseEvents", ignore, forward);
  },
  onGhostModeToggled: (callback) => {
    const listener = (_e, enabled) => callback(enabled);
    ipcRenderer.on("overlay:ghostModeToggled", listener);
    return () => ipcRenderer.removeListener("overlay:ghostModeToggled", listener);
  },
  toggleOverlay: () => {
    ipcRenderer.send("yandexMusicMod.toggleOverlay");
  },
  toggleKaraoke: () => {
    ipcRenderer.send("yandexMusicMod.toggleKaraoke");
  },
  resizeOverlay: (width, height) => {
    ipcRenderer.send("yandexMusicMod.resizeOverlay", width, height);
  },
  getPlayerState: () => ipcRenderer.invoke("yandexMusicMod.getLastPlayerState"),
  getLyrics: () => ipcRenderer.invoke("yandexMusicMod.getLastLyrics"),
  getLastPlayerState: () => ipcRenderer.invoke("yandexMusicMod.getLastPlayerState"),
  getLastLyrics: () => ipcRenderer.invoke("yandexMusicMod.getLastLyrics"),
  getStorageValue: (key) => ipcRenderer.invoke("yandexMusicMod.getStorageValue", key),
  setStorageValue: (key, value) => ipcRenderer.send("yandexMusicMod.setStorageValue", key, value),
  onStorageChanged: (callback) => {
    const listener = (_e, key, value) => callback(key, value);
    ipcRenderer.on("yandexMusicMod.storageValueUpdated", listener);
    return () => ipcRenderer.removeListener("yandexMusicMod.storageValueUpdated", listener);
  },
});
