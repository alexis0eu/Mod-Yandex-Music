import os, re

RENDERER_JS = r"d:\Яндекс Музыка мод\src\renderer\mod-renderer.js"

with open(RENDERER_JS, "r", encoding="utf-8") as f:
    c = f.read()

# 1. Add missing constants at top of file
if "const SCALE_STYLESHEET_ID" not in c:
    c = c.replace(
        'const UI_CLEANER_STYLESHEET_ID = "ym-mod-ui-cleaner-styles";',
        'const UI_CLEANER_STYLESHEET_ID = "ym-mod-ui-cleaner-styles";\n  const SCALE_STYLESHEET_ID = "ym-mod-scale-styles";\n  const THEME_STYLESHEET_ID = "ym-mod-custom-theme-styles";'
    )
    print("[+] Added missing SCALE_STYLESHEET_ID and THEME_STYLESHEET_ID")

# 2. Add applyTheme function definition
APPLY_THEME_FUNC = '''
  function applyTheme(accent = "#007acc", enabled = true) {
    try {
      const existing = document.getElementById(THEME_STYLESHEET_ID);
      if (existing) existing.remove();

      if (!enabled || !accent) return;

      const style = document.createElement("style");
      style.id = THEME_STYLESHEET_ID;
      style.textContent = `
        :root {
          --yandexMusicModAccent: ${accent} !important;
          --accent: ${accent} !important;
          --accent-glow: ${accent}66 !important;
        }
        .ym-mod-btn-icon, .ym-float-icon {
          color: ${accent} !important;
        }
      `;
      (document.head || document.documentElement).appendChild(style);
    } catch (e) {
      console.error("[YandexMusicMod] Error applying theme:", e);
    }
  }
'''

if "function applyTheme(" not in c:
    # insert before applyFont
    c = c.replace('function applyFont(', APPLY_THEME_FUNC + '\n  function applyFont(')
    print("[+] Added applyTheme function definition")

# 3. Patch setupModalInteractions with safe null checks
OLD_MODAL_INTERACTIONS = '''  function setupModalInteractions() {
    const backdrop = document.getElementById("ym-mod-modal-backdrop");
    const closeBtn = document.getElementById("ym-mod-close-btn");

    if (closeBtn && backdrop) {
      closeBtn.addEventListener("click", () => backdrop.classList.remove("open"));
    }
    if (backdrop) {
      backdrop.addEventListener("click", (e) => {
        if (e.target === backdrop) backdrop.classList.remove("open");
      });
    }

    // Tab Switching
    const tabBtns = document.querySelectorAll(".ym-tab-btn");
    const panes = document.querySelectorAll(".ym-tab-pane");

    tabBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        tabBtns.forEach((b) => b.classList.remove("active"));
        panes.forEach((p) => p.classList.remove("active"));
        btn.classList.add("active");
        const target = document.getElementById(btn.getAttribute("data-tab"));
        if (target) target.classList.add("active");
      });
    });

    // Plus & Design Reload Buttons
    document.getElementById("btn-reload-plus")?.addEventListener("click", () => {
      window.location.reload();
    });
    document.getElementById("btn-reload-design")?.addEventListener("click", () => {
      window.location.reload();
    });

    // Bind UI Cleaner switches
    const cleanerKeys = [
      ["opt-clean-concerts", "cleaner/hideConcerts"],
      ["opt-clean-kids", "cleaner/hideKids"],
      ["opt-clean-podcasts", "cleaner/hidePodcasts"],
      ["opt-clean-trailers", "cleaner/hideTrailers"],
      ["opt-clean-radio", "cleaner/hideRadio"],
      ["opt-clean-vibe", "cleaner/hideVibe"],
      ["opt-clean-banners", "cleaner/hideBanners"],
      ["opt-clean-dislike", "cleaner/hideDislike"],
      ["opt-clean-queue", "cleaner/hideQueue"],
      ["opt-clean-lyrics", "cleaner/hideLyrics"],
      ["opt-clean-fullscreen", "cleaner/hideFullscreen"],
      ["opt-clean-prev", "cleaner/hidePrev"],
      ["opt-clean-quality", "cleaner/hideQuality"],
      ["opt-clean-volume", "cleaner/hideVolume"],
    ];

    cleanerKeys.forEach(([id, settingKey]) => {
      const el = document.getElementById(id);
      if (el) {
        el.checked = settingKey === "cleaner/hideBanners" ? modSettings[settingKey] !== false : !!modSettings[settingKey];
        el.addEventListener("change", () => {
          saveSetting(settingKey, el.checked);
          if (settingKey === "cleaner/hideConcerts") saveSetting("custom-themes/hideConcerts", el.checked);
          if (settingKey === "cleaner/hideKids") saveSetting("custom-themes/hideKids", el.checked);
          applyUiCleaner();
          showToast("Интерфейс обновлен");
        });
      }
    });

    // Option Binds
    const optDesignMode = document.getElementById("opt-design-mode");
    const optDisableVibe = document.getElementById("opt-disable-vibe");
    const optFontEnabled = document.getElementById("opt-font-enabled");
    const optFontFamily = document.getElementById("opt-font-family");
    const optFontCustom = document.getElementById("opt-font-custom");
    const optOverlayGhost = document.getElementById("opt-overlay-ghost");
    const optDiscordRpc = document.getElementById("opt-discord-rpc");
    const optAutoQuality = document.getElementById("opt-auto-quality");
    const optUiScale = document.getElementById("opt-ui-scale");
    const optHideConcerts = document.getElementById("opt-hide-concerts");
    const optHideKids = document.getElementById("opt-hide-kids");

    // Populate initial values safely
    if (optDesignMode) optDesignMode.value = modSettings["design/mode"] || "classic";
    if (optDisableVibe) optDisableVibe.checked = !!modSettings["custom-themes/disableVibeAnimation"];
    if (optHideConcerts) optHideConcerts.checked = !!modSettings["custom-themes/hideConcerts"];
    if (optHideKids) optHideKids.checked = !!modSettings["custom-themes/hideKids"];
    if (optFontEnabled) optFontEnabled.checked = modSettings["font-changer/enabled"] !== false;
    if (optFontFamily) optFontFamily.value = modSettings["font-changer/savedFont"] || "JetBrains Mono";
    if (optOverlayGhost) optOverlayGhost.checked = !!modSettings["overlay/clickThrough"];
    if (optDiscordRpc) optDiscordRpc.checked = modSettings["discordRPC/enabled"] !== false;
    if (optAutoQuality) optAutoQuality.checked = modSettings["autoQuality/enabled"] !== false;
    if (optUiScale) optUiScale.value = String(modSettings["scale-changer/savedScale"] || "1.0");

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
        showToast(`Цвет темы: ${color}`);
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
        showToast("Режим дизайна изменен", true);
      });
    }

    if (optDisableVibe) {
      optDisableVibe.addEventListener("change", () => {
        saveSetting("custom-themes/disableVibeAnimation", optDisableVibe.checked);
        applyTheme(modSettings["custom-themes/accent"] || "#007acc", true);
      });
    }

    if (optFontEnabled) {
      optFontEnabled.addEventListener("change", () => {
        saveSetting("font-changer/enabled", optFontEnabled.checked);
        applyFont(optFontFamily ? optFontFamily.value : "JetBrains Mono", optFontEnabled.checked);
      });
    }

    if (optFontFamily) {
      optFontFamily.addEventListener("change", () => {
        saveSetting("font-changer/savedFont", optFontFamily.value);
        applyFont(optFontFamily.value, optFontEnabled ? optFontEnabled.checked : true);
        showToast(`Шрифт: ${optFontFamily.value}`);
      });
    }

    if (optFontCustom) {
      optFontCustom.addEventListener("change", () => {
        if (optFontCustom.value.trim()) {
          saveSetting("font-changer/savedFont", optFontCustom.value.trim());
          applyFont(optFontCustom.value.trim(), true);
          showToast(`Кастомный шрифт: ${optFontCustom.value.trim()}`);
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
        showToast(optAutoQuality.checked ? "Авто-выбор качества включен" : "Авто-выбор качества отключен");
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
    document.getElementById("btn-open-overlay")?.addEventListener("click", () => {
      if (window.yandexMusicMod) window.yandexMusicMod.toggleOverlay();
    });

    document.getElementById("btn-open-karaoke")?.addEventListener("click", () => {
      if (window.yandexMusicMod) window.yandexMusicMod.toggleKaraoke();
    });

    document.getElementById("btn-open-devtools")?.addEventListener("click", () => {
      if (window.yandexMusicMod) window.yandexMusicMod.openDevTools();
    });
  }'''

# Replace old setupModalInteractions
modal_pattern = re.compile(r'  function setupModalInteractions\(\) \{[\s\S]*?document\.getElementById\("btn-open-devtools"\)\.addEventListener\("click", \(\) => \{[\s\S]*?\}\);\s*\}', re.MULTILINE)
if modal_pattern.search(c):
    c = modal_pattern.sub(lambda m: OLD_MODAL_INTERACTIONS, c, count=1)
    print("[+] Replaced setupModalInteractions with safe null checks")
else:
    print("[-] WARNING: Could not find setupModalInteractions block!")

# 4. Patch init() to wrap every step in try-catch
NEW_BULLETPROOF_INIT = '''  // ==========================================
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

    console.log("[YandexMusicMod] Mod initialized successfully!");
  }'''

init_pattern = re.compile(r'  // ==========================================\s*// 8\. INITIALIZE ALL[\s\S]*?console\.log\("\[YandexMusicMod\] Mod initialized successfully!"\);\s*\}', re.MULTILINE)
if init_pattern.search(c):
    c = init_pattern.sub(lambda m: NEW_BULLETPROOF_INIT, c, count=1)
    print("[+] Replaced init() with bulletproof try-catch wrapper")
else:
    print("[-] WARNING: Could not find init() block!")

with open(RENDERER_JS, "w", encoding="utf-8") as f:
    f.write(c)

print("[+] Updated mod-renderer.js successfully!")
