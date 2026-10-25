// Yandex Music Gaming HUD Overlay Controller
// Features 10-14: Immediate cache delivery, 60fps interpolation timer, optimistic controls, lyrics sync

const isBrowser = typeof window !== "undefined" && typeof document !== "undefined";

let currentTrack = null;
let currentProgress = { position: 0, duration: 0 };
let isPlaying = false;
let isGhostMode = false;
let overlayLyrics = [];
let overlayLyricsIndex = -1;

// Interpolation state
let basePosition = 0;
let baseTimestamp = (typeof performance !== "undefined" && performance.now) ? performance.now() : 0;
let trackDuration = 0;
let playbackSpeed = 1.0;
let animFrameId = null;

// DOM Elements
const trackTitle = isBrowser ? document.getElementById("track-title") : null;
const trackArtist = isBrowser ? document.getElementById("track-artist") : null;
const trackCover = isBrowser ? document.getElementById("track-cover") : null;
const statusDot = isBrowser ? document.getElementById("status-dot") : null;
const eqBars = isBrowser ? document.getElementById("eq-bars") : null;

const timeCurrent = isBrowser ? document.getElementById("time-current") : null;
const timeTotal = isBrowser ? document.getElementById("time-total") : null;
const progressBarContainer = isBrowser ? document.getElementById("progress-bar-container") : null;
const progressBarFill = isBrowser ? document.getElementById("progress-bar-fill") : null;
const progressBarThumb = isBrowser ? document.getElementById("progress-bar-thumb") : null;

const btnPlay = isBrowser ? document.getElementById("btn-play") : null;
const iconPlay = isBrowser ? document.getElementById("icon-play") : null;
const iconPause = isBrowser ? document.getElementById("icon-pause") : null;
const btnPrev = isBrowser ? document.getElementById("btn-prev") : null;
const btnNext = isBrowser ? document.getElementById("btn-next") : null;
const btnLike = isBrowser ? document.getElementById("btn-like") : null;

const btnGhost = isBrowser ? document.getElementById("btn-ghost") : null;
const ghostLabel = isBrowser ? document.getElementById("ghost-label") : null;
const btnLyricsToggle = isBrowser ? document.getElementById("btn-lyrics-toggle") : null;
const btnKaraoke = isBrowser ? document.getElementById("btn-karaoke") : null;
const btnClose = isBrowser ? document.getElementById("btn-close") : null;
const overlayCard = isBrowser ? document.getElementById("overlay-card") : null;
const overlayLyricsContainer = isBrowser ? document.getElementById("overlay-lyrics-container") : null;
const overlayLyricsActive = isBrowser ? document.getElementById("overlay-lyrics-active") : null;

/**
 * Feature 11: Pure interpolation calculator.
 * pos(t) = basePosition + (now - baseTimestamp) / 1000 * speed (clamped to [0, duration])
 */
function interpolatePosition(basePos, baseTs, nowTs, duration, speed, playing) {
  const dur = Number(duration) > 0 ? Number(duration) : Infinity;
  const spd = typeof speed === "number" && speed > 0 ? speed : 1.0;
  if (!playing || spd <= 0) {
    return Math.max(0, Math.min(Number(basePos) || 0, dur));
  }
  const elapsed = Math.max(0, ((Number(nowTs) || 0) - (Number(baseTs) || 0)) / 1000.0);
  const calculated = (Number(basePos) || 0) + elapsed * spd;
  return Math.max(0, Math.min(calculated, dur));
}

function getInterpolatedPosition() {
  const now = (typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now();
  return interpolatePosition(basePosition, baseTimestamp, now, trackDuration, playbackSpeed, isPlaying);
}

function formatTime(seconds) {
  if (!seconds || isNaN(seconds) || seconds < 0) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s < 10 ? "0" : ""}${s}`;
}

function parseLRC(lrcText, duration = 0) {
  if (!lrcText) return [];
  if (Array.isArray(lrcText)) {
    return lrcText
      .map((item) => {
        let t = 0;
        if (item.time !== undefined) {
          t = Number(item.time);
        } else if (item.time_seconds !== undefined) {
          t = Number(item.time_seconds);
        } else if (item.timestamp !== undefined) {
          t = Number(item.timestamp) > 1000 ? Number(item.timestamp) / 1000 : Number(item.timestamp);
        }
        return {
          time: t,
          text: item.text || item.line || "",
        };
      })
      .filter((x) => x.text)
      .sort((a, b) => a.time - b.time);
  }

  if (typeof lrcText !== "string") return [];
  const rawLines = lrcText.split("\n");
  const parsed = [];
  const regex = /\[(\d{1,2}):(\d{2})(?:[.:](\d{1,3}))?\](.*)/;

  for (const line of rawLines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    // Skip metadata headers e.g. [ti:Song], [ar:Artist]
    if (/^\[([a-zA-Z][a-zA-Z0-9_-]*):\s*([^\]]*)\]/.test(trimmed)) continue;

    const match = regex.exec(trimmed);
    if (match) {
      const min = parseInt(match[1], 10);
      const sec = parseInt(match[2], 10);
      let ms = 0;
      if (match[3]) {
        const rawMs = match[3];
        if (rawMs.length === 1) ms = parseInt(rawMs, 10) * 100;
        else if (rawMs.length === 2) ms = parseInt(rawMs, 10) * 10;
        else ms = parseInt(rawMs, 10);
      }
      const time = min * 60 + sec + ms / 1000;
      const text = match[4].trim();
      if (text) {
        parsed.push({ time, text });
      }
    }
  }

  if (parsed.length === 0) {
    const cleanLines = rawLines.map((l) => l.trim()).filter((l) => l.length > 0 && !/^\[.*\]/.test(l));
    const dur = duration > 10 ? duration : Math.max(30, cleanLines.length * 4);
    const step = dur / Math.max(1, cleanLines.length);
    cleanLines.forEach((text, i) => {
      parsed.push({ time: Math.round(i * step * 10) / 10, text });
    });
  }

  return parsed.sort((a, b) => a.time - b.time);
}

function syncLyricsPosition(position) {
  if (!overlayLyrics || overlayLyrics.length === 0 || !overlayLyricsActive) return;
  let found = -1;
  for (let i = 0; i < overlayLyrics.length; i++) {
    if (position >= overlayLyrics[i].time) {
      found = i;
    } else {
      break;
    }
  }

  if (found !== overlayLyricsIndex) {
    overlayLyricsIndex = found;
    if (found >= 0 && found < overlayLyrics.length) {
      overlayLyricsActive.textContent = overlayLyrics[found].text;
    } else if (found < 0 && overlayLyrics.length > 0) {
      overlayLyricsActive.textContent = "♫ Вступление...";
    }
  }
}

function renderProgress(pos) {
  const dur = trackDuration > 0 ? trackDuration : (currentProgress && currentProgress.duration > 0 ? currentProgress.duration : 0);
  const percent = dur > 0 ? Math.min(100, Math.max(0, (pos / dur) * 100)) : 0;

  if (timeCurrent) timeCurrent.textContent = formatTime(pos);
  if (dur > 0 && timeTotal) timeTotal.textContent = formatTime(dur);
  if (progressBarFill) progressBarFill.style.width = `${percent}%`;
  if (progressBarThumb) progressBarThumb.style.left = `${percent}%`;

  syncLyricsPosition(pos);
}

function tickInterpolation() {
  if (!isPlaying) {
    stopInterpolation();
    return;
  }

  const pos = getInterpolatedPosition();
  renderProgress(pos);

  if (trackDuration > 0 && pos >= trackDuration) {
    stopInterpolation();
    return;
  }

  scheduleNextTick();
}

function scheduleNextTick() {
  if (!isPlaying) return;
  if (typeof requestAnimationFrame === "function") {
    animFrameId = requestAnimationFrame(tickInterpolation);
  } else if (typeof setTimeout === "function") {
    animFrameId = setTimeout(tickInterpolation, 16);
    if (animFrameId && typeof animFrameId.unref === "function") {
      animFrameId.unref();
    }
  }
}

function startInterpolation() {
  stopInterpolation();
  if (isPlaying) {
    scheduleNextTick();
  }
}

function stopInterpolation() {
  if (animFrameId !== null) {
    if (typeof cancelAnimationFrame === "function") {
      cancelAnimationFrame(animFrameId);
    } else if (typeof clearTimeout === "function") {
      clearTimeout(animFrameId);
    }
    animFrameId = null;
  }
}

function handleLyricsData(lyricsData) {
  if (!lyricsData) return;
  const src = lyricsData.syncLyrics || lyricsData.lrc || lyricsData.lines || lyricsData.lyrics;
  if (src) {
    const dur = trackDuration > 0 ? trackDuration : (currentProgress && currentProgress.duration > 0 ? currentProgress.duration : 0);
    overlayLyrics = parseLRC(src, dur);
    overlayLyricsIndex = -1;
    if (overlayLyrics.length > 0) {
      const pos = getInterpolatedPosition();
      syncLyricsPosition(pos);
    } else if (overlayLyricsActive) {
      overlayLyricsActive.textContent = "♫ Текст песни не найден";
    }
  } else {
    overlayLyrics = [];
    overlayLyricsIndex = -1;
    if (overlayLyricsActive) {
      overlayLyricsActive.textContent = "♫ Текст отсутствует";
    }
  }
}

// Format and set track info
function updateUI(state) {
  if (!state) return;
  const { track, progress, isPlaying: playing } = state;

  isPlaying = !!playing;

  // 1. Play / Pause Visual State
  if (isPlaying) {
    if (iconPlay) iconPlay.classList.add("hidden");
    if (iconPause) iconPause.classList.remove("hidden");
    if (statusDot) statusDot.classList.remove("paused");
    if (eqBars) eqBars.classList.add("playing");
  } else {
    if (iconPlay) iconPlay.classList.remove("hidden");
    if (iconPause) iconPause.classList.add("hidden");
    if (statusDot) statusDot.classList.add("paused");
    if (eqBars) eqBars.classList.remove("playing");
  }

  // 2. Track Transition & Metadata (Feature 14)
  if (track) {
    const isNewTrack = !currentTrack || currentTrack.id !== track.id;
    if (isNewTrack) {
      // Feature 14: Immediately reset lyrics on track change to prevent lingering
      overlayLyrics = [];
      overlayLyricsIndex = -1;
      if (overlayLyricsActive) {
        overlayLyricsActive.textContent = "♫ Загрузка текста...";
      }
      basePosition = 0;
      baseTimestamp = (typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now();
      if (track.durationMs) {
        trackDuration = track.durationMs / 1000;
      }
    }
    currentTrack = track;

    if (trackTitle) trackTitle.textContent = track.title || "Трек не воспроизводится";

    const artists = Array.isArray(track.artists)
      ? track.artists.map((a) => (typeof a === "object" ? a.name : a)).join(", ")
      : track.artists || "Исполнитель не указан";
    if (trackArtist) trackArtist.textContent = artists;

    // Cover art
    if (trackCover) {
      let coverUrl = track.coverUrl || "";
      if (!coverUrl && track.ogImage) {
        coverUrl = "https://" + track.ogImage.replace("%%", "400x400");
      }
      if (coverUrl && coverUrl.startsWith("//")) {
        coverUrl = "https:" + coverUrl;
      }
      if (coverUrl && trackCover.src !== coverUrl) {
        trackCover.src = coverUrl;
      }
      trackCover.onerror = () => {
        trackCover.src = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='100' height='100' viewBox='0 0 24 24' fill='%23777'><path d='M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z'/></svg>";
      };
    }

    if (btnLike) {
      if (track.liked) {
        btnLike.classList.add("liked");
      } else {
        btnLike.classList.remove("liked");
      }
    }
  }

  // 3. Progress Sync & Timer Management (Feature 11)
  if (progress) {
    const newPos = Number(progress.position) || 0;
    const newDur = Number(progress.duration) || 0;
    const newSpeed = Number(progress.speed) || 1.0;

    basePosition = newPos;
    baseTimestamp = (typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now();
    if (newDur > 0) trackDuration = newDur;
    playbackSpeed = newSpeed > 0 ? newSpeed : 1.0;

    currentProgress = {
      position: newPos,
      duration: trackDuration,
    };

    renderProgress(basePosition);
  }

  // 4. Timer control based on active state
  if (isPlaying) {
    startInterpolation();
  } else {
    stopInterpolation();
  }
}

// Setup Event Listeners
function setupControls() {
  if (!btnPlay) return;

  btnPlay.addEventListener("click", () => {
    // Feature 13: Optimistic play/pause toggle
    isPlaying = !isPlaying;
    if (isPlaying) {
      if (iconPlay) iconPlay.classList.add("hidden");
      if (iconPause) iconPause.classList.remove("hidden");
      if (statusDot) statusDot.classList.remove("paused");
      if (eqBars) eqBars.classList.add("playing");
      baseTimestamp = (typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now();
      startInterpolation();
    } else {
      if (iconPlay) iconPlay.classList.remove("hidden");
      if (iconPause) iconPause.classList.add("hidden");
      if (statusDot) statusDot.classList.add("paused");
      if (eqBars) eqBars.classList.remove("playing");
      basePosition = getInterpolatedPosition();
      baseTimestamp = (typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now();
      stopInterpolation();
      renderProgress(basePosition);
    }

    if (typeof window !== "undefined" && window.overlayApi) {
      const sendFn = window.overlayApi.sendPlayerAction || window.overlayApi.sendAction;
      if (typeof sendFn === "function") {
        sendFn("playPause");
      }
    }
  });

  if (btnPrev) {
    btnPrev.addEventListener("click", () => {
      if (typeof window !== "undefined" && window.overlayApi) {
        const sendFn = window.overlayApi.sendPlayerAction || window.overlayApi.sendAction;
        if (typeof sendFn === "function") sendFn("prev");
      }
    });
  }

  if (btnNext) {
    btnNext.addEventListener("click", () => {
      if (typeof window !== "undefined" && window.overlayApi) {
        const sendFn = window.overlayApi.sendPlayerAction || window.overlayApi.sendAction;
        if (typeof sendFn === "function") sendFn("next");
      }
    });
  }

  if (btnLike) {
    btnLike.addEventListener("click", () => {
      btnLike.classList.toggle("liked");
      if (typeof window !== "undefined" && window.overlayApi) {
        const sendFn = window.overlayApi.sendPlayerAction || window.overlayApi.sendAction;
        if (typeof sendFn === "function") sendFn("like");
      }
    });
  }

  if (btnLyricsToggle && overlayLyricsContainer) {
    btnLyricsToggle.addEventListener("click", () => {
      overlayLyricsContainer.classList.toggle("collapsed");
      btnLyricsToggle.classList.toggle("active");
    });
  }

  if (btnKaraoke) {
    btnKaraoke.addEventListener("click", () => {
      if (typeof window !== "undefined" && window.overlayApi && window.overlayApi.toggleKaraoke) {
        window.overlayApi.toggleKaraoke();
      }
    });
  }

  if (btnClose) {
    btnClose.addEventListener("click", () => {
      if (typeof window !== "undefined" && window.overlayApi && window.overlayApi.toggleOverlay) {
        window.overlayApi.toggleOverlay();
      }
    });
  }

  // Ghost Mode Toggle Button
  if (btnGhost) {
    btnGhost.addEventListener("click", () => {
      isGhostMode = !isGhostMode;
      if (typeof window !== "undefined" && window.overlayApi) {
        if (window.overlayApi.setClickThrough) window.overlayApi.setClickThrough(isGhostMode);
        updateGhostModeUI();
        if (isGhostMode && window.overlayApi.setIgnoreMouseEvents) {
          window.overlayApi.setIgnoreMouseEvents(true, true);
        } else if (window.overlayApi.setIgnoreMouseEvents) {
          window.overlayApi.setIgnoreMouseEvents(false);
        }
      }
    });
  }

  // Feature 13: Optimistic Seek
  if (progressBarContainer) {
    progressBarContainer.addEventListener("click", (e) => {
      const rect = progressBarContainer.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const percent = Math.max(0, Math.min(1, clickX / rect.width));
      const dur = trackDuration > 0 ? trackDuration : (currentProgress && currentProgress.duration > 0 ? currentProgress.duration : 0);
      const seekSeconds = percent * dur;

      basePosition = seekSeconds;
      baseTimestamp = (typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now();
      if (currentProgress) currentProgress.position = seekSeconds;

      renderProgress(seekSeconds);

      if (typeof window !== "undefined" && window.overlayApi) {
        const sendFn = window.overlayApi.sendPlayerAction || window.overlayApi.sendAction;
        if (typeof sendFn === "function") {
          sendFn("seek", { position: seekSeconds, progress: percent });
        }
      }
    });
  }

  // Dynamic hover detection for Ghost mode
  if (overlayCard) {
    overlayCard.addEventListener("mouseenter", () => {
      if (isGhostMode && typeof window !== "undefined" && window.overlayApi && window.overlayApi.setIgnoreMouseEvents) {
        window.overlayApi.setIgnoreMouseEvents(false);
      }
    });

    overlayCard.addEventListener("mouseleave", () => {
      if (isGhostMode && typeof window !== "undefined" && window.overlayApi && window.overlayApi.setIgnoreMouseEvents) {
        window.overlayApi.setIgnoreMouseEvents(true, true);
      }
    });
  }
}

function updateGhostModeUI() {
  if (!btnGhost || !ghostLabel) return;
  if (isGhostMode) {
    btnGhost.classList.add("active");
    ghostLabel.textContent = "Сквозной (Ghost)";
    btnGhost.title = "Сквозной клик активен (Ctrl+Shift+G переключить). При наведении на HUD кнопки кликабельны.";
  } else {
    btnGhost.classList.remove("active");
    ghostLabel.textContent = "Кликабельный";
    btnGhost.title = "Обычный режим кликов (Ctrl+Shift+G переключить)";
  }
}

// Accent Color from Settings
async function applyAccentColor() {
  if (typeof window === "undefined" || !window.overlayApi || !window.overlayApi.getStorageValue) return;
  try {
    const accent = await window.overlayApi.getStorageValue("custom-themes/accent");
    if (accent && document.documentElement) {
      document.documentElement.style.setProperty("--accent", accent);
      document.documentElement.style.setProperty("--accent-glow", `${accent}66`);
    }
  } catch (e) {}
}

// Feature 10: Initialize & Immediate cache delivery via IPC pull
function initOverlay() {
  if (typeof window === "undefined" || !window.overlayApi) return;

  // Push listeners
  if (window.overlayApi.onTrackUpdate) {
    window.overlayApi.onTrackUpdate((state) => {
      updateUI(state);
    });
  }

  if (window.overlayApi.onLyricsUpdate) {
    window.overlayApi.onLyricsUpdate((lyricsData) => {
      handleLyricsData(lyricsData);
    });
  }

  // Pull immediately on startup to eliminate cold-start blank state (Feature 10)
  const pullStateFn = window.overlayApi.getPlayerState || window.overlayApi.getLastPlayerState;
  if (typeof pullStateFn === "function") {
    pullStateFn()
      .then((state) => {
        if (state && (state.track || state.progress !== undefined || state.isPlaying !== undefined)) {
          updateUI(state);
        } else if (window.overlayApi.sendPlayerAction) {
          window.overlayApi.sendPlayerAction("requestState");
        }
      })
      .catch(() => {
        if (window.overlayApi.sendPlayerAction) {
          window.overlayApi.sendPlayerAction("requestState");
        }
      });
  }

  const pullLyricsFn = window.overlayApi.getLyrics || window.overlayApi.getLastLyrics;
  if (typeof pullLyricsFn === "function") {
    pullLyricsFn()
      .then((lyricsData) => {
        if (lyricsData) handleLyricsData(lyricsData);
      })
      .catch(() => {});
  }

  if (window.overlayApi.onStorageChanged) {
    window.overlayApi.onStorageChanged((key, value) => {
      if (key === "custom-themes/accent") {
        if (document.documentElement) {
          document.documentElement.style.setProperty("--accent", value);
          document.documentElement.style.setProperty("--accent-glow", `${value}66`);
        }
      } else if (key === "overlay/clickThrough") {
        isGhostMode = !!value;
        updateGhostModeUI();
      } else if (key === "overlay/showLyrics") {
        if (overlayLyricsContainer) {
          overlayLyricsContainer.style.display = value === false ? "none" : "";
        }
      }
    });
  }

  if (window.overlayApi.onGhostModeToggled) {
    window.overlayApi.onGhostModeToggled((enabled) => {
      isGhostMode = !!enabled;
      updateGhostModeUI();
      if (isGhostMode && window.overlayApi.setIgnoreMouseEvents) {
        window.overlayApi.setIgnoreMouseEvents(true, true);
      } else if (window.overlayApi.setIgnoreMouseEvents) {
        window.overlayApi.setIgnoreMouseEvents(false);
      }
    });
  }

  if (window.overlayApi.getStorageValue) {
    window.overlayApi
      .getStorageValue("overlay/clickThrough")
      .then((val) => {
        isGhostMode = !!val;
        updateGhostModeUI();
      })
      .catch(() => {});

    window.overlayApi
      .getStorageValue("overlay/showLyrics")
      .then((val) => {
        if (overlayLyricsContainer && val === false) {
          overlayLyricsContainer.style.display = "none";
        }
      })
      .catch(() => {});
  }

  applyAccentColor();
}

if (isBrowser) {
  setupControls();
  initOverlay();
}

// Export for Node/unit test environments
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    interpolatePosition,
    getInterpolatedPosition,
    formatTime,
    parseLRC,
    syncLyricsPosition,
    renderProgress,
    updateUI,
    handleLyricsData,
    setupControls,
    initOverlay,
    startInterpolation,
    stopInterpolation,
    getState: () => ({
      currentTrack,
      currentProgress,
      isPlaying,
      overlayLyrics,
      overlayLyricsIndex,
      basePosition,
      baseTimestamp,
      trackDuration,
      playbackSpeed,
    }),
    setState: (newState) => {
      if (newState.currentTrack !== undefined) currentTrack = newState.currentTrack;
      if (newState.currentProgress !== undefined) currentProgress = newState.currentProgress;
      if (newState.isPlaying !== undefined) isPlaying = newState.isPlaying;
      if (newState.overlayLyrics !== undefined) overlayLyrics = newState.overlayLyrics;
      if (newState.overlayLyricsIndex !== undefined) overlayLyricsIndex = newState.overlayLyricsIndex;
      if (newState.basePosition !== undefined) basePosition = newState.basePosition;
      if (newState.baseTimestamp !== undefined) baseTimestamp = newState.baseTimestamp;
      if (newState.trackDuration !== undefined) trackDuration = newState.trackDuration;
      if (newState.playbackSpeed !== undefined) playbackSpeed = newState.playbackSpeed;
    },
    resetState: () => {
      currentTrack = null;
      currentProgress = { position: 0, duration: 0 };
      isPlaying = false;
      overlayLyrics = [];
      overlayLyricsIndex = -1;
      basePosition = 0;
      baseTimestamp = (typeof performance !== "undefined" && performance.now) ? performance.now() : 0;
      trackDuration = 0;
      playbackSpeed = 1.0;
      stopInterpolation();
    },
  };
}
