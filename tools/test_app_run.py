import os
import sys
import time
import subprocess
import psutil

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

app_dir = r"C:\Users\denbi\AppData\Local\Programs\YandexMusic"
exe_name = [f for f in os.listdir(app_dir) if f.endswith(".exe") and not f.startswith("Uninstall")][0]
exe_path = os.path.join(app_dir, exe_name)
print(f"Detected EXE: {exe_name} -> {exe_path}")

log_dir = os.path.join(os.environ.get("APPDATA", ""), "YandexMusic")
log_path = os.path.join(log_dir, "mod-renderer-console.log")
main_log = os.path.join(log_dir, "logs", "main.log")
screen_path = os.path.join(log_dir, "mod-screen-capture.png")

# Kill any existing instances first
for p in psutil.process_iter(['pid', 'name']):
    try:
        n = p.info['name']
        if n and ('yandex' in n.lower() or 'музык' in n.lower()):
            p.kill()
    except Exception:
        pass

time.sleep(1)

if os.path.exists(log_path):
    os.remove(log_path)
if os.path.exists(screen_path):
    os.remove(screen_path)

print("Starting clean instance...")
proc = subprocess.Popen([exe_path], cwd=app_dir)
print(f"Spawned PID: {proc.pid}")

# Wait for Next.js to hydrate and dumpState to fire
time.sleep(8)

if os.path.exists(log_path):
    print("=== RENDERER LOG FOUND ===")
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
        print(content)
else:
    print("=== NO RENDERER LOG FOUND ===")

if os.path.exists(screen_path):
    print(f"=== SCREENSHOT CAPTURED: {screen_path} ({os.path.getsize(screen_path)} bytes) ===")
else:
    print("=== NO SCREENSHOT CAPTURED ===")

print("Terminating YandexMusic processes...")
for p in psutil.process_iter(['pid', 'name']):
    try:
        n = p.info['name']
        if n and ('yandex' in n.lower() or 'музык' in n.lower()):
            p.kill()
    except Exception:
        pass

print("Test complete.")
