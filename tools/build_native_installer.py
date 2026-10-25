import os
import shutil
import subprocess
import sys

def build_installer():
    app_dir = os.path.expandvars(r"%LOCALAPPDATA%\Programs\YandexMusic")
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    staging_dir = os.path.join(repo_root, "dist", "staging")
    nsis_exe = os.path.join(repo_root, "tools", "nsis", "makensis.exe")
    nsi_script = os.path.join(repo_root, "tools", "native_installer.nsi")
    dist_dir = os.path.join(repo_root, "dist")

    if not os.path.isdir(app_dir):
        print(f"[-] App directory not found: {app_dir}")
        sys.exit(1)

    print(f"[+] Staging files from {app_dir} to {staging_dir}...")
    if os.path.exists(staging_dir):
        shutil.rmtree(staging_dir, ignore_errors=True)
    os.makedirs(staging_dir, exist_ok=True)

    def ignore_patterns(folder, items):
        ignored = []
        for item in items:
            if item.endswith(".bak") or item.endswith(".tmp") or item.endswith(".log"):
                ignored.append(item)
        return ignored

    # Copy files
    for root, dirs, files in os.walk(app_dir):
        rel_path = os.path.relpath(root, app_dir)
        dest_folder = os.path.join(staging_dir, rel_path) if rel_path != "." else staging_dir
        os.makedirs(dest_folder, exist_ok=True)
        for f in files:
            if f.endswith(".bak") or f.endswith(".tmp") or f.endswith(".log"):
                continue
            src_file = os.path.join(root, f)
            dest_file = os.path.join(dest_folder, f)
            shutil.copy2(src_file, dest_file)

    print(f"[+] Staged files count: {sum(len(f) for _, _, f in os.walk(staging_dir))}")

    print(f"[+] Compiling installer with NSIS: {nsis_exe} (/INPUTCHARSET UTF8)...")
    proc = subprocess.run([nsis_exe, "/INPUTCHARSET", "UTF8", nsi_script], cwd=os.path.join(repo_root, "tools"), capture_output=True)
    try:
        print(proc.stdout.decode("utf-8", errors="replace"))
    except Exception:
        pass
    if proc.returncode != 0:
        print("[-] NSIS compilation failed:")
        try:
            print(proc.stderr.decode("utf-8", errors="replace"))
        except Exception:
            pass
        sys.exit(1)

    target_mod = os.path.join(dist_dir, "Yandex_Music_x64_5.124.1_Mod.exe")

    if not os.path.isfile(target_mod):
        print(f"[-] Expected output file not found: {target_mod}")
        sys.exit(1)

    size_mod = os.path.getsize(target_mod) / (1024 * 1024)
    print(f"[+] Created {target_mod} ({size_mod:.1f} MB)")

    print("[+] Cleaning up staging directory...")
    shutil.rmtree(staging_dir, ignore_errors=True)
    print("[+] Done!")

if __name__ == "__main__":
    build_installer()
