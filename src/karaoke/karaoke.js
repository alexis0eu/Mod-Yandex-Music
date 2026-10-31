// Yandex Music Floating Karaoke Window Controller (v1.3.7)
// Features: 60fps sub-millisecond interpolation, robust multi-tag LRC parser, instant state pull, Apple Music styling

let lines = [];
let currentIndex = -1;
let currentTrackId = null;
let currentDuration = 0;
let isPlaying = false;

// 60fps interpolation state
let basePosition = 0;
let baseTimestamp = (typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now();
let trackDuration = 0;
let playbackSpeed = 1.0;
let animFrameId = null;

const lyricPrev = document.getElementById("lyric-prev");
const lyricActive = document.getElementById("lyric-active");
const lyricNext = document.getElementById("lyric-next");

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
      .filter((x) => x.text)
      .sort((a, b) => a.time - b.time);
  }

  if (typeof lrcText !== "string") return [];
  const rawLines = lrcText.split("\n");
  const parsed = [];
  let globalOffsetMs = 0;

  // 1. Check for global [offset:+/-ms] tag
  for (const line of rawLines) {
    const offsetMatch = line.match(/^\[offset:\s*([+-]?\d+)\]/i);
    if (offsetMatch) {
      globalOffsetMs = parseInt(offsetMatch[1], 10) || 0;
      break;
    }
  }

  // 2. Parse lines with one or multiple timestamp tags
  const tagRegex = /\[(\d{1,2}):(\d{2})(?:[.:](\d{1,3}))?\]/g;

  for (const line of rawLines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    // Skip metadata headers e.g. [ti:Title], [ar:Artist], [al:Album], [by:Name]
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

  // 3. Fallback: If text was plain without timestamps, distribute evenly
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

function updateLyricsDisplay(index) {
  if (index === currentIndex) return;
  currentIndex = index;

  if (index < 0 || index >= lines.length) {
    if (lyricPrev) lyricPrev.textContent = "";
    if (lyricActive) lyricActive.textContent = lines.length > 0 ? "♫ Вступление..." : "♫ Текст этой песни недоступен.";
    if (lyricNext) lyricNext.textContent = lines[0] ? lines[0].text : "";
    return;
  }

  if (lyricPrev) lyricPrev.textContent = index > 0 ? lines[index - 1].text : "";
  if (lyricActive) lyricActive.textContent = lines[index].text;
  if (lyricNext) lyricNext.textContent = index < lines.length - 1 ? lines[index + 1].text : "";
}

function syncPosition(position) {
  if (!lines || lines.length === 0) return;

  let found = -1;
  for (let i = 0; i < lines.length; i++) {
    if (position >= lines[i].time) {
      found = i;
    } else {
      break;
    }
  }

  updateLyricsDisplay(found);
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
    if (lines.length > 0) {
      const pos = getInterpolatedPosition();
      syncPosition(pos);
    } else if (lyricActive) {
      lyricActive.textContent = "♫ Текст этой песни недоступен.";
    }
  } else {
    lines = [];
    currentIndex = -1;
    if (lyricActive) {
      lyricActive.textContent = "♫ Текст отсутствует";
    }
  }
}

// Accent Color from Settings
async function applyAccentColor() {
  try {
    if (window.karaokeApi && window.karaokeApi.getStorageValue) {
      const accent = await window.karaokeApi.getStorageValue("custom-themes/accent");
      if (accent) {
        document.documentElement.style.setProperty("--accent", accent);
        document.documentElement.style.setProperty("--accent-glow", `${accent}99`);
      }
    }
  } catch (e) {}
}

if (typeof window !== "undefined" && window.karaokeApi) {
  window.karaokeApi.onTrackUpdate((state) => {
    if (!state) return;
    const { track, progress, isPlaying: playing } = state;

    isPlaying = !!playing;

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
      const trackKey = track.id || `${track.title}-${track.artists}`;
      if (trackKey !== currentTrackId) {
        currentTrackId = trackKey;
        currentIndex = -1;
        const artist = Array.isArray(track.artists)
          ? track.artists.map((a) => (typeof a === "object" ? a.name : a)).join(", ")
          : track.artists || "";

        if (track.lyrics) {
          lines = parseLRC(track.lyrics, currentDuration);
        } else {
          lines = [];
          if (lyricPrev) lyricPrev.textContent = "";
          if (lyricActive) lyricActive.textContent = `${track.title || "Трек"} — ${artist || "..."}`;
          if (lyricNext) lyricNext.textContent = "Загрузка текста...";
        }
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

  window.karaokeApi.onStorageChanged((key, value) => {
    if (key === "custom-themes/accent") {
      document.documentElement.style.setProperty("--accent", value);
      document.documentElement.style.setProperty("--accent-glow", `${value}99`);
    }
  });

  // Pull immediately on startup to avoid cold-start empty state
  if (window.karaokeApi.getLastPlayerState) {
    window.karaokeApi.getLastPlayerState().then((state) => {
      if (state && state.track) {
        isPlaying = !!state.isPlaying;
        if (state.progress && state.progress.duration) {
          currentDuration = state.progress.duration;
          trackDuration = state.progress.duration;
          basePosition = state.progress.position || 0;
        }
        currentTrackId = state.track.id || `${state.track.title}-${state.track.artists}`;
        if (isPlaying) startInterpolation();
      }
    }).catch(() => {});
  }

  if (window.karaokeApi.getLastLyrics) {
    window.karaokeApi.getLastLyrics().then((lyricsData) => {
      if (lyricsData) applyLyricsData(lyricsData);
    }).catch(() => {});
  }

  applyAccentColor();
}
