import os
import re

RENDERER_JS = r"d:\Яндекс Музыка мод\src\renderer\mod-renderer.js"
PRELOAD_JS = r"d:\Яндекс Музыка мод\src\preload\mod-preload.js"

print("=" * 60)
print("APPLYING STEPHANZION / VZLOMHIK ARCHITECTURE FIXES")
print("=" * 60)

with open(RENDERER_JS, "r", encoding="utf-8") as f:
    r_code = f.read()

# 1. REMOVE DANGEROUS document.head.appendChild override (caused Next.js hydration crash)
old_append_child_pattern = re.compile(
    r'  // ==========================================\s*// 1\. AD & TELEMETRY BLOCKER\s*// ==========================================[\s\S]*?// ==========================================\s*// 2\. PLUS UNLOCKER',
    re.MULTILINE
)
safe_telemetry_blocker = '''  // ==========================================
  // 1. AD & TELEMETRY BLOCKER (SAFE)
  // ==========================================
  try {
    navigator.sendBeacon = () => true;
  } catch (e) {}

  // ==========================================
  // 2. PLUS UNLOCKER'''

if old_append_child_pattern.search(r_code):
    r_code = old_append_child_pattern.sub(safe_telemetry_blocker, r_code, count=1)
    print("[+] Removed dangerous document.head.appendChild override")
else:
    print("[-] Warning: appendChild block pattern not matched")

# 2. REMOVE FAKE EXPERIMENT OVERRIDES (caused black screen in modern mode)
old_experiments_pattern = re.compile(
    r'    // 4\. Experiments details for Classic vs Modern Design switch[\s\S]*?return originalFetch\.apply\(this, args\);\s*\}\s*\}\s*return originalFetch\.apply\(this, args\);',
    re.MULTILINE
)
safe_experiments = '''    // 4. Experiments details (Pass-through with user overrides only, as in Stephanzion mod)
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
              headers: res.headers,
            });
          }
          return new Response(JSON.stringify(data), {
            status: res.status,
            headers: res.headers,
          });
        }
      } catch (err) {
        console.error("[YandexMusicMod] Error in experiments interceptor:", err);
      }
    }

    return originalFetch.apply(this, args);'''

if old_experiments_pattern.search(r_code):
    r_code = old_experiments_pattern.sub(safe_experiments, r_code, count=1)
    print("[+] Removed fake experiment overrides (fixed black screen)")
else:
    print("[-] Warning: experiments pattern not matched")

# 3. USE STEPHANZION TARGET SELECTOR FOR SIDEBAR BUTTON
old_inject_btn = re.compile(
    r'  function injectSidebarButton\(\) \{[\s\S]*?if \(navbar\) \{\s*navbar\.appendChild\(btn\);\s*return;\s*\}\s*\}',
    re.MULTILINE
)

new_inject_btn = '''  function injectSidebarButton() {
    // Permanent floating trigger for 100% fail-proof access
    injectFloatingBadge();

    const containerId = "ym-mod-sidebar-container";
    let container = document.getElementById(containerId);

    // Exact Stephanzion / Vzlomhik target selector: User profile container at sidebar bottom
    const targetSelector = 'div[class*="NavbarDesktopUserWidget_userProfileContainer"], aside [data-test-id="USER_PROFILE"], aside [data-test-id="USER_PROFILE_AVATAR_CONTAINER"]';
    const targetElement = document.querySelector(targetSelector);

    if (targetElement && targetElement.parentNode) {
      if (!container) {
        container = document.createElement("div");
        container.id = containerId;
        container.style.cssText = "display: flex; justify-content: center; width: 100%; box-sizing: border-box; margin: 6px 0; padding: 0 12px;";

        const btn = document.createElement("button");
        btn.id = "ym-mod-menu-btn";
        btn.className = "ym-mod-menu-btn";
        btn.setAttribute("title", "Настройки мода (Ctrl+Shift+S / Ctrl+, / F10)");
        btn.innerHTML = `
          <span class="ym-mod-btn-icon">⚡</span>
          <span class="ym-mod-btn-text">Настройки Мода</span>
        `;
        btn.addEventListener("click", (e) => {
          e.preventDefault();
          e.stopPropagation();
          toggleModSettings();
        });

        container.appendChild(btn);
        targetElement.parentNode.insertBefore(container, targetElement);
      }
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
  }'''

if old_inject_btn.search(r_code):
    r_code = old_inject_btn.sub(new_inject_btn, r_code, count=1)
    print("[+] Replaced injectSidebarButton with Stephanzion user-widget placement")
else:
    print("[-] Warning: injectSidebarButton pattern not matched")

# 4. EXPOSE window.__getPlayerState for Stephanzion-style compatibility
if "window.__getPlayerState" not in r_code:
    player_state_hook = '''
  // Expose window.__getPlayerState (Stephanzion / Vzlomhik standard)
  window.__getPlayerState = () => {
    return {
      enabled: modSettings["discordRPC/enabled"] !== false,
      data: window.__lastPlayerState || null,
    };
  };
'''
    r_code = r_code.replace('  // ==========================================\n  // 8. INITIALIZE ALL', player_state_hook + '\n  // ==========================================\n  // 8. INITIALIZE ALL')
    print("[+] Exposed window.__getPlayerState")

# Update window.__lastPlayerState inside observePlayer
r_code = r_code.replace(
    'window.yandexMusicMod.updatePlayerState(state);',
    'window.__lastPlayerState = state;\n        window.yandexMusicMod.updatePlayerState(state);'
)

with open(RENDERER_JS, "w", encoding="utf-8") as f:
    f.write(r_code)

print("[+] Updated mod-renderer.js")

# 5. FIX mod-preload.js to inject safely on DOMContentLoaded (prevents race condition before DOM exists)
SAFE_PRELOAD = '''// === Yandex Music Mod Preload Integration ===
(function () {
  try {
    const electron = require("electron");
    const path = require("path");
    const fs = require("fs");

    electron.contextBridge.exposeInMainWorld("yandexMusicMod", {
      getStorageValue: (key) => electron.ipcRenderer.invoke("yandexMusicMod.getStorageValue", key),
      setStorageValue: (key, value) => electron.ipcRenderer.send("yandexMusicMod.setStorageValue", key, value),
      getAllSettings: () => electron.ipcRenderer.invoke("yandexMusicMod.getAllSettings"),
      onStorageChanged: (callback) => {
        const listener = (_e, key, value) => callback(key, value);
        electron.ipcRenderer.on("yandexMusicMod.storageValueUpdated", listener);
        return () => electron.ipcRenderer.removeListener("yandexMusicMod.storageValueUpdated", listener);
      },
      updatePlayerState: (state) => electron.ipcRenderer.send("yandexMusicMod.updatePlayerState", state),
      updateLyrics: (lyricsData) => electron.ipcRenderer.send("yandexMusicMod.updateLyrics", lyricsData),
      fetchLyrics: (track, artist) => electron.ipcRenderer.invoke("yandexMusicMod.fetchLyrics", track, artist),
      onExecutePlayerAction: (callback) => {
        const listener = (_e, action, payload) => callback(action, payload);
        electron.ipcRenderer.on("yandexMusicMod.executePlayerAction", listener);
        return () => electron.ipcRenderer.removeListener("yandexMusicMod.executePlayerAction", listener);
      },
      toggleOverlay: () => electron.ipcRenderer.send("yandexMusicMod.toggleOverlay"),
      toggleKaraoke: () => electron.ipcRenderer.send("yandexMusicMod.toggleKaraoke"),
      setOverlayClickThrough: (enabled) => electron.ipcRenderer.send("yandexMusicMod.setOverlayClickThrough", enabled),
      setOverlayIgnoreMouseEvents: (ignore, forward) => electron.ipcRenderer.send("yandexMusicMod.setOverlayIgnoreMouseEvents", ignore, forward),
      openDevTools: () => electron.ipcRenderer.send("yandexMusicMod.openDevTools"),
      selectDownloadFolder: () => electron.ipcRenderer.invoke("yandexMusicMod.selectDownloadFolder"),
      openDownloadDirectory: () => electron.ipcRenderer.send("yandexMusicMod.openDownloadDirectory"),
      openFolder: (path) => electron.ipcRenderer.invoke("yandexMusicMod.openFolder", path),
      onOpenSettings: (callback) => {
        const listener = () => callback();
        electron.ipcRenderer.on("yandexMusicMod.openSettingsModal", listener);
        return () => electron.ipcRenderer.removeListener("yandexMusicMod.openSettingsModal", listener);
      },
    });

    // Safe injection on DOMContentLoaded
    function injectMod() {
      try {
        const rendererJsPath = path.join(__dirname, "app", "yandexMusicMod", "renderer.js");
        const rendererCssPath = path.join(__dirname, "app", "yandexMusicMod", "renderer.css");

        if (electron.webFrame) {
          try {
            if (fs.existsSync(rendererCssPath)) {
              const cssData = fs.readFileSync(rendererCssPath, "utf8");
              electron.webFrame.insertCSS(cssData);
            }
          } catch (e) {}

          try {
            if (fs.existsSync(rendererJsPath)) {
              const jsData = fs.readFileSync(rendererJsPath, "utf8");
              electron.webFrame.executeJavaScript(jsData);
            }
          } catch (e) {}
        }
      } catch (err) {
        console.error("[Mod Preload Injection Error]", err);
      }
    }

    if (typeof window !== "undefined" && typeof document !== "undefined") {
      if (document.readyState === "loading") {
        window.document.addEventListener("DOMContentLoaded", injectMod);
      } else {
        injectMod();
      }
    }
  } catch (e) {
    console.error("[Mod Preload Error]", e);
  }
})();
'''

with open(PRELOAD_JS, "w", encoding="utf-8") as f:
    f.write(SAFE_PRELOAD)

print("[+] Updated mod-preload.js with safe DOMContentLoaded injection")
