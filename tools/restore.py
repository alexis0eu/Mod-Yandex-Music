import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import shutil
import psutil

DEFAULT_APP_DIR = r"C:\Users\denbi\AppData\Local\Programs\YandexMusic"
DEFAULT_RESOURCES_DIR = os.path.join(DEFAULT_APP_DIR, "resources")
DEFAULT_ASAR = os.path.join(DEFAULT_RESOURCES_DIR, "app.asar")
DEFAULT_BACKUP = os.path.join(DEFAULT_RESOURCES_DIR, "app.asar.bak")

def check_process_running():
    for proc in psutil.process_iter(['name']):
        try:
            name = proc.info['name']
            if name and ('yandexmusic' in name.lower() or 'яндекс музыка' in name.lower()):
                print(f"[!] Warning: Process {name} (PID: {proc.pid}) is currently running.")
                print(f"[!] Terminating process to allow file restoration...")
                proc.kill()
                proc.wait(timeout=5)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

def restore_backup(asar_path=DEFAULT_ASAR):
    app_dir = os.path.dirname(os.path.dirname(asar_path))
    exe_file = None
    if os.path.exists(app_dir):
        for f in os.listdir(app_dir):
            if f.endswith(".exe") and not f.startswith("Uninstall"):
                exe_file = os.path.join(app_dir, f)
                break

    check_process_running()

    # 1. Restore executable if backup exists
    if exe_file and os.path.exists(exe_file + ".bak"):
        print(f"[+] Restoring original executable from {exe_file}.bak")
        if os.path.exists(exe_file):
            os.remove(exe_file)
        shutil.copy2(exe_file + ".bak", exe_file)
        print("[+] Restored original executable successfully!")

    # 2. Restore ASAR from backup
    backup_path = asar_path + ".bak"
    print(f"[+] Target ASAR: {asar_path}")
    print(f"[+] Backup path: {backup_path}")

    if not os.path.exists(backup_path):
        print(f"[-] Error: Backup file not found at {backup_path}")
        return False

    print("[+] Restoring original ASAR from backup...")
    if os.path.exists(asar_path):
        os.remove(asar_path)
    shutil.copy2(backup_path, asar_path)
    print("[+] Restored original ASAR successfully!")
    return True

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ASAR
    restore_backup(target)
