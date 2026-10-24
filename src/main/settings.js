const fs = require("fs");
const path = require("path");
const { app } = require("electron");

const DEFAULT_SETTINGS = {
  // Plus Unlocker
  "plus-unlocker/enabled": true,
  "plus-unlocker/bypassAds": true,
  "plus-unlocker/unlimitedSkips": true,
  "plus-unlocker/hideUpgradePrompts": true,

  // Appearance & Design
  "design/mode": "classic", // "classic" | "modern"
  "custom-themes/enabled": true,
  "custom-themes/accent": "#fed42b",
  "custom-themes/playerColorsReplace": true,
  "custom-themes/disableVibeAnimation": false,
  "custom-themes/disableExplicitMark": false,
  "custom-themes/hideMenuItems": [],

  // Fonts & Typography
  "font-changer/enabled": true,
  "font-changer/savedFont": "JetBrains Mono",
  "font-changer/sizeScale": 1.0,
  "font-changer/weight": "normal",
  "font-changer/letterSpacing": "normal",
  "scale-changer/savedScale": 1.0,

  // UI Cleaner (Hide unwanted buttons/sections)
  "cleaner/hideDislike": false,
  "cleaner/hideQueue": false,
  "cleaner/hideLyrics": false,
  "cleaner/hidePrev": false,
  "cleaner/hideQuality": false,
  "cleaner/hideVolume": false,
  "cleaner/hideVibeBlock": false,
  "cleaner/hidePodcasts": false,
  "cleaner/hideTrailers": false,
  "cleaner/hideRadio": false,

  // Equalizer & Audio FX
  "equalizer/enabled": false,
  "equalizer/preset": "flat",

  // Killer Features: Overlays & Tools
  "downloader/enabled": true,
  "osd/enabled": false,
  "autoLiker/enabled": false,

  // Killer Features: Overlays
  "overlay/enabled": true,
  "overlay/hotkey": "CommandOrControl+Shift+O",
  "overlay/clickThrough": false,
  "overlay/hudTheme": "steam-glass", // "steam-glass" | "discord-dark" | "cyberpunk"
  "karaoke/enabled": false,
  "karaoke/hotkey": "CommandOrControl+Shift+L",
  "karaoke/position": "bottom", // "top" | "bottom"
  "karaoke/glow": true,

  // Tweaks & Tools
  "discordRPC/enabled": true,
  "devtools/enabled": true,
  "blockAds/enabled": true,
  "autoQuality/enabled": true,
  "autoLiker/enabled": false,
  "settings/accountExperimentsOverride": []
};

class SettingsManager {
  constructor() {
    this.userDataPath = app ? app.getPath("userData") : "";
    this.filePath = path.join(this.userDataPath, "mod_settings.json");
    this.settings = { ...DEFAULT_SETTINGS };
    this.listeners = new Set();
    this.load();
  }

  load() {
    try {
      if (fs.existsSync(this.filePath)) {
        const raw = fs.readFileSync(this.filePath, "utf8");
        const parsed = JSON.parse(raw);
        this.settings = { ...DEFAULT_SETTINGS, ...parsed };
      } else {
        this.save();
      }
    } catch (e) {
      console.error("[Mod Settings] Error reading settings, resetting to defaults:", e);
      this.settings = { ...DEFAULT_SETTINGS };
    }
  }

  save() {
    try {
      fs.writeFileSync(this.filePath, JSON.stringify(this.settings, null, 2), "utf8");
    } catch (e) {
      console.error("[Mod Settings] Error writing settings:", e);
    }
  }

  get(key, defaultValue = undefined) {
    if (this.settings[key] !== undefined) {
      return this.settings[key];
    }
    return defaultValue !== undefined ? defaultValue : DEFAULT_SETTINGS[key];
  }

  getAll() {
    return { ...this.settings };
  }

  set(key, value) {
    this.settings[key] = value;
    this.save();
    for (const cb of this.listeners) {
      try {
        cb(key, value);
      } catch (e) {}
    }
  }

  onChange(callback) {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }
}

module.exports = { SettingsManager, DEFAULT_SETTINGS };
