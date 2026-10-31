// Yandex Music Gaming HUD Overlay Controller (v1.3.7)
// Features: Apple Music MiniPlayer HUD, 1-in-1 synchronized rolling karaoke, expanded Apple Music lyrics view, 60fps interpolation

const isBrowser = typeof window !== "undefined" && typeof document !== "undefined";

let currentTrack = null;
let currentTrackKey = "";
let currentProgress = { position: 0, duration: 0 };
let isPlaying = false;
let isGhostMode = false;
let isExpandedLyrics = false;
let overlayLyrics = [];
let overlayLyricsIndex = -1;

// Interpolation state
let basePosition = 0;
let baseTimestamp = (typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now();
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
const overlayLyricPrev = isBrowser ? document.getElementById("overlay-lyric-prev") : null;
const overlayLyricsActive = isBrowser ? document.getElementById("overlay-lyrics-active") : null;
const overlayLyricNext = isBrowser ? document.getElementById("overlay-lyric-next") : null;

const overlayFullLyrics = isBrowser ? document.getElementById("overlay-full-lyrics") : null;
const fullLyricsScroll = isBrowser ? document.getElementById("full-lyrics-scroll") : null;

function normalizeCoverUrl(url) {
  if (!url || typeof url !== "string") return "";
  let clean = url.trim();
  if (!clean) return "";
  clean = clean.replace(/^music-application:\/?\/?/i, "");
  clean = clean.replace(/^(?:https?:\/?\/)+/i, "");
  clean = clean.replace(/^\/\//, "");
  clean = clean.replace("%%", "400x400");
  clean = clean.replace(/\/(?:50x50|100x100|200x200)\b/, "/400x400");
  return "https://" + clean;
}

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
        } else if (item.fromSec !== undefined) {
          t = Number(item.fromSec);
        } else if (item.time_seconds !== undefined) {
          t = Number(item.time_seconds);
        } else if (item.timestamp !== undefined) {
          t = Number(item.timestamp) > 1000 ? Number(item.timestamp) / 1000 : Number(item.timestamp);
        } else if (item.offset !== undefined) {
          t = Number(item.offset) > 1000 ? Number(item.offset) / 1000 : Number(item.offset);
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
  let globalOffsetMs = 0;

  for (const line of rawLines) {
    const offsetMatch = line.match(/^\[offset:\s*([+-]?\d+)\]/i);
    if (offsetMatch) {
      globalOffsetMs = parseInt(offsetMatch[1], 10) || 0;
      break;
    }
  }

  const tagRegex = /\[(\d{1,2}):(\d{2})(?:[.:](\d{1,3}))?\]/g;

  for (const line of rawLines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    if (/^\[([a-zA-Z][a-zA-Z0-9_-]*):\s*([^\]]*)\]/.test(trimmed)) continue;

    const timestamps = [];
    let match;
    tagRegex.lastIndex = 0;

    while ((match = tagRegex.exec(trimmed)) !== null) {
      const min = parseInt(match[1], 10);
      const sec = parseInt(match[2], 10);
      let ms = 0;
      if (match[3]) {
        const rawMs = match[3];
        if (rawMs.length === 1) ms = parseInt(rawMs, 10) * 100;
        else if (rawMs.length === 2) ms = parseInt(rawMs, 10) * 10;
        else ms = parseInt(rawMs, 10);
      }
      const time = Math.max(0, min * 60 + sec + (ms + globalOffsetMs) / 1000);
      timestamps.push(time);
    }

    if (timestamps.length > 0) {
      const text = trimmed.replace(tagRegex, "").trim();
      if (text) {
        for (const t of timestamps) {
          parsed.push({ time: t, text });
        }
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
  if (!overlayLyrics || overlayLyrics.length === 0) return;

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

    // 1. Update Compact Rolling 3-line strip
    if (found >= 0 && found < overlayLyrics.length) {
      if (overlayLyricPrev) overlayLyricPrev.textContent = found > 0 ? overlayLyrics[found - 1].text : "";
      if (overlayLyricsActive) overlayLyricsActive.textContent = overlayLyrics[found].text;
      if (overlayLyricNext) overlayLyricNext.textContent = found < overlayLyrics.length - 1 ? overlayLyrics[found + 1].text : "";
    } else if (found < 0) {
      if (overlayLyricPrev) overlayLyricPrev.textContent = "";
      if (overlayLyricsActive) overlayLyricsActive.textContent = overlayLyrics.length > 0 ? "♫ Вступление..." : "♫ Текст этой песни недоступен.";
      if (overlayLyricNext) overlayLyricNext.textContent = overlayLyrics[0] ? overlayLyrics[0].text : "";
    }

    // 2. Update Expanded Apple Music Lyrics View
    if (fullLyricsScroll) {
      const allLines = fullLyricsScroll.querySelectorAll(".full-lrc-line");
      allLines.forEach((el, idx) => {
        if (idx === found) {
          el.classList.add("active");
          el.scrollIntoView({ behavior: "smooth", block: "center" });
        } else {
          el.classList.remove("active");
        }
      });
    }
  }
}

function renderProgress(pos) {
  const dur = trackDuration > 0 ? trackDuration : (currentProgress && currentProgress.duration > 0 ? currentProgress.duration : 0);
  const percent = dur > 0 ? Math.min(100, Math.max(0, (pos / dur) * 100)) : 0;
  const rem = dur > pos ? dur - pos : 0;

  if (timeCurrent) timeCurrent.textContent = formatTime(pos);
  if (timeTotal) timeTotal.textContent = dur > 0 ? `-${formatTime(rem)}` : "0:00";
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
  } else {
    animFrameId = setTimeout(tickInterpolation, 16);
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
    } else {
      clearTimeout(animFrameId);
    }
    animFrameId = null;
  }
}

function renderFullLyricsUI() {
  if (!fullLyricsScroll) return;

  if (!overlayLyrics || overlayLyrics.length === 0) {
    fullLyricsScroll.innerHTML = `<div class="full-lyrics-empty">Текст этой песни недоступен.</div>`;
    return;
  }

  fullLyricsScroll.innerHTML = overlayLyrics
    .map((item, idx) => `<div class="full-lrc-line" data-idx="${idx}" data-time="${item.time}">${escapeHtml(item.text)}</div>`)
    .join("");

  fullLyricsScroll.querySelectorAll(".full-lrc-line").forEach((el) => {
    el.addEventListener("click", () => {
      const t = parseFloat(el.getAttribute("data-time"));
      if (!isNaN(t) && t >= 0) {
        basePosition = t;
        baseTimestamp = (typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now();
        renderProgress(t);
        if (typeof window !== "undefined" && window.overlayApi) {
          const sendFn = window.overlayApi.sendPlayerAction || window.overlayApi.sendAction;
          if (typeof sendFn === "function") {
            const dur = trackDuration > 0 ? trackDuration : (currentProgress && currentProgress.duration > 0 ? currentProgress.duration : 1);
            sendFn("seek", { position: t, progress: t / dur });
          }
        }
      }
    });
  });

  const pos = getInterpolatedPosition();
  syncLyricsPosition(pos);
}

function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function handleLyricsData(lyricsData) {
  if (!lyricsData) return;
  const src = lyricsData.lines || lyricsData.syncLyrics || lyricsData.lrc || lyricsData.lyrics;
  if (src) {
    const dur = trackDuration > 0 ? trackDuration : (currentProgress && currentProgress.duration > 0 ? currentProgress.duration : 0);
    overlayLyrics = parseLRC(src, dur);
    overlayLyricsIndex = -1;
    renderFullLyricsUI();
    if (overlayLyrics.length > 0) {
      const pos = getInterpolatedPosition();
      syncLyricsPosition(pos);
    } else if (overlayLyricsActive) {
      overlayLyricsActive.textContent = "♫ Текст этой песни недоступен.";
    }
  } else {
    overlayLyrics = [];
    overlayLyricsIndex = -1;
    renderFullLyricsUI();
    if (overlayLyricsActive) {
      overlayLyricsActive.textContent = "♫ Текст отсутствует";
    }
  }
}

// Update UI
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

  // 2. Track Transition & Metadata
  if (track) {
    const trackKey = (track.id ? String(track.id) : "") + "|" + (track.title || "") + "|" + (track.artists || "");
    const isNewTrack = trackKey !== currentTrackKey;

    if (isNewTrack) {
      currentTrackKey = trackKey;
      overlayLyrics = [];
      overlayLyricsIndex = -1;
      if (overlayLyricPrev) overlayLyricPrev.textContent = "";
      if (overlayLyricsActive) overlayLyricsActive.textContent = "♫ Загрузка текста...";
      if (overlayLyricNext) overlayLyricNext.textContent = "";
      renderFullLyricsUI();

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

    // Cover art extraction
    if (trackCover) {
      let rawCover = track.coverUrl || "";
      if (!rawCover && track.ogImage) {
        rawCover = track.ogImage;
      }
      const coverUrl = normalizeCoverUrl(rawCover);
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

  // 3. Progress Sync
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

function setLyricsExpanded(expanded) {
  isExpandedLyrics = expanded;
  if (!overlayCard) return;

  if (isExpandedLyrics) {
    overlayCard.classList.add("expanded");
    if (overlayFullLyrics) overlayFullLyrics.classList.remove("hidden");
    if (overlayLyricsContainer) overlayLyricsContainer.classList.add("hidden");
    if (btnLyricsToggle) btnLyricsToggle.classList.add("active");
    if (typeof window !== "undefined" && window.overlayApi && window.overlayApi.resizeOverlay) {
      window.overlayApi.resizeOverlay(480, 470);
    }
  } else {
    overlayCard.classList.remove("expanded");
    if (overlayFullLyrics) overlayFullLyrics.classList.add("hidden");
    if (overlayLyricsContainer) overlayLyricsContainer.classList.remove("hidden");
    if (btnLyricsToggle) btnLyricsToggle.classList.remove("active");
    if (typeof window !== "undefined" && window.overlayApi && window.overlayApi.resizeOverlay) {
      window.overlayApi.resizeOverlay(480, 220);
    }
  }
}

// Setup Event Listeners
function setupControls() {
  if (!btnPlay) return;

  btnPlay.addEventListener("click", () => {
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

  if (btnLyricsToggle) {
    btnLyricsToggle.addEventListener("click", () => {
      setLyricsExpanded(!isExpandedLyrics);
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

  // Seek
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
    ghostLabel.textContent = "Ghost";
    btnGhost.title = "Сквозной клик активен (Ctrl+Shift+G переключить). При наведении на HUD кнопки кликабельны.";
  } else {
    btnGhost.classList.remove("active");
    ghostLabel.textContent = "Клик";
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

function initOverlay() {
  if (typeof window === "undefined" || !window.overlayApi) return;

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

  // Pull immediately on startup
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
    normalizeCoverUrl,
  };
}
