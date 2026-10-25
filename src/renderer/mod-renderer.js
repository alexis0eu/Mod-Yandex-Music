(function () {

// ==========================================
// 0. IMMEDIATE SPLASH SCREEN KILLER (ZERO BLACK SCREEN)
// ==========================================
(function killSplashScreen() {
  const hideElement = (node) => {
    if (!node || !node.style) return;
    try {
      node.style.setProperty("display", "none", "important");
      node.style.setProperty("opacity", "0", "important");
      node.style.setProperty("visibility", "hidden", "important");
      node.style.setProperty("pointer-events", "none", "important");
      node.style.setProperty("z-index", "-9999", "important");
    } catch (e) {}
  };

  const nuke = () => {
    try {
      const splashes = document.querySelectorAll('div[class*="SplashScreen_root"], .SplashScreen_root__3jzFk, div[class*="WithTopBanner_banner"], #ym-osd-toast, .ym-osd-toast');
      splashes.forEach(hideElement);
      const osd = document.getElementById("ym-osd-toast");
      if (osd) osd.remove();
      const topRoots = document.querySelectorAll('div[class*="WithTopBanner_root"]');
      topRoots.forEach(node => {
        node.style.setProperty("display", "flex", "important");
        node.style.setProperty("flex-direction", "column", "important");
        node.style.setProperty("height", "100vh", "important");
      });
    } catch (e) {}
  };

  nuke();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", nuke);
  }
  window.addEventListener("load", nuke);
  try {
    const splashObs = new MutationObserver((mutations) => {
      for (const m of mutations) {
        for (const node of m.addedNodes) {
          if (node.nodeType === 1) {
            if (node.className && typeof node.className === "string" && node.className.includes("SplashScreen_root")) {
              hideElement(node);
            } else if (node.querySelector) {
              const nested = node.querySelector('div[class*="SplashScreen_root"], .SplashScreen_root__3jzFk');
              if (nested) hideElement(nested);
            }
          }
        }
      }
    });
    if (document.documentElement) {
      splashObs.observe(document.documentElement, { childList: true, subtree: true });
    }
    setTimeout(() => splashObs.disconnect(), 6000);
  } catch (e) {}
})();

  // Idempotency guard - prevent double execution if injected both via preload and HTML
  if (window.__ymModInitialized) {
    return;
  }
  window.__ymModInitialized = true;

  console.log("[YandexMusicMod] Initializing mod renderer v5.124.1...");
  window.__ymLastErrors = [];
  window.addEventListener("error", (e) => {
    window.__ymLastErrors.push({
      type: "error",
      message: e.message,
      filename: e.filename,
      lineno: e.lineno,
      colno: e.colno,
      stack: e.error ? e.error.stack : null
    });
    console.error("[YM-UNCAUGHT-ERROR]", e.message, e.filename, e.lineno, e.error);
  });
  window.addEventListener("unhandledrejection", (e) => {
    window.__ymLastErrors.push({
      type: "unhandledrejection",
      reason: String(e.reason),
      stack: e.reason && e.reason.stack ? e.reason.stack : null
    });
    console.error("[YM-UNHANDLED-REJECTION]", e.reason);
  });


  const UI_CLEANER_STYLESHEET_ID = "ym-mod-ui-cleaner-style";
  const SCALE_STYLESHEET_ID = "ym-mod-scale-style";
  const THEME_STYLESHEET_ID = "ym-mod-custom-theme-style";
  const FONT_STYLESHEET_ID = "ym-mod-custom-font-style";

  // ==========================================
  // 1. AD & TELEMETRY BLOCKER (SAFE)
  // ==========================================
  try {
    navigator.sendBeacon = () => true;
  } catch (e) {}

  // ==========================================
  // 2. PLUS UNLOCKER & FETCH INTERCEPTOR
  // ==========================================
  const originalFetch = window.fetch;
  let modSettings = {};
  const SECRET_KEY = "kzqU4XhfCaY6B6JTHODeq5";

  async function loadSettings() {
    if (window.yandexMusicMod && window.yandexMusicMod.getAllSettings) {
      try {
        modSettings = (await window.yandexMusicMod.getAllSettings()) || {};
      } catch (e) {
        modSettings = {};
      }
    }
  }

  // HMAC-SHA256 signature generator for Yandex Music track URLs
  async function getSign(secretKey, data) {
    try {
      const encoder = new TextEncoder();
      const keyData = encoder.encode(secretKey);
      const cryptoKey = await window.crypto.subtle.importKey(
        "raw",
        keyData,
        { name: "HMAC", hash: { name: "SHA-256" } },
        false,
        ["sign"]
      );
      const messageData = encoder.encode(data);
      const signature = await window.crypto.subtle.sign("HMAC", cryptoKey, messageData);
      const base64Signature = btoa(String.fromCharCode(...new Uint8Array(signature))).slice(0, -1);
      return base64Signature;
    } catch (e) {
      console.error("[PlusUnlocker] HMAC signature generation failed:", e);
      return null;
    }
  }

  // Re-request direct audio stream without ads or preview restrictions
  async function fetchCleanTrackInfo(trackId, quality = "lossless") {
    try {
      const ts = Math.floor(Date.now() / 1000);
      const audioCodecs = ["flac", "aac", "he-aac", "mp3", "flac-mp4", "aac-mp4", "he-aac-mp4"];
      const transports = "encraw";
      const sign = await getSign(SECRET_KEY, `${ts}${trackId}${quality}${audioCodecs.join("")}${transports}`);
      if (!sign) return null;

      let oauthToken = null;
      try {
        if (window.localStorage && window.localStorage.oauth) {
          const parsed = JSON.parse(window.localStorage.oauth);
          if (parsed && parsed.value) {
            oauthToken = "OAuth " + parsed.value;
          }
        }
      } catch (e) {}

      const headers = {
        "X-Yandex-Music-Client": "YandexMusicDesktopAppWindows/5.124.1",
        "X-Yandex-Music-Frontend": "new",
        "X-Yandex-Music-Without-Invocation-Info": "1",
      };
      if (oauthToken) {
        headers["Authorization"] = oauthToken;
      }

      const directUrl = `https://api.music.yandex.net/get-file-info?ts=${ts}&trackId=${trackId}&quality=${quality}&codecs=${encodeURIComponent(audioCodecs.join(","))}&transports=${transports}&sign=${encodeURIComponent(sign)}`;

      const res = await originalFetch(directUrl, { headers });
      if (res.ok) {
        const data = await res.json();
        if (data && data.downloadInfo && String(data.downloadInfo.trackId) === String(trackId)) {
          return data;
        }
      }
    } catch (err) {
      console.warn("[PlusUnlocker] Error fetching clean track info:", err);
    }
    return null;
  }

  window.fetch = async function (...args) {
    const request = args[0];
    const url = typeof request === "string" ? request : request && request.url ? request.url : "";

    // 0. Only intercept telemetry and api.music.yandex.net requests.
    // Internal Next.js requests (_next, chunks, pages, media) MUST pass through untouched!
    const isYandexApi = url.includes("api.music.yandex.net");
    const isTelemetry = url.includes("log.strm.yandex.ru") || url.includes("dynamic-pages/trigger/polling");
    const isPromo = url.includes("/editorial-promotion") || url.includes("/proxy/plus-red-alert/v1/alerts") || url.includes("/donation");

    if (!isYandexApi && !isTelemetry && !isPromo) {
      return originalFetch.apply(this, args);
    }

    // Block telemetry & tracking polling
    if (isTelemetry) {
      return new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }

    // Suppress subscription paywalls, red alerts, promo banners, and donations
    if (url.includes("/editorial-promotion")) {
      return new Response(JSON.stringify({ promotions: [], result: { promotions: [] } }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    if (url.includes("/proxy/plus-red-alert/v1/alerts")) {
      return new Response(JSON.stringify({ alerts: [], result: { alerts: [] } }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    if (url.includes("/donation")) {
      return new Response(JSON.stringify({ donations: [], result: { donations: [] } }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }

    // 1. Account Info & hasPlus Unlock (Plus + Free Web User blocker)
    if (url.includes("/account/about") || url.includes("/account/status")) {
      try {
        const res = await originalFetch.apply(this, args);
        if (res.ok) {
          const data = await res.json();
          data.hasPlus = true;
          data.isFreeWebUser = false;
          data.freeAccess = false;
          if (data.result) {
            data.result.hasPlus = true;
            data.result.isFreeWebUser = false;
            data.result.freeAccess = false;
            if (data.result.plus) data.result.plus.hasPlus = true;
          }
          console.log("[PlusUnlocker] Injected hasPlus = true and suppressed free web flags");
          return new Response(JSON.stringify(data), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
      } catch (err) {
        console.error("[PlusUnlocker] Error in account interceptor:", err);
      }
    }

    // 2. Rotor sessions - filter out audio ads and promo items
    if (url.includes("/rotor/session/")) {
      try {
        const res = await originalFetch.apply(this, args);
        if (res.ok) {
          const data = await res.json();
          if (!url.includes("feedback")) {
            const filterAds = (tracks) => {
              if (!Array.isArray(tracks)) return tracks;
              return tracks.filter((item) => {
                const t = item.track || item;
                if (!t) return false;
                if (t.type === "ad" || t.ad) return false;
                const title = t.title || "";
                if (title.includes("Upgrade") || title.includes("Промокод")) return false;
                if (t.type === "promo" || t.isPromo) return false;
                return true;
              });
            };

            if (data.sequence) {
              data.sequence = filterAds(data.sequence);
            }
            if (data.result && data.result.sequence) {
              data.result.sequence = filterAds(data.result.sequence);
            }
          }
          return new Response(JSON.stringify(data), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
      } catch (err) {
        console.error("[PlusUnlocker] Error in rotor interceptor:", err);
      }
    }

    // 3. get-file-info - remove track restrictions, audio ads and track preview limits
    if (url.includes("/get-file-info")) {
      try {
        const res = await originalFetch.apply(this, args);
        if (res.ok) {
          const data = await res.json();
          let requestedTrackId = null;
          try {
            const urlObj = new URL(url.startsWith("http") ? url : "https://api.music.yandex.net" + url);
            requestedTrackId = urlObj.searchParams.get("trackId");
          } catch (e) {}

          const returnedTrackId = data && data.downloadInfo ? String(data.downloadInfo.trackId) : null;
          const isAdCodec = data && data.downloadInfo && (data.downloadInfo.codec === "ad" || data.downloadInfo.title === "Upgrade");

          if (requestedTrackId && (returnedTrackId !== String(requestedTrackId) || isAdCodec)) {
            console.log(`[PlusUnlocker] Ad detected in get-file-info for track ${requestedTrackId}, bypassing...`);
            const cleanInfo = await fetchCleanTrackInfo(requestedTrackId);
            if (cleanInfo) {
              return new Response(JSON.stringify(cleanInfo), {
                status: 200,
                headers: { "Content-Type": "application/json" },
              });
            }
          }

          return new Response(JSON.stringify(data), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
      } catch (err) {
        console.error("[PlusUnlocker] Error in get-file-info interceptor:", err);
      }
    }

    // 4. Experiments details (Pass-through with user overrides only)
    if (url.includes("/account/experiments/details")) {
      try {
        const res = await originalFetch.apply(this, args);
        if (res.ok) {
          const data = await res.json();
          const customOverrides = modSettings["settings/accountExperimentsOverride"] || [];
          if (Array.isArray(customOverrides) && customOverrides.length > 0) {
            const modified = { ...data };
            for (const item of customOverrides) {
              if (item && item.id) {
                modified[item.id] = item.value;
              }
            }
            return new Response(JSON.stringify(modified), {
              status: res.status,
              headers: { "Content-Type": "application/json" },
            });
          }
          return new Response(JSON.stringify(data), {
            status: res.status,
            headers: { "Content-Type": "application/json" },
          });
        }
      } catch (err) {
        console.error("[YandexMusicMod] Error in experiments interceptor:", err);
      }
    }

    return originalFetch.apply(this, args);
  };

  
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
  function applyUiCleaner() {
    const existing = document.getElementById(UI_CLEANER_STYLESHEET_ID);
    if (existing) existing.remove();

    let css = "";
    
    // Sidebar Navigation items
    if (modSettings["cleaner/hideConcerts"] || modSettings["custom-themes/hideConcerts"]) {
      css += `
        aside[data-test-id="NAVBAR"] li:has([data-test-id="NAVBAR_NAVIGATION_ITEM_CONCERTS"]),
        aside [data-test-id="NAVBAR_NAVIGATION_ITEM_CONCERTS"],
        aside li:has(a[href*="/concerts"]),
        aside a[href*="/concerts"],
        aside a[href*="/concert"] { display: none !important; }
      `;
    }
    if (modSettings["cleaner/hideKids"] || modSettings["custom-themes/hideKids"]) {
      css += `
        aside[data-test-id="NAVBAR"] li:has([data-test-id="NAVBAR_NAVIGATION_ITEM_KIDS"]),
        aside [data-test-id="NAVBAR_NAVIGATION_ITEM_KIDS"],
        aside li:has(a[href*="/kids"]),
        aside a[href*="/kids"],
        [data-test-id="SETTINGS_KIDS_BUTTON"] { display: none !important; }
      `;
    }
    if (modSettings["cleaner/hidePodcasts"]) {
      css += `
        aside[data-test-id="NAVBAR"] li:has([data-test-id="NAVBAR_NAVIGATION_ITEM_NON_MUSIC"]),
        aside [data-test-id="NAVBAR_NAVIGATION_ITEM_NON_MUSIC"],
        aside li:has(a[href*="/non-music"]),
        aside a[href*="/non-music"],
        aside li:has(a[href*="/podcasts"]),
        aside a[href*="/podcasts"],
        aside a[href*="/books"] { display: none !important; }
      `;
    }
    if (modSettings["cleaner/hideTrends"]) {
      css += `aside li:has([data-test-id="NAVBAR_NAVIGATION_ITEM_FOR_YOU_AND_TRENDS"]), aside a[href*="/landing"] { display: none !important; }
`;
    }
    if (modSettings["cleaner/hideRadio"]) {
      css += `aside a[href*="/radio"] { display: none !important; }
`;
    }

    // Ads, Promos & Banners
    if (modSettings["cleaner/hideBanners"] !== false) {
      css += `
        div[class*="Paywall"], div[class*="Subscription"], div[data-test-id*="PROMO"], 
        div[data-test-id*="PAYWALL"], div[class*="paywall"], div[class*="WithTopBanner_banner_"], 
        div[class*="PromoBanner_"], div[class*="PaywallBanner_"], div[class*="SubscriptionBanner_"], 
        div[data-test-id="NAVBAR_NAVIGATION_ITEM_PLUS"] { display: none !important; }
      `;
    }
    if (modSettings["cleaner/hideMobileApp"] !== false) {
      css += `div[class*="InstallApp"], div[class*="MobileApp"], div[class*="QrCode"], a[href*="desktop#mobile"] { display: none !important; }
`;
    }
    if (modSettings["cleaner/hideDonates"]) {
      css += `div[class*="Donate"], button[data-test-id*="DONATE"], div[class*="TipsBlock"], a[href*="/support"], div[class*="ArtistSupport_"] { display: none !important; }
`;
    }
    if (modSettings["cleaner/hideTickets"]) {
      css += `div[class*="Ticket"], a[href*="afisha.yandex.ru"], button[data-test-id*="TICKET"], div[class*="ConcertWidget"] { display: none !important; }
`;
    }
    if (modSettings["cleaner/hideTrailers"]) {
      css += `aside a[href*="/trailers"], [data-test-id*="TRAILER"], div[class*="VideoBlock"] { display: none !important; }
`;
    }

    // Player Bar items
    if (modSettings["cleaner/hideDislike"]) {
      css += `button[data-test-id="DISLIKE_BUTTON"] { display: none !important; }
`;
    }
    if (modSettings["cleaner/hideQueue"]) {
      css += `button[data-test-id="PLAYERBAR_DESKTOP_PLAY_QUEUE_BUTTON"], button[data-test-id="QUEUE_BUTTON"] { display: none !important; }
`;
    }
    if (modSettings["cleaner/hideFullscreen"]) {
      css += `button[data-test-id="FULLSCREEN_PLAYER_BUTTON"] { display: none !important; }
`;
    }
    if (modSettings["cleaner/hideQuality"]) {
      css += `button[data-test-id="SOUND_QUALITY_BUTTON"], button[data-test-id="CONTEXT_MENU_AUDIO_QUALITY_ITEM"] { display: none !important; }
`;
    }
    if (modSettings["cleaner/hidePrev"]) {
      css += `button[data-test-id="PREVIOUS_TRACK_BUTTON"], button[data-test-id="sonata.PREVIOUS_TRACK_BUTTON"] { display: none !important; }
`;
    }
    if (modSettings["cleaner/hideLyrics"]) {
      css += `button[data-test-id="PLAYERBAR_DESKTOP_SYNC_LYRICS_BUTTON"], button[data-test-id*="LYRICS"] { display: none !important; }
`;
    }
    if (modSettings["cleaner/hideVolume"]) {
      css += `div[data-test-id="VOLUME_CONTROL_CONTAINER"], div[class*="Volume"] { display: none !important; }
`;
    }

    if (css.trim()) {
      const style = document.createElement("style");
      style.id = UI_CLEANER_STYLESHEET_ID;
      style.textContent = css;
      (document.head || document.documentElement).appendChild(style);
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
          const m = link.href.match(/track\/(\d+)/);
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
      const safeFilename = `${artist} - ${title}.mp3`.replace(/[\\/:*?"<>|]/g, "_");

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
    // Disabled inside main window to permanently prevent layout shifts or unwanted top banners
    const existing = document.getElementById("ym-osd-toast");
    if (existing) existing.remove();
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

  // ==========================================
  // 3. GUARANTEED FONTS APPLICATOR
  // ==========================================
  function ensureBaseStylesheet() {
    if (!document.getElementById("ym-mod-renderer-style")) {
      const link = document.createElement("link");
      link.id = "ym-mod-renderer-style";
      link.rel = "stylesheet";
      link.href = "/yandexMusicMod/renderer.css";
      (document.head || document.documentElement).appendChild(link);
    }
  }

  
  function applyTheme(accent = "#8b5cf6", enabled = true) {
    try {
      const existing = document.getElementById(THEME_STYLESHEET_ID);
      if (existing) existing.remove();

      if (!enabled || !accent) return;

      const glassBlur = modSettings["design/glassBlur"] || "medium";
      const cardHover = modSettings["design/cardHoverFx"] !== false;
      const playerGlow = modSettings["design/playerGlow"] !== false;
      const glowProgress = modSettings["design/glowProgress"] !== false;
      const smoothTransitions = modSettings["design/smoothTransitions"] !== false;

      let blurCss = "backdrop-filter: blur(28px) saturate(180%) !important; -webkit-backdrop-filter: blur(28px) saturate(180%) !important;";
      if (glassBlur === "off") {
        blurCss = "backdrop-filter: none !important; -webkit-backdrop-filter: none !important;";
      } else if (glassBlur === "light") {
        blurCss = "backdrop-filter: blur(14px) saturate(140%) !important; -webkit-backdrop-filter: blur(14px) saturate(140%) !important;";
      } else if (glassBlur === "ultra") {
        blurCss = "backdrop-filter: blur(44px) saturate(220%) !important; -webkit-backdrop-filter: blur(44px) saturate(220%) !important;";
      }

      let extra = "";
      if (cardHover) {
        extra += `
          div[class*="EntityCard_root"], div[class*="ItemCard_root"], div[data-test-id*="CARD"], div[class*="Track_root"]:hover {
            transition: transform 0.22s cubic-bezier(0.2, 0, 0, 1), box-shadow 0.22s cubic-bezier(0.2, 0, 0, 1) !important;
          }
          div[class*="EntityCard_root"]:hover, div[class*="ItemCard_root"]:hover, div[data-test-id*="CARD"]:hover {
            transform: translateY(-4px) scale(1.02) !important;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.5), 0 0 16px ${accent}44 !important;
          }
        `;
      }
      if (playerGlow) {
        extra += `
          div[class*="PlayerBarDesktop_root"], footer[class*="PlayerBar_root"] {
            box-shadow: 0 -4px 30px ${accent}33 !important;
            border-top: 1px solid rgba(255, 255, 255, 0.12) !important;
          }
        `;
      }
      if (glowProgress) {
        extra += `
          div[class*="ProgressBar_sliderThumb"] {
            background-color: ${accent} !important;
            box-shadow: 0 0 10px ${accent} !important;
          }
          div[class*="ProgressBar_progress_"] {
            background-color: ${accent} !important;
            box-shadow: 0 0 8px ${accent}88 !important;
          }
        `;
      }
      if (smoothTransitions) {
        extra += `
          main, div[class*="DefaultLayout_content"] {
            animation: ymPageFadeIn 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
          }
          @keyframes ymPageFadeIn {
            from { opacity: 0.85; transform: translateY(4px); }
            to { opacity: 1; transform: translateY(0); }
          }
        `;
      }

      const style = document.createElement("style");
      style.id = THEME_STYLESHEET_ID;
      style.textContent = `
        :root {
          --yandexMusicModAccent: ${accent} !important;
          --accent: ${accent} !important;
          --accent-glow: ${accent}55 !important;
          --ym-accent: ${accent} !important;
        }
        .ym-mod-btn-icon, .ym-float-icon {
          color: ${accent} !important;
        }
        .ym-mod-modal, div[class*="NavbarDesktop_root"], div[class*="PlayerBarDesktop_root"] {
          ${blurCss}
        }
        ${extra}
      `;
      (document.head || document.documentElement).appendChild(style);
    } catch (e) {
      console.error("[YandexMusicMod] Error applying theme:", e);
    }
  }

  function applyFont(fontName, enabled = true) {
    ensureBaseStylesheet();

    const existing = document.getElementById(FONT_STYLESHEET_ID);
    if (existing) existing.remove();

    if (!enabled) return;

    let fontFamily = fontName || "JetBrains Mono";
    let extraCss = "";
    if (fontName === "Terraria" || fontName === "Andy Bold") {
      fontFamily = "Terraria";
    } else if (fontName === "Minecraft") {
      fontFamily = "Minecraft";
      extraCss = "*:not(.UserID-Avatar-Image):not(img) { border-radius: 0 !important; }";
    } else if (fontName === "Russo One") {
      fontFamily = "Russo One";
    } else if (fontName === "Comfortaa") {
      fontFamily = "Comfortaa";
    } else if (fontName === "Unbounded") {
      fontFamily = "Unbounded";
    } else if (fontName === "Caveat") {
      fontFamily = "Caveat";
    } else if (fontName === "Podkova") {
      fontFamily = "Podkova";
    } else if (fontName === "JetBrains Mono") {
      fontFamily = "JetBrains Mono";
    }

    // Sanitize custom font names to strip quotes, braces, semicolons, and angle brackets
    fontFamily = String(fontFamily).replace(/["'{}<>;\\]/g, "").trim() || "JetBrains Mono";

    const rawSizeScale = parseFloat(modSettings["font-changer/sizeScale"]);
    let fontSizeScale = (!isNaN(rawSizeScale) && isFinite(rawSizeScale)) ? Math.max(0.5, Math.min(2.0, rawSizeScale)) : 1.0;
    if (isNaN(fontSizeScale)) {
      fontSizeScale = 1.0;
    }
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
      * {
        ${fontRule}
        ${sizeRule}
        ${weightRule}
        ${spacingRule}
      }
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
      }
      ${extraCss}
    `;
    (document.head || document.documentElement).appendChild(style);

    // Update live preview in settings if present
    const previewBox = document.getElementById("font-preview-box");
    if (previewBox) {
      previewBox.style.fontFamily = `"${fontFamily}", sans-serif`;
    }

    try {
      if (document.fonts && document.fonts.load && fontName && fontName !== "Yandex Sans (Original)") {
        document.fonts.load(`14px "${fontFamily}"`);
      }
    } catch (e) {}
  }
  function applyHiddenMenuItems() {
    const existing = document.getElementById("ym-mod-hidden-menu-items");
    if (existing) existing.remove();

    const hideConcerts = modSettings["custom-themes/hideConcerts"] === true;
    const hideKids = modSettings["custom-themes/hideKids"] === true;

    if (!hideConcerts && !hideKids) return;

    const style = document.createElement("style");
    style.id = "ym-mod-hidden-menu-items";
    let css = "";
    if (hideConcerts) {
      css += `
        aside[data-test-id="NAVBAR"] li:has(a[href*="/concerts"]),
        aside[data-test-id="NAVBAR"] a[href*="/concerts"],
        aside a[href*="/concerts"],
        li:has(a[href*="/concerts"]) {
          display: none !important;
        }
      `;
    }
    if (hideKids) {
      css += `
        aside[data-test-id="NAVBAR"] li:has(a[href*="/kids"]),
        aside[data-test-id="NAVBAR"] a[href*="/kids"],
        aside a[href*="/kids"],
        li:has(a[href*="/kids"]) {
          display: none !important;
        }
      `;
    }
    style.textContent = css;
    (document.head || document.documentElement).appendChild(style);
  }

  function applyScale(scale) {
    const existing = document.getElementById(SCALE_STYLESHEET_ID);
    if (existing) existing.remove();

    const numericScale = parseFloat(scale) || 1.0;
    if (numericScale === 1.0) return;

    const style = document.createElement("style");
    style.id = SCALE_STYLESHEET_ID;
    style.textContent = `
      div[class*="DefaultLayout_root_"],
      div[class*="RootLayout_root_"],
      div[class*="layout_root_"],
      main {
        zoom: ${numericScale} !important;
      }
    `;
    (document.head || document.documentElement).appendChild(style);
  }

  function applyAutoQuality() {
    if (modSettings["autoQuality/enabled"] !== false) {
      try {
        if (window.localStorage && window.localStorage.ymPlayerQuality) {
          const data = JSON.parse(window.localStorage.ymPlayerQuality);
          if (data && data.value !== "high_quality") {
            data.value = "high_quality";
            data.expires = "2077-01-01T11:29:20.427Z";
            window.localStorage.setItem("ymPlayerQuality", JSON.stringify(data));
          }
        }
      } catch (e) {}
    }
  }

  // ==========================================
  // 5. REACT FIBER TRAVERSAL HELPERS (STEPHANZION ENGINE)
  // ==========================================
  function findFiberNode(element) {
    if (!element) return null;
    const fiberKey = Object.keys(element).find((key) => key.startsWith("__reactFiber$") || key.startsWith("__reactInternalInstance$"));
    return fiberKey ? element[fiberKey] : null;
  }

  function getRootFiber(fiber) {
    let current = fiber;
    while (current && current.return) {
      current = current.return;
    }
    return current || null;
  }

  function traverseFiber(fiber, isFoundCallback, depth = 0) {
    if (!fiber || depth > 250) return null;
    const result = isFoundCallback(fiber, depth);
    if (result !== null && result !== undefined) return result;

    if (fiber.child) {
      const childResult = traverseFiber(fiber.child, isFoundCallback, depth + 1);
      if (childResult !== null && childResult !== undefined) return childResult;
    }
    if (fiber.sibling) {
      const siblingResult = traverseFiber(fiber.sibling, isFoundCallback, depth);
      if (siblingResult !== null && siblingResult !== undefined) return siblingResult;
    }
    return null;
  }

  function searchFiberProperty(element, property) {
    if (!element) return null;
    try {
      const fiberNode = findFiberNode(element);
      if (!fiberNode) return null;
      const root = getRootFiber(fiberNode);
      return traverseFiber(root, (fiber) => {
        if (fiber.memoizedProps && Object.prototype.hasOwnProperty.call(fiber.memoizedProps, property)) {
          return fiber.memoizedProps;
        }
        return null;
      });
    } catch (e) {
      return null;
    }
  }

  function extractSonataStateFromFiber(element) {
    if (!element) return null;
    try {
      // 1. Direct search from root fiber for entityMeta
      const entityMetaProps = searchFiberProperty(element, "entityMeta");
      if (entityMetaProps && entityMetaProps.entityMeta) {
        const timecodeProps = searchFiberProperty(element, "timecodeClassName") || searchFiberProperty(element, "currentTimecodeClassName");
        return {
          entityMeta: entityMetaProps.entityMeta,
          isPlaying: entityMetaProps.isPlaying,
          position: timecodeProps && timecodeProps.position !== undefined ? timecodeProps.position : entityMetaProps.position,
          duration: timecodeProps && timecodeProps.duration !== undefined ? timecodeProps.duration : entityMetaProps.duration
        };
      }

      // 2. Queue-based local search fallback
      const fiberNode = findFiberNode(element);
      if (!fiberNode) return null;

      const visited = new Set();
      const queue = [fiberNode];
      let steps = 0;

      while (queue.length > 0 && steps < 150) {
        steps++;
        const curr = queue.shift();
        if (!curr || visited.has(curr)) continue;
        visited.add(curr);

        if (curr.memoizedProps) {
          if (curr.memoizedProps.sonataState && curr.memoizedProps.sonataState.entityMeta) {
            return curr.memoizedProps.sonataState;
          }
          if (curr.memoizedProps.entityMeta && (curr.memoizedProps.entityMeta.title || curr.memoizedProps.entityMeta.id)) {
            return {
              entityMeta: curr.memoizedProps.entityMeta,
              isPlaying: curr.memoizedProps.isPlaying,
              position: curr.memoizedProps.position,
              duration: curr.memoizedProps.duration
            };
          }
          if (curr.memoizedProps.track && (curr.memoizedProps.track.title || curr.memoizedProps.track.id)) {
            return {
              entityMeta: curr.memoizedProps.track,
              isPlaying: curr.memoizedProps.isPlaying,
              position: curr.memoizedProps.position,
              duration: curr.memoizedProps.duration
            };
          }
        }

        if (curr.child) queue.push(curr.child);
        if (curr.sibling) queue.push(curr.sibling);
        if (curr.return && steps < 40) queue.push(curr.return);
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  function searchFiberProperty(element, property) {
    if (!element) return null;
    try {
      const fiberNode = findFiberNode(element);
      if (!fiberNode) return null;

      // 1. Direct check
      if (fiberNode.memoizedProps && fiberNode.memoizedProps[property] !== undefined) {
        return fiberNode.memoizedProps;
      }

      // 2. Breadth-first traversal down subtree (up to depth 150)
      const queue = [];
      if (fiberNode.child) queue.push(fiberNode.child);
      if (fiberNode.sibling) queue.push(fiberNode.sibling);

      let steps = 0;
      while (queue.length > 0 && steps < 150) {
        steps++;
        const curr = queue.shift();
        if (!curr) continue;
        if (curr.memoizedProps && curr.memoizedProps[property] !== undefined) {
          return curr.memoizedProps;
        }
        if (curr.child) queue.push(curr.child);
        if (curr.sibling) queue.push(curr.sibling);
      }

      // 3. Check parents up to 8 levels
      let parent = fiberNode.return;
      let pCount = 0;
      while (parent && pCount < 8) {
        if (parent.memoizedProps && parent.memoizedProps[property] !== undefined) {
          return parent.memoizedProps;
        }
        parent = parent.return;
        pCount++;
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  // ==========================================
  // 6. MOD SETTINGS MODAL UI
  // ==========================================
  function injectModUI() {
    if (document.getElementById("ym-mod-modal-backdrop")) return;

    // 1. Create Modal Backdrop
    const backdrop = document.createElement("div");
    backdrop.id = "ym-mod-modal-backdrop";
    backdrop.className = "ym-mod-modal-backdrop";

    backdrop.innerHTML = `
      <div class="ym-mod-modal" id="ym-mod-modal">
        <!-- Header -->
        <div class="ym-modal-header">
          <div class="ym-modal-title-wrap">
            <div class="ym-modal-logo">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M9 18V5l12-2v13"></path>
                <circle cx="6" cy="18" r="3"></circle>
                <circle cx="18" cy="16" r="3"></circle>
              </svg>
            </div>
            <div class="ym-modal-title">Настройки мода</div>
            <div class="ym-modal-version">v1.2.0 (YM 5.124.1)</div>
          </div>
          <button class="ym-modal-close" id="ym-mod-close-btn" title="Закрыть (Esc)">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <!-- Body -->
        <div class="ym-modal-body">
          <!-- Sidebar Tabs -->
          <div class="ym-modal-tabs">
            <button class="ym-tab-btn active" data-tab="tab-plus">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
              </svg>
              <span>Основные</span>
            </button>
            <button class="ym-tab-btn" data-tab="tab-appearance">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="13.5" cy="6.5" r=".5" fill="currentColor"></circle>
                <circle cx="17.5" cy="10.5" r=".5" fill="currentColor"></circle>
                <circle cx="8.5" cy="7.5" r=".5" fill="currentColor"></circle>
                <circle cx="6.5" cy="12.5" r=".5" fill="currentColor"></circle>
                <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.563-2.512 5.563-5.563C22 6.5 17.5 2 12 2z"></path>
              </svg>
              <span>Внешний вид</span>
            </button>
            <button class="ym-tab-btn" data-tab="tab-cleaner">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                <line x1="1" y1="1" x2="23" y2="23"></line>
              </svg>
              <span>Очистка UI</span>
            </button>
            <button class="ym-tab-btn" data-tab="tab-fonts">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="4 7 4 4 20 4 20 7"></polyline>
                <line x1="9" y1="20" x2="15" y2="20"></line>
                <line x1="12" y1="4" x2="12" y2="20"></line>
              </svg>
              <span>Шрифты</span>
            </button>
            <button class="ym-tab-btn" data-tab="tab-overlay">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="2" y="6" width="20" height="12" rx="2"></rect>
                <line x1="6" y1="12" x2="10" y2="12"></line>
                <line x1="8" y1="10" x2="8" y2="14"></line>
                <circle cx="15" cy="13" r="1"></circle>
                <circle cx="18" cy="11" r="1"></circle>
              </svg>
              <span>Игровой HUD</span>
            </button>
            <button class="ym-tab-btn" data-tab="tab-karaoke">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                <line x1="12" y1="19" x2="12" y2="23"></line>
                <line x1="8" y1="23" x2="16" y2="23"></line>
              </svg>
              <span>Караоке</span>
            </button>
            <button class="ym-tab-btn" data-tab="tab-tweaks">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
              </svg>
              <span>Discord и твики</span>
            </button>
            <button class="ym-tab-btn" data-tab="tab-about">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
              <span>О моде</span>
            </button>
          </div>

          <!-- Content Panels -->
          <div class="ym-modal-content">
            <!-- TAB 0: PLUS UNLOCKER -->
            <div class="ym-tab-pane active" id="tab-plus">
              <div class="ym-card">
                <div class="ym-card-title">Яндекс Плюс</div>
                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Статус подписки</span>
                    <span class="ym-desc" style="color:#10b981;font-weight:600;">Активен (hasPlus: true)</span>
                  </div>
                  <button class="ym-btn-action ym-btn-primary" id="btn-reload-plus">
                    Перезагрузить приложение
                  </button>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Снятие 30-секундного лимита</span>
                    <span class="ym-desc">Воспроизведение полных аудиотреков в высоком битрейте</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-plus-enabled" checked disabled>
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Неограниченные пропуски</span>
                    <span class="ym-desc">Снятие ограничений на пропуск треков в Моей Волне</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-plus-skips" checked disabled>
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Блокировка рекламы</span>
                    <span class="ym-desc">Подавление баннеров подписки и рекламных аудиовставок</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-plus-ads" checked disabled>
                    <span class="ym-slider"></span>
                  </label>
                </div>
              </div>
            </div>

            <!-- TAB 1: APPEARANCE -->
            <div class="ym-tab-pane" id="tab-appearance">
              <div class="ym-card">
                <div class="ym-card-title">Стиль и акцентные цвета</div>
                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Режим оформления</span>
                    <span class="ym-desc">Переключение визуальной структуры плеера</span>
                  </div>
                  <select class="ym-select" id="opt-design-mode">
                    <option value="modern">Modern Glass (Матовое стекло)</option>
                    <option value="classic">Классический темный</option>
                    <option value="compact">Компактный (Минимализм)</option>
                  </select>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Акцентный цвет</span>
                    <span class="ym-desc">Цвет выделения, кнопок, свечения и ползунков</span>
                  </div>
                  <div class="ym-palette-wrap">
                    <div class="ym-color-swatch" data-color="#8b5cf6" style="background:#8b5cf6;" title="Киберпанк Фиолетовый"></div>
                    <div class="ym-color-swatch" data-color="#007acc" style="background:#007acc;" title="Неоновый Синий"></div>
                    <div class="ym-color-swatch" data-color="#fed42b" style="background:#fed42b;" title="Яндекс Жёлтый"></div>
                    <div class="ym-color-swatch" data-color="#10b981" style="background:#10b981;" title="Изумрудный Неон"></div>
                    <div class="ym-color-swatch" data-color="#ff7b00" style="background:#ff7b00;" title="Закатный Оранжевый"></div>
                    <div class="ym-color-swatch" data-color="#ff3347" style="background:#ff3347;" title="Рубиновый Красный"></div>
                    <div class="ym-color-swatch" data-color="#f43f5e" style="background:#f43f5e;" title="Неоновый Розовый"></div>
                    <div class="ym-color-swatch" data-color="#e2e8f0" style="background:#e2e8f0;" title="Серебряный Монохром"></div>
                    <input type="color" class="ym-color-picker" id="opt-custom-color" value="#8b5cf6" title="Свой цвет">
                  </div>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Размытие стекла (Glassmorphism)</span>
                    <span class="ym-desc">Интенсивность матового эффекта фона</span>
                  </div>
                  <select class="ym-select" id="opt-glass-blur">
                    <option value="medium">Премиум стекло (28px)</option>
                    <option value="light">Мягкое стекло (14px)</option>
                    <option value="ultra">Глубокое матовое (44px)</option>
                    <option value="off">Без размытия (Выкл)</option>
                  </select>
                </div>
              </div>

              <div class="ym-card">
                <div class="ym-card-title">Эффекты и плавные анимации</div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Плавные анимации карточек (Hover FX)</span>
                    <span class="ym-desc">Мягкий подъем и неоновое свечение треков и альбомов при наведении</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-card-hover">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Неоновая подсветка плеера (Ambient Glow)</span>
                    <span class="ym-desc">Мягкое свечение нижней панели плеера под цвет акцента</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-player-glow">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Светящийся прогресс-бар</span>
                    <span class="ym-desc">Неоновое свечение линии воспроизведения трека</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-glow-progress">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Плавные переходы страниц</span>
                    <span class="ym-desc">60fps анимации переходов между альбомами и плейлистами</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-smooth-transitions">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Отключить 3D-анимацию «Моя Волна»</span>
                    <span class="ym-desc">Снижает нагрузку на видеокарту и экономит ресурсы</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-disable-vibe">
                    <span class="ym-slider"></span>
                  </label>
                </div>
              </div>
            </div>

            <!-- TAB 2: CLEANER -->
            <div class="ym-tab-pane" id="tab-cleaner">
              <div class="ym-card">
                <div class="ym-card-title">Боковое меню навигации</div>
                
                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть раздел «Концерты»</span>
                    <span class="ym-desc">Убирает пункт афиши концертов из панели навигации</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-cleaner-concerts">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть раздел «Детям»</span>
                    <span class="ym-desc">Убирает детский раздел из левой панели</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-cleaner-kids">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть раздел «Подкасты и книги»</span>
                    <span class="ym-desc">Убирает подкасты, аудиокниги и лекции</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-cleaner-podcasts">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть раздел «Тренды и рекомендации»</span>
                    <span class="ym-desc">Убирает блок трендов и промо-чартов</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-cleaner-trends">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть раздел «Радио»</span>
                    <span class="ym-desc">Убирает радиостанции из бокового меню</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-cleaner-radio">
                    <span class="ym-slider"></span>
                  </label>
                </div>
              </div>

              <div class="ym-card">
                <div class="ym-card-title">Реклама, баннеры и промо-блоки</div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть рекламные баннеры и Плюс</span>
                    <span class="ym-desc">Убирает все промо-баннеры и предложения оформить подписку</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-cleaner-banners">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть блок «Установить на телефон»</span>
                    <span class="ym-desc">Убирает QR-коды и баннеры мобильного приложения</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-cleaner-mobile">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть «Донаты артисту» (чаевые)</span>
                    <span class="ym-desc">Убирает кнопки донатов на страницах исполнителей</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-cleaner-donates">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть «Купить билет на концерт»</span>
                    <span class="ym-desc">Убирает афиши и виджеты покупки билетов у артистов</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-cleaner-tickets">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть видеоклипы и трейлеры</span>
                    <span class="ym-desc">Убирает блоки видеороликов на страницах треков</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-cleaner-trailers">
                    <span class="ym-slider"></span>
                  </label>
                </div>
              </div>

              <div class="ym-card">
                <div class="ym-card-title">Элементы плеера (Нижняя панель)</div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть кнопку «Дизлайк» (Не нравится)</span>
                    <span class="ym-desc">Убирает кнопку дизлайка из панели воспроизведения</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-cleaner-dislike">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть кнопку «Очередь воспроизведения»</span>
                    <span class="ym-desc">Убирает список следующих треков из нижнего бара</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-cleaner-queue">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть кнопку «Полноэкранный режим»</span>
                    <span class="ym-desc">Убирает иконку перехода на полный экран</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-cleaner-fullscreen">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть кнопку «Качество звука»</span>
                    <span class="ym-desc">Убирает значок HQ / Lossless из плеера</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-cleaner-quality">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть кнопку «Предыдущий трек»</span>
                    <span class="ym-desc">Оставляет только кнопки воспроизведения и перехода вперёд</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-cleaner-prev">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть кнопку «Текст песни»</span>
                    <span class="ym-desc">Убирает штатную кнопку караоке из нижнего плеера</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-cleaner-lyrics">
                    <span class="ym-slider"></span>
                  </label>
                </div>
              </div>
            </div>

            <!-- TAB 3: FONTS -->
            <div class="ym-tab-pane" id="tab-fonts">
              <div class="ym-card">
                <div class="ym-card-title">Кастомная типографика</div>
                
                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Включить замену шрифта</span>
                    <span class="ym-desc">Применять выбранный шрифт ко всему интерфейсу приложения</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-font-enabled">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Семейство шрифтов</span>
                    <span class="ym-desc">Встроенные игровые, ретро и современные шрифты с поддержкой кириллицы</span>
                  </div>
                  <select class="ym-select" id="opt-font-family">
                    <option value="Terraria">Terraria / Andy Bold (Мультяшный)</option>
                    <option value="Minecraft">Minecraft (Пиксельный ретро)</option>
                    <option value="Russo One">Russo One (Аркадный геймерский)</option>
                    <option value="Comfortaa">Comfortaa (Сглаженный футуризм)</option>
                    <option value="Unbounded">Unbounded (Техно / Sci-Fi)</option>
                    <option value="Caveat">Caveat (Живой рукописный)</option>
                    <option value="Podkova">Podkova (Винтажный брусок)</option>
                    <option value="JetBrains Mono">JetBrains Mono (Моноширинный код)</option>
                    <option value="Yandex Sans (Original)">Оригинальный (Yandex Sans)</option>
                  </select>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Пользовательский шрифт</span>
                    <span class="ym-desc">Имя любого системного шрифта Windows (Arial, Segoe UI, Comic Sans...)</span>
                  </div>
                  <input type="text" class="ym-input" id="opt-font-custom" placeholder="Например: Segoe UI" />
                </div>
              </div>

              <!-- Live Font Preview -->
              <div class="ym-card ym-font-preview-card">
                <div class="ym-card-title">Предпросмотр шрифта</div>
                <div class="ym-font-preview-box" id="font-preview-box">
                  <div class="ym-preview-title">Яндекс Музыка</div>
                  <div class="ym-preview-body">Съешь же ещё этих мягких французских булок, да выпей чаю.</div>
                  <div class="ym-preview-sub">The quick brown fox jumps over the lazy dog • 0123456789 • ♫ ♪ ♬</div>
                </div>
              </div>
            </div>

            <!-- TAB 4: OVERLAY -->
            <div class="ym-tab-pane" id="tab-overlay">
              <div class="ym-card">
                <div class="ym-card-title">Игровой HUD Оверлей</div>
                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Включить оверлей</span>
                    <span class="ym-desc">Плавающий прозрачный HUD поверх всех игр и полноэкранных окон</span>
                  </div>
                  <button class="ym-btn-action ym-btn-primary" id="btn-open-overlay">
                    Открыть оверлей
                  </button>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Режим сквозного клика (Ghost Mode)</span>
                    <span class="ym-desc">Клики проходят сквозь оверлей прямо в окно игры</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-overlay-ghost">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Без цветного ореола (Чистая тень)</span>
                    <span class="ym-desc">Убирает красные и цветные блики вокруг окна HUD</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-hud-pure-shadow">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Строка караоке в HUD</span>
                    <span class="ym-desc">Отображать бегущую строку текста песни внизу HUD</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-hud-show-lyrics">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Горячая клавиша скрытия</span>
                    <span class="ym-desc">Быстро скрыть или показать HUD в игре</span>
                  </div>
                  <span class="ym-badge">Ctrl + Shift + O</span>
                </div>
              </div>
            </div>

            <!-- TAB 5: KARAOKE -->
            <div class="ym-tab-pane" id="tab-karaoke">
              <div class="ym-card">
                <div class="ym-card-title">Плавающее Караоке</div>
                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Синхронный караоке-текст</span>
                    <span class="ym-desc">Отображать бегущую строку текста текущей песни поверх окон</span>
                  </div>
                  <button class="ym-btn-action ym-btn-primary" id="btn-open-karaoke">
                    Открыть караоке
                  </button>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Горячая клавиша</span>
                    <span class="ym-desc">Включение и выключение караоке виджета</span>
                  </div>
                  <span class="ym-badge">Ctrl + Shift + K</span>
                </div>
              </div>
            </div>

            <!-- TAB 6: TWEAKS -->
            <div class="ym-tab-pane" id="tab-tweaks">
              <div class="ym-card">
                <div class="ym-card-title">Discord и твики</div>
                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Discord Rich Presence (RPC)</span>
                    <span class="ym-desc">Отображение текущего трека, обложки и времени в вашем Discord статусе</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-discord-rpc">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Авто-выбор максимального качества</span>
                    <span class="ym-desc">Принудительно запрашивать максимальный доступный аудиобитрейт</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-auto-quality">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Масштаб интерфейса</span>
                    <span class="ym-desc">Регулировка масштабирования элементов окна</span>
                  </div>
                  <select class="ym-select" id="opt-ui-scale">
                    <option value="0.8">80%</option>
                    <option value="0.9">90%</option>
                    <option value="1.0">100% (По умолчанию)</option>
                    <option value="1.1">110%</option>
                    <option value="1.25">125%</option>
                  </select>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Консоль отладки</span>
                    <span class="ym-desc">Открыть Chrome Developer Tools для инспекции элементов</span>
                  </div>
                  <button class="ym-btn-action ym-btn-secondary" id="btn-open-devtools">
                    Открыть DevTools
                  </button>
                </div>
              </div>
            </div>

            <!-- TAB 7: ABOUT -->
            <div class="ym-tab-pane" id="tab-about">
              <div class="ym-card">
                <div class="ym-card-title">О моде</div>
                <p style="font-size:13px;color:rgba(255,255,255,0.65);line-height:1.6;margin:0 0 12px 0;">
                  Модификация для официального настольного клиента Яндекс Музыки (версия 5.124.1).<br>
                  Включает разблокировку Яндекс Плюс, кастомные шрифты с поддержкой кириллицы, игровой оверлей, плавающее караоке с каскадным поиском текстов и синхронизацию Discord RPC.
                </p>
                <div class="ym-row" style="border-top:1px solid rgba(255,255,255,0.06);padding-top:12px;">
                  <span class="ym-label">Горячие клавиши настроек</span>
                  <span class="ym-badge">Ctrl + Shift + S</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(backdrop);

    // Tab Switching
    const tabBtns = backdrop.querySelectorAll(".ym-tab-btn");
    const tabPanes = backdrop.querySelectorAll(".ym-tab-pane");

    tabBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        tabBtns.forEach((b) => b.classList.remove("active"));
        tabPanes.forEach((p) => p.classList.remove("active"));
        btn.classList.add("active");
        const targetId = btn.getAttribute("data-tab");
        const targetPane = document.getElementById(targetId);
        if (targetPane) targetPane.classList.add("active");
      });
    });

    // Close handlers
    const closeBtn = document.getElementById("ym-mod-close-btn");
    if (closeBtn) closeBtn.addEventListener("click", closeModSettings);

    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) closeModSettings();
    });

    // Option Binds
    const optDesignMode = document.getElementById("opt-design-mode");
    const optGlassBlur = document.getElementById("opt-glass-blur");
    const optCardHover = document.getElementById("opt-card-hover");
    const optPlayerGlow = document.getElementById("opt-player-glow");
    const optGlowProgress = document.getElementById("opt-glow-progress");
    const optSmoothTransitions = document.getElementById("opt-smooth-transitions");
    const optDisableVibe = document.getElementById("opt-disable-vibe");
    
    const optFontEnabled = document.getElementById("opt-font-enabled");
    const optFontFamily = document.getElementById("opt-font-family");
    const optFontCustom = document.getElementById("opt-font-custom");
    const previewBox = document.getElementById("font-preview-box");

    const optOverlayGhost = document.getElementById("opt-overlay-ghost");
    const optHudPureShadow = document.getElementById("opt-hud-pure-shadow");
    const optHudShowLyrics = document.getElementById("opt-hud-show-lyrics");

    const optDiscordRpc = document.getElementById("opt-discord-rpc");
    const optAutoQuality = document.getElementById("opt-auto-quality");
    const optUiScale = document.getElementById("opt-ui-scale");

    // Cleaner binds
    const optCleanerConcerts = document.getElementById("opt-cleaner-concerts");
    const optCleanerKids = document.getElementById("opt-cleaner-kids");
    const optCleanerPodcasts = document.getElementById("opt-cleaner-podcasts");
    const optCleanerTrends = document.getElementById("opt-cleaner-trends");
    const optCleanerRadio = document.getElementById("opt-cleaner-radio");
    const optCleanerBanners = document.getElementById("opt-cleaner-banners");
    const optCleanerMobile = document.getElementById("opt-cleaner-mobile");
    const optCleanerDonates = document.getElementById("opt-cleaner-donates");
    const optCleanerTickets = document.getElementById("opt-cleaner-tickets");
    const optCleanerTrailers = document.getElementById("opt-cleaner-trailers");
    const optCleanerDislike = document.getElementById("opt-cleaner-dislike");
    const optCleanerQueue = document.getElementById("opt-cleaner-queue");
    const optCleanerFullscreen = document.getElementById("opt-cleaner-fullscreen");
    const optCleanerQuality = document.getElementById("opt-cleaner-quality");
    const optCleanerPrev = document.getElementById("opt-cleaner-prev");
    const optCleanerLyrics = document.getElementById("opt-cleaner-lyrics");

    // Populate initial values safely
    if (optDesignMode) optDesignMode.value = modSettings["design/mode"] || "modern";
    if (optGlassBlur) optGlassBlur.value = modSettings["design/glassBlur"] || "medium";
    if (optCardHover) optCardHover.checked = modSettings["design/cardHoverFx"] !== false;
    if (optPlayerGlow) optPlayerGlow.checked = modSettings["design/playerGlow"] !== false;
    if (optGlowProgress) optGlowProgress.checked = modSettings["design/glowProgress"] !== false;
    if (optSmoothTransitions) optSmoothTransitions.checked = modSettings["design/smoothTransitions"] !== false;
    if (optDisableVibe) optDisableVibe.checked = !!modSettings["custom-themes/disableVibeAnimation"];

    if (optFontEnabled) optFontEnabled.checked = modSettings["font-changer/enabled"] !== false;
    if (optFontFamily) {
      optFontFamily.value = modSettings["font-changer/savedFont"] || "Terraria";
      if (previewBox) {
        previewBox.style.fontFamily = `"${optFontFamily.value}", sans-serif`;
      }
    }

    if (optOverlayGhost) optOverlayGhost.checked = !!modSettings["overlay/clickThrough"];
    if (optHudPureShadow) optHudPureShadow.checked = modSettings["overlay/pureShadow"] !== false;
    if (optHudShowLyrics) optHudShowLyrics.checked = modSettings["overlay/showLyrics"] !== false;

    if (optDiscordRpc) optDiscordRpc.checked = modSettings["discordRPC/enabled"] !== false;
    if (optAutoQuality) optAutoQuality.checked = modSettings["autoQuality/enabled"] !== false;
    if (optUiScale) optUiScale.value = String(modSettings["scale-changer/savedScale"] || "1.0");

    // Cleaner values
    if (optCleanerConcerts) optCleanerConcerts.checked = !!modSettings["cleaner/hideConcerts"];
    if (optCleanerKids) optCleanerKids.checked = !!modSettings["cleaner/hideKids"];
    if (optCleanerPodcasts) optCleanerPodcasts.checked = !!modSettings["cleaner/hidePodcasts"];
    if (optCleanerTrends) optCleanerTrends.checked = !!modSettings["cleaner/hideTrends"];
    if (optCleanerRadio) optCleanerRadio.checked = !!modSettings["cleaner/hideRadio"];
    if (optCleanerBanners) optCleanerBanners.checked = modSettings["cleaner/hideBanners"] !== false;
    if (optCleanerMobile) optCleanerMobile.checked = modSettings["cleaner/hideMobileApp"] !== false;
    if (optCleanerDonates) optCleanerDonates.checked = !!modSettings["cleaner/hideDonates"];
    if (optCleanerTickets) optCleanerTickets.checked = !!modSettings["cleaner/hideTickets"];
    if (optCleanerTrailers) optCleanerTrailers.checked = !!modSettings["cleaner/hideTrailers"];
    if (optCleanerDislike) optCleanerDislike.checked = !!modSettings["cleaner/hideDislike"];
    if (optCleanerQueue) optCleanerQueue.checked = !!modSettings["cleaner/hideQueue"];
    if (optCleanerFullscreen) optCleanerFullscreen.checked = !!modSettings["cleaner/hideFullscreen"];
    if (optCleanerQuality) optCleanerQuality.checked = !!modSettings["cleaner/hideQuality"];
    if (optCleanerPrev) optCleanerPrev.checked = !!modSettings["cleaner/hidePrev"];
    if (optCleanerLyrics) optCleanerLyrics.checked = !!modSettings["cleaner/hideLyrics"];

    // Palette swatches
    const swatches = document.querySelectorAll(".ym-color-swatch");
    const customColor = document.getElementById("opt-custom-color");
    const currentAccent = modSettings["custom-themes/accent"] || "#007acc";

    swatches.forEach((s) => {
      if (s.getAttribute("data-color") === currentAccent) s.classList.add("active");
      s.addEventListener("click", () => {
        swatches.forEach((sw) => sw.classList.remove("active"));
        s.classList.add("active");
        const color = s.getAttribute("data-color");
        saveSetting("custom-themes/accent", color);
        applyTheme(color, true);
        showToast(`Акцент: ${color}`);
      });
    });

    if (customColor) {
      customColor.value = currentAccent;
      customColor.addEventListener("change", () => {
        swatches.forEach((sw) => sw.classList.remove("active"));
        saveSetting("custom-themes/accent", customColor.value);
        applyTheme(customColor.value, true);
        showToast(`Цвет: ${customColor.value}`);
      });
    }

    // Change listeners safely
    if (optDesignMode) {
      optDesignMode.addEventListener("change", () => {
        saveSetting("design/mode", optDesignMode.value);
        showToast("Стиль оформления обновлен", true);
      });
    }

    if (optDisableVibe) {
      optDisableVibe.addEventListener("change", () => {
        saveSetting("custom-themes/disableVibeAnimation", optDisableVibe.checked);
        applyTheme(modSettings["custom-themes/accent"] || "#007acc", true);
      });
    }

    if (optGlassBlur) {
      optGlassBlur.addEventListener("change", () => {
        saveSetting("design/glassBlur", optGlassBlur.value);
        applyTheme(modSettings["custom-themes/accent"] || "#8b5cf6", true);
        showToast("Интенсивность матового стекла обновлена");
      });
    }

    if (optCardHover) {
      optCardHover.addEventListener("change", () => {
        saveSetting("design/cardHoverFx", optCardHover.checked);
        applyTheme(modSettings["custom-themes/accent"] || "#8b5cf6", true);
      });
    }

    if (optPlayerGlow) {
      optPlayerGlow.addEventListener("change", () => {
        saveSetting("design/playerGlow", optPlayerGlow.checked);
        applyTheme(modSettings["custom-themes/accent"] || "#8b5cf6", true);
      });
    }

    if (optGlowProgress) {
      optGlowProgress.addEventListener("change", () => {
        saveSetting("design/glowProgress", optGlowProgress.checked);
        applyTheme(modSettings["custom-themes/accent"] || "#8b5cf6", true);
      });
    }

    if (optSmoothTransitions) {
      optSmoothTransitions.addEventListener("change", () => {
        saveSetting("design/smoothTransitions", optSmoothTransitions.checked);
        applyTheme(modSettings["custom-themes/accent"] || "#8b5cf6", true);
      });
    }

    if (optHudPureShadow) {
      optHudPureShadow.addEventListener("change", () => {
        saveSetting("overlay/pureShadow", optHudPureShadow.checked);
        showToast(optHudPureShadow.checked ? "Чистые тени HUD включены" : "Чистые тени HUD выключены");
      });
    }

    if (optHudShowLyrics) {
      optHudShowLyrics.addEventListener("change", () => {
        saveSetting("overlay/showLyrics", optHudShowLyrics.checked);
      });
    }

    // UI Cleaner listeners
    const cleanerBinds = [
      { el: optCleanerConcerts, key: "cleaner/hideConcerts" },
      { el: optCleanerKids, key: "cleaner/hideKids" },
      { el: optCleanerPodcasts, key: "cleaner/hidePodcasts" },
      { el: optCleanerTrends, key: "cleaner/hideTrends" },
      { el: optCleanerRadio, key: "cleaner/hideRadio" },
      { el: optCleanerBanners, key: "cleaner/hideBanners" },
      { el: optCleanerMobile, key: "cleaner/hideMobileApp" },
      { el: optCleanerDonates, key: "cleaner/hideDonates" },
      { el: optCleanerTickets, key: "cleaner/hideTickets" },
      { el: optCleanerTrailers, key: "cleaner/hideTrailers" },
      { el: optCleanerDislike, key: "cleaner/hideDislike" },
      { el: optCleanerQueue, key: "cleaner/hideQueue" },
      { el: optCleanerFullscreen, key: "cleaner/hideFullscreen" },
      { el: optCleanerQuality, key: "cleaner/hideQuality" },
      { el: optCleanerPrev, key: "cleaner/hidePrev" },
      { el: optCleanerLyrics, key: "cleaner/hideLyrics" }
    ];

    cleanerBinds.forEach(({ el, key }) => {
      if (el) {
        el.addEventListener("change", () => {
          saveSetting(key, el.checked);
          applyUiCleaner();
        });
      }
    });

    if (optFontEnabled) {
      optFontEnabled.addEventListener("change", () => {
        saveSetting("font-changer/enabled", optFontEnabled.checked);
        const curFont = optFontFamily ? optFontFamily.value : "Terraria";
        applyFont(curFont, optFontEnabled.checked);
      });
    }

    if (optFontFamily) {
      optFontFamily.addEventListener("change", () => {
        saveSetting("font-changer/savedFont", optFontFamily.value);
        applyFont(optFontFamily.value, optFontEnabled ? optFontEnabled.checked : true);
        if (previewBox) {
          previewBox.style.fontFamily = `"${optFontFamily.value}", sans-serif`;
        }
        showToast(`Шрифт: ${optFontFamily.value}`);
      });
    }

    if (optFontCustom) {
      optFontCustom.addEventListener("change", () => {
        const sanitizedFont = optFontCustom.value.replace(/["'{}<>;\\]/g, "").trim();
        if (sanitizedFont) {
          saveSetting("font-changer/savedFont", sanitizedFont);
          applyFont(sanitizedFont, true);
          if (previewBox) {
            previewBox.style.fontFamily = `"${sanitizedFont}", sans-serif`;
          }
          showToast(`Шрифт: ${sanitizedFont}`);
        }
      });
    }

    if (optOverlayGhost) {
      optOverlayGhost.addEventListener("change", () => {
        saveSetting("overlay/clickThrough", optOverlayGhost.checked);
        if (window.yandexMusicMod && window.yandexMusicMod.setOverlayClickThrough) {
          window.yandexMusicMod.setOverlayClickThrough(optOverlayGhost.checked);
        }
      });
    }

    if (optDiscordRpc) {
      optDiscordRpc.addEventListener("change", () => {
        saveSetting("discordRPC/enabled", optDiscordRpc.checked);
      });
    }

    if (optAutoQuality) {
      optAutoQuality.addEventListener("change", () => {
        saveSetting("autoQuality/enabled", optAutoQuality.checked);
        applyAutoQuality();
        showToast(optAutoQuality.checked ? "Авто-качество включено" : "Авто-качество выключено");
      });
    }

    if (optUiScale) {
      optUiScale.addEventListener("change", () => {
        const scaleVal = parseFloat(optUiScale.value) || 1.0;
        saveSetting("scale-changer/savedScale", scaleVal);
        applyScale(scaleVal);
        showToast(`Масштаб: ${Math.round(scaleVal * 100)}%`);
      });
    }

    // Action Buttons
    document.getElementById("btn-reload-plus")?.addEventListener("click", () => {
      window.location.reload();
    });

    document.getElementById("btn-open-overlay")?.addEventListener("click", () => {
      if (window.yandexMusicMod) window.yandexMusicMod.toggleOverlay();
    });

    document.getElementById("btn-open-karaoke")?.addEventListener("click", () => {
      if (window.yandexMusicMod) window.yandexMusicMod.toggleKaraoke();
    });

    document.getElementById("btn-open-devtools")?.addEventListener("click", () => {
      if (window.yandexMusicMod) window.yandexMusicMod.openDevTools();
    });
  }

  function saveSetting(key, value) {
    modSettings[key] = value;
    if (window.yandexMusicMod && window.yandexMusicMod.setStorageValue) {
      window.yandexMusicMod.setStorageValue(key, value);
    }
  }

  // ==========================================
  // SIDEBAR BUTTON & HOTKEYS
  // ==========================================
  // ==========================================
  // SIDEBAR BUTTON & FLOATING BADGE & HOTKEYS
  // ==========================================
  function openModSettings() {
    const backdrop = document.getElementById("ym-mod-modal-backdrop");
    if (backdrop) {
      backdrop.classList.add("open");
    }
  }

  function closeModSettings() {
    const backdrop = document.getElementById("ym-mod-modal-backdrop");
    if (backdrop) {
      backdrop.classList.remove("open");
    }
  }

  function toggleModSettings() {
    const backdrop = document.getElementById("ym-mod-modal-backdrop");
    if (backdrop) {
      if (backdrop.classList.contains("open")) {
        closeModSettings();
      } else {
        openModSettings();
      }
    }
  }

  function injectFloatingBadge() {
    if (document.getElementById("ym-mod-floating-trigger")) return;

    const floatBtn = document.createElement("button");
    floatBtn.id = "ym-mod-floating-trigger";
    floatBtn.className = "ym-mod-floating-trigger";
    floatBtn.setAttribute("title", "Настройки мода (Ctrl+Shift+S / Ctrl+, / F10)");
    floatBtn.innerHTML = `
      <span class="ym-float-icon">⚡</span>
      <span class="ym-float-text">Настройки Мода</span>
    `;

    floatBtn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      toggleModSettings();
    });

    document.body.appendChild(floatBtn);
  }

  function injectSidebarButton() {
    injectFloatingBadge();

    const containerId = "ym-mod-sidebar-container";
    let container = document.getElementById(containerId);

    const targetSelector = 'div[class*="NavbarDesktopUserWidget_userProfileContainer"], aside [data-test-id="USER_PROFILE"], aside [data-test-id="USER_PROFILE_AVATAR_CONTAINER"]';
    const targetElement = document.querySelector(targetSelector);

    if (targetElement && targetElement.parentNode) {
      if (!container) {
        container = document.createElement("div");
        container.id = containerId;
        container.className = "ym-mod-sidebar-container";

        const btn = document.createElement("button");
        btn.id = "ym-mod-menu-btn";
        btn.className = "ym-mod-menu-btn";
        btn.setAttribute("title", "Настройки мода (Ctrl+Shift+S / F10)");
        btn.innerHTML = `
          <div class="ym-mod-icon-wrapper">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" class="ym-mod-custom-logo">
              <defs>
                <linearGradient id="ymLogoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#ff3347"/>
                  <stop offset="50%" stop-color="#ff8800"/>
                  <stop offset="100%" stop-color="#8b5cf6"/>
                </linearGradient>
              </defs>
              <circle cx="12" cy="12" r="10" stroke="url(#ymLogoGrad)" stroke-width="2.2" stroke-dasharray="5 2.5"/>
              <path d="M9 8.5v7l6-3.5-6-3.5z" fill="url(#ymLogoGrad)"/>
              <circle cx="12" cy="12" r="2" fill="#fff"/>
            </svg>
          </div>
          <span class="ym-mod-btn-text">Настройки Мода</span>
          <span class="ym-mod-ver-tag">v1.2.0</span>
        `;
        btn.addEventListener("click", (e) => {
          e.preventDefault();
          e.stopPropagation();
          toggleModSettings();
        });

        container.appendChild(btn);
        targetElement.parentNode.insertBefore(container, targetElement);

        // Sidebar collapse observer
        const aside = targetElement.closest("aside") || document.querySelector("aside");
        if (aside && typeof ResizeObserver !== "undefined") {
          const checkCollapsed = () => {
            if (aside.offsetWidth < 120) {
              container.classList.add("ym-sidebar-collapsed");
            } else {
              container.classList.remove("ym-sidebar-collapsed");
            }
          };
          const ro = new ResizeObserver(checkCollapsed);
          ro.observe(aside);
          checkCollapsed();
        }
      }
      const floatBtn = document.getElementById("ym-mod-floating-trigger");
      if (floatBtn) floatBtn.style.display = "none";
    } else {
      // Fallback: Navbar list item
      const navItem = document.querySelector('[data-test-id="NAVBAR_NAVIGATION_ITEM_COLLECTION"]') ||
                      document.querySelector('[data-test-id="NAVBAR_NAVIGATION_ITEM_HOME"]');
      if (navItem && !document.getElementById("ym-mod-menu-btn")) {
        const parentLi = navItem.closest("li");
        if (parentLi && parentLi.parentNode) {
          const li = document.createElement("li");
          li.id = "ym-mod-nav-item";
          li.className = parentLi.className || "";
          li.style.cssText = "list-style: none; margin: 4px 12px; padding: 0;";

          const btn = document.createElement("button");
          btn.id = "ym-mod-menu-btn";
          btn.className = "ym-mod-menu-btn";
          btn.innerHTML = `
            <span class="ym-mod-btn-icon">⚡</span>
            <span class="ym-mod-btn-text">Мод</span>
            <span class="ym-mod-badge">Menu</span>
          `;
          btn.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();
            toggleModSettings();
          });

          li.appendChild(btn);
          parentLi.parentNode.insertBefore(li, parentLi.nextSibling);
        }
      }
    }
  }

  // Global Hotkeys for opening settings: Ctrl+Shift+S, Ctrl+, F10 and Escape
  window.addEventListener("keydown", (e) => {
    const isCtrlShiftS = (e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === "S" || e.key === "s" || e.code === "KeyS");
    const isCtrlComma = (e.ctrlKey || e.metaKey) && (e.key === "," || e.code === "Comma");
    const isF10 = e.key === "F10" || e.code === "F10";
    if (isCtrlShiftS || isCtrlComma || isF10) {
      e.preventDefault();
      toggleModSettings();
    }
    if (e.key === "Escape") {
      closeModSettings();
    }
  });

  // Listen for openModSettings IPC from main process
  if (window.yandexMusicMod && window.yandexMusicMod.onOpenSettings) {
    window.yandexMusicMod.onOpenSettings(() => openModSettings());
  }


  // ==========================================
  // 7. PLAYER OBSERVATION & REMOTE CONTROL
  // ==========================================
  let lastTrackId = null;

  function parseTimecode(text) {
    if (!text || typeof text !== "string") return 0;
    const parts = text.trim().split(":").map((p) => parseInt(p, 10));
    if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
      return parts[0] * 60 + parts[1];
    }
    if (parts.length === 3 && !isNaN(parts[0]) && !isNaN(parts[1]) && !isNaN(parts[2])) {
      return parts[0] * 3600 + parts[1] * 60 + parts[2];
    }
    return 0;
  }

  function scrapeCurrentPlayerState() {
    let title = "";
    let artists = "";
    let coverUrl = "";
    let trackId = "";
    let duration = 0;
    let position = 0;
    let liked = false;
    let isPlaying = false;
    let rawMeta = null;

    // 1. MediaSession API (Authoritative source across all views)
    if (navigator.mediaSession) {
      if (navigator.mediaSession.metadata) {
        const m = navigator.mediaSession.metadata;
        if (m.title) title = String(m.title).trim();
        if (m.artist) artists = String(m.artist).trim();
        if (Array.isArray(m.artwork) && m.artwork.length > 0) {
          coverUrl = m.artwork[m.artwork.length - 1].src;
        }
      }
      if (navigator.mediaSession.playbackState) {
        if (navigator.mediaSession.playbackState === "playing") isPlaying = true;
        else if (navigator.mediaSession.playbackState === "paused") isPlaying = false;
      }
    }

    // 2. Audio Elements (Precise position, duration, and playing state)
    const audios = Array.from(document.querySelectorAll("audio"));
    const activeAudio = audios.find((a) => !a.paused) || audios[0];
    if (activeAudio) {
      if (!isPlaying) isPlaying = !activeAudio.paused;
      if (activeAudio.currentTime !== undefined && !isNaN(activeAudio.currentTime)) {
        position = Math.floor(activeAudio.currentTime);
      }
      if (activeAudio.duration && !isNaN(activeAudio.duration) && activeAudio.duration > 0) {
        duration = Math.floor(activeAudio.duration);
      }
    }

    // 3. React Fiber Inspection on all candidate containers
    const containers = [
      document.querySelector('div[data-test-id="FULLSCREEN_PLAYER_MODAL"]'),
      document.querySelector('section[data-test-id="PLAYERBAR_DESKTOP"]'),
      document.querySelector('div[data-test-id="VIBE_BLOCK"]'),
      document.querySelector('div[data-test-id="VIBE_PLAYERBAR"]'),
      document.querySelector('[data-test-id="VIBE_PLAYERBAR_TRACK_NAME"]'),
      document.querySelector('[data-test-id="TRACK_TITLE"]'),
      document.querySelector('[data-test-id="VIBE_ALBUM_COVER"]'),
      document.querySelector('[data-test-id="PLAYERBAR_DESKTOP_COVER_CONTAINER"]'),
      window.sonataState ? { memoizedProps: { sonataState: window.sonataState } } : null
    ];

    for (const el of containers) {
      if (!el) continue;
      const sonata = extractSonataStateFromFiber(el);
      if (sonata && sonata.entityMeta) {
        rawMeta = sonata.entityMeta;
        if (!title && rawMeta.title) title = String(rawMeta.title).trim();
        if (!artists) {
          if (Array.isArray(rawMeta.artists)) {
            artists = rawMeta.artists.map((a) => (typeof a === "object" ? a.name : a)).join(", ");
          } else if (rawMeta.artists) {
            artists = String(rawMeta.artists).trim();
          }
        }
        if (!coverUrl) {
          if (rawMeta.coverUri) coverUrl = "https://" + rawMeta.coverUri.replace("%%", "400x400");
          else if (rawMeta.ogImage) coverUrl = "https://" + rawMeta.ogImage.replace("%%", "400x400");
        }
        if (rawMeta.id) trackId = String(rawMeta.id);
        if ((!duration || duration === 0) && rawMeta.durationMs) {
          duration = Math.floor(rawMeta.durationMs / 1000);
        }
        if (sonata.position !== undefined && typeof sonata.position === "number") {
          position = Math.floor(sonata.position);
        }
        if (sonata.duration !== undefined && typeof sonata.duration === "number" && (!duration || duration === 0)) {
          duration = Math.floor(sonata.duration);
        }
        if (sonata.isPlaying !== undefined) isPlaying = !!sonata.isPlaying;
        break;
      }
    }

    // 4. Vibe Mode DOM Fallbacks (Fullscreen Player Modal)
    const fullscreenModal = document.querySelector('div[data-test-id="FULLSCREEN_PLAYER_MODAL"], div[data-test-id="VIBE_BLOCK"]');
    if (fullscreenModal) {
      if (!title) {
        // Track title in vibe mode is often inside a centered pill button or prominent heading
        const titleCandidates = fullscreenModal.querySelectorAll('button[class*="SonataTrackInfo"] span, button[class*="TrackInfo"] span, [class*="TrackTitle"], [class*="title"], h2');
        for (const tc of titleCandidates) {
          const tText = (tc.textContent || "").trim();
          if (tText && !tText.includes("Моя волна") && !tText.includes("Очередь")) {
            title = tText;
            break;
          }
        }
      }
      if (!artists) {
        const artistCandidates = fullscreenModal.querySelectorAll('h1, [class*="Artist"], [class*="artist"], a[href*="/artist/"]');
        for (const ac of artistCandidates) {
          const aText = (ac.textContent || "").trim();
          if (aText && aText !== title && !aText.includes("Моя волна")) {
            artists = aText;
            break;
          }
        }
      }
      if (!coverUrl) {
        const coverImg = fullscreenModal.querySelector('img[src*="avatars.yandex.net"], [data-test-id="VIBE_ALBUM_COVER"] img');
        if (coverImg && coverImg.src) {
          coverUrl = coverImg.src.replace(/\/(?:50x50|100x100|200x200)\b/, "/400x400");
        }
      }
    }

    // 5. Desktop Playerbar DOM Fallbacks
    const desktopPlayer = document.querySelector('section[data-test-id="PLAYERBAR_DESKTOP"]');
    if (desktopPlayer) {
      if (!title) {
        const titleEl = desktopPlayer.querySelector('[data-test-id="TRACK_TITLE"]');
        if (titleEl) title = (titleEl.getAttribute("title") || titleEl.textContent || "").trim();
      }
      if (!artists) {
        const artistEls = desktopPlayer.querySelectorAll('a[href*="/artist/"], [class*="description"] a');
        if (artistEls.length > 0) {
          artists = Array.from(artistEls).map((el) => el.textContent.trim()).filter(Boolean).join(", ");
        }
      }
      if (!coverUrl) {
        const imgEl = desktopPlayer.querySelector('[data-test-id="PLAYERBAR_DESKTOP_COVER_CONTAINER"] img, img[class*="cover"], img[src*="avatars.yandex.net"]');
        if (imgEl && imgEl.src) coverUrl = imgEl.src.replace(/\/(?:50x50|100x100|200x200)\b/, "/400x400");
      }
      if (!trackId) {
        const trackLink = desktopPlayer.querySelector('a[href*="/track/"]');
        if (trackLink) {
          const m = trackLink.href.match(/track\/(\d+)/);
          if (m) trackId = m[1];
        }
      }
    }

    // 6. Global Document Title Fallback
    if (!title && document.title && document.title.includes(" — ")) {
      const parts = document.title.split(" — ");
      if (parts.length >= 2 && !parts[0].includes("Яндекс Музыка")) {
        title = parts[0].trim();
        if (!artists && parts[1] && !parts[1].includes("Яндекс Музыка")) {
          artists = parts[1].trim();
        }
      }
    }

    // 7. Track ID fallback
    if (!trackId && title) {
      trackId = `${title}-${artists || "unknown"}`;
    }

    // 8. Like status
    const likeBtn = document.querySelector('button[data-test-id="LIKE_BUTTON"], button[aria-label*="Нравится"], button[aria-label*="like"]');
    if (likeBtn) {
      liked = likeBtn.getAttribute("aria-pressed") === "true" || likeBtn.classList.contains("liked");
    }

    return {
      isPlaying,
      track: {
        id: trackId,
        title,
        artists,
        coverUrl,
        liked,
        rawMeta,
      },
      progress: {
        position,
        duration,
      },
    };
  }

  function observePlayer() {
    // Only one interval runner
    if (window.__ymModObserverRunning) return;
    window.__ymModObserverRunning = true;

    setInterval(() => {
      try {
        const state = scrapeCurrentPlayerState();
        if (state && (state.track.title || state.isPlaying || state.progress.duration > 0)) {
          window.__lastPlayerState = state;
          if (window.yandexMusicMod && window.yandexMusicMod.updatePlayerState) {
            window.yandexMusicMod.updatePlayerState(state);
          }

          // If new track detected, fetch lyrics and notify
          if (state.track.id && state.track.id !== lastTrackId && state.track.title) {
            lastTrackId = state.track.id;
            fetchTrackLyrics(state.track.title, state.track.artists, state.track.rawMeta, state.track.id);
            // showOsdTrackToast disabled to prevent layout shift
          }
        }
      } catch (err) {}
    }, 350);

    // Listen for remote player actions from Overlay and Shortcuts
    if (window.yandexMusicMod && window.yandexMusicMod.onExecutePlayerAction) {
      window.yandexMusicMod.onExecutePlayerAction((action, payload) => {
        handlePlayerAction(action, payload);
      });
    }
  }

  function handlePlayerAction(action, payload) {
    if (action === "requestState") {
      const state = scrapeCurrentPlayerState();
      if (state && window.yandexMusicMod && window.yandexMusicMod.updatePlayerState) {
        window.yandexMusicMod.updatePlayerState(state);
      }
      return;
    }

    const playPauseBtn = document.querySelector('button[data-test-id="PLAY_BUTTON"], button[data-test-id="PAUSE_BUTTON"], [data-test-id="VIBE_PLAYERBAR"] button[data-test-id*="PLAY"], section[data-test-id="PLAYERBAR_DESKTOP"] button[data-test-id*="PLAY"]');
    const nextBtn = document.querySelector('button[data-test-id="sonata.NEXT_TRACK_BUTTON"], button[data-test-id="NEXT_TRACK_BUTTON"], button[data-test-id="NEXT_BUTTON"], button[aria-label*="Следующий"], button[aria-label*="next"]');
    const prevBtn = document.querySelector('button[data-test-id="sonata.PREVIOUS_TRACK_BUTTON"], button[data-test-id="PREVIOUS_TRACK_BUTTON"], button[data-test-id="PREV_BUTTON"], button[aria-label*="Предыдущий"], button[aria-label*="prev"]');
    const likeBtn = document.querySelector('button[data-test-id="LIKE_BUTTON"], button[aria-label*="Нравится"], button[aria-label*="like"]');

    if (action === "playPause") {
      if (playPauseBtn) {
        playPauseBtn.click();
      } else {
        const audios = document.querySelectorAll("audio");
        for (const a of audios) {
          a.paused ? a.play() : a.pause();
        }
      }
    } else if (action === "next") {
      if (nextBtn) nextBtn.click();
    } else if (action === "prev") {
      if (prevBtn) prevBtn.click();
    } else if (action === "like") {
      if (likeBtn) likeBtn.click();
    } else if (action === "seek" && payload && payload.position !== undefined) {
      const audios = document.querySelectorAll("audio");
      for (const a of audios) {
        a.currentTime = payload.position;
      }
    }
  }

  async function fetchTrackLyrics(title, artist, meta, directTrackId = null) {
    try {
      let lrcFound = null;
      const trackId = directTrackId || (meta && meta.id ? meta.id : null);

      // 1. Try Yandex Music API supplement with authorization headers
      if (trackId) {
        try {
          let oauthToken = null;
          try {
            if (window.localStorage && window.localStorage.oauth) {
              const parsed = JSON.parse(window.localStorage.oauth);
              if (parsed && parsed.value) oauthToken = "OAuth " + parsed.value;
            }
          } catch (e) {}

          const headers = {
            "X-Yandex-Music-Client": "YandexMusicDesktopAppWindows/5.124.1",
            "X-Yandex-Music-Frontend": "new",
          };
          if (oauthToken) headers["Authorization"] = oauthToken;

          const resp = await originalFetch(`https://api.music.yandex.net/tracks/${trackId}/supplement`, { headers });
          if (resp.ok) {
            const data = await resp.json();
            const result = data.result || data;
            if (result && result.lyrics) {
              if (result.lyrics.syncLyrics && result.lyrics.syncLyrics.length > 0) {
                lrcFound = result.lyrics.syncLyrics.map((item) => ({
                  time: item.timestamp !== undefined ? item.timestamp / 1000 : (item.offset ? item.offset / 1000 : 0),
                  text: item.line || item.text || "",
                }));
              } else if (result.lyrics.fullLyrics) {
                lrcFound = result.lyrics.fullLyrics;
              }
            }
          }
        } catch (e) {}
      }

      // 2. Fallback to LRCLib via IPC bridge
      if (!lrcFound && window.yandexMusicMod && window.yandexMusicMod.fetchLyrics && title) {
        try {
          lrcFound = await window.yandexMusicMod.fetchLyrics(title, artist, trackId);
        } catch (e) {}
      }

      // 3. Emit lyrics to Karaoke window and Overlay
      if (window.yandexMusicMod && window.yandexMusicMod.updateLyrics) {
        window.yandexMusicMod.updateLyrics({
          track: title,
          artist: artist,
          lrc: lrcFound || `[00:00.00] ${title} - ${artist}\n[00:03.00] ♫ Текст песни не найден`,
        });
      }
    } catch (e) {
      console.error("[YandexMusicMod] Error fetching track lyrics:", e);
    }
  }


  // Expose window.__getPlayerState (Stephanzion / Vzlomhik standard)
  window.__getPlayerState = () => {
    const s = window.__lastPlayerState;
    if (!s || !s.track) {
      return {
        enabled: modSettings["discordRPC/enabled"] !== false,
        showModButton: modSettings["discordRPC/showModButton"] !== false,
        data: null,
      };
    }
    const artistsArr = Array.isArray(s.track.artists)
      ? s.track.artists
      : (s.track.artists || "").split(", ").map(name => ({ name: name.trim() }));
    return {
      enabled: modSettings["discordRPC/enabled"] !== false,
      showModButton: modSettings["discordRPC/showModButton"] !== false,
      data: {
        trackMeta: {
          id: s.track.id || "0",
          title: s.track.title || "Unknown",
          version: s.track.version || "",
          coverUri: s.track.coverUrl ? s.track.coverUrl.replace(/^https?:\/\//, "").replace(/\/400x400\b/, "/%%") : "",
          artists: artistsArr,
        },
        playback: {
          position: s.progress ? s.progress.position : 0,
          duration: s.progress ? s.progress.duration : 0,
          progress: s.progress && s.progress.duration > 0 ? s.progress.position / s.progress.duration : 0,
        },
        isPlaying: !!s.isPlaying,
      },
    };
  };

  // ==========================================
  // 8. INITIALIZE ALL
  // ==========================================
  async function init() {
    try {
      await loadSettings();
    } catch (e) {
      console.error("[YandexMusicMod] Error loading settings:", e);
    }

    try {
      const accent = modSettings["custom-themes/accent"] || "#007acc";
      applyTheme(accent, true);
    } catch (e) {
      console.error("[YandexMusicMod] Error applying theme:", e);
    }

    try {
      const fontName = modSettings["font-changer/savedFont"] || "JetBrains Mono";
      const fontEnabled = modSettings["font-changer/enabled"] !== false;
      applyFont(fontName, fontEnabled);
    } catch (e) {
      console.error("[YandexMusicMod] Error applying font:", e);
    }

    try {
      applyScale(modSettings["scale-changer/savedScale"] || 1.0);
    } catch (e) {
      console.error("[YandexMusicMod] Error applying scale:", e);
    }

    try {
      applyAutoQuality();
    } catch (e) {
      console.error("[YandexMusicMod] Error applying auto quality:", e);
    }

    try {
      applyHiddenMenuItems();
    } catch (e) {
      console.error("[YandexMusicMod] Error applying hidden menu items:", e);
    }

    try {
      applyUiCleaner();
    } catch (e) {
      console.error("[YandexMusicMod] Error applying UI cleaner:", e);
    }

    try {
      injectModUI();
    } catch (e) {
      console.error("[YandexMusicMod] Error injecting Mod UI:", e);
    }

    try {
      injectSidebarButton();
      injectFloatingBadge();
    } catch (e) {
      console.error("[YandexMusicMod] Error injecting Mod buttons:", e);
    }

    try {
      const observer = new MutationObserver(() => {
        injectSidebarButton();
        injectFloatingBadge();
      });
      observer.observe(document.body, { childList: true, subtree: true });
    } catch (e) {
      console.error("[YandexMusicMod] Error observing DOM mutations:", e);
    }

    try {
      observePlayer();
    } catch (e) {
      console.error("[YandexMusicMod] Error observing player:", e);
    }

    // Continuous Top Banner Eliminator
  function killTopBanner() {
    try {
      const root = document.querySelector('div[class*="WithTopBanner_root"]');
      if (root) {
        root.style.setProperty("display", "block", "important");
        root.style.setProperty("grid-template", "none", "important");
        root.style.setProperty("height", "100vh", "important");
        root.style.setProperty("max-height", "100vh", "important");
        root.style.setProperty("overflow", "hidden", "important");

        for (const child of Array.from(root.children)) {
          if (!child.className.includes("WithTopBanner_content")) {
            child.remove();
          } else {
            child.style.setProperty("height", "100vh", "important");
            child.style.setProperty("max-height", "100vh", "important");
            child.style.setProperty("min-height", "100vh", "important");
          }
        }
      }
    } catch (e) {}
  }
  setInterval(killTopBanner, 300);
  killTopBanner();

  console.log("[YandexMusicMod] Mod initialized successfully!");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
