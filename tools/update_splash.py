import os

target = r"src\renderer\mod-renderer.js"
with open(target, "r", encoding="utf-8") as f:
    c = f.read()

old_block = """(function killSplashScreen() {
  const nuke = () => {
    try {
      const splashes = document.querySelectorAll('div[class*="SplashScreen_root"], .SplashScreen_root__3jzFk');
      splashes.forEach(s => s.remove());
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
              node.remove();
            } else if (node.querySelector) {
              const nested = node.querySelector('div[class*="SplashScreen_root"], .SplashScreen_root__3jzFk');
              if (nested) nested.remove();
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
})();"""

new_block = """(function killSplashScreen() {
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
      const splashes = document.querySelectorAll('div[class*="SplashScreen_root"], .SplashScreen_root__3jzFk');
      splashes.forEach(hideElement);
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
})();"""

c_normalized = c.replace("\r\n", "\n")
old_normalized = old_block.replace("\r\n", "\n")
new_normalized = new_block.replace("\r\n", "\n")

if old_normalized in c_normalized:
    c_updated = c_normalized.replace(old_normalized, new_normalized)
    with open(target, "w", encoding="utf-8") as f:
        f.write(c_updated)
    print("Successfully updated killSplashScreen to safe CSS property setter")
else:
    print("Could not match old_normalized in mod-renderer.js!")
