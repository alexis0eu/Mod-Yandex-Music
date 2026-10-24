import os

css_path = os.path.join("src", "renderer", "mod-renderer.css")
with open(css_path, "r", encoding="utf-8") as f:
    css = f.read()

start_marker = "/* === MODAL BACKDROP === */"
if start_marker not in css:
    start_marker = ".ym-mod-modal-backdrop {"

end_marker = "/* === SUBSCRIPTION & PROMOTION AD SUPPRESSION ==="

idx_start = css.find(start_marker)
idx_end = css.find(end_marker)

print("idx_start:", idx_start, "idx_end:", idx_end)

new_modal_css = """/* ========================================================
   YANDEX MUSIC MOD - NATIVE FROSTED GLASS DESIGN SYSTEM
   Strict Anti-slop: Matte dark glass rgba(20, 20, 24, 0.88),
   backdrop blur 32px, 1px subtle white/0.08 borders,
   subtle 1px inner highlight, clean native typography.
   Matching context menu reference (media_1792861283133_821f0222.png).
   ======================================================== */

.ym-mod-modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  z-index: 999999;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.22s cubic-bezier(0.16, 1, 0.3, 1);
}

.ym-mod-modal-backdrop.open {
  opacity: 1;
  pointer-events: auto;
}

/* === MODAL WINDOW === */
.ym-mod-modal {
  width: 860px;
  max-width: 94vw;
  height: 640px;
  max-height: 90vh;
  background: rgba(20, 20, 24, 0.88) !important;
  backdrop-filter: blur(36px) saturate(180%) !important;
  -webkit-backdrop-filter: blur(36px) saturate(180%) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  border-radius: 18px !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12), 0 28px 72px rgba(0, 0, 0, 0.7) !important;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transform: scale(0.96);
  transition: transform 0.22s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.22s ease;
  color: #f0f0f0;
  font-family: inherit;
}

.ym-mod-modal-backdrop.open .ym-mod-modal {
  transform: scale(1);
}

/* === MODAL HEADER === */
.ym-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 22px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.02);
}

.ym-modal-title-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ym-modal-logo {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  background: var(--yandexMusicModAccent, #fed42b);
  color: #121212;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 800;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.ym-modal-title {
  font-size: 15px;
  font-weight: 600;
  color: #ffffff;
  letter-spacing: 0.2px;
}

.ym-modal-version {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.45);
  font-weight: 500;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 2px 8px;
  border-radius: 6px;
}

.ym-modal-close {
  background: transparent;
  border: 1px solid transparent;
  color: rgba(255, 255, 255, 0.55);
  font-size: 16px;
  cursor: pointer;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.ym-modal-close:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.12);
  color: #ffffff;
}

/* === MODAL LAYOUT === */
.ym-modal-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* Tabs Sidebar */
.ym-modal-tabs {
  width: 210px;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  padding: 14px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: rgba(0, 0, 0, 0.2);
  overflow-y: auto;
}

.ym-tab-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 14px;
  border-radius: 10px;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.55);
  font-size: 13px;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition: all 0.15s ease;
  position: relative;
  font-family: inherit;
}

.ym-tab-btn:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #ffffff;
}

.ym-tab-btn.active {
  background: rgba(255, 255, 255, 0.10);
  color: #ffffff;
  font-weight: 600;
  box-shadow: inset 3px 0 0 var(--yandexMusicModAccent, #fed42b);
}

/* Tab Content */
.ym-modal-content {
  flex: 1;
  padding: 22px 26px;
  overflow-y: auto;
  background: transparent;
}

.ym-tab-pane {
  display: none;
  flex-direction: column;
  gap: 16px;
}

.ym-tab-pane.active {
  display: flex;
}

/* === CARDS & SETTING ROWS === */
.ym-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 14px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  transition: border-color 0.15s ease;
}

.ym-card:hover {
  border-color: rgba(255, 255, 255, 0.10);
}

.ym-card-title {
  font-size: 13px;
  font-weight: 600;
  color: #ffffff;
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.ym-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.ym-col-info {
  display: flex;
  flex-direction: column;
  gap: 3px;
  flex: 1;
}

.ym-label {
  font-size: 13px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.92);
}

.ym-desc {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.48);
  line-height: 1.4;
}

/* === NATIVE SWITCH COMPONENT === */
.ym-switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 22px;
  flex-shrink: 0;
}

.ym-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.ym-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(255, 255, 255, 0.14);
  transition: background-color 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  border-radius: 22px;
}

.ym-slider:before {
  position: absolute;
  content: "";
  height: 16px;
  width: 16px;
  left: 3px;
  bottom: 3px;
  background-color: #ffffff;
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  border-radius: 50%;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.ym-switch input:checked + .ym-slider {
  background-color: var(--yandexMusicModAccent, #fed42b);
}

.ym-switch input:checked + .ym-slider:before {
  transform: translateX(18px);
  background-color: #121212;
}

/* === COLOR PALETTE SWATCHES === */
.ym-color-palette {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.ym-color-swatch {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  cursor: pointer;
  border: 1px solid rgba(255, 255, 255, 0.15);
  transition: transform 0.15s ease, border-color 0.15s ease;
  position: relative;
}

.ym-color-swatch:hover {
  transform: scale(1.1);
  border-color: rgba(255, 255, 255, 0.4);
}

.ym-color-swatch.active {
  border: 2px solid #ffffff;
  transform: scale(1.08);
  box-shadow: 0 0 8px rgba(255, 255, 255, 0.3);
}

.ym-custom-color-input {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  cursor: pointer;
  padding: 0;
  background: transparent;
  outline: none;
}

/* === ACTION BUTTONS === */
.ym-btn-action {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.10);
  color: #f0f0f0;
  padding: 8px 15px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.15s ease;
  font-family: inherit;
  outline: none;
}

.ym-btn-action:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.16);
  color: #ffffff;
}

.ym-btn-action:active {
  transform: scale(0.98);
}

.ym-btn-primary {
  background: var(--yandexMusicModAccent, #fed42b);
  border-color: var(--yandexMusicModAccent, #fed42b);
  color: #121212;
  font-weight: 600;
}

.ym-btn-primary:hover {
  filter: brightness(1.1);
  color: #000000;
}

/* === SELECTS & INPUTS === */
.ym-select {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.10);
  color: #ffffff;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 12px;
  outline: none;
  cursor: pointer;
  font-family: inherit;
  transition: border-color 0.15s ease;
}

.ym-select:focus {
  border-color: var(--yandexMusicModAccent, #fed42b);
}

.ym-select option {
  background: #18181c;
  color: #ffffff;
}

.ym-input {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.10);
  color: #ffffff;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 12px;
  outline: none;
  font-family: inherit;
  transition: border-color 0.15s ease;
}

.ym-input:focus {
  border-color: var(--yandexMusicModAccent, #fed42b);
}

/* === RANGE SLIDER === */
.ym-range-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 140px;
  height: 4px;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.12);
  outline: none;
}

.ym-range-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--yandexMusicModAccent, #fed42b);
  cursor: pointer;
  box-shadow: 0 0 6px rgba(0, 0, 0, 0.4);
  transition: transform 0.1s ease;
}

.ym-range-slider::-webkit-slider-thumb:hover {
  transform: scale(1.15);
}

/* === TOAST NOTIFICATION === */
.ym-toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  background: rgba(24, 24, 28, 0.92);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.10);
  border-radius: 12px;
  padding: 12px 18px;
  color: #ffffff;
  font-size: 13px;
  font-weight: 500;
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  gap: 12px;
  z-index: 1000000;
  transform: translateY(40px);
  opacity: 0;
  pointer-events: none;
  transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
}

.ym-toast.show {
  transform: translateY(0);
  opacity: 1;
  pointer-events: auto;
}

"""

if idx_start != -1 and idx_end != -1:
    updated_css = css[:idx_start] + new_modal_css + css[idx_end:]
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(updated_css)
    print("Successfully replaced modal CSS with native frosted dark glass styling!")
else:
    print("Marker mismatch:", idx_start, idx_end)
