import os

target = r"src\main\mod-main.js"
with open(target, "r", encoding="utf-8") as f:
    content = f.read()

start_marker = "    const dumpState = async () => {"
end_marker = "    win.webContents.on(\"did-finish-load\""

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    new_dump = """    const dumpState = async () => {
      try {
        const domDump = await win.webContents.executeJavaScript(`
          (() => {
            const getElInfo = (el) => {
              if (!el) return null;
              const r = el.getBoundingClientRect();
              const s = window.getComputedStyle(el);
              return {
                tag: el.tagName,
                id: el.id,
                cls: el.className,
                rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
                display: s.display,
                visibility: s.visibility,
                opacity: s.opacity,
                zIndex: s.zIndex,
                bg: s.backgroundColor,
                color: s.color,
                overflow: s.overflow
              };
            };

            const pointCenter = document.elementFromPoint(Math.round(window.innerWidth / 2), Math.round(window.innerHeight / 2));
            const pointSidebar = document.elementFromPoint(50, 150);
            const pointTop = document.elementFromPoint(100, 20);

            return JSON.stringify({
              windowSize: { w: window.innerWidth, h: window.innerHeight },
              elementsAtPoints: {
                top: pointTop ? { tag: pointTop.tagName, id: pointTop.id, cls: pointTop.className } : null,
                sidebar: pointSidebar ? { tag: pointSidebar.tagName, id: pointSidebar.id, cls: pointSidebar.className } : null,
                center: pointCenter ? { tag: pointCenter.tagName, id: pointCenter.id, cls: pointCenter.className } : null
              },
              nodes: {
                body: getElInfo(document.body),
                modalBackdrop: getElInfo(document.getElementById("ym-mod-modal-backdrop")),
                withTopBanner: getElInfo(document.querySelector('div[class*="WithTopBanner_root"]')),
                withTopBannerContent: getElInfo(document.querySelector('div[class*="WithTopBanner_content"]')),
                defaultLayout: getElInfo(document.querySelector('div[class*="DefaultLayout_root"]')),
                navbar: getElInfo(document.querySelector('aside[data-test-id="NAVBAR"], aside, nav')),
                sidebarBtn: getElInfo(document.getElementById("ym-mod-menu-btn")),
                floatingTrigger: getElInfo(document.getElementById("ym-mod-floating-trigger"))
              },
              errors: window.__ymLastErrors || []
            }, null, 2);
          })()
        `);
        fs.appendFileSync(consoleLogPath, `[DEEP DOM DUMP] ${domDump}\\n`, "utf8");

        const screenshotPath = path.join(appFolder, "mod-screen-capture.png");
        try {
          const image = await win.webContents.capturePage();
          fs.writeFileSync(screenshotPath, image.toPNG());
          fs.appendFileSync(consoleLogPath, `[SCREENSHOT SAVED] ${screenshotPath} (${image.getSize().width}x${image.getSize().height})\\n`, "utf8");
        } catch (scErr) {
          fs.appendFileSync(consoleLogPath, `[SCREENSHOT ERROR] ${scErr.message}\\n`, "utf8");
        }
      } catch (e) {
        fs.appendFileSync(consoleLogPath, `[DUMP ERROR] ${e.message}\\n`, "utf8");
      }
    };
"""
    content = content[:start_idx] + new_dump + "\n" + content[end_idx:]
    with open(target, "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully updated dumpState in mod-main.js")
else:
    print("Could not find markers in file!", start_idx, end_idx)
