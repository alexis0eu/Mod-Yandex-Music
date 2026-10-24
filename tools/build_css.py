import os
import base64

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FONTS_DIR = os.path.join(PROJECT_DIR, "src", "fonts")
OUTPUT_CSS = os.path.join(PROJECT_DIR, "src", "renderer", "mod-renderer.css")

def load_font_b64(filename):
    path = os.path.join(FONTS_DIR, filename)
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

jb_b64 = load_font_b64("JetBrainsMono-Regular.woff2")
mc_b64 = load_font_b64("Minecraft.woff2")
andy_b64 = load_font_b64("Andy-Bold.woff2")
press_b64 = load_font_b64("PressStart2P.woff2")
vt_b64 = load_font_b64("VT323.woff2")
uncut_b64 = load_font_b64("UncutSans-Regular.woff2")

css_content = f"""/* === YANDEX MUSIC MOD - EMBEDDED BASE64 FONTS === */
@font-face {{
  font-family: "JetBrains Mono";
  src: url("data:font/woff2;base64,{jb_b64}") format("woff2"),
       url("/yandexMusicMod/JetBrainsMono-Regular.woff2") format("woff2");
  font-weight: normal;
  font-style: normal;
  font-display: swap;
}}

@font-face {{
  font-family: "Minecraft";
  src: url("data:font/woff2;base64,{mc_b64}") format("woff2"),
       url("/yandexMusicMod/Minecraft.woff2") format("woff2");
  font-weight: normal;
  font-style: normal;
  font-display: swap;
}}

/* Dual-alias for Terraria / Andy Bold: declares both "Andy Bold" and "Terraria" */
@font-face {{
  font-family: "Andy Bold";
  src: url("data:font/woff2;base64,{andy_b64}") format("woff2"),
       url("/yandexMusicMod/Andy-Bold.woff2") format("woff2");
  font-weight: normal;
  font-style: normal;
  font-display: swap;
}}

@font-face {{
  font-family: "Andy Bold";
  src: url("data:font/woff2;base64,{andy_b64}") format("woff2"),
       url("/yandexMusicMod/Andy-Bold.woff2") format("woff2");
  font-weight: bold;
  font-style: normal;
  font-display: swap;
}}

@font-face {{
  font-family: "Terraria";
  src: url("data:font/woff2;base64,{andy_b64}") format("woff2"),
       url("/yandexMusicMod/Andy-Bold.woff2") format("woff2");
  font-weight: normal;
  font-style: normal;
  font-display: swap;
}}

@font-face {{
  font-family: "Terraria";
  src: url("data:font/woff2;base64,{andy_b64}") format("woff2"),
       url("/yandexMusicMod/Andy-Bold.woff2") format("woff2");
  font-weight: bold;
  font-style: normal;
  font-display: swap;
}}

@font-face {{
  font-family: "Press Start 2P";
  src: url("data:font/woff2;base64,{press_b64}") format("woff2"),
       url("/yandexMusicMod/PressStart2P.woff2") format("woff2");
  font-weight: normal;
  font-style: normal;
  font-display: swap;
}}

@font-face {{
  font-family: "Press Start 2P";
  src: url("data:font/woff2;base64,{press_b64}") format("woff2"),
       url("/yandexMusicMod/PressStart2P.woff2") format("woff2");
  font-weight: bold;
  font-style: normal;
  font-display: swap;
}}

@font-face {{
  font-family: "VT323";
  src: url("data:font/woff2;base64,{vt_b64}") format("woff2"),
       url("/yandexMusicMod/VT323.woff2") format("woff2");
  font-weight: normal;
  font-style: normal;
  font-display: swap;
}}

@font-face {{
  font-family: "VT323";
  src: url("data:font/woff2;base64,{vt_b64}") format("woff2"),
       url("/yandexMusicMod/VT323.woff2") format("woff2");
  font-weight: bold;
  font-style: normal;
  font-display: swap;
}}

@font-face {{
  font-family: "Uncut Sans";
  src: url("data:font/woff2;base64,{uncut_b64}") format("woff2"),
       url("/yandexMusicMod/UncutSans-Regular.woff2") format("woff2");
  font-weight: normal;
  font-style: normal;
  font-display: swap;
}}

@font-face {{
  font-family: "Uncut Sans";
  src: url("data:font/woff2;base64,{uncut_b64}") format("woff2"),
       url("/yandexMusicMod/UncutSans-Regular.woff2") format("woff2");
  font-weight: bold;
  font-style: normal;
  font-display: swap;
}}

/* ========================================================
   YANDEX MUSIC MOD - NATIVE GRAPHITE DESIGN SYSTEM
   Anti-slop: Matte #121212 / #181818, crisp #262626 borders,
   neutral typography, zero artificial AI-purple gradients.
   ======================================================== */

:root {{
  --ym-mod-bg: #121212;
  --ym-mod-card-bg: #181818;
  --ym-mod-card-hover: #1f1f1f;
  --ym-mod-border: #262626;
  --ym-mod-border-subtle: #202020;
  --ym-mod-text: #f0f0f0;
  --ym-mod-text-secondary: #8c8c8c;
  --ym-mod-text-muted: #5f5f5f;
  --yandexMusicModAccent: #fed42b;
}}

/* === FLOATING MOD SETTINGS TRIGGER === */
#ym-mod-floating-trigger {{
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
}}

#ym-mod-floating-trigger:hover {{
  background: rgba(32, 32, 32, 0.98) !important;
  border-color: rgba(254, 212, 43, 0.6) !important;
  transform: translateY(-2px) scale(1.03) !important;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.75), 0 0 16px rgba(254, 212, 43, 0.35) !important;
  color: #ffffff !important;
}}

#ym-mod-floating-trigger:active {{
  transform: translateY(0) scale(0.97) !important;
}}

#ym-mod-floating-trigger .ym-float-icon {{
  font-size: 14px !important;
  color: var(--yandexMusicModAccent, #fed42b) !important;
  display: flex !important;
  align-items: center !important;
}}

#ym-mod-floating-trigger .ym-float-text {{
  letter-spacing: 0.3px !important;
}}

/* Auto-hide floating trigger when sidebar button is mounted in DOM */
body:has(#ym-mod-menu-btn) #ym-mod-floating-trigger {{
  display: none !important;
}}

/* === SIDEBAR MOD NAVIGATION ITEM === */
#ym-mod-nav-item {{
  list-style: none !important;
  margin: 4px 12px !important;
  padding: 0 !important;
}}

/* === SIDEBAR MOD BUTTON === */
#ym-mod-menu-btn {{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  margin: 6px 10px;
  border-radius: 10px;
  border: 1px solid var(--ym-mod-border, #262626);
  background: var(--ym-mod-card-bg, #181818);
  color: var(--ym-mod-text, #f0f0f0);
  cursor: pointer;
  transition: all 0.15s ease;
  font-size: 13px;
  font-weight: 500;
  font-family: inherit;
  outline: none;
}}

#ym-mod-menu-btn:hover {{
  background: var(--ym-mod-card-hover, #1f1f1f);
  border-color: #383838;
  color: #ffffff;
}}

#ym-mod-menu-btn:active {{
  transform: scale(0.98);
}}

.ym-mod-btn-icon {{
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--yandexMusicModAccent, #fed42b);
}}

.ym-mod-badge {{
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.08);
  color: var(--ym-mod-text-secondary, #8c8c8c);
  margin-left: auto;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}}

/* === MODAL BACKDROP === */
.ym-mod-modal-backdrop {{
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.72);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  z-index: 999999;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}}

.ym-mod-modal-backdrop.open {{
  opacity: 1;
  pointer-events: auto;
}}

/* === MODAL WINDOW === */
.ym-mod-modal {{
  width: 820px;
  max-width: 92vw;
  height: 620px;
  max-height: 88vh;
  background: var(--ym-mod-bg, #121212);
  border: 1px solid var(--ym-mod-border, #262626);
  border-radius: 14px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.65);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transform: scale(0.97);
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  color: var(--ym-mod-text, #f0f0f0);
  font-family: inherit;
}}

.ym-mod-modal-backdrop.open .ym-mod-modal {{
  transform: scale(1);
}}

/* === MODAL HEADER === */
.ym-modal-header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--ym-mod-border, #262626);
  background: #141414;
}}

.ym-modal-title-wrap {{
  display: flex;
  align-items: center;
  gap: 12px;
}}

.ym-modal-logo {{
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: var(--yandexMusicModAccent, #fed42b);
  color: #121212;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 800;
}}

.ym-modal-title {{
  font-size: 15px;
  font-weight: 600;
  color: #ffffff;
  letter-spacing: 0.2px;
}}

.ym-modal-version {{
  font-size: 11px;
  color: var(--ym-mod-text-secondary, #8c8c8c);
  font-weight: 500;
  background: #1e1e1e;
  border: 1px solid #282828;
  padding: 2px 7px;
  border-radius: 5px;
}}

.ym-modal-close {{
  background: transparent;
  border: 1px solid transparent;
  color: #888888;
  font-size: 16px;
  cursor: pointer;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}}

.ym-modal-close:hover {{
  background: #202020;
  border-color: #303030;
  color: #ffffff;
}}

/* === MODAL LAYOUT === */
.ym-modal-body {{
  display: flex;
  flex: 1;
  overflow: hidden;
}}

/* Tabs Sidebar */
.ym-modal-tabs {{
  width: 200px;
  border-right: 1px solid var(--ym-mod-border, #262626);
  padding: 14px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: #141414;
  overflow-y: auto;
}}

.ym-tab-btn {{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--ym-mod-text-secondary, #8c8c8c);
  font-size: 13px;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition: all 0.12s ease;
  position: relative;
  font-family: inherit;
}}

.ym-tab-btn:hover {{
  background: #1c1c1c;
  color: #e0e0e0;
}}

.ym-tab-btn.active {{
  background: #202020;
  color: #ffffff;
  font-weight: 600;
  box-shadow: inset 3px 0 0 var(--yandexMusicModAccent, #fed42b);
}}

/* Tab Content */
.ym-modal-content {{
  flex: 1;
  padding: 20px 24px;
  overflow-y: auto;
  background: var(--ym-mod-bg, #121212);
}}

.ym-tab-pane {{
  display: none;
  flex-direction: column;
  gap: 16px;
}}

.ym-tab-pane.active {{
  display: flex;
}}

/* === CARDS & SETTING ROWS === */
.ym-card {{
  background: var(--ym-mod-card-bg, #181818);
  border: 1px solid var(--ym-mod-border, #262626);
  border-radius: 10px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}}

.ym-card-title {{
  font-size: 13px;
  font-weight: 600;
  color: #ffffff;
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--ym-mod-border-subtle, #202020);
}}

.ym-row {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}}

.ym-col-info {{
  display: flex;
  flex-direction: column;
  gap: 3px;
  flex: 1;
}}

.ym-label {{
  font-size: 13px;
  font-weight: 500;
  color: #f0f0f0;
}}

.ym-desc {{
  font-size: 11px;
  color: var(--ym-mod-text-secondary, #8c8c8c);
  line-height: 1.4;
}}

/* === NATIVE SWITCH COMPONENT === */
.ym-switch {{
  position: relative;
  display: inline-block;
  width: 38px;
  height: 20px;
  flex-shrink: 0;
}}

.ym-switch input {{
  opacity: 0;
  width: 0;
  height: 0;
}}

.ym-slider {{
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #2c2c2c;
  transition: background-color 0.18s ease;
  border-radius: 20px;
}}

.ym-slider:before {{
  position: absolute;
  content: "";
  height: 14px;
  width: 14px;
  left: 3px;
  bottom: 3px;
  background-color: #ffffff;
  transition: transform 0.18s cubic-bezier(0.16, 1, 0.3, 1);
  border-radius: 50%;
}}

.ym-switch input:checked + .ym-slider {{
  background-color: var(--yandexMusicModAccent, #fed42b);
}}

.ym-switch input:checked + .ym-slider:before {{
  transform: translateX(18px);
  background-color: #121212;
}}

/* === COLOR PALETTE SWATCHES === */
.ym-color-palette {{
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}}

.ym-color-swatch {{
  width: 26px;
  height: 26px;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid rgba(255, 255, 255, 0.15);
  transition: transform 0.15s ease, border-color 0.15s ease;
  position: relative;
}}

.ym-color-swatch:hover {{
  transform: scale(1.1);
  border-color: rgba(255, 255, 255, 0.4);
}}

.ym-color-swatch.active {{
  border: 2px solid #ffffff;
  transform: scale(1.08);
}}

.ym-custom-color-input {{
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid var(--ym-mod-border, #262626);
  cursor: pointer;
  padding: 0;
  background: transparent;
  outline: none;
}}

/* === ACTION BUTTONS === */
.ym-btn-action {{
  background: #202020;
  border: 1px solid var(--ym-mod-border, #262626);
  color: #f0f0f0;
  padding: 7px 14px;
  border-radius: 7px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.15s ease;
  font-family: inherit;
  outline: none;
}}

.ym-btn-action:hover {{
  background: #282828;
  border-color: #383838;
  color: #ffffff;
}}

.ym-btn-action:active {{
  transform: scale(0.98);
}}

.ym-btn-primary {{
  background: var(--yandexMusicModAccent, #fed42b);
  border-color: var(--yandexMusicModAccent, #fed42b);
  color: #121212;
  font-weight: 600;
}}

.ym-btn-primary:hover {{
  background: color-mix(in srgb, var(--yandexMusicModAccent, #fed42b) 90%, white);
  border-color: color-mix(in srgb, var(--yandexMusicModAccent, #fed42b) 90%, white);
  color: #121212;
}}

/* === SELECTS & INPUTS === */
.ym-select, .ym-input {{
  background: #1c1c1c;
  border: 1px solid var(--ym-mod-border, #262626);
  color: #f0f0f0;
  padding: 7px 11px;
  border-radius: 7px;
  font-size: 12px;
  outline: none;
  transition: border-color 0.15s ease;
  font-family: inherit;
}}

.ym-select:focus, .ym-input:focus {{
  border-color: var(--yandexMusicModAccent, #fed42b);
}}

/* === TOAST NOTIFICATION === */
.ym-toast {{
  position: fixed;
  bottom: 24px;
  right: 24px;
  background: #181818;
  border: 1px solid var(--ym-mod-border, #262626);
  color: #f0f0f0;
  padding: 10px 16px;
  border-radius: 9px;
  font-size: 12px;
  font-weight: 500;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6);
  z-index: 9999999;
  display: flex;
  align-items: center;
  gap: 12px;
  opacity: 0;
  transform: translateY(12px);
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  pointer-events: none;
  font-family: inherit;
}}

.ym-toast.show {{
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
}}

.ym-toast-reload-btn {{
  background: #252525;
  border: 1px solid #353535;
  color: #ffffff;
  padding: 3px 9px;
  border-radius: 5px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}}

.ym-toast-reload-btn:hover {{
  background: var(--yandexMusicModAccent, #fed42b);
  border-color: var(--yandexMusicModAccent, #fed42b);
  color: #121212;
}}

/* === SUBSCRIPTION & PROMOTION AD SUPPRESSION === */
div[class*="PaywallBanner_"],
div[class*="SubscriptionNotice_"],
div[class*="UpgradeBanner_"],
div[class*="PlusModal_"],
div[class*="PromoBanner_"],
div[class*="SubscriptionBanner_"],
div[class*="PromoBar_"],
aside[data-test-id="NAVBAR"] [class*="PlusButton_"],
aside[data-test-id="NAVBAR"] a[href*="plus.yandex"],
[data-test-id="PLUS_BADGE_CONTAINER"],
button[data-test-id="UPGRADE_BUTTON"],
div[class*="PlusBadge_"],
div[class*="GetPlus_"] {{
  display: none !important;
}}
"""

with open(OUTPUT_CSS, "w", encoding="utf-8") as f:
    f.write(css_content)

print(f"[+] Successfully wrote mod-renderer.css ({os.path.getsize(OUTPUT_CSS)} bytes)")
