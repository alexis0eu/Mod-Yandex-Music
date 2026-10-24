import sys
import os
import re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

RENDERER_JS = r"d:\Яндекс Музыка мод\src\renderer\mod-renderer.js"

with open(RENDERER_JS, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Add Equalizer, Downloader, OSD, UI Cleaner helper functions
helper_functions = '''
  // ==========================================
  // 3.1 EQUALIZER & WEBAUDIO SOUND FX
  // ==========================================
  let audioCtx = null;
  let audioSource = null;
  let eqFilters = [];
  const EQ_FREQUENCIES = [32, 64, 125, 250, 500, 1000, 2000, 4000, 8000, 16000];
  const EQ_PRESETS = {
    flat: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    bassBoost: [9, 8, 6, 3, 1, 0, 0, 1, 2, 3],
    vocal: [-2, -2, -1, 3, 6, 6, 4, 2, 0, -1],
    club: [6, 5, 3, 0, 0, 2, 4, 5, 5, 0],
    rock: [5, 4, 2, -1, -2, 1, 3, 5, 6, 6],
  };

  function initAudioEqualizer() {
    if (audioSource) return;
    const audioEl = document.querySelector("audio");
    if (!audioEl) return;

    try {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      audioCtx = new AudioContextClass();
      audioSource = audioCtx.createMediaElementSource(audioEl);

      eqFilters = EQ_FREQUENCIES.map((freq, idx) => {
        const filter = audioCtx.createBiquadFilter();
        if (idx === 0) {
          filter.type = "lowshelf";
        } else if (idx === EQ_FREQUENCIES.length - 1) {
          filter.type = "highshelf";
        } else {
          filter.type = "peaking";
          filter.Q.value = 1.4;
        }
        filter.frequency.value = freq;
        filter.gain.value = 0;
        return filter;
      });

      let prev = audioSource;
      for (const filter of eqFilters) {
        prev.connect(filter);
        prev = filter;
      }
      prev.connect(audioCtx.destination);

      const savedPreset = modSettings["equalizer/preset"] || "flat";
      applyEqualizerPreset(savedPreset);
    } catch (e) {
      console.warn("[Equalizer] WebAudio init:", e);
    }
  }

  function applyEqualizerPreset(presetName) {
    const gains = EQ_PRESETS[presetName] || EQ_PRESETS.flat;
    if (eqFilters.length > 0) {
      eqFilters.forEach((f, i) => {
        if (f.gain) f.gain.value = gains[i] || 0;
      });
    }
    if (audioCtx && audioCtx.state === "suspended") {
      audioCtx.resume();
    }
  }

  // ==========================================
  // 3.2 GRANULAR UI CLEANER
  // ==========================================
  const UI_CLEANER_STYLESHEET_ID = "ym-mod-ui-cleaner-style";

  function applyUiCleaner() {
    const existing = document.getElementById(UI_CLEANER_STYLESHEET_ID);
    if (existing) existing.remove();

    let css = "";
    if (modSettings["cleaner/hideDislike"]) {
      css += `button[data-test-id="DISLIKE_BUTTON"] { display: none !important; }\\n`;
    }
    if (modSettings["cleaner/hideQueue"]) {
      css += `button[data-test-id="QUEUE_BUTTON"] { display: none !important; }\\n`;
    }
    if (modSettings["cleaner/hideLyrics"]) {
      css += `button[data-test-id*="SYNC_LYRICS"], button[data-test-id*="LYRICS"] { display: none !important; }\\n`;
    }
    if (modSettings["cleaner/hidePrev"]) {
      css += `button[data-test-id="PREVIOUS_TRACK_BUTTON"] { display: none !important; }\\n`;
    }
    if (modSettings["cleaner/hideQuality"]) {
      css += `button[data-test-id="QUALITY_BUTTON"] { display: none !important; }\\n`;
    }
    if (modSettings["cleaner/hideVolume"]) {
      css += `div[class*="VolumeControl_"] { display: none !important; }\\n`;
    }
    if (modSettings["cleaner/hideVibeBlock"]) {
      css += `div[data-test-id="VIBE_BLOCK"] { display: none !important; }\\n`;
    }
    if (modSettings["cleaner/hidePodcasts"]) {
      css += `aside[data-test-id="NAVBAR"] li:has(a[href*="/podcasts"]), aside[data-test-id="NAVBAR"] a[href*="/podcasts"] { display: none !important; }\\n`;
    }
    if (modSettings["cleaner/hideTrailers"]) {
      css += `aside[data-test-id="NAVBAR"] li:has(a[href*="/trailers"]), aside[data-test-id="NAVBAR"] a[href*="/trailers"] { display: none !important; }\\n`;
    }
    if (modSettings["cleaner/hideRadio"]) {
      css += `aside[data-test-id="NAVBAR"] li:has(a[href*="/radio"]), aside[data-test-id="NAVBAR"] a[href*="/radio"] { display: none !important; }\\n`;
    }

    if (css) {
      const style = document.createElement("style");
      style.id = UI_CLEANER_STYLESHEET_ID;
      style.textContent = css;
      document.head.appendChild(style);
    }
  }

  // ==========================================
  // 3.3 1-CLICK DOWNLOADER & OSD TOAST
  // ==========================================
  async function downloadCurrentTrack() {
    try {
      showToast("⏳ Получение ссылки для скачивания...");
      const player = document.querySelector('section[data-test-id="PLAYERBAR_DESKTOP"]');
      let trackId = null;
      let title = "track";
      let artist = "artist";

      const fiberMeta = searchFiberProperty(player, "entityMeta");
      if (fiberMeta && fiberMeta.entityMeta) {
        trackId = fiberMeta.entityMeta.id;
        title = fiberMeta.entityMeta.title;
        artist = Array.isArray(fiberMeta.entityMeta.artists)
          ? fiberMeta.entityMeta.artists.map((a) => (typeof a === "object" ? a.name : a)).join(", ")
          : fiberMeta.entityMeta.artists || "";
      } else {
        const link = player ? player.querySelector('a[href*="/track/"]') : null;
        if (link) {
          const m = link.href.match(/track\\/(\\d+)/);
          if (m) trackId = m[1];
        }
        title = player?.querySelector('[class*="Track_title"]')?.textContent || "track";
        artist = player?.querySelector('[class*="Track_artists"]')?.textContent || "artist";
      }

      if (!trackId) {
        showToast("❌ Не удалось определить ID трека");
        return;
      }

      const cleanInfo = await fetchCleanTrackInfo(trackId, "lossless");
      if (!cleanInfo || !cleanInfo.downloadInfo || !cleanInfo.downloadInfo.downloadUrl) {
        showToast("❌ Ошибка получения потока трека");
        return;
      }

      const downloadUrl = cleanInfo.downloadInfo.downloadUrl;
      const safeFilename = `${artist} - ${title}.mp3`.replace(/[\\\\/:*?"<>|]/g, "_");

      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = safeFilename;
      a.target = "_blank";
      document.body.appendChild(a);
      a.click();
      a.remove();
      showToast(`⬇️ Скачивание: ${safeFilename}`);
    } catch (e) {
      showToast("❌ Ошибка при скачивании");
    }
  }

  function showOsdTrackToast(title, artist, coverUrl) {
    if (modSettings["osd/enabled"] === false) return;
    let toast = document.getElementById("ym-osd-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "ym-osd-toast";
      toast.className = "ym-osd-toast";
      document.body.appendChild(toast);
    }
    toast.innerHTML = `
      <img class="ym-osd-cover" src="${coverUrl || 'https://avatars.yandex.net/get-music-content/175942/default/200x200'}" alt="Cover">
      <div class="ym-osd-info">
        <div class="ym-osd-title">${title}</div>
        <div class="ym-osd-artist">${artist}</div>
      </div>
    `;
    toast.classList.add("show");
    clearTimeout(window.__osdTimer);
    window.__osdTimer = setTimeout(() => toast.classList.remove("show"), 3200);
  }

  function injectPlayerDownloadButton() {
    if (document.getElementById("ym-btn-player-download")) return;
    const player = document.querySelector('section[data-test-id="PLAYERBAR_DESKTOP"]');
    if (!player) return;
    const likeBtn = player.querySelector('button[data-test-id="LIKE_BUTTON"]');
    if (!likeBtn || !likeBtn.parentNode) return;

    const btn = document.createElement("button");
    btn.id = "ym-btn-player-download";
    btn.className = "ym-player-download-btn";
    btn.title = "Скачать трек (Yandex Music Mod)";
    btn.innerHTML = `<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>`;
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      downloadCurrentTrack();
    });
    likeBtn.parentNode.insertBefore(btn, likeBtn.nextSibling);
  }
'''

# Insert helper functions before applyFont
insert_marker = "// ==========================================\n  // 3. GUARANTEED FONTS APPLICATOR"
if insert_marker in code and "initAudioEqualizer" not in code:
    code = code.replace(insert_marker, helper_functions + "\n  " + insert_marker)
    print("[+] Added Equalizer, Cleaner, Downloader, OSD helper functions")

# 2. Update applyFont with sizeScale, weight, letterSpacing
apply_font_pattern = r'function applyFont\(fontName, enabled = true\) \{[\s\S]*?document\.head\.appendChild\(style\);\n  \}'
new_apply_font = '''function applyFont(fontName, enabled = true) {
    ensureBaseStylesheet();

    const existing = document.getElementById(FONT_STYLESHEET_ID);
    if (existing) existing.remove();

    if (!enabled) return;

    let fontFamily = fontName || "JetBrains Mono";
    let extraCss = "";
    if (fontName === "Terraria") {
      fontFamily = "Terraria";
      extraCss = "* { font-size-adjust: 0.66 !important; }";
    } else if (fontName === "Minecraft") {
      extraCss = "*:not(.UserID-Avatar-Image):not(img) { border-radius: 0 !important; font-size-adjust: 0.55 !important; }";
    }

    const fontSizeScale = parseFloat(modSettings["font-changer/sizeScale"] || 1.0);
    const fontWeight = modSettings["font-changer/weight"] || "normal";
    const letterSpacing = modSettings["font-changer/letterSpacing"] || "normal";

    const fontRule = (fontName && fontName !== "Yandex Sans (Original)") 
      ? `font-family: "${fontFamily}", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;` 
      : "";
    const sizeRule = fontSizeScale !== 1.0 ? `font-size: calc(1em * ${fontSizeScale}) !important;` : "";
    const weightRule = fontWeight !== "normal" ? `font-weight: ${fontWeight} !important;` : "";
    const spacingRule = letterSpacing !== "normal" ? `letter-spacing: ${letterSpacing} !important;` : "";

    const style = document.createElement("style");
    style.id = FONT_STYLESHEET_ID;
    style.textContent = `
      *, *::before, *::after,
      html, body,
      button, input, select, textarea,
      [class*="Typography_"],
      [class*="Font_"],
      [class*="Text_"],
      [class*="title"],
      [class*="artist"],
      div, span, p, a, h1, h2, h3, h4, h5, h6 {
        ${fontRule}
        ${sizeRule}
        ${weightRule}
        ${spacingRule}
      }
      ${extraCss}
    `;
    document.head.appendChild(style);

    try {
      if (document.fonts && document.fonts.load && fontName && fontName !== "Yandex Sans (Original)") {
        document.fonts.load(`14px "${fontFamily}"`);
      }
    } catch (e) {}
  }'''

code = re.sub(apply_font_pattern, new_apply_font, code, count=1)
print("[+] Updated applyFont with typography scaling, weight and spacing")

with open(RENDERER_JS, "w", encoding="utf-8") as f:
    f.write(code)

print("[+] Successfully saved patched mod-renderer.js")
