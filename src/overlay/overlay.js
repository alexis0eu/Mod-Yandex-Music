// Apple Music macOS MiniPlayer Overlay Controller (v1.3.11)
// Real-time 60fps interpolation, 1-in-1 lyrics synchronization, smooth centering scroll, click-to-seek

const isBrowser = typeof window !== "undefined" && typeof document !== "undefined";

let currentTrack = null;
let currentTrackKey = "";
let isPlaying = false;
let isGhostMode = false;
let currentViewMode = "compact"; // "compact" | "lyrics" | "artwork"

let overlayLyrics = [];
let overlayLyricsIndex = -1;
let lyricsTrackKey = "";

// 60fps interpolation state
let basePosition = 0;
let baseTimestamp = (typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now();
let trackDuration = 0;
let playbackSpeed = 1.0;
let animFrameId = null;

// DOM Elements
const playerCard = isBrowser ? document.getElementById("am-player-card") : null;
const amCover = isBrowser ? document.getElementById("am-cover") : null;
const amLargeArt = isBrowser ? document.getElementById("am-large-art") : null;
const coverWrap = isBrowser ? document.getElementById("am-cover-wrap") : null;

const amTitle = isBrowser ? document.getElementById("am-title") : null;
const amArtist = isBrowser ? document.getElementById("am-artist") : null;

const timeCurrent = isBrowser ? document.getElementById("am-time-current") : null;
const timeRemaining = isBrowser ? document.getElementById("am-time-remaining") : null;
const sliderTrack = isBrowser ? document.getElementById("am-slider-track") : null;
const sliderFill = isBrowser ? document.getElementById("am-slider-fill") : null;
const sliderThumb = isBrowser ? document.getElementById("am-slider-thumb") : null;

const compactKaraoke = isBrowser ? document.getElementById("am-compact-karaoke") : null;
const compactLine = isBrowser ? document.getElementById("am-compact-line") : null;

const expandedLyrics = isBrowser ? document.getElementById("am-expanded-lyrics") : null;
const lyricsScroll = isBrowser ? document.getElementById("am-lyrics-scroll") : null;
const artworkView = isBrowser ? document.getElementById("am-artwork-view") : null;

const btnGhost = isBrowser ? document.getElementById("btn-ghost") : null;
const btnCompact = isBrowser ? document.getElementById("btn-compact") : null;
const btnPopout = isBrowser ? document.getElementById("btn-popout") : null;
const btnClose = isBrowser ? document.getElementById("btn-close") : null;

const btnVol = isBrowser ? document.getElementById("btn-vol") : null;
const btnLike = isBrowser ? document.getElementById("btn-like") : null;
const btnPrev = isBrowser ? document.getElementById("btn-prev") : null;
const btnPlay = isBrowser ? document.getElementById("btn-play") : null;
const iconPlay = isBrowser ? document.getElementById("icon-play") : null;
const iconPause = isBrowser ? document.getElementById("icon-pause") : null;
const btnNext = isBrowser ? document.getElementById("btn-next") : null;
const btnLyricsToggle = isBrowser ? document.getElementById("btn-lyrics-toggle") : null;
const btnKaraoke = isBrowser ? document.getElementById("btn-karaoke") : null;

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

function getTrackKey(track) {
  if (!track) return "";
  const t = (track.title || "").trim().toLowerCase();
  let a = "";
  if (Array.isArray(track.artists)) {
    a = track.artists.map((x) => (typeof x === "object" ? x.name : x)).join(", ");
  } else {
    a = String(track.artists || "");
  }
  return `${t} — ${a.trim().toLowerCase()}`;
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

function formatRemainingTime(seconds, duration) {
  if (!duration || duration <= 0) return "-0:00";
  const rem = Math.max(0, duration - (seconds || 0));
  return `-${formatTime(rem)}`;
}

function parseLRC(lrcText, duration = 0) {
  if (!lrcText) return [];
  let items = [];
  let hasExplicitTime = false;

  if (Array.isArray(lrcText)) {
    items = lrcText
      .map((item) => {
        let t = -1;
        if (item.time !== undefined && item.time !== null) {
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
        if (t >= 0) hasExplicitTime = true;
        return {
          time: t,
          text: (item.text || item.line || "").trim(),
        };
      })
      .filter((x) => x.text && x.text.trim());
  } else if (typeof lrcText === "string") {
    const rawLines = lrcText.split("\n");
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
        hasExplicitTime = true;
      }

      const cleanText = trimmed.replace(tagRegex, "").trim();
      if (cleanText) {
        if (timestamps.length > 0) {
          for (const t of timestamps) {
            items.push({ time: t, text: cleanText });
          }
        } else {
          items.push({ time: -1, text: cleanText });
        }
      }
    }
  }

  if (items.length === 0) return [];

  // Filter out meta headers like "[Текст песни ...]", contributors, translations
  items = items.filter((x) => {
    const txt = (x.text || "").trim().toLowerCase();
    if (!txt) return false;
    if (txt.startsWith("[текст песни") || txt.startsWith("[lyrics of")) return false;
    if (txt.includes("contributors") || txt.includes("translations")) return false;
    if (txt === "♫ текст этой песни недоступен." || txt === "текст этой песни недоступен.") return false;
    return true;
  });

  if (items.length === 0) return [];

  // If track has plain lyrics without LRC timestamps, distribute them evenly across duration!
  if (!hasExplicitTime) {
    const effDur = duration > 0 ? duration : (trackDuration > 0 ? trackDuration : 180);
    const startOffset = Math.min(3, effDur * 0.03);
    const availableTime = Math.max(10, effDur - startOffset - 2);
    const step = availableTime / Math.max(1, items.length);

    items.forEach((item, idx) => {
      item.time = +(startOffset + idx * step).toFixed(2);
      item.isSyntheticTime = true;
    });
  } else {
    items.sort((a, b) => a.time - b.time);
  }

  return items;
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

function renderProgress(pos) {
  if (timeCurrent) timeCurrent.textContent = formatTime(pos);
  if (timeRemaining) timeRemaining.textContent = formatRemainingTime(pos, trackDuration);

  if (sliderFill && trackDuration > 0) {
    const pct = Math.max(0, Math.min((pos / trackDuration) * 100, 100));
    sliderFill.style.width = `${pct}%`;
    if (sliderThumb) sliderThumb.style.left = `${pct}%`;
  }

  syncLyricsPosition(pos);
}

function findActiveLyricIndex(pos) {
  if (!overlayLyrics || overlayLyrics.length === 0) return -1;
  let activeIdx = -1;
  for (let i = 0; i < overlayLyrics.length; i++) {
    if (overlayLyrics[i].time <= pos + 0.15) {
      activeIdx = i;
    } else {
      break;
    }
  }
  if (activeIdx === -1 && overlayLyrics.length > 0 && pos >= 0) {
    activeIdx = 0;
  }
  return activeIdx;
}

function syncLyricsPosition(pos) {
  if (!overlayLyrics || overlayLyrics.length === 0) {
    if (compactLine) compactLine.textContent = "♫ Текст этой песни недоступен.";
    return;
  }

  const activeIdx = findActiveLyricIndex(pos);

  // Update Compact Karaoke Line
  if (compactLine && activeIdx >= 0 && activeIdx < overlayLyrics.length) {
    const targetText = overlayLyrics[activeIdx].text;
    if (compactLine.textContent !== targetText) {
      compactLine.textContent = targetText;
    }
  }

  // Update Expanded Scrolling Lyrics
  if (currentViewMode === "lyrics" && activeIdx !== overlayLyricsIndex) {
    overlayLyricsIndex = activeIdx;
    if (lyricsScroll) {
      const allLines = lyricsScroll.querySelectorAll(".am-lrc-line");
      allLines.forEach((lineEl, idx) => {
        if (idx === activeIdx) {
          lineEl.classList.add("active");
          // Smooth center scrolling
          const containerHeight = lyricsScroll.clientHeight;
          const lineOffsetTop = lineEl.offsetTop;
          const targetScrollTop = lineOffsetTop - containerHeight / 2 + lineEl.clientHeight / 2;
          lyricsScroll.scrollTo({
            top: Math.max(0, targetScrollTop),
            behavior: "smooth",
          });
        } else {
          lineEl.classList.remove("active");
        }
      });
    }
  }
}

function renderFullLyricsUI() {
  if (!lyricsScroll) return;

  if (!overlayLyrics || overlayLyrics.length === 0) {
    lyricsScroll.innerHTML = `<div class="am-lyrics-empty">Текст этой песни недоступен.</div>`;
    return;
  }

  const pos = getInterpolatedPosition();
  const activeIdx = findActiveLyricIndex(pos);

  lyricsScroll.innerHTML = overlayLyrics
    .map((item, idx) => {
      const isActive = idx === activeIdx;
      return `<div class="am-lrc-line ${isActive ? "active" : ""}" data-idx="${idx}" data-time="${item.time}">${escapeHtml(item.text)}</div>`;
    })
    .join("");

  overlayLyricsIndex = activeIdx;

  lyricsScroll.querySelectorAll(".am-lrc-line").forEach((el) => {
    el.addEventListener("click", () => {
      const t = parseFloat(el.getAttribute("data-time"));
      if (!isNaN(t) && t >= 0) {
        basePosition = t;
        baseTimestamp = (typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now();
        renderProgress(t);
        if (typeof window !== "undefined" && window.overlayApi) {
          const sendFn = window.overlayApi.sendPlayerAction || window.overlayApi.sendAction;
          if (typeof sendFn === "function") {
            const dur = trackDuration > 0 ? trackDuration : 1;
            sendFn("seek", { position: t, progress: t / dur });
          }
        }
      }
    });
  });

  if (activeIdx >= 0) {
    requestAnimationFrame(() => {
      const activeEl = lyricsScroll.querySelector(`.am-lrc-line[data-idx="${activeIdx}"]`);
      if (activeEl) {
        const containerHeight = lyricsScroll.clientHeight;
        const targetScrollTop = activeEl.offsetTop - containerHeight / 2 + activeEl.clientHeight / 2;
        lyricsScroll.scrollTo({
          top: Math.max(0, targetScrollTop),
          behavior: "auto",
        });
      }
    });
  }
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

function setViewMode(mode) {
  currentViewMode = mode;
  if (!playerCard) return;

  if (mode === "compact") {
    if (expandedLyrics) expandedLyrics.classList.add("hidden");
    if (artworkView) artworkView.classList.add("hidden");
    if (compactKaraoke) compactKaraoke.classList.remove("hidden");
    if (btnLyricsToggle) btnLyricsToggle.classList.remove("active");
    if (window.overlayApi && window.overlayApi.resizeOverlay) {
      window.overlayApi.resizeOverlay(380, 160);
    }
  } else if (mode === "lyrics") {
    if (compactKaraoke) compactKaraoke.classList.add("hidden");
    if (artworkView) artworkView.classList.add("hidden");
    if (expandedLyrics) expandedLyrics.classList.remove("hidden");
    if (btnLyricsToggle) btnLyricsToggle.classList.add("active");
    if (window.overlayApi && window.overlayApi.resizeOverlay) {
      window.overlayApi.resizeOverlay(380, 480);
    }
    overlayLyricsIndex = -1;
    renderFullLyricsUI();
  } else if (mode === "artwork") {
    if (compactKaraoke) compactKaraoke.classList.add("hidden");
    if (expandedLyrics) expandedLyrics.classList.add("hidden");
    if (artworkView) artworkView.classList.remove("hidden");
    if (btnLyricsToggle) btnLyricsToggle.classList.remove("active");
    if (window.overlayApi && window.overlayApi.resizeOverlay) {
      window.overlayApi.resizeOverlay(380, 390);
    }
  }
}

function handleLyricsData(lyricsData) {
  if (!lyricsData) return;
  const src = (Array.isArray(lyricsData.lines) && lyricsData.lines.length > 0)
    ? lyricsData.lines
    : (lyricsData.syncLyrics || lyricsData.lrc || lyricsData.lyrics);

  if (src && (Array.isArray(src) ? src.length > 0 : String(src).trim().length > 0)) {
    const dur = trackDuration > 0 ? trackDuration : 0;
    const parsed = parseLRC(src, dur);
    if (parsed && parsed.length > 0) {
      overlayLyrics = parsed;
      overlayLyricsIndex = -1;
      lyricsTrackKey = currentTrackKey;
      renderFullLyricsUI();
      const pos = getInterpolatedPosition();
      syncLyricsPosition(pos);
      return;
    }
  }

  overlayLyrics = [];
  overlayLyricsIndex = -1;
  renderFullLyricsUI();
  if (compactLine) compactLine.textContent = "♫ Текст этой песни недоступен.";
}

function updateUI(state) {
  if (!state) return;
  const { track, progress, isPlaying: playing } = state;

  isPlaying = !!playing;

  // 1. Play / Pause Visual State
  if (isPlaying) {
    if (iconPlay) iconPlay.classList.add("hidden");
    if (iconPause) iconPause.classList.remove("hidden");
  } else {
    if (iconPlay) iconPlay.classList.remove("hidden");
    if (iconPause) iconPause.classList.add("hidden");
  }

  // 2. Track Transition & Metadata
  if (track) {
    const newTrackKey = getTrackKey(track);
    const isNewTrack = newTrackKey && newTrackKey !== currentTrackKey;

    if (isNewTrack) {
      currentTrackKey = newTrackKey;
      if (lyricsTrackKey !== newTrackKey) {
        overlayLyrics = [];
        overlayLyricsIndex = -1;
        if (compactLine) compactLine.textContent = "♫ Синхронизация текста...";
        renderFullLyricsUI();
      }

      basePosition = 0;
      baseTimestamp = (typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now();
      if (track.durationMs) {
        trackDuration = track.durationMs / 1000;
      }
    }
    currentTrack = track;

    if (amTitle) amTitle.textContent = track.title || "Трек не воспроизводится";

    let artistsStr = "";
    if (Array.isArray(track.artists)) {
      artistsStr = track.artists.map((a) => (typeof a === "object" ? a.name : a)).join(", ");
    } else {
      artistsStr = track.artists || "Исполнитель не указан";
    }

    const albumStr = (track.rawMeta && track.rawMeta.albums && track.rawMeta.albums[0]?.title) || "";
    if (amArtist) {
      amArtist.textContent = albumStr ? `${artistsStr} — ${albumStr}` : artistsStr;
    }

    // Cover art extraction
    const rawCover = track.coverUrl || track.coverUri || (track.ogImage ? "https://" + track.ogImage.replace("%%", "400x400") : "");
    const coverUrl = normalizeCoverUrl(rawCover);

    if (coverUrl) {
      if (amCover && amCover.src !== coverUrl) amCover.src = coverUrl;
      if (amLargeArt && amLargeArt.src !== coverUrl) amLargeArt.src = coverUrl;
    }

    if (btnLike) {
      if (track.liked) btnLike.classList.add("liked");
      else btnLike.classList.remove("liked");
    }
  }

  // 3. Progress Sync
  if (progress) {
    const newPos = Number(progress.position) || 0;
    const newDur = Number(progress.duration) || 0;
    const newSpeed = Number(progress.speed) || 1.0;

    basePosition = newPos;
    baseTimestamp = (typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now();
    if (newDur > 0) {
      const durChanged = Math.abs(newDur - trackDuration) > 1;
      trackDuration = newDur;
      if (durChanged && overlayLyrics && overlayLyrics.length > 0 && overlayLyrics[0].isSyntheticTime) {
        const startOffset = Math.min(3, trackDuration * 0.03);
        const availableTime = Math.max(10, trackDuration - startOffset - 2);
        const step = availableTime / Math.max(1, overlayLyrics.length);
        overlayLyrics.forEach((item, idx) => {
          item.time = +(startOffset + idx * step).toFixed(2);
        });
      }
    }
    playbackSpeed = newSpeed > 0 ? newSpeed : 1.0;

    renderProgress(basePosition);
  }

  // 4. Timer control based on active state
  if (isPlaying) {
    startInterpolation();
  } else {
    stopInterpolation();
  }
}

// Scrubber Click & Drag Seeking
if (sliderTrack) {
  let isDraggingScrubber = false;

  const seekFromEvent = (e) => {
    const rect = sliderTrack.getBoundingClientRect();
    const ratio = Math.max(0, Math.min((e.clientX - rect.left) / rect.width, 1));
    const targetPos = ratio * trackDuration;
    basePosition = targetPos;
    baseTimestamp = (typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now();
    renderProgress(targetPos);

    if (window.overlayApi) {
      const sendFn = window.overlayApi.sendPlayerAction || window.overlayApi.sendAction;
      if (typeof sendFn === "function") {
        sendFn("seek", { position: targetPos, progress: ratio });
      }
    }
  };

  sliderTrack.addEventListener("mousedown", (e) => {
    isDraggingScrubber = true;
    seekFromEvent(e);
  });

  window.addEventListener("mousemove", (e) => {
    if (isDraggingScrubber) seekFromEvent(e);
  });

  window.addEventListener("mouseup", () => {
    isDraggingScrubber = false;
  });
}

// Player Action Controls
if (btnPlay) {
  btnPlay.addEventListener("click", () => {
    if (window.overlayApi) {
      const sendFn = window.overlayApi.sendPlayerAction || window.overlayApi.sendAction;
      if (typeof sendFn === "function") sendFn("playPause");
    }
  });
}

if (btnPrev) {
  btnPrev.addEventListener("click", () => {
    if (window.overlayApi) {
      const sendFn = window.overlayApi.sendPlayerAction || window.overlayApi.sendAction;
      if (typeof sendFn === "function") sendFn("prev");
    }
  });
}

if (btnNext) {
  btnNext.addEventListener("click", () => {
    if (window.overlayApi) {
      const sendFn = window.overlayApi.sendPlayerAction || window.overlayApi.sendAction;
      if (typeof sendFn === "function") sendFn("next");
    }
  });
}

if (btnLike) {
  btnLike.addEventListener("click", () => {
    if (window.overlayApi) {
      const sendFn = window.overlayApi.sendPlayerAction || window.overlayApi.sendAction;
      if (typeof sendFn === "function") sendFn("like");
    }
  });
}

if (btnVol) {
  btnVol.addEventListener("click", () => {
    if (window.overlayApi) {
      const sendFn = window.overlayApi.sendPlayerAction || window.overlayApi.sendAction;
      if (typeof sendFn === "function") sendFn("toggleMute");
    }
  });
}

// Window & View Mode Controls
if (btnLyricsToggle) {
  btnLyricsToggle.addEventListener("click", () => {
    if (currentViewMode === "lyrics") {
      setViewMode("compact");
    } else {
      setViewMode("lyrics");
    }
  });
}

if (btnCompact) {
  btnCompact.addEventListener("click", () => {
    if (currentViewMode === "compact") {
      setViewMode("lyrics");
    } else {
      setViewMode("compact");
    }
  });
}

if (btnPopout) {
  btnPopout.addEventListener("click", () => {
    if (currentViewMode === "lyrics") {
      setViewMode("compact");
    } else {
      setViewMode("lyrics");
    }
  });
}

if (coverWrap) {
  coverWrap.addEventListener("click", () => {
    if (currentViewMode === "artwork") {
      setViewMode("lyrics");
    } else {
      setViewMode("artwork");
    }
  });
}

if (btnKaraoke) {
  btnKaraoke.addEventListener("click", () => {
    if (window.overlayApi && window.overlayApi.toggleKaraoke) {
      window.overlayApi.toggleKaraoke();
    }
  });
}

if (btnGhost) {
  btnGhost.addEventListener("click", () => {
    isGhostMode = !isGhostMode;
    btnGhost.classList.toggle("active", isGhostMode);
    if (window.overlayApi && window.overlayApi.setClickThrough) {
      window.overlayApi.setClickThrough(isGhostMode);
    }
  });
}

if (btnClose) {
  btnClose.addEventListener("click", () => {
    if (window.overlayApi && window.overlayApi.toggleOverlay) {
      window.overlayApi.toggleOverlay();
    }
  });
}

// Global API Listeners
if (typeof window !== "undefined" && window.overlayApi) {
  window.overlayApi.onTrackUpdate((state) => {
    updateUI(state);
  });

  window.overlayApi.onLyricsUpdate((lyricsData) => {
    handleLyricsData(lyricsData);
  });

  window.overlayApi.onGhostModeToggled((enabled) => {
    isGhostMode = !!enabled;
    if (btnGhost) btnGhost.classList.toggle("active", isGhostMode);
  });

  // Hydrate immediately
  if (window.overlayApi.getLastPlayerState) {
    window.overlayApi.getLastPlayerState().then((state) => {
      if (state) updateUI(state);
    }).catch(() => {});
  }

  if (window.overlayApi.getLastLyrics) {
    window.overlayApi.getLastLyrics().then((lyrics) => {
      if (lyrics) handleLyricsData(lyrics);
    }).catch(() => {});
  }
}

// Initial mode setup: start in clean compact mode (~160px)
setViewMode("compact");
