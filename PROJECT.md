# Project: Yandex Music Mod Modernization

## Architecture
The Yandex Music Mod integrates into the desktop Electron application (`Яндекс Музыка.exe`) by patching `app.asar` via Python automation. It features:
- **Main Process (`src/main/`)**:
  - `mod-main.js`: IPC hub between renderer, overlay, karaoke, and external network services. Manages window lifecycles, player state broadcasting, and the 3-tier cascading lyrics engine.
  - `discord-rpc.js`: Named-pipe (`\\.\pipe\discord-ipc-0..9`) Rich Presence client with handshake watchdog and automatic reconnection.
  - `settings.js`: `SettingsManager` reading/writing `mod_settings.json` in Electron `userData`.
- **Preload Layer (`src/preload/`)**:
  - `mod-preload.js`: Exposes `window.yandexMusicMod` to the main renderer context.
  - `overlay-preload.js`: Exposes `window.overlayApi` with pull & push handlers for player state and lyrics.
  - `karaoke-preload.js`: Exposes `window.karaokeApi` for floating synchronized lyrics.
- **Renderer Process (`src/renderer/`)**:
  - `mod-renderer.js`: UI injection, player state observer (HTML5 audio + React Fiber hooks), font switching via dynamic CSS, and settings modal controller.
  - `mod-renderer.css`: Base64-inlined fonts and native dark frosted glass styling.
- **HUD Overlay & Karaoke (`src/overlay/`, `src/karaoke/`)**:
  - `overlay.js` / `overlay.html` / `overlay.css`: Low-overhead gaming overlay with smooth 60fps interpolation timer, instant cache hydration, and two-way controls.
  - `karaoke.js` / `karaoke.html` / `karaoke.css`: Floating transparent karaoke window.
- **Packaging & Verification (`tools/`)**:
  - `tools/verify.py`: Syntax, ASAR integrity, injection simulation, and API tests.
  - `tools/inject.py`: ASAR extraction, patching, repacking, and Electron fuse validation bypass.
  - `tools/test_app_run.py`: Real app launch, Next.js hydration, DOM verification, and screenshot capture.
  - `tools/build_css.py`: WOFF2 to Base64 inliner for `mod-renderer.css`.

---

## Feature Inventory

Every feature identified during the survey phase is enumerated below with an assigned milestone:

| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | WOFF2 Base64 Inlining | Convert all 6 fonts (Andy-Bold, Minecraft, JetBrains Mono, Press Start 2P, VT323, Uncut Sans) into Base64 data URIs inside `mod-renderer.css` | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Dual-Alias Andy / Terraria | Declare `@font-face` for both `"Andy Bold"` and `"Terraria"` to resolve runtime font-family matching failure | M1 | Survey Spec Miner 3 |
| 3 | Universal Font Enforcement | Apply dynamic `<style>` tag with `* { font-family: ... !important; }` and font-specific scale factors | M1 | ORIGINAL_REQUEST §R1 |
| 4 | Uncut Sans Asset Integration | Retrieve and integrate `UncutSans-Regular.woff2` into `src/fonts/` and packaging pipeline | M1 | Survey Explorer 1 / Spec Miner 3 |
| 5 | Discord RPC Socket Lifecycle | Clean up socket error listeners on connect, prevent orphaned handlers, safe `cleanupSocket()` | M2 | Survey Explorer 2 |
| 6 | Discord Handshake Watchdog | 5000ms timeout on handshake; tear down socket and schedule reconnect if Discord stalls | M2 | Survey Explorer 2 |
| 7 | Discord Pipe Reconnect Watchdog | Resilient 15s periodic health check watchdog to reconnect if Discord launches late or restarts | M2 | ORIGINAL_REQUEST §R2 |
| 8 | Poller vs. Renderer Race Fix | Renderer push is authoritative; poller demoted to slow fallback (>3.5s silence) | M2 | ORIGINAL_REQUEST §R2 |
| 9 | Instant Track Dispatch | Eliminate 2000ms throttle on track switches; immediate 0ms Discord presence update | M2 | ORIGINAL_REQUEST §R2 |
| 10 | Overlay Cache Immediate Delivery | Add `getLastPlayerState` and `getLastLyrics` IPC pull handlers in main and preload; invoke on DOM load | M3 | ORIGINAL_REQUEST §R3 |
| 11 | Overlay Smooth Progress Interpolation | Local 60fps interpolation timer (`requestAnimationFrame`/50ms) driving progress bar and timecodes | M3 | ORIGINAL_REQUEST §R3 |
| 12 | Overlay Controls De-duplication | Eliminate redundant `desktop:player:action` dispatch when `executePlayerAction` is sent | M3 | Survey Explorer 2 |
| 13 | Overlay Optimistic UI | Instant icon toggling and seek preview on click without waiting for IPC round-trip | M3 | Survey Explorer 2 |
| 14 | Overlay Track Transition Reset | Reset lyrics array and index immediately on track change to prevent lingering previous lyrics | M3 | Survey Explorer 2 |
| 15 | Yandex Lyrics Provider | Query `https://api.music.yandex.net/tracks/{id}/supplement` with session cookies from `session.defaultSession` | M4 | ORIGINAL_REQUEST §R4 |
| 16 | Musixmatch Android Signer | HMAC-SHA1 signing using secret `967Pn4)N3&R_GBg5$b('` and `yMMdd` date format | M4 | ORIGINAL_REQUEST §R4 |
| 17 | Musixmatch Fallback Provider | Query Musixmatch Android API (`macro.subtitles.get`) with Dalvik User-Agent | M4 | ORIGINAL_REQUEST §R4 |
| 18 | LRCLib Provider & Fallback | LRCLib `get` with stripped `search` query fallback | M4 | ORIGINAL_REQUEST §R4 |
| 19 | LRC Metadata Tag Cleaner | Regex-based cleaner stripping `[ar:...]`, `[ti:...]`, etc., leaving only clean lyrics lines | M4 | ORIGINAL_REQUEST §R4 |
| 20 | Dual Lyrics Broadcast | Broadcast resolved lyrics to both HUD Overlay and Karaoke windows | M4 | ORIGINAL_REQUEST §R4 |
| 21 | Native Frosted Glass Styling | `rgba(20, 20, 24, 0.88)`, `backdrop-filter: blur(30px) saturate(170%)`, `1px rgba(255, 255, 255, 0.08)`, 18px radius | M5 | ORIGINAL_REQUEST §R5 |
| 22 | 6-Section Sidebar Tabs | Reorganize modal into 6 tabs: Внешний вид, Шрифты, Discord, Оверлей, Тексты, Очистка интерфейса | M5 | ORIGINAL_REQUEST §R5 |
| 23 | Native Dark UI Switches | Compact graphite switches (36x20px, 16px thumb, `#fed42b` accent) | M5 | ORIGINAL_REQUEST §R5 |
| 24 | Scale & Font Sliders | Native sliders for interface scale (80%-130%) and font scale (0.8x-1.3x) | M5 | ORIGINAL_REQUEST §R5 |
| 25 | Verification Toolchain & E2E Acceptance | Pass 100% of `tools/verify.py`, `tools/inject.py`, `tools/test_app_run.py`, and E2E test suite | M6 | ORIGINAL_REQUEST §Acceptance |

---

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Font Pack & Base64 Inlining | Features 1, 2, 3, 4: `src/fonts/`, `tools/build_css.py`, `src/renderer/mod-renderer.css`, `src/renderer/mod-renderer.js` | none | DONE |
| M2 | Discord RPC Stabilization | Features 5, 6, 7, 8, 9: `src/main/discord-rpc.js`, `src/main/mod-main.js` | none | DONE |
| M3 | Gaming HUD Overlay Modernization | Features 10, 11, 12, 13, 14: `src/overlay/`, `src/preload/overlay-preload.js`, `src/main/mod-main.js` | M2 | PLANNED |
| M4 | Cascading Lyrics Engine | Features 15, 16, 17, 18, 19, 20: `src/main/mod-main.js` (`yandexMusicMod.fetchLyrics`) | M3 | PLANNED |
| M5 | Anti-Slop Settings Modal Redesign | Features 21, 22, 23, 24: `src/renderer/mod-renderer.js`, `src/renderer/mod-renderer.css`, `tools/build_css.py` | M1 | PLANNED |
| M6 | Final Verification, E2E Pass & Hardening | Feature 25: Pass 100% of E2E test suite (Tiers 1-4), verify.py, inject.py, test_app_run.py, Tier 5 hardening | M1, M2, M3, M4, M5 | PLANNED |

---

## Interface Contracts

### 1. Font System (`tools/build_css.py` ↔ `src/renderer/mod-renderer.js`)
- **CSS `@font-face` declarations**:
  - Inlined as `url("data:font/woff2;base64,...") format("woff2")`.
  - Families defined: `"JetBrains Mono"`, `"Minecraft"`, `"Andy Bold"`, `"Terraria"` (alias pointing to Andy Bold data URI), `"Press Start 2P"`, `"VT323"`, `"Uncut Sans"`.
- **Dynamic Style Injection**:
  - Tag: `<style id="ym-mod-custom-font-style">`.
  - Body: `* { font-family: "${fontFamily}", ... !important; }` with `font-size-adjust` and clamped scale `[0.5, 2.0]`.

### 2. Player State & Discord RPC (`src/renderer/` ↔ `src/main/` ↔ `src/main/discord-rpc.js`)
- **Renderer Push**:
  - Channel: `yandexMusicMod.updatePlayerState`
  - Payload: `{ track: { id, title, artists, albums, durationMs, coverUrl }, progress: { position, duration, speed }, isPlaying: boolean }`
- **Main Internal Cache**:
  - `lastPlayerState`: updated synchronously upon renderer push.
  - `updateDiscordActivity(playerData)`: evaluates `trackChanged` and sends immediate presence if track changed; seeks within track update presence without being blocked by 2000ms delay.
- **Poller Heartbeat**:
  - Poller runs every 1500ms; if `Date.now() - lastPlayerStateTimestamp < 3500ms`, poller skips execution.
- **Discord Socket**:
  - `DiscordRPC.setActivity(activity)`
  - Automatic reconnection watchdog runs every 15s when enabled and `!connected`.

### 3. Overlay & Lyrics Cache IPC (`src/main/mod-main.js` ↔ `src/preload/overlay-preload.js` ↔ `src/overlay/overlay.js`)
- **IPC Handlers**:
  - `ipcMain.handle("yandexMusicMod.getLastPlayerState", () => lastPlayerState)`
  - `ipcMain.handle("yandexMusicMod.getLastLyrics", () => lastLyricsData)`
- **Preload API**:
  - `window.overlayApi.getPlayerState(): Promise<PlayerState>`
  - `window.overlayApi.getLyrics(): Promise<LyricsPayload>`
- **Overlay Action Channel**:
  - `ipcRenderer.send("yandexMusicMod.overlayAction", action, payload)`
  - `mod-main.js` delivers `win.webContents.send("yandexMusicMod.executePlayerAction", action, payload)` (no duplicate `desktop:player:action`).

### 4. Cascading Lyrics IPC (`src/renderer/` / `src/overlay/` ↔ `src/main/mod-main.js`)
- **IPC Channel**:
  - `ipcMain.handle("yandexMusicMod.fetchLyrics", async (_ev, { trackId, trackTitle, trackArtist, duration }) => LyricsResult)`
- **Return Shape**:
  - `{ success: boolean, provider: "yandex" | "musixmatch" | "lrclib", isLrc: boolean, lyrics: string, syncLyrics: Array<{ time: number, line: string }> }`
- **Broadcast Events**:
  - `overlayWindow.webContents.send("overlay:lyricsUpdate", payload)`
  - `karaokeWindow.webContents.send("karaoke:lyricsUpdate", payload)`

---

## Code Layout

- `src/fonts/`: Font binaries (WOFF2). Owned by M1.
- `tools/build_css.py`: CSS font inliner generator. Owned by M1 & M5.
- `src/renderer/mod-renderer.css`: Master stylesheet (Base64 fonts + modal styles). Owned by M1 & M5.
- `src/renderer/mod-renderer.js`: DOM injector, font changer, settings modal. Owned by M1 & M5.
- `src/main/discord-rpc.js`: Discord IPC named pipe driver. Owned by M2.
- `src/main/mod-main.js`: Main process IPC, window managers, lyrics engine. Owned by M2, M3, M4.
- `src/preload/overlay-preload.js`: Overlay context bridge. Owned by M3.
- `src/overlay/`: HUD overlay HTML, CSS, JS. Owned by M3.
- `src/karaoke/`: Karaoke window assets. Owned by M4.
- `tools/verify.py`, `tools/inject.py`, `tools/test_app_run.py`: Acceptance verification tools. Used by M6 and all test gates.
- `tests/e2e/`: Requirement-driven E2E test suite. Owned exclusively by the E2E Testing Track.
