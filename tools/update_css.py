import os

css_path = r"src\renderer\mod-renderer.css"
with open(css_path, "r", encoding="utf-8") as f:
    c = f.read()

old_block = """.ym-mod-modal-backdrop {
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
}

.ym-mod-modal-backdrop.open {
  opacity: 1;
  pointer-events: auto;
}"""

new_block = """.ym-mod-modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.72);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  z-index: 999999;
  display: none;
  align-items: center;
  justify-content: center;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.ym-mod-modal-backdrop.open {
  display: flex !important;
  opacity: 1;
  pointer-events: auto;
}"""

c_normalized = c.replace("\r\n", "\n")
old_normalized = old_block.replace("\r\n", "\n")
new_normalized = new_block.replace("\r\n", "\n")

if old_normalized in c_normalized:
    c_updated = c_normalized.replace(old_normalized, new_normalized)
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(c_updated)
    print("Successfully updated .ym-mod-modal-backdrop display rule")
else:
    print("Could not match old_normalized in css!")
