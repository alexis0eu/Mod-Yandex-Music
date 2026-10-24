import os

RENDERER_JS = r"src\renderer\mod-renderer.js"

with open(RENDERER_JS, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update vibeTitleEl parsing
old_vibe = """          const vibeTitleEl = document.querySelector('[data-test-id="VIBE_PLAYERBAR_TRACK_NAME"]');
          if (vibeTitleEl) {
            const rawText = (vibeTitleEl.textContent || "").trim();
            if (rawText.includes(" — ")) {
              const parts = rawText.split(" — ");
              if (!artists) artists = parts[0].trim();
              if (!title) title = parts[1].trim();
            } else if (!title && rawText) {
              title = rawText;
            }
          }"""

new_vibe = """          const vibeTitleEl = document.querySelector('[data-test-id="VIBE_PLAYERBAR_TRACK_NAME"]');
          if (vibeTitleEl) {
            const rawText = (vibeTitleEl.textContent || "").trim();
            const parts = rawText.split(/\\s+[—–-]\\s+/);
            if (parts.length >= 2) {
              if (!artists) artists = parts[0].trim();
              if (!title) title = parts.slice(1).join(" - ").trim();
            } else if (!title && rawText) {
              title = rawText;
            }
          }"""

# 2. Add MediaSession fallback
old_mediasession = """        // 6. Audio element position/duration fallback (Zero-Lag Precision)"""
new_mediasession = """        // 5.5 MediaSession API Fallback (Standard Chromium OS integration)
        if (navigator.mediaSession && navigator.mediaSession.metadata) {
          const m = navigator.mediaSession.metadata;
          if (!title && m.title) title = m.title.trim();
          if (!artists && m.artist) artists = m.artist.trim();
          if (!coverUrl && Array.isArray(m.artwork) && m.artwork.length > 0) {
            coverUrl = m.artwork[m.artwork.length - 1].src;
          }
        }
        if (navigator.mediaSession && navigator.mediaSession.playbackState) {
          if (navigator.mediaSession.playbackState === "playing") isPlaying = true;
          else if (navigator.mediaSession.playbackState === "paused") isPlaying = false;
        }

        // 6. Audio element position/duration fallback (Zero-Lag Precision)"""

# 3. Update window.__getPlayerState
old_get_state = """  // Expose window.__getPlayerState (Stephanzion / Vzlomhik standard)
  window.__getPlayerState = () => {
    return {
      enabled: modSettings["discordRPC/enabled"] !== false,
      data: window.__lastPlayerState || null,
    };
  };"""

new_get_state = """  // Expose window.__getPlayerState (Stephanzion / Vzlomhik standard)
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
          coverUri: s.track.coverUrl ? s.track.coverUrl.replace(/^https?:\\/\\//, "").replace(/\\/400x400\\b/, "/%%") : "",
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
  };"""

norm_text = text.replace("\r\n", "\n")
norm_old_vibe = old_vibe.replace("\r\n", "\n")
norm_new_vibe = new_vibe.replace("\r\n", "\n")
norm_old_ms = old_mediasession.replace("\r\n", "\n")
norm_new_ms = new_mediasession.replace("\r\n", "\n")
norm_old_gs = old_get_state.replace("\r\n", "\n")
norm_new_gs = new_get_state.replace("\r\n", "\n")

applied = 0
if norm_old_vibe in norm_text:
    norm_text = norm_text.replace(norm_old_vibe, norm_new_vibe, 1)
    applied += 1
    print("[+] Patched vibe title parser")
else:
    print("[-] Warning: vibe pattern not found")

if norm_old_ms in norm_text:
    norm_text = norm_text.replace(norm_old_ms, norm_new_ms, 1)
    applied += 1
    print("[+] Patched mediaSession fallback")
else:
    print("[-] Warning: mediaSession pattern not found")

if norm_old_gs in norm_text:
    norm_text = norm_text.replace(norm_old_gs, norm_new_gs, 1)
    applied += 1
    print("[+] Patched window.__getPlayerState")
else:
    print("[-] Warning: getPlayerState pattern not found")

with open(RENDERER_JS, "w", encoding="utf-8") as f:
    f.write(norm_text)

print(f"Done. Applied {applied}/3 patches.")
