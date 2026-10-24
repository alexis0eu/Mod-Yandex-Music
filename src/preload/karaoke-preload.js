const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("karaokeApi", {
  onTrackUpdate: (callback) => {
    const listener = (_e, state) => callback(state);
    ipcRenderer.on("karaoke:trackUpdate", listener);
    return () => ipcRenderer.removeListener("karaoke:trackUpdate", listener);
  },
  onLyricsUpdate: (callback) => {
    const listener = (_e, lyrics) => callback(lyrics);
    ipcRenderer.on("karaoke:lyricsUpdate", listener);
    return () => ipcRenderer.removeListener("karaoke:lyricsUpdate", listener);
  },
  toggleKaraoke: () => {
    ipcRenderer.send("yandexMusicMod.toggleKaraoke");
  },
  getStorageValue: (key) => ipcRenderer.invoke("yandexMusicMod.getStorageValue", key),
  onStorageChanged: (callback) => {
    const listener = (_e, key, value) => callback(key, value);
    ipcRenderer.on("yandexMusicMod.storageValueUpdated", listener);
    return () => ipcRenderer.removeListener("yandexMusicMod.storageValueUpdated", listener);
  },
});
