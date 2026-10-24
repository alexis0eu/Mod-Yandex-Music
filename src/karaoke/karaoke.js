let lines = [];
let currentIndex = -1;
let currentTrackId = null;
let currentDuration = 0;

const lyricPrev = document.getElementById("lyric-prev");
const lyricActive = document.getElementById("lyric-active");
const lyricNext = document.getElementById("lyric-next");

function parseLRC(lrcText, duration = 0) {
  if (!lrcText) return [];
  if (Array.isArray(lrcText)) {
    return lrcText.map((item) => ({
      time: item.time !== undefined ? Number(item.time) : (Number(item.timestamp || 0) / (item.timestamp > 1000 ? 1000 : 1)),
      text: item.text || item.line || "",
    })).filter(x => x.text).sort((a, b) => a.time - b.time);
  }

  if (typeof lrcText !== "string") return [];
  const rawLines = lrcText.split("\n");
  const parsed = [];
  const regex = /\[(\d{2}):(\d{2})\.?(\d{2,3})?\]/;

  for (const line of rawLines) {
    const match = regex.exec(line);
    if (match) {
      const min = parseInt(match[1], 10);
      const sec = parseInt(match[2], 10);
      let ms = 0;
      if (match[3]) {
        ms = match[3].length === 2 ? parseInt(match[3], 10) * 10 : parseInt(match[3], 10);
      }
      const time = min * 60 + sec + ms / 1000;
      const text = line.replace(/\[\d{2}:\d{2}\.?\d{2,3}?\]/g, "").trim();
      if (text) {
        parsed.push({ time, text });
      }
    }
  }

  // Fallback: If text was plain without timestamps, distribute lines evenly across duration
  if (parsed.length === 0) {
    const cleanLines = rawLines.map((l) => l.trim()).filter((l) => l.length > 0);
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
    lyricPrev.textContent = "";
    lyricActive.textContent = lines.length > 0 ? "♫ Вступление..." : "♫ Текст песни отсутствует";
    lyricNext.textContent = lines[0] ? lines[0].text : "";
    return;
  }

  lyricPrev.textContent = index > 0 ? lines[index - 1].text : "";
  lyricActive.textContent = lines[index].text;
  lyricNext.textContent = index < lines.length - 1 ? lines[index + 1].text : "";
}

function syncPosition(position) {
  if (!lines || lines.length === 0) return;

  // Find line where line.time <= position < nextLine.time
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

// Accent Color from Settings
async function applyAccentColor() {
  try {
    const accent = await window.karaokeApi.getStorageValue("custom-themes/accent");
    if (accent) {
      document.documentElement.style.setProperty("--accent", accent);
      document.documentElement.style.setProperty("--accent-glow", `${accent}88`);
    }
  } catch (e) {}
}

if (window.karaokeApi) {
  window.karaokeApi.onTrackUpdate((state) => {
    if (!state || !state.track) return;
    const { track, progress } = state;

    if (progress && progress.duration) {
      currentDuration = progress.duration;
    }

    if (track.id !== currentTrackId) {
      currentTrackId = track.id;
      currentIndex = -1;
      const artist = Array.isArray(track.artists)
        ? track.artists.map((a) => (typeof a === "object" ? a.name : a)).join(", ")
        : track.artists || "";

      // If track already has embedded lyrics
      if (track.lyrics) {
        lines = parseLRC(track.lyrics, currentDuration);
      } else {
        lines = [];
        lyricPrev.textContent = "";
        lyricActive.textContent = `${track.title} - ${artist}`;
        lyricNext.textContent = "Загрузка текста...";
      }
    }

    if (progress && progress.position !== undefined) {
      syncPosition(progress.position);
    }
  });

  window.karaokeApi.onLyricsUpdate((lyricsData) => {
    if (lyricsData && (lyricsData.lrc || lyricsData.lines || lyricsData.lyrics)) {
      const src = lyricsData.lrc || lyricsData.lines || lyricsData.lyrics;
      lines = parseLRC(src, currentDuration);
      currentIndex = -1;
    }
  });

  window.karaokeApi.onStorageChanged((key, value) => {
    if (key === "custom-themes/accent") {
      document.documentElement.style.setProperty("--accent", value);
      document.documentElement.style.setProperty("--accent-glow", `${value}88`);
    }
  });

  applyAccentColor();
}
