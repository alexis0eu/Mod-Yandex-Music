# -*- coding: utf-8 -*-
"""
v1.3.8 Comprehensive Patcher
- Real-time Audio Element Capture (fixes 0:00 timecode & stuck lyrics)
- Authentic Apple Music macOS MiniPlayer HUD & Full Lyrics View
- Sleek Frosted Glass Capsule Karaoke
- Discord RPC Russian Client ID (1269826362399522849)
- Custom Font Exclusion for Apple Music UI
- Version Bump to 1.3.8
"""
import os
import re

def patch_renderer_js():
    path = os.path.join("src", "renderer", "mod-renderer.js")
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()

    # 1. Bump version
    code = code.replace('const CURRENT_MOD_VERSION = "v1.3.7";', 'const CURRENT_MOD_VERSION = "v1.3.8";')
    code = code.replace('v1.3.7 (YM 5.124.1)', 'v1.3.8 (YM 5.124.1)')
    code = code.replace('<span class="ym-mod-ver-tag">v1.3.7</span>', '<span class="ym-mod-ver-tag">v1.3.8</span>')
    code = code.replace('// Broadcast to Karaoke window and Overlay (v1.3.7:', '// Broadcast to Karaoke window and Overlay (v1.3.8:')

    # 2. Audio Capture Hook at top
    audio_capture_code = '''
// ==========================================
// 0. AUDIO ELEMENT CAPTURE (v1.3.8)
// Intercepts detached <audio> elements created by Yandex Music Yasp player
// ==========================================
(function setupAudioCapture() {
  if (window.__ymAudioHookInstalled) return;
  window.__ymAudioHookInstalled = true;
  window.__ymActiveAudio = null;
  window.__ymKnownAudios = new Set();

  function registerAudio(audio) {
    if (!audio || !(audio instanceof HTMLMediaElement)) return;
    window.__ymKnownAudios.add(audio);
    window.__ymActiveAudio = audio;

    if (!audio.__ymTrackingAttached) {
      audio.__ymTrackingAttached = true;
      const onTick = () => {
        window.__ymActiveAudio = audio;
        if (typeof window.__ymOnAudioTimeUpdate === "function") {
          window.__ymOnAudioTimeUpdate(audio.currentTime, audio.duration, !audio.paused);
        }
      };
      audio.addEventListener("timeupdate", onTick);
      audio.addEventListener("play", onTick);
      audio.addEventListener("pause", onTick);
      audio.addEventListener("seeking", onTick);
      audio.addEventListener("seeked", onTick);
      audio.addEventListener("durationchange", onTick);
      audio.addEventListener("loadedmetadata", onTick);
    }
  }

  window.__ymGetActiveAudio = function() {
    if (window.__ymActiveAudio && !window.__ymActiveAudio.error) {
      return window.__ymActiveAudio;
    }
    if (window.__ymKnownAudios && window.__ymKnownAudios.size > 0) {
      for (const a of window.__ymKnownAudios) {
        if (!a.paused || a.currentTime > 0) return a;
      }
      const first = window.__ymKnownAudios.values().next().value;
      if (first) return first;
    }
    return document.querySelector("audio") || null;
  };

  try {
    const origCreateElement = document.createElement.bind(document);
    document.createElement = function (tagName, options) {
      const el = origCreateElement(tagName, options);
      if (typeof tagName === "string" && tagName.toLowerCase() === "audio") {
        registerAudio(el);
      }
      return el;
    };
  } catch (e) {}

  try {
    const origAudio = window.Audio;
    if (origAudio) {
      const PatchedAudio = function (...args) {
        const el = new origAudio(...args);
        registerAudio(el);
        return el;
      };
      PatchedAudio.prototype = origAudio.prototype;
      window.Audio = PatchedAudio;
    }
  } catch (e) {}

  try {
    const origPlay = HTMLMediaElement.prototype.play;
    HTMLMediaElement.prototype.play = function (...args) {
      registerAudio(this);
      return origPlay.apply(this, args);
    };
  } catch (e) {}
})();
'''
    if "setupAudioCapture" not in code:
        code = code.replace("(function () {", "(function () {\n" + audio_capture_code, 1)

    # 3. Helper getActiveAudioElement
    helper_code = '''
  function getActiveAudioElement() {
    if (typeof window.__ymGetActiveAudio === "function") {
      const a = window.__ymGetActiveAudio();
      if (a) return a;
    }
    return document.querySelector("audio") || null;
  }
'''
    if "function getActiveAudioElement()" not in code:
        code = code.replace("function seekAudioTo(targetSeconds) {", helper_code + "\n  function seekAudioTo(targetSeconds) {", 1)

    # 4. Patch seekAudioTo
    old_seek = '''  function seekAudioTo(targetSeconds) {
    try {
      const audio = document.querySelector("audio");
      if (audio) {
        audio.currentTime = targetSeconds;
      }
    } catch (e) {}
  }'''
    new_seek = '''  function seekAudioTo(targetSeconds) {
    try {
      const audio = getActiveAudioElement();
      if (audio) {
        audio.currentTime = targetSeconds;
      }
    } catch (e) {}
  }'''
    code = code.replace(old_seek, new_seek)

    # 5. Patch hookDirectAudioElement and wire window.__ymOnAudioTimeUpdate
    old_hook = '''  function hookDirectAudioElement() {
    try {
      const audio = document.querySelector("audio");
      if (audio && !audio.__ymAmLyricsHooked) {
        audio.__ymAmLyricsHooked = true;
        audio.addEventListener("timeupdate", () => {
          if (fsLyricsVisible) {
            updateFullscreenLyricsActiveLine(audio.currentTime);
            updateAppleMusicProgress(audio.currentTime, audio.duration || 0, !audio.paused);
          }
        });
      }
    } catch (e) {}
  }'''
    new_hook = '''  function hookDirectAudioElement() {
    try {
      window.__ymOnAudioTimeUpdate = (currentTime, duration, isPlaying) => {
        if (fsLyricsVisible) {
          updateFullscreenLyricsActiveLine(currentTime);
          updateAppleMusicProgress(currentTime, duration || 0, isPlaying);
        }
      };
      const audio = getActiveAudioElement();
      if (audio && !audio.__ymAmLyricsHooked) {
        audio.__ymAmLyricsHooked = true;
        audio.addEventListener("timeupdate", () => {
          if (fsLyricsVisible) {
            updateFullscreenLyricsActiveLine(audio.currentTime);
            updateAppleMusicProgress(audio.currentTime, audio.duration || 0, !audio.paused);
          }
        });
      }
    } catch (e) {}
  }'''
    code = code.replace(old_hook, new_hook)

    # 6. Patch scrapeCurrentPlayerState audio query
    old_scrape_audio = '''    // 2. Audio Elements (Precise position, duration, and playing state)
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
    }'''
    new_scrape_audio = '''    // 2. Audio Elements (Precise position, duration, and playing state - v1.3.8)
    const activeAudio = getActiveAudioElement();
    if (activeAudio) {
      if (!isPlaying) isPlaying = !activeAudio.paused;
      if (activeAudio.currentTime !== undefined && !isNaN(activeAudio.currentTime)) {
        position = activeAudio.currentTime; // Float precision for 60fps lyrics sync
      }
      if (activeAudio.duration && !isNaN(activeAudio.duration) && activeAudio.duration > 0) {
        duration = activeAudio.duration;
      }
    }'''
    code = code.replace(old_scrape_audio, new_scrape_audio)

    # 7. Patch handlePlayerAction
    old_hpa = '''    if (action === "playPause") {
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
    }'''
    new_hpa = '''    const activeAudio = getActiveAudioElement();
    if (action === "playPause") {
      if (playPauseBtn) {
        playPauseBtn.click();
      } else if (activeAudio) {
        activeAudio.paused ? activeAudio.play().catch(() => {}) : activeAudio.pause();
      }
    } else if (action === "next") {
      if (nextBtn) nextBtn.click();
    } else if (action === "prev") {
      if (prevBtn) prevBtn.click();
    } else if (action === "like") {
      if (likeBtn) likeBtn.click();
    } else if (action === "seek" && payload) {
      const targetSec = payload.position !== undefined ? Number(payload.position) : (payload.progress !== undefined && activeAudio?.duration ? payload.progress * activeAudio.duration : 0);
      if (activeAudio) {
        activeAudio.currentTime = targetSec;
      }
    }'''
    code = code.replace(old_hpa, new_hpa)

    # 8. Exclude Apple Music modal and overlays from font distortion in applyCustomFont
    old_font_rule = '''      /* Prevent modal and lyrics distortion from global font scaling */
      #ym-mod-settings-modal, #ym-proposal-modal, #ym-mod-fullscreen-lyrics, .ym-mod-modal {
        font-size: ${Math.round(14 * modalSizeScale)}px !important;
      }'''
    new_font_rule = '''      /* Prevent modal and lyrics distortion from global font scaling (v1.3.8) */
      #ym-mod-settings-modal, #ym-proposal-modal, #ym-mod-fullscreen-lyrics, .ym-mod-modal {
        font-size: ${Math.round(14 * modalSizeScale)}px !important;
      }
      /* STRICT ISOLATION: Keep Apple Music views with pure Apple SF Pro / Inter typography */
      #ym-am-lyrics-modal,
      #ym-am-lyrics-modal *,
      .ym-am-lyrics-modal,
      .ym-am-lyrics-modal *,
      #ym-am-lyrics-body,
      #ym-am-lyrics-body *,
      .ym-am-lrc-line,
      .ym-am-lrc-line *,
      .ym-am-title,
      .ym-am-artist,
      .ym-am-time,
      .overlay-card,
      .overlay-card *,
      .karaoke-banner,
      .karaoke-banner * {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Inter", "Segoe UI", Roboto, sans-serif !important;
        letter-spacing: normal !important;
        text-transform: none !important;
      }'''
    code = code.replace(old_font_rule, new_font_rule)

    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    print("Patched mod-renderer.js successfully.")

def patch_renderer_css():
    path = os.path.join("src", "renderer", "mod-renderer.css")
    with open(path, "r", encoding="utf-8") as f:
        css = f.read()

    # Hide scrollbar on Apple Music lyrics body
    old_lrc_body = '''.ym-am-lyrics-body {
  position: relative !important;
  z-index: 2 !important;
  flex: 1 !important;
  overflow-y: auto !important;
  padding: 24px 20px !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 16px !important;
  scroll-behavior: smooth !important;
  mask-image: linear-gradient(to bottom, transparent 0%, black 12%, black 88%, transparent 100%) !important;
  -webkit-mask-image: linear-gradient(to bottom, transparent 0%, black 12%, black 88%, transparent 100%) !important;
}'''
    new_lrc_body = '''.ym-am-lyrics-body {
  position: relative !important;
  z-index: 2 !important;
  flex: 1 !important;
  overflow-y: auto !important;
  padding: 24px 20px !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 16px !important;
  scroll-behavior: smooth !important;
  scrollbar-width: none !important;
  -ms-overflow-style: none !important;
  mask-image: linear-gradient(to bottom, transparent 0%, black 12%, black 88%, transparent 100%) !important;
  -webkit-mask-image: linear-gradient(to bottom, transparent 0%, black 12%, black 88%, transparent 100%) !important;
}

.ym-am-lyrics-body::-webkit-scrollbar {
  display: none !important;
  width: 0 !important;
  height: 0 !important;
}'''
    if old_lrc_body in css:
        css = css.replace(old_lrc_body, new_lrc_body)
    elif "scrollbar-width: none !important;" not in css:
        css += "\n.ym-am-lyrics-body { scrollbar-width: none !important; -ms-overflow-style: none !important; }\n.ym-am-lyrics-body::-webkit-scrollbar { display: none !important; }\n"

    with open(path, "w", encoding="utf-8") as f:
        f.write(css)
    print("Patched mod-renderer.css successfully.")

def patch_main_js():
    path = os.path.join("src", "main", "mod-main.js")
    with open(path, "r", encoding="utf-8") as f:
        main_code = f.read()

    # Russian Discord Client ID: replace 1283109459463377011 with FozerG verified 1269826362399522849
    main_code = main_code.replace("1283109459463377011", "1269826362399522849")
    main_code = main_code.replace("YandexMusicMod/1.3.7", "YandexMusicMod/1.3.8")

    # Set overlay resizable to true and compact default size 380x175
    main_code = main_code.replace("const overlayWidth = 480;\n  const overlayHeight = 200;", "const overlayWidth = 380;\n  const overlayHeight = 175;")
    main_code = main_code.replace("resizable: false,", "resizable: true,")

    with open(path, "w", encoding="utf-8") as f:
        f.write(main_code)
    print("Patched mod-main.js successfully.")

def patch_discord_rpc_js():
    path = os.path.join("src", "main", "discord-rpc.js")
    with open(path, "r", encoding="utf-8") as f:
        rpc_code = f.read()
    rpc_code = rpc_code.replace("1283109459463377011", "1269826362399522849")
    with open(path, "w", encoding="utf-8") as f:
        f.write(rpc_code)
    print("Patched discord-rpc.js successfully.")

def patch_package_json():
    path = "package.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            pkg = f.read()
        pkg = re.sub(r'"version":\s*"[^"]+"', '"version": "1.3.8"', pkg)
        with open(path, "w", encoding="utf-8") as f:
            f.write(pkg)
        print("Patched package.json successfully.")

def patch_nsi():
    path = "native_installer.nsi"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            nsi = f.read()
        nsi = re.sub(r'!define PRODUCT_VERSION\s*"[^"]+"', '!define PRODUCT_VERSION "1.3.8"', nsi)
        with open(path, "w", encoding="utf-8") as f:
            f.write(nsi)
        print("Patched native_installer.nsi successfully.")

if __name__ == "__main__":
    patch_renderer_js()
    patch_renderer_css()
    patch_main_js()
    patch_discord_rpc_js()
    patch_package_json()
    patch_nsi()
    print("All core files patched for v1.3.8!")
