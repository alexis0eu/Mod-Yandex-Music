// Apple Music Floating Karaoke Pill Controller (v1.3.8)
// Real-time 60fps interpolation, stable track identity, 1-in-1 lyrics synchronization

let lines = [];
let currentIndex = -1;
let currentTrackKey = "";
let lyricsTrackKey = "";
let currentDuration = 0;
let isPlaying = false;

// 60fps interpolation state
let basePosition = 0;
let baseTimestamp = (typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now();
let trackDuration = 0;
let playbackSpeed = 1.0;
let animFrameId = null;

const capsuleCover = document.getElementById("capsule-cover");
const lineActive = document.getElementById("capsule-line-active");
const lineNext = document.getElementById("capsule-line-next");
const btnPlay = document.getElementById("btn-karaoke-play");
const iconPlay = document.getElementById("karaoke-icon-play");
const iconPause = document.getElementById("karaoke-icon-pause");
const btnClose = document.getElementById("btn-karaoke-close");

function normalizeCoverUrl(url) {
  if (!url || typeof url !== "string") return "";
  let clean = url.trim();
  if (!clean) return "";
  clean = clean.replace(/^music-application:\/?\/?/i, "");
  clean = clean.replace(/^(?:https?:\/?\/)+/i, "");
  clean = clean.replace(/^\/\//, "");
  clean = clean.replace("%%", "200x200");
  clean = clean.replace(/\/(?:50x50|100x100|400x400)\b/, "/200x200");
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
      .filter((x) => x.text && x.text.trim())
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

    const cleanText = trimmed.replace(tagRegex, "").trim();
    if (cleanText) {
      if (timestamps.length > 0) {
        for (const t of timestamps) {
          parsed.push({ time: t, text: cleanText });
        }
      } else {
        parsed.push({ time: 0, text: cleanText });
      }
    }
  }

  return parsed.sort((a, b) => a.time - b.time);
}

function syncPosition(pos) {
  if (!lines || lines.length === 0) {
    if (lineActive) lineActive.textContent = "♫ Текст этой песни недоступен.";
    if (lineNext) lineNext.textContent = "";
    return;
  }

  let activeIdx = -1;
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].time <= pos + 0.15) {
      activeIdx = i;
    } else {
      break;
    }
  }

  if (activeIdx === -1 && lines.length > 0) {
    activeIdx = 0;
  }

  if (activeIdx !== currentIndex) {
    currentIndex = activeIdx;
    if (lineActive && activeIdx >= 0 && activeIdx < lines.length) {
      lineActive.textContent = lines[activeIdx].text;
    }
    if (lineNext) {
      const nextIdx = activeIdx + 1;
      if (nextIdx < lines.length) {
        lineNext.textContent = lines[nextIdx].text;
      } else {
        lineNext.textContent = "♫ Конец трека";
      }
    }
  }
}

function tickInterpolation() {
  if (!isPlaying) {
    stopInterpolation();
    return;
  }

  const pos = getInterpolatedPosition();
  syncPosition(pos);

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

function applyLyricsData(lyricsData) {
  if (!lyricsData) return;
  const src = lyricsData.lines || lyricsData.syncLyrics || lyricsData.lrc || lyricsData.lyrics;
  if (src) {
    const dur = trackDuration > 0 ? trackDuration : (currentDuration > 0 ? currentDuration : 0);
    lines = parseLRC(src, dur);
    currentIndex = -1;
    lyricsTrackKey = currentTrackKey;
    if (lines.length > 0) {
      const pos = getInterpolatedPosition();
      syncPosition(pos);
    } else if (lineActive) {
      lineActive.textContent = "♫ Текст этой песни недоступен.";
      if (lineNext) lineNext.textContent = "";
    }
  } else {
    lines = [];
    currentIndex = -1;
    if (lineActive) lineActive.textContent = "♫ Текст отсутствует";
    if (lineNext) lineNext.textContent = "";
  }
}

if (btnPlay) {
  btnPlay.addEventListener("click", () => {
    if (window.karaokeApi && window.karaokeApi.sendPlayerAction) {
      window.karaokeApi.sendPlayerAction("playPause");
    }
  });
}

if (btnClose) {
  btnClose.addEventListener("click", () => {
    if (window.karaokeApi && window.karaokeApi.toggleKaraoke) {
      window.karaokeApi.toggleKaraoke();
    }
  });
}

if (typeof window !== "undefined" && window.karaokeApi) {
  window.karaokeApi.onTrackUpdate((state) => {
    if (!state) return;
    const { track, progress, isPlaying: playing } = state;

    isPlaying = !!playing;

    if (isPlaying) {
      if (iconPlay) iconPlay.classList.add("hidden");
      if (iconPause) iconPause.classList.remove("hidden");
    } else {
      if (iconPlay) iconPlay.classList.remove("hidden");
      if (iconPause) iconPause.classList.add("hidden");
    }

    if (progress) {
      const newPos = Number(progress.position) || 0;
      const newDur = Number(progress.duration) || 0;
      basePosition = newPos;
      baseTimestamp = (typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now();
      if (newDur > 0) {
        trackDuration = newDur;
        currentDuration = newDur;
      }
      syncPosition(basePosition);
    }

    if (track) {
      const newTrackKey = getTrackKey(track);
      if (newTrackKey && newTrackKey !== currentTrackKey) {
        currentTrackKey = newTrackKey;
        if (lyricsTrackKey !== newTrackKey) {
          currentIndex = -1;
          lines = [];
          const artist = Array.isArray(track.artists)
            ? track.artists.map((a) => (typeof a === "object" ? a.name : a)).join(", ")
            : track.artists || "";
          if (lineActive) lineActive.textContent = `${track.title || "Трек"} — ${artist || "..."}`;
          if (lineNext) lineNext.textContent = "Синхронизация текста...";
        }
      }

      // Cover art
      const rawCover = track.coverUrl || track.coverUri || (track.ogImage ? "https://" + track.ogImage.replace("%%", "200x200") : "");
      const coverUrl = normalizeCoverUrl(rawCover);
      if (coverUrl && capsuleCover && capsuleCover.src !== coverUrl) {
        capsuleCover.src = coverUrl;
      }
    }

    if (isPlaying) {
      startInterpolation();
    } else {
      stopInterpolation();
    }
  });

  window.karaokeApi.onLyricsUpdate((lyricsData) => {
    applyLyricsData(lyricsData);
  });

  // Hydrate immediately
  if (window.karaokeApi.getLastPlayerState) {
    window.karaokeApi.getLastPlayerState().then((state) => {
      if (state && state.track) {
        isPlaying = !!state.isPlaying;
        if (state.progress && state.progress.duration) {
          currentDuration = state.progress.duration;
          trackDuration = state.progress.duration;
          basePosition = state.progress.position || 0;
        }
        currentTrackKey = getTrackKey(state.track);
        if (isPlaying) startInterpolation();
      }
    }).catch(() => {});
  }

  if (window.karaokeApi.getLastLyrics) {
    window.karaokeApi.getLastLyrics().then((lyricsData) => {
      if (lyricsData) applyLyricsData(lyricsData);
    }).catch(() => {});
  }
}
