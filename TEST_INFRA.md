# Test Infrastructure Specification: Yandex Music Mod

## 1. Overview & Principles

The test infrastructure provides an opaque-box, requirement-driven test suite designed to validate the Yandex Music Mod modernization project across all 25 features identified in `PROJECT.md` and `ORIGINAL_REQUEST.md`.

### Core Engineering Principles
1. **Opaque-Box Verification**: Tests validate behavior against documented interface contracts, mathematical properties, and specifications rather than implementation internals.
2. **Deterministic Independence**: Every test is self-contained and isolated. No test depends on the execution order or side-effects of another.
3. **Zero External Runtime Dependencies**: Built entirely using Python 3 standard libraries (`unittest`, `struct`, `hmac`, `hashlib`, `json`, `base64`), eliminating npm dependency drift or platform-specific node version incompatibilities.
4. **Progressive Testability**: Features are verified against contract specifications and simulated runtimes so tests run deterministically during concurrent worker milestone implementation.
5. **Authoritative Output Derivation**: Cryptographic signatures (Musixmatch HMAC-SHA1), LRC metadata tag cleansing, Discord IPC framing, and 60fps interpolation math are derived directly from authoritative specifications in `reference_sources/` and `PROJECT.md`.

---

## 2. Directory Layout

```
d:\Яндекс Музыка мод\
├── TEST_INFRA.md                   # This document
├── TEST_READY.md                   # Test suite readiness report and coverage matrix
├── tests/
│   └── e2e/
│       ├── __init__.py             # Test package initialization
│       ├── run_tests.py            # Standalone CLI test runner (exit code 0 on pass)
│       ├── harness/
│       │   ├── __init__.py         # Harness exports
│       │   ├── contracts.py        # Authoritative data classes, schemas, and constants
│       │   ├── oracles.py          # Reference calculation engines (HMAC, LRC, Discord, WOFF2)
│       │   └── simulators.py       # Mock Electron IPC, Discord Pipe daemon, Lyrics Cascade
│       ├── test_tier1_features.py  # Tier 1: 36 Feature coverage tests (Features 1-25)
│       ├── test_tier2_boundaries.py# Tier 2: 35 Boundary & corner case tests
│       ├── test_tier3_combinations.py # Tier 3: 10 Cross-feature pairwise interaction tests
│       └── test_tier4_journeys.py  # Tier 4: 5 Real-world application user journeys
```

---

## 3. Tier Methodology & Coverage Structure

The test suite is structured into four distinct verification tiers:

### Tier 1: Feature Coverage (Features 1–25)
- **Goal**: Verify every feature in isolation across all 6 functional domains with >= 5 equivalence-class tests per domain.
- **Scope**:
  - **Area 1: Fonts & Inlining (Features 1–4)**: WOFF2 Base64 data URI structure, Andy Bold / Terraria dual alias, dynamic universal font enforcement (`* { font-family: ... !important; }`), Uncut Sans asset specification, and scale factor clamping.
  - **Area 2: Discord RPC & Networking (Features 5–9)**: Socket error listener cleanup on connect, 5000ms handshake watchdog, 15s reconnect watchdog, poller vs. renderer race fix (>3.5s silence rule), and instant 0ms track dispatch.
  - **Area 3: Gaming HUD Overlay (Features 10–14)**: Cache pull handlers (`getLastPlayerState`, `getLastLyrics`), local 60fps interpolation calculation, control deduplication (no redundant `desktop:player:action`), optimistic UI state flipping, and track transition lyrics reset.
  - **Area 4: Cascading Lyrics Engine (Features 15–20)**: Yandex supplement request with session cookies, Musixmatch Android HMAC-SHA1 signer, Musixmatch fallback provider, LRCLib get + search fallback, LRC tag cleaner, and dual broadcast to overlay and karaoke.
  - **Area 5: Anti-Slop Settings UI (Features 21–24)**: Native dark smoked glass CSS (`rgba(20, 20, 24, 0.88)`, `blur(30px) saturate(170%)`, `18px` radius), 6-section sidebar tabs, compact graphite switches (36x20px, 16px thumb, `#fed42b`), and interface/font scale sliders.
  - **Area 6: Packaging & Toolchain Verification (Feature 25)**: ASAR pack/unpack byte-for-byte roundtrip, required source manifest verification, HUD overlay isolation (no renderer.js contamination), and SettingsManager schema defaults.
- **Total Tests**: 36 test cases.

### Tier 2: Boundary & Corner Cases
- **Goal**: Subject the mod's architecture to extreme boundaries, empty inputs, limits, offline conditions, and cascading failures with >= 5 tests per domain.
- **Scope**:
  - Empty, null, or special-character font names.
  - Scale factor clamping under extreme inputs (-50%, +500%).
  - Corrupted base64 font payloads and invalid WOFF2 headers.
  - Discord named pipe exhaustion (all 10 pipes unavailable).
  - Stalled Discord handshake timing out at 5001ms.
  - 0ms, negative, or NaN track durations in RPC presence formatting.
  - 500-character track title and artist string truncation.
  - Rapid concurrent reconnect spam idempotency.
  - Opening HUD overlay before any music has played (null state handling).
  - Calculated progress position exceeding track duration ($pos > dur$).
  - Negative playback position clamping.
  - Complete cascade failure (Yandex 404, Musixmatch blocked, LRCLib empty).
  - Track titles with complex parentheses, brackets, and Cyrillic text.
  - LRC files with plain text without timestamps or with 100 metadata headers.
  - Corrupted or empty `mod_settings.json` files.
  - ASAR corrupted headers, 0-byte files, and deep directory nesting.
- **Total Tests**: 35 test cases.

### Tier 3: Cross-Feature Combinations
- **Goal**: Verify pairwise cross-module interactions to prevent regressions at component boundaries.
- **Scope**:
  - **Pair 1**: Font enforcement in main renderer ↔ Scoped CSS isolation in HUD overlay.
  - **Pair 2**: Track switch event ↔ Simultaneous 0ms Discord RPC update & async lyrics trigger.
  - **Pair 3**: HUD overlay optimistic play click ↔ Renderer push & poller suppression.
  - **Pair 4**: Settings persistence on disk ↔ Rehydration and dynamic font style injection.
  - **Pair 5**: Musixmatch fallback lyrics resolution ↔ LRC tag cleaning & dual window broadcast.
  - **Pair 6**: UI cleaner settings toggles ↔ Uninterrupted audio element observer loop.
  - **Pair 7**: Discord RPC watchdog late reconnect ↔ Active track presence hydration.
  - **Pair 8**: Overlay cache pull on cold start ↔ Subsequent renderer push hydration.
  - **Pair 9**: Interface zoom scale ↔ Font size scale independence.
  - **Pair 10**: Musixmatch signer protocol ↔ Special Cyrillic & query parameter escaping.
- **Total Tests**: 10 test cases.

### Tier 4: Real-World Application Journeys
- **Goal**: Validate end-to-end user journeys replicating real-world interactive sessions from boot to shutdown.
- **Scope**:
  - **Journey 1: Cold App Launch & Mod Initialization**: App boot, SettingsManager loading, IPC handler mounting, window tracking, and Discord pipe handshake.
  - **Journey 2: Music Playback & Real-Time Sync**: Track playback start, instant 0ms Discord activity update, poller suppression, and forward seek handling.
  - **Journey 3: Cascading Lyrics Resolution & Dual Broadcast**: 3-tier cascade resolution across Yandex, Musixmatch, and LRCLib, tag stripping, and synchronized dispatch to HUD and Karaoke windows.
  - **Journey 4: Gaming HUD Overlay Interactive Session**: Overlay open, cache pull, 60fps interpolation, optimistic play/pause toggle, seek scrubbing, deduplicated action emit, and track transition reset.
  - **Journey 5: Anti-Slop Settings Customization & Persistence**: Native frosted glass modal, 6-tab navigation, Terraria font selection with dual alias, Discord toggle, atomic disk persistence.
- **Total Tests**: 5 test cases.

---

## 4. Test Harness Architecture & Oracles

### Contracts (`tests/e2e/harness/contracts.py`)
- Defines authoritative constants: `EMBEDDED_FONTS`, `FONT_SIZE_ADJUST_PRESETS`, `DISCORD_HANDSHAKE_TIMEOUT_MS` (5000ms), `DISCORD_WATCHDOG_INTERVAL_MS` (15000ms), `RENDERER_POLLER_SILENCE_THRESHOLD_MS` (3500ms), `MODAL_STYLE_SPECS`, and `SIDEBAR_TABS`.
- Data transfer objects: `TrackMetadata`, `PlayerProgress`, `PlayerState`, `LyricsPayload`, `LyricsLine`.

### Oracles (`tests/e2e/harness/oracles.py`)
- `compute_musixmatch_signature(original_url, dt, secret_key)`: Implements HMAC-SHA1 signature using secret `967Pn4)N3&R_GBg5$b('` and `yMMdd` date format matching Dalvik Android client.
- `clean_lrc_metadata_tags(raw_lrc)`: Strips `[ar:...]`, `[ti:...]`, `[al:...]`, `[length:...]`, `[by:...]` while preserving lyric lines.
- `parse_lrc_timestamps(lrc_text)`: Parses timestamp brackets into chronologically sorted `LyricsLine` objects.
- `interpolate_playback_position(base_pos, base_t, cur_t, duration, speed, is_playing)`: Evaluates $pos(t) = basePos + (t - baseTime) \times speed$ clamped to $[0, duration]$.
- `encode_discord_ipc_packet` / `decode_discord_ipc_packet`: Validates Opcode 0 (Handshake) and Opcode 1 (Frame) packets.
- `validate_woff2_bytes`: Validates WOFF2 binary signature (`wOF2` magic number `0x774F4632`).

### Simulators (`tests/e2e/harness/simulators.py`)
- `MockElectronIPC`: Emulates Electron `ipcMain` and `ipcRenderer` invoke/handle and push/listen mechanics.
- `MockBrowserWindow`: Emulates Electron BrowserWindow and WebContents with message capture.
- `MockDiscordServer`: Simulates a local Discord named pipe (`\\.\pipe\discord-ipc-0`) responding to handshakes and logging activity updates.
- `MockCascadingLyricsEngine`: Emulates Yandex Music Supplement, Musixmatch Android API, and LRCLib endpoints with configurable failure and timeout modes.

---

## 5. Execution Instructions

### Running the Full Test Suite
```bash
python tests/e2e/run_tests.py
```

### Running Specific Tiers
```bash
# Tier 1 only (Feature Coverage)
python tests/e2e/run_tests.py --tier=1

# Tier 2 only (Boundary & Corner Cases)
python tests/e2e/run_tests.py --tier=2

# Tier 3 only (Cross-Feature Combinations)
python tests/e2e/run_tests.py --tier=3

# Tier 4 only (Real-World Journeys)
python tests/e2e/run_tests.py --tier=4
```

### Running in Verbose Mode
```bash
python tests/e2e/run_tests.py -v
```

### Running via Python unittest Discover
```bash
python -m unittest discover -s tests/e2e -t .
```

---

## 6. Acceptance & Quality Gates

The test runner exits with code **0** upon 100% test success and code **1** if any failure occurs.
All tests execute in **< 0.100s**, allowing instant regression verification during CI/CD build cycles and local development.
