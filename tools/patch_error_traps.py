import os

MAIN_JS = r"src\main\mod-main.js"
with open(MAIN_JS, "r", encoding="utf-8") as f:
    code = f.read()

target = """  // 3. Register devtools shortcuts & console logger on every created window
  app.on("browser-window-created", (_ev, win) => {
    const consoleLogPath = path.join(appFolder, "mod-renderer-console.log");

    win.webContents.on("console-message", (_event, level, message, line, sourceId) => {
      const entry = `[LVL ${level}] ${message} (${sourceId}:${line})\\n`;
      try {
        fs.appendFileSync(consoleLogPath, entry, "utf8");
      } catch (e) {}
    });

    win.webContents.on("did-fail-load", (_ev, errorCode, errorDescription, validatedURL) => {
      const entry = `[FAIL LOAD] Code: ${errorCode}, Desc: ${errorDescription}, URL: ${validatedURL}\\n`;
      try {
        fs.appendFileSync(consoleLogPath, entry, "utf8");
      } catch (e) {}
    });

    win.webContents.on("did-finish-load", () => {
      setTimeout(async () => {
        try {
          const domDump = await win.webContents.executeJavaScript(`
            JSON.stringify({
              title: document.title,
              url: window.location.href,
              bodyClasses: document.body.className,
              bodyChildren: Array.from(document.body.children).map(c => ({ tag: c.tagName, id: c.id, cls: c.className })),
              hasRoot: !!document.getElementById("__next") || !!document.getElementById("root"),
              errors: window.__ymLastErrors || []
            }, null, 2)
          `);
          fs.appendFileSync(consoleLogPath, `[DOM DUMP] ${domDump}\\n`, "utf8");
        } catch (e) {}
      }, 2000);
    });

    win.webContents.on("before-input-event", (event, input) => {
      if (input.type === "keyDown") {
        const isF12 = input.key === "F12";
        const isCtrlShiftI = (input.control || input.meta) && input.shift && input.key && input.key.toLowerCase() === "i";
        if (isF12 || isCtrlShiftI) {
          if (settingsManager.get("devtools/enabled", true)) {
            win.webContents.toggleDevTools();
            event.preventDefault();
          }
        }
      }
    });
  });"""

replacement = """  // 3. Register devtools shortcuts & console logger on every window
  function attachToWindow(win) {
    if (!win || win.isDestroyed()) return;

    const consoleLogPath = path.join(appFolder, "mod-renderer-console.log");

    win.webContents.on("console-message", (_event, level, message, line, sourceId) => {
      const entry = `[LVL ${level}] ${message} (${sourceId}:${line})\\n`;
      try {
        fs.appendFileSync(consoleLogPath, entry, "utf8");
      } catch (e) {}
    });

    win.webContents.on("did-fail-load", (_ev, errorCode, errorDescription, validatedURL) => {
      const entry = `[FAIL LOAD] Code: ${errorCode}, Desc: ${errorDescription}, URL: ${validatedURL}\\n`;
      try {
        fs.appendFileSync(consoleLogPath, entry, "utf8");
      } catch (e) {}
    });

    const dumpState = async () => {
      try {
        const domDump = await win.webContents.executeJavaScript(`
          JSON.stringify({
            title: document.title,
            url: window.location.href,
            bodyClasses: document.body ? document.body.className : "",
            bodyChildren: document.body ? Array.from(document.body.children).map(c => ({ tag: c.tagName, id: c.id, cls: c.className })) : [],
            hasRoot: !!document.getElementById("__next") || !!document.getElementById("root"),
            errors: window.__ymLastErrors || []
          }, null, 2)
        `);
        fs.appendFileSync(consoleLogPath, `[DOM DUMP] ${domDump}\\n`, "utf8");
      } catch (e) {}
    };

    win.webContents.on("did-finish-load", () => {
      setTimeout(dumpState, 1500);
    });
    setTimeout(dumpState, 1000);

    win.webContents.on("before-input-event", (event, input) => {
      if (input.type === "keyDown") {
        const isF12 = input.key === "F12";
        const isCtrlShiftI = (input.control || input.meta) && input.shift && input.key && input.key.toLowerCase() === "i";
        if (isF12 || isCtrlShiftI) {
          if (settingsManager.get("devtools/enabled", true)) {
            win.webContents.toggleDevTools();
            event.preventDefault();
          }
        }
      }
    });
  }

  // Attach to existing windows immediately
  BrowserWindow.getAllWindows().forEach(attachToWindow);

  // Attach to future windows
  app.on("browser-window-created", (_ev, win) => {
    attachToWindow(win);
  });"""

norm_code = code.replace("\r\n", "\n")
norm_target = target.replace("\r\n", "\n")
norm_repl = replacement.replace("\r\n", "\n")

if norm_target in norm_code:
    norm_code = norm_code.replace(norm_target, norm_repl, 1)
    with open(MAIN_JS, "w", encoding="utf-8") as f:
        f.write(norm_code)
    print("[+] Patched attachToWindow in mod-main.js")
else:
    print("[-] Error: Target not found in mod-main.js")

# 2. Add error listeners in mod-renderer.js
RENDERER_JS = r"src\renderer\mod-renderer.js"
with open(RENDERER_JS, "r", encoding="utf-8") as f:
    r_code = f.read()

error_traps = """  window.__ymLastErrors = [];
  window.addEventListener("error", (e) => {
    window.__ymLastErrors.push({
      type: "error",
      message: e.message,
      filename: e.filename,
      lineno: e.lineno,
      colno: e.colno,
      stack: e.error ? e.error.stack : null
    });
    console.error("[YM-UNCAUGHT-ERROR]", e.message, e.filename, e.lineno, e.error);
  });
  window.addEventListener("unhandledrejection", (e) => {
    window.__ymLastErrors.push({
      type: "unhandledrejection",
      reason: String(e.reason),
      stack: e.reason && e.reason.stack ? e.reason.stack : null
    });
    console.error("[YM-UNHANDLED-REJECTION]", e.reason);
  });
"""

if "window.__ymLastErrors = [];" not in r_code:
    r_code = r_code.replace(
        'console.log("[YandexMusicMod] Initializing mod renderer v5.124.1...");',
        'console.log("[YandexMusicMod] Initializing mod renderer v5.124.1...");\n' + error_traps
    )
    with open(RENDERER_JS, "w", encoding="utf-8") as f:
        f.write(r_code)
    print("[+] Added error listeners in mod-renderer.js")
else:
    print("[i] Error listeners already present")
