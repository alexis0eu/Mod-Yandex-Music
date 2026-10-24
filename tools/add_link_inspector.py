import os
import sys
import time
import subprocess
import psutil

app_dir = r"C:\Users\denbi\AppData\Local\Programs\YandexMusic"
exe_name = [f for f in os.listdir(app_dir) if f.endswith(".exe") and not f.startswith("Uninstall")][0]
exe_path = os.path.join(app_dir, exe_name)

# Kill any existing instances
for p in psutil.process_iter(['pid', 'name']):
    try:
        n = p.info['name']
        if n and ('yandex' in n.lower() or 'музык' in n.lower()):
            p.kill()
    except Exception:
        pass

log_dir = os.path.join(os.environ.get("APPDATA", ""), "YandexMusic")
log_path = os.path.join(log_dir, "mod-renderer-console.log")
if os.path.exists(log_path):
    os.remove(log_path)

# Update dump in mod-main.js to print all sidebar links
main_js = r"src\main\mod-main.js"
with open(main_js, "r", encoding="utf-8") as f:
    m_code = f.read()

# Replace dumpState with detailed sidebar links dumper
marker = "const pointCenter = document.elementFromPoint"
if marker in m_code:
    replacement = """
            const asideLinks = Array.from(document.querySelectorAll('aside a, [data-test-id="NAVBAR"] a')).map(a => ({
              href: a.getAttribute("href"),
              text: a.innerText.trim(),
              testId: a.getAttribute("data-test-id") || (a.parentElement ? a.parentElement.getAttribute("data-test-id") : null)
            }));

            const pointCenter = document.elementFromPoint"""
    m_code = m_code.replace("const pointCenter = document.elementFromPoint", replacement)
    m_code = m_code.replace("center: pointCenter ? { tag: pointCenter.tagName, id: pointCenter.id, cls: pointCenter.className } : null", "center: pointCenter ? { tag: pointCenter.tagName, id: pointCenter.id, cls: pointCenter.className } : null,\n                sidebarLinks: asideLinks")
    with open(main_js, "w", encoding="utf-8") as f:
        f.write(m_code)
    print("Added sidebar links inspection to mod-main.js")
