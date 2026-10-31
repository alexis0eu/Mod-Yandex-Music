# Design Document: Apple Music MiniPlayer HUD & Playback Engine Overhaul (v1.3.9)

## 1. Intent & The Why
The existing desktop overlay suffers from multiple visual and functional defects:
- An unappealing ambient glow and an empty bottom area that created a giant black box on the user's screen.
- A frozen timeline (`0:00 / -0:00`) and lyrics displaying `"♫ Текст этой песни недоступен."` due to detached audio elements in the `Yasp` engine.
- Play, pause, next, previous, and volume buttons that fail to trigger actions because DOM selectors did not account for all Yandex Music button variations (e.g. `MY_VIBE_PLAY_BUTTON`, `NEXT_TRACK_BUTTON`).
- A permanently active (red heart) like button due to incorrect class matching.
- Track metadata and cover art failing to extract when playing from the "Коллекция" page because React Fiber stores track data in `.track` rather than `.entityMeta`.
- Official app update banners (e.g. "ДОСТУПНА ВЕРСИЯ 5.125.3") continuing to show despite blocking attempts.
- Lyrics styling corrupted by global Halloween gothic fonts rather than clean, native Apple Music typography.

The goal is to deliver an authentic, high-performance Apple Music macOS-style MiniPlayer HUD with real-time 1-in-1 audio synchronized lyrics, responsive controls, universal metadata extraction, and a clean frosted glass design.

---

## 2. Goals, Non-Goals & Anti-Goals

### Goals
1. **Clean Visuals**: Remove all messy ambient glow layers and ugly gradients. Default the MiniPlayer to a compact card (~165px height) with sleek Apple frosted glass (`background: rgba(28, 28, 30, 0.96); backdrop-filter: blur(40px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px;`).
2. **On-Demand Lyrics Expansion**: Only expand the window downward (to ~480px) when the user clicks the lyrics toggle button (`💬`), and only if lyrics are present.
3. **1-in-1 Synced Lyrics**: Interpolate audio position at 60 FPS using `window.__ymGetActiveAudio()`. Render lyrics in clean SF Pro / Inter font (never Halloween font), with the active line in bold white (`#ffffff`) and inactive lines softly dimmed (`rgba(255, 255, 255, 0.35)`).
4. **Universal Track & Cover Extraction**: React Fiber inspection must support `.track` (Collection, playlists, albums) in addition to `.entityMeta` (My Wave). Fallback to URL parsing (`/track/{id}`) or search API to ensure `trackId` is always available for the Yandex Supplement API.
5. **Fully Working HUD Controls**: All buttons (Play/Pause, Prev, Next, Like, Volume, Lyrics) must work reliably across all page states, with fallback to direct audio engine methods.
6. **Like Button Accuracy**: Check `likeButton_active` and `aria-checked="true"` to prevent false positive liked states.
7. **Block Update Banner**: Intercept `IpcChannel.UPDATE_AVAILABLE` in preload and hide `.NotificationUpdate_root` via CSS.

### Non-Goals
- Keeping the old transparent Gaming HUD (the user explicitly opted for "только новый").
- Showing ambient background glow or dynamic album color bleeding outside the card.

### Anti-Goals
- No layout shifts or unwanted window resizing when changing songs.
- No bleeding of seasonal/Halloween themes into the lyrics or overlay text.
- No click-through or ghost mode locking mouse events on interactive buttons.

---

## 3. Approaches Considered & Selected

### Approach 1: Native Apple Music Engine (Selected by User)
- **Design**: Strict adherence to macOS Apple Music MiniPlayer. Clean frosted acrylic card without ambient glow or huge blank areas.
- **Behavior**: Opens compact (~165px). Expands to ~480px only when lyrics are requested and available.
- **Lyrics**: Apple Music layout, bold white active line, smooth centering scroll, clean sans-serif typography.
- **Engine**: Direct hook into `window.__ymGetActiveAudio()` for exact sub-second position, full Fiber property inspection (`.track` and `.entityMeta`).
- **Verdict**: Chosen for stability, aesthetic clarity, and direct alignment with user expectations.

### Approach 2: Automatic Height Resizing Docker (Rejected)
- Automatically grows and shrinks the window height depending on whether the current song has lyrics.
- **Trade-off**: Causes annoying visual popping and window jumping on the desktop with every song change.

---

## 4. Architectural Details

### 4.1 Overlay Window & CSS (`src/overlay/overlay.html`, `overlay.css`, `overlay.js`)
- Remove `.am-ambient-glow` and any pseudo-elements creating blurry background halos.
- Default window height to `165px` in `src/main/mod-main.js` and `overlay.js`.
- In `setViewMode("compact")`, resize window to `(380, 165)`. In `setViewMode("lyrics")`, resize to `(380, 480)`.
- Apply strict typography to lyrics: `-apple-system, BlinkMacSystemFont, "SF Pro Display", "Inter", sans-serif !important;`.
- Active lyric style: `font-size: 22px; font-weight: 700; color: #ffffff; opacity: 1; transform: scale(1.02); transition: all 0.25s ease;`.
- Inactive lyric style: `font-size: 19px; font-weight: 600; color: rgba(255, 255, 255, 0.35); filter: blur(0.3px);`.

### 4.2 State Scraping & Remote Control (`src/renderer/mod-renderer.js`)
- Update `extractSonataStateFromFiber()` to inspect `track`, `entityMeta`, and `sonataState`.
- In `scrapeCurrentPlayerState()`, retrieve playback position and duration from `window.__ymGetActiveAudio()` first, then audio elements.
- In `handlePlayerAction()`:
  - Play/pause: Query `button[data-test-id="MY_VIBE_PLAY_BUTTON"]`, `button[data-test-id="MY_VIBE_PAUSE_BUTTON"]`, `button[data-test-id="PLAY_BUTTON"]`, `button[data-test-id="PAUSE_BUTTON"]`. Fallback to `activeAudio.paused ? activeAudio.play() : activeAudio.pause()`.
  - Next/Prev: Query `button[data-test-id="NEXT_TRACK_BUTTON"]`, `button[data-test-id="PREVIOUS_TRACK_BUTTON"]`, `button[data-test-id="NEXT_BUTTON"]`, `button[data-test-id="PREV_BUTTON"]`.
  - Like: Query `button[data-test-id="LIKE_BUTTON"]`. Check active state via `likeButton_active` or `aria-checked="true"`.
- Block official update notification:
  - In `src/preload/mod-preload.js`, stub `window.musicDesktop.app.onUpdateAvailable = () => () => {};`.
  - In `src/renderer/mod-renderer.css`, hide `div[class*="NotificationUpdate_root"]`, `[data-test-id*="APP_UPDATE_NOTIFICATION_BUTTON"]`.

---

## 5. What's Left to the Builder
- Implementing the precise CSS and JS updates.
- Verifying regression tests with `tools/verify.py`.
- Re-injecting with `tools/inject.py` into local Yandex Music install.
- Compiling native NSIS installer and publishing release tag `v1.3.9`.
