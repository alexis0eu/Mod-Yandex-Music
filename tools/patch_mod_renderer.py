import os, re

RENDERER_JS = r"d:\Яндекс Музыка мод\src\renderer\mod-renderer.js"
RENDERER_CSS = r"d:\Яндекс Музыка мод\src\renderer\mod-renderer.css"

with open(RENDERER_JS, "r", encoding="utf-8") as f:
    js_content = f.read()

# =========================================================================
# 1. Update searchFiberProperty to also search for sonataState and entityMeta
# =========================================================================
NEW_FIBER_FUNCS = '''  function findFiberNode(element) {
    if (!element) return null;
    const fiberKey = Object.keys(element).find((key) => key.startsWith("__reactFiber$") || key.startsWith("__reactInternalInstance$"));
    return fiberKey ? element[fiberKey] : null;
  }

  function extractSonataStateFromFiber(element) {
    if (!element) return null;
    try {
      const fiberNode = findFiberNode(element);
      if (!fiberNode) return null;

      const visited = new Set();
      const queue = [fiberNode];
      let steps = 0;

      while (queue.length > 0 && steps < 200) {
        steps++;
        const curr = queue.shift();
        if (!curr || visited.has(curr)) continue;
        visited.add(curr);

        // Check memoizedProps
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

        // Check memoizedState (React hooks linked list)
        let hook = curr.memoizedState;
        let hCount = 0;
        while (hook && hCount < 25) {
          hCount++;
          if (hook.memoizedState && typeof hook.memoizedState === "object") {
            const ms = hook.memoizedState;
            if (ms.sonataState && ms.sonataState.entityMeta) {
              return ms.sonataState;
            }
            if (ms.entityMeta && (ms.entityMeta.title || ms.entityMeta.id)) {
              return ms;
            }
          }
          hook = hook.next;
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
  }'''

# Replace searchFiberProperty definition block
old_fiber_pattern = re.compile(r'  function findFiberNode\(element\) \{[\s\S]*?return null;\s*\}\s*catch \(e\) \{\s*return null;\s*\}\s*\}', re.MULTILINE)
if old_fiber_pattern.search(js_content):
    js_content = old_fiber_pattern.sub(lambda m: NEW_FIBER_FUNCS, js_content, count=1)
    print("Replaced findFiberNode and searchFiberProperty successfully.")
else:
    print("WARNING: Could not find old findFiberNode block!")

# =========================================================================
# 2. Update applyUiCleaner to target parents and all navbar variants
# =========================================================================
NEW_UI_CLEANER = '''  function applyUiCleaner() {
    const existing = document.getElementById(UI_CLEANER_STYLESHEET_ID);
    if (existing) existing.remove();

    let css = "";
    // Navigation / Sidebar items (hide anchor and wrapper <li>)
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
    if (modSettings["cleaner/hideTrailers"]) {
      css += `aside a[href*="/trailers"], [data-test-id*="TRAILER"] { display: none !important; }\\n`;
    }
    if (modSettings["cleaner/hideRadio"]) {
      css += `aside a[href*="/radio"] { display: none !important; }\\n`;
    }
    if (modSettings["cleaner/hideVibe"]) {
      css += `div[data-test-id="VIBE_BLOCK"], div[class*="VibeBlock"] { display: none !important; }\\n`;
    }
    if (modSettings["cleaner/hideBanners"] !== false) {
      css += `div[class*="Paywall"], div[class*="Subscription"], div[data-test-id*="PROMO"], div[data-test-id*="PAYWALL"], div[class*="paywall"], div[class*="Banner"], div[data-test-id="NAVBAR_NAVIGATION_ITEM_PLUS"] { display: none !important; }\\n`;
    }

    // Player bar items
    if (modSettings["cleaner/hideDislike"]) {
      css += `button[data-test-id="DISLIKE_BUTTON"] { display: none !important; }\\n`;
    }
    if (modSettings["cleaner/hideQueue"]) {
      css += `button[data-test-id="PLAYERBAR_DESKTOP_PLAY_QUEUE_BUTTON"], button[data-test-id="QUEUE_BUTTON"] { display: none !important; }\\n`;
    }
    if (modSettings["cleaner/hideLyrics"]) {
      css += `button[data-test-id="PLAYERBAR_DESKTOP_SYNC_LYRICS_BUTTON"], button[data-test-id*="LYRICS"] { display: none !important; }\\n`;
    }
    if (modSettings["cleaner/hideFullscreen"]) {
      css += `button[data-test-id="FULLSCREEN_PLAYER_BUTTON"] { display: none !important; }\\n`;
    }
    if (modSettings["cleaner/hidePrev"]) {
      css += `button[data-test-id="PREVIOUS_TRACK_BUTTON"], button[data-test-id="sonata.PREVIOUS_TRACK_BUTTON"] { display: none !important; }\\n`;
    }
    if (modSettings["cleaner/hideQuality"]) {
      css += `button[data-test-id="SOUND_QUALITY_BUTTON"], button[data-test-id="CONTEXT_MENU_AUDIO_QUALITY_ITEM"] { display: none !important; }\\n`;
    }
    if (modSettings["cleaner/hideVolume"]) {
      css += `div[data-test-id="VOLUME_CONTROL_CONTAINER"], div[class*="Volume"] { display: none !important; }\\n`;
    }

    if (css.trim()) {
      const style = document.createElement("style");
      style.id = UI_CLEANER_STYLESHEET_ID;
      style.textContent = css;
      document.head.appendChild(style);
    }
  }'''

old_cleaner_pattern = re.compile(r'  function applyUiCleaner\(\) \{[\s\S]*?document\.head\.appendChild\(style\);\s*\}\s*\}', re.MULTILINE)
if old_cleaner_pattern.search(js_content):
    js_content = old_cleaner_pattern.sub(lambda m: NEW_UI_CLEANER, js_content, count=1)
    print("Replaced applyUiCleaner successfully.")
else:
    print("WARNING: Could not find old applyUiCleaner block!")

# =========================================================================
# 3. Update injectSidebarButton, hotkeys, and add floating badge
# =========================================================================
NEW_SIDEBAR_AND_TRIGGER = '''  // ==========================================
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

    if (document.getElementById("ym-mod-menu-btn")) return;

    const btn = document.createElement("button");
    btn.id = "ym-mod-menu-btn";
    btn.className = "ym-mod-menu-btn";
    btn.setAttribute("title", "Настройки мода (Ctrl+Shift+S / Ctrl+, / F10)");
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

    // Strategy 1: Place in navbar as its own <li> after Collection or Home
    const navItem = document.querySelector('[data-test-id="NAVBAR_NAVIGATION_ITEM_COLLECTION"]') ||
                    document.querySelector('[data-test-id="NAVBAR_NAVIGATION_ITEM_HOME"]');
    if (navItem) {
      const parentLi = navItem.closest("li");
      if (parentLi && parentLi.parentNode) {
        const li = document.createElement("li");
        li.id = "ym-mod-nav-item";
        li.className = parentLi.className || "";
        li.style.cssText = "list-style: none; margin: 4px 0; padding: 0;";
        li.appendChild(btn);
        parentLi.parentNode.insertBefore(li, parentLi.nextSibling);
        return;
      }
    }

    // Strategy 2: Place above user profile card in sidebar
    const userContainer = document.querySelector('[data-test-id="USER_PROFILE"]') || 
                          document.querySelector('[data-test-id="USER_PROFILE_AVATAR_CONTAINER"]');
    if (userContainer && userContainer.parentNode) {
      userContainer.parentNode.insertBefore(btn, userContainer);
      return;
    }

    // Strategy 3: Place directly in navbar aside
    const navbar = document.querySelector('aside[data-test-id="NAVBAR"]') || document.querySelector("aside");
    if (navbar) {
      navbar.appendChild(btn);
      return;
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
  }'''

# Replace from openModSettings to right before 7. PLAYER OBSERVATION
old_sidebar_pattern = re.compile(r'  function openModSettings\(\) \{[\s\S]*?window\.yandexMusicMod\.onOpenSettings\(\(\) => openModSettings\(\)\);\s*\}', re.MULTILINE)
if old_sidebar_pattern.search(js_content):
    js_content = old_sidebar_pattern.sub(lambda m: NEW_SIDEBAR_AND_TRIGGER, js_content, count=1)
    print("Replaced injectSidebarButton and hotkeys successfully.")
else:
    print("WARNING: Could not find old openModSettings block!")

# =========================================================================
# 4. Update observePlayer to fully support VIBE_PLAYERBAR and Fiber
# =========================================================================
NEW_OBSERVE_PLAYER = '''  // ==========================================
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

  function observePlayer() {
    // Only one interval runner
    if (window.__ymModObserverRunning) return;
    window.__ymModObserverRunning = true;

    setInterval(() => {
      try {
        const desktopPlayer = document.querySelector('section[data-test-id="PLAYERBAR_DESKTOP"]');
        const vibePlayer = document.querySelector('div[data-test-id="VIBE_PLAYERBAR"]');
        const audio = document.querySelector("audio");

        // If no player elements and no audio in DOM, nothing to observe
        if (!desktopPlayer && !vibePlayer && !audio) return;

        let title = "";
        let artists = "";
        let coverUrl = "";
        let trackId = "";
        let duration = 0;
        let position = 0;
        let liked = false;
        let isPlaying = false;
        let rawMeta = null;

        // 1. Play / Pause status
        if (audio && audio.duration) {
          isPlaying = !audio.paused;
        } else if (vibePlayer) {
          isPlaying = !vibePlayer.querySelector('button[data-test-id="PLAY_BUTTON"]');
        } else if (desktopPlayer) {
          isPlaying = !desktopPlayer.querySelector('button[data-test-id="PLAY_BUTTON"]');
        }

        // 2. React Fiber Extraction (supports both VIBE_PLAYERBAR and PLAYERBAR_DESKTOP)
        const fiberCandidates = [
          vibePlayer,
          desktopPlayer,
          document.querySelector('[data-test-id="VIBE_PLAYERBAR_TRACK_NAME"]'),
          document.querySelector('[data-test-id="TRACK_TITLE"]'),
          document.querySelector('[data-test-id="VIBE_ALBUM_COVER"]'),
          document.querySelector('[data-test-id="PLAYERBAR_DESKTOP_COVER_CONTAINER"]'),
          window.sonataState ? { memoizedProps: { sonataState: window.sonataState } } : null
        ];

        for (const candidate of fiberCandidates) {
          if (!candidate) continue;
          const sonata = extractSonataStateFromFiber(candidate);
          if (sonata && sonata.entityMeta) {
            rawMeta = sonata.entityMeta;
            if (rawMeta.title) title = String(rawMeta.title).trim();
            if (Array.isArray(rawMeta.artists)) {
              artists = rawMeta.artists.map((a) => (typeof a === "object" ? a.name : a)).join(", ");
            } else if (rawMeta.artists) {
              artists = String(rawMeta.artists).trim();
            }
            if (rawMeta.coverUri) {
              coverUrl = "https://" + rawMeta.coverUri.replace("%%", "400x400");
            } else if (rawMeta.ogImage) {
              coverUrl = "https://" + rawMeta.ogImage.replace("%%", "400x400");
            }
            if (rawMeta.id) {
              trackId = String(rawMeta.id);
            }
            if (rawMeta.durationMs) {
              duration = Math.floor(rawMeta.durationMs / 1000);
            }
            if (sonata.position !== undefined && typeof sonata.position === "number") {
              position = Math.floor(sonata.position);
            }
            if (sonata.duration !== undefined && typeof sonata.duration === "number") {
              duration = Math.floor(sonata.duration);
            }
            if (sonata.isPlaying !== undefined) {
              isPlaying = !!sonata.isPlaying;
            }
            break;
          }
        }

        // 3. Robust DOM Fallbacks for VIBE_PLAYERBAR (Моя Волна mode)
        if (vibePlayer || document.querySelector('[data-test-id="VIBE_PLAYERBAR_TRACK_NAME"]')) {
          const vibeTitleEl = document.querySelector('[data-test-id="VIBE_PLAYERBAR_TRACK_NAME"]');
          if (vibeTitleEl) {
            const rawText = (vibeTitleEl.textContent || "").trim();
            if (rawText.includes(" — ")) {
              const parts = rawText.split(" — ");
              if (!artists) artists = parts[0].trim();
              if (!title) title = parts[1].trim();
            } else if (!title && rawText) {
              title = rawText;
            }
          }

          if (!artists) {
            const artistEls = vibePlayer ? vibePlayer.querySelectorAll('a[href*="/artist/"]') : document.querySelectorAll('main a[href*="/artist/"], [class*="Hero"] a[href*="/artist/"]');
            if (artistEls.length > 0) {
              artists = Array.from(artistEls).map((el) => el.textContent.trim()).filter(Boolean).join(", ");
            }
          }

          if (!coverUrl) {
            const imgEl = document.querySelector('[data-test-id="VIBE_ALBUM_COVER"] img, [data-test-id="VIBE_PLAYERBAR"] img[src*="avatars.yandex.net"], img[src*="avatars.yandex.net/get-music-content/"]');
            if (imgEl && imgEl.src) {
              coverUrl = imgEl.src.replace(/\\/(?:50x50|100x100|200x200)\\b/, "/400x400");
            }
          }

          if (!duration || !position) {
            const timecodeEl = document.querySelector('[data-test-id="VIBE_PLAYERBAR_TIMECODE"]');
            if (timecodeEl && timecodeEl.textContent.includes("/")) {
              const [cur, tot] = timecodeEl.textContent.split("/");
              if (!position) position = parseTimecode(cur);
              if (!duration) duration = parseTimecode(tot);
            }
          }
        }

        // 4. Robust DOM Fallbacks for Desktop Player (PLAYERBAR_DESKTOP)
        if (desktopPlayer) {
          if (!title) {
            const titleEl = desktopPlayer.querySelector('[data-test-id="TRACK_TITLE"]');
            if (titleEl) {
              title = (titleEl.getAttribute("title") || titleEl.textContent || "").trim();
            }
          }

          if (!artists) {
            const artistEls = desktopPlayer.querySelectorAll('a[href*="/artist/"], [class*="description"] a');
            if (artistEls.length > 0) {
              artists = Array.from(artistEls).map((el) => el.textContent.trim()).filter(Boolean).join(", ");
            }
          }

          if (!coverUrl) {
            const imgEl = desktopPlayer.querySelector('[data-test-id="PLAYERBAR_DESKTOP_COVER_CONTAINER"] img, img[class*="cover"], img[src*="avatars.yandex.net"]');
            if (imgEl && imgEl.src) {
              coverUrl = imgEl.src.replace(/\\/(?:50x50|100x100|200x200)\\b/, "/400x400");
            }
          }

          if (!trackId) {
            const trackLink = desktopPlayer.querySelector('a[href*="/track/"]');
            if (trackLink) {
              const m = trackLink.href.match(/track\\/(\\d+)/);
              if (m) trackId = m[1];
            }
          }
        }

        // 5. Global Document Title Fallback (if still empty)
        if (!title && document.title && document.title.includes(" — ")) {
          const parts = document.title.split(" — ");
          if (parts.length >= 2 && !parts[0].includes("Яндекс Музыка")) {
            title = parts[0].trim();
            if (!artists && parts[1] && !parts[1].includes("Яндекс Музыка")) {
              artists = parts[1].trim();
            }
          }
        }

        // 6. Audio element position/duration fallback (Zero-Lag Precision)
        if (audio) {
          if (!position && audio.currentTime) {
            position = Math.floor(audio.currentTime);
          }
          if ((!duration || isNaN(duration)) && audio.duration && !isNaN(audio.duration) && audio.duration > 0) {
            duration = Math.floor(audio.duration);
          }
        }

        // 7. Track ID fallback
        if (!trackId && title) {
          trackId = `${title}-${artists}`;
        }

        // 8. Like status
        const likeBtn = document.querySelector('button[data-test-id="LIKE_BUTTON"]');
        if (likeBtn) {
          liked = likeBtn.getAttribute("aria-pressed") === "true" || likeBtn.classList.contains("liked");
        }

        const state = {
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

        if (window.yandexMusicMod && window.yandexMusicMod.updatePlayerState) {
          window.yandexMusicMod.updatePlayerState(state);
        }

        // If new track detected, fetch lyrics and notify
        if (trackId && trackId !== lastTrackId && title) {
          lastTrackId = trackId;
          fetchTrackLyrics(title, artists, rawMeta, trackId);
          showOsdTrackToast(title, artists, coverUrl);
        }
      } catch (err) {}
    }, 400);

    // Listen for remote player actions from Overlay and Shortcuts
    if (window.yandexMusicMod && window.yandexMusicMod.onExecutePlayerAction) {
      window.yandexMusicMod.onExecutePlayerAction((action, payload) => {
        handlePlayerAction(action, payload);
      });
    }
  }

  function handlePlayerAction(action, payload) {
    const playPauseBtn = document.querySelector('[data-test-id="VIBE_PLAYERBAR"] button[data-test-id="PLAY_BUTTON"], [data-test-id="VIBE_PLAYERBAR"] button[data-test-id="PAUSE_BUTTON"], section[data-test-id="PLAYERBAR_DESKTOP"] button[data-test-id="PLAY_BUTTON"], section[data-test-id="PLAYERBAR_DESKTOP"] button[data-test-id="PAUSE_BUTTON"], button[data-test-id="PLAY_BUTTON"], button[data-test-id="PAUSE_BUTTON"]');
    const nextBtn = document.querySelector('[data-test-id="VIBE_PLAYERBAR"] button[data-test-id="sonata.NEXT_TRACK_BUTTON"], [data-test-id="VIBE_PLAYERBAR"] button[data-test-id*="NEXT"], section[data-test-id="PLAYERBAR_DESKTOP"] button[data-test-id="NEXT_TRACK_BUTTON"], button[data-test-id="NEXT_BUTTON"]');
    const prevBtn = document.querySelector('[data-test-id="VIBE_PLAYERBAR"] button[data-test-id="sonata.PREVIOUS_TRACK_BUTTON"], [data-test-id="VIBE_PLAYERBAR"] button[data-test-id*="PREV"], section[data-test-id="PLAYERBAR_DESKTOP"] button[data-test-id="PREVIOUS_TRACK_BUTTON"], button[data-test-id="PREV_BUTTON"]');
    const likeBtn = document.querySelector('button[data-test-id="LIKE_BUTTON"]');

    if (action === "playPause") {
      if (playPauseBtn) {
        playPauseBtn.click();
      } else {
        const audio = document.querySelector("audio");
        if (audio) {
          audio.paused ? audio.play() : audio.pause();
        }
      }
    } else if (action === "next") {
      if (nextBtn) nextBtn.click();
    } else if (action === "prev") {
      if (prevBtn) prevBtn.click();
    } else if (action === "like") {
      if (likeBtn) likeBtn.click();
    } else if (action === "seek" && payload && payload.position !== undefined) {
      const audio = document.querySelector("audio");
      if (audio) {
        audio.currentTime = payload.position;
      }
    }
  }'''

old_observe_pattern = re.compile(r'  // ==========================================\s*// 7\. PLAYER OBSERVATION & REMOTE CONTROL[\s\S]*?audio\.currentTime = payload\.position;\s*\}\s*\}\s*\}', re.MULTILINE)
if old_observe_pattern.search(js_content):
    js_content = old_observe_pattern.sub(lambda m: NEW_OBSERVE_PLAYER, js_content, count=1)
    print("Replaced observePlayer and handlePlayerAction successfully.")
else:
    print("WARNING: Could not find old observePlayer block!")

# =========================================================================
# 5. Fix duplicate observePlayer and make sure applyUiCleaner runs in init()
# =========================================================================
# Remove duplicate `observePlayer();` before init()
js_content = re.sub(r'  observePlayer\(\);\s*(?=  // ==========================================\s*// 8\. INITIALIZE ALL)', '', js_content)

# Update init()
NEW_INIT = '''  // ==========================================
  // 8. INITIALIZE ALL
  // ==========================================
  async function init() {
    await loadSettings();

    // Apply saved theme & font
    const accent = modSettings["custom-themes/accent"] || "#007acc";
    applyTheme(accent, true);

    const fontName = modSettings["font-changer/savedFont"] || "JetBrains Mono";
    const fontEnabled = modSettings["font-changer/enabled"] !== false;
    applyFont(fontName, fontEnabled);

    // Apply scale & auto quality
    applyScale(modSettings["scale-changer/savedScale"] || 1.0);
    applyAutoQuality();
    applyHiddenMenuItems();
    applyUiCleaner();

    // Inject UI elements
    injectModUI();
    injectSidebarButton();
    injectFloatingBadge();

    // Observe DOM mutations to keep button and UI cleaner attached
    const observer = new MutationObserver(() => {
      injectSidebarButton();
      injectFloatingBadge();
    });
    observer.observe(document.body, { childList: true, subtree: true });

    // Start player polling
    observePlayer();

    console.log("[YandexMusicMod] Mod initialized successfully!");
  }'''

old_init_pattern = re.compile(r'  // ==========================================\s*// 8\. INITIALIZE ALL[\s\S]*?console\.log\("\[YandexMusicMod\] Mod initialized successfully!"\);\s*\}', re.MULTILINE)
if old_init_pattern.search(js_content):
    js_content = old_init_pattern.sub(lambda m: NEW_INIT, js_content, count=1)
    print("Replaced init() successfully.")
else:
    print("WARNING: Could not find old init() block!")

with open(RENDERER_JS, "w", encoding="utf-8") as f:
    f.write(js_content)
print("Updated", RENDERER_JS)

# =========================================================================
# 6. Update mod-renderer.css for #ym-mod-floating-trigger and #ym-mod-nav-item
# =========================================================================
with open(RENDERER_CSS, "r", encoding="utf-8") as f:
    css_content = f.read()

FLOATING_CSS = '''
/* === FLOATING MOD SETTINGS TRIGGER === */
#ym-mod-floating-trigger {
  position: fixed !important;
  bottom: 85px !important;
  left: 18px !important;
  z-index: 999999 !important;
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
  padding: 8px 15px !important;
  border-radius: 20px !important;
  background: rgba(22, 22, 22, 0.94) !important;
  border: 1px solid rgba(255, 255, 255, 0.15) !important;
  backdrop-filter: blur(16px) !important;
  -webkit-backdrop-filter: blur(16px) !important;
  color: #f0f0f0 !important;
  font-size: 12px !important;
  font-weight: 600 !important;
  font-family: inherit !important;
  cursor: pointer !important;
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.65), 0 0 10px rgba(254, 212, 43, 0.2) !important;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
  outline: none !important;
}

#ym-mod-floating-trigger:hover {
  background: rgba(32, 32, 32, 0.98) !important;
  border-color: rgba(254, 212, 43, 0.6) !important;
  transform: translateY(-2px) scale(1.03) !important;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.75), 0 0 16px rgba(254, 212, 43, 0.35) !important;
  color: #ffffff !important;
}

#ym-mod-floating-trigger:active {
  transform: translateY(0) scale(0.97) !important;
}

#ym-mod-floating-trigger .ym-float-icon {
  font-size: 14px !important;
  color: var(--yandexMusicModAccent, #fed42b) !important;
  display: flex !important;
  align-items: center !important;
}

#ym-mod-floating-trigger .ym-float-text {
  letter-spacing: 0.3px !important;
}

/* === SIDEBAR MOD NAVIGATION ITEM === */
#ym-mod-nav-item {
  list-style: none !important;
  margin: 4px 12px !important;
  padding: 0 !important;
}

#ym-mod-menu-btn {
  display: flex !important;
  align-items: center !important;
  gap: 10px !important;
  width: 100% !important;
  box-sizing: border-box !important;
  padding: 9px 14px !important;
  margin: 4px 0 !important;
  border-radius: 12px !important;
  border: 1px solid var(--ym-mod-border, #262626) !important;
  background: var(--ym-mod-card-bg, #181818) !important;
  color: var(--ym-mod-text, #f0f0f0) !important;
  cursor: pointer !important;
  transition: all 0.15s ease !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  font-family: inherit !important;
  outline: none !important;
}

#ym-mod-menu-btn:hover {
  background: var(--ym-mod-card-hover, #222222) !important;
  border-color: rgba(254, 212, 43, 0.4) !important;
  color: #ffffff !important;
}

#ym-mod-menu-btn:active {
  transform: scale(0.98) !important;
}
'''

if "#ym-mod-floating-trigger" not in css_content:
    css_content += FLOATING_CSS
    with open(RENDERER_CSS, "w", encoding="utf-8") as f:
        f.write(css_content)
    print("Appended floating badge styles to", RENDERER_CSS)
else:
    print("Floating badge styles already present in CSS.")
