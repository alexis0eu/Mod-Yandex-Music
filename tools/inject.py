import os

import sys



if hasattr(sys.stdout, 'reconfigure'):

    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)



import shutil

import tempfile

import psutil

import struct

import hashlib

import re

from asar_tool import extract_asar, pack_asar



DEFAULT_APP_DIR = r"C:\Users\denbi\AppData\Local\Programs\YandexMusic"

DEFAULT_RESOURCES_DIR = os.path.join(DEFAULT_APP_DIR, "resources")

DEFAULT_ASAR = os.path.join(DEFAULT_RESOURCES_DIR, "app.asar")

DEFAULT_BACKUP = os.path.join(DEFAULT_RESOURCES_DIR, "app.asar.bak")



PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

SRC_DIR = os.path.join(PROJECT_DIR, "src")



def check_process_running():

    for proc in psutil.process_iter(['name']):

        try:

            name = proc.info['name']

            if name and ('yandexmusic' in name.lower() or 'яндекс музыка' in name.lower()):

                print(f"[!] Warning: Process {name} (PID: {proc.pid}) is currently running.")

                print(f"[!] Terminating process to allow file modification...")

                proc.kill()

                proc.wait(timeout=5)

        except (psutil.NoSuchProcess, psutil.AccessDenied):

            pass



def copy_file_safe(src, dst):

    os.makedirs(os.path.dirname(dst), exist_ok=True)

    shutil.copy2(src, dst)



def patch_executable_integrity(asar_path):

    app_dir = os.path.dirname(os.path.dirname(asar_path))

    exe_file = None

    for f in os.listdir(app_dir):

        if f.endswith(".exe") and not f.startswith("Uninstall"):

            exe_file = os.path.join(app_dir, f)

            break

    if not exe_file:

        print("[!] No main executable found to patch integrity.")

        return



    # Backup exe if not backed up

    exe_bak = exe_file + ".bak"

    if not os.path.exists(exe_bak):

        print(f"[+] Backing up executable to {exe_bak}")

        shutil.copy2(exe_file, exe_bak)



    # Compute new ASAR header SHA256

    with open(asar_path, "rb") as f:

        u1, u2, u3, u4 = struct.unpack("<IIII", f.read(16))

        header_bytes = f.read(u4)

    new_hash = hashlib.sha256(header_bytes).hexdigest().encode("ascii")



    # Read clean original header hash from asar backup if available

    asar_bak = asar_path + ".bak"

    orig_hash = None

    if os.path.exists(asar_bak):

        with open(asar_bak, "rb") as f:

            u1, u2, u3, u4 = struct.unpack("<IIII", f.read(16))

            orig_header = f.read(u4)

        orig_hash = hashlib.sha256(orig_header).hexdigest().encode("ascii")



    base_exe = exe_bak if os.path.exists(exe_bak) else exe_file

    with open(base_exe, "rb") as f:

        exe_data = f.read()



    patched = False

    if orig_hash and orig_hash in exe_data:

        exe_data = exe_data.replace(orig_hash, new_hash)

        print(f"[+] Updated ASAR integrity hash in executable to {new_hash.decode('ascii')}")

        patched = True

    else:

        match = re.search(rb'("file":"resources[\\/]app\.asar","alg":"SHA256","value":")([a-f0-9]{64})(")', exe_data)

        if match:

            exe_data = exe_data[:match.start(2)] + new_hash + exe_data[match.end(2):]

            print(f"[+] Updated ASAR integrity hash in executable via pattern to {new_hash.decode('ascii')}")

            patched = True



    # Disable fuse EnableEmbeddedAsarIntegrityValidation (5th fuse in 8-byte string)

    fuse_magic = b'dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX\x01\x0810111101'

    fuse_magic_disabled = b'dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX\x01\x0810110101'

    if fuse_magic in exe_data:

        exe_data = exe_data.replace(fuse_magic, fuse_magic_disabled)

        print("[+] Disabled Electron fuse EnableEmbeddedAsarIntegrityValidation in executable")

        patched = True



    if patched:

        with open(exe_file, "wb") as f:

            f.write(exe_data)

        print("[+] Executable integrity and fuses successfully configured!")



def inject_mod(asar_path=DEFAULT_ASAR):

    print(f"[+] Target ASAR: {asar_path}")

    if not os.path.exists(asar_path):

        raise FileNotFoundError(f"Target ASAR not found at {asar_path}")



    check_process_running()



    # 1. Backup original asar if .bak does not exist

    backup_path = asar_path + ".bak"

    if not os.path.exists(backup_path):

        print(f"[+] Creating original backup: {backup_path}")

        shutil.copy2(asar_path, backup_path)

    else:

        print(f"[i] Backup already exists at {backup_path}")



    # 2. Extract ASAR to temporary staging directory

    staging_dir = tempfile.mkdtemp(prefix="ym_mod_staging_")

    print(f"[+] Extracting ASAR to temporary staging area: {staging_dir}")

    try:

        extract_asar(asar_path, staging_dir)

        print(f"[+] ASAR extracted successfully.")



        # 3. Create destination folders inside staging

        mod_app_dir = os.path.join(staging_dir, "app", "yandexMusicMod")

        mod_preload_dir = os.path.join(staging_dir, "preload")

        app_preload_dir = os.path.join(staging_dir, "app", "preload")

        os.makedirs(mod_app_dir, exist_ok=True)

        os.makedirs(mod_preload_dir, exist_ok=True)

        os.makedirs(app_preload_dir, exist_ok=True)



        # 4. Copy Main Process scripts

        print("[+] Copying Main Process modules...")

        copy_file_safe(os.path.join(SRC_DIR, "main", "mod-main.js"), os.path.join(mod_app_dir, "main.js"))

        copy_file_safe(os.path.join(SRC_DIR, "main", "discord-rpc.js"), os.path.join(mod_app_dir, "discord-rpc.js"))

        copy_file_safe(os.path.join(SRC_DIR, "main", "settings.js"), os.path.join(mod_app_dir, "settings.js"))



        # 5. Copy Preload bridges to all locations for bulletproof path resolution

        print("[+] Copying Preload bridges...")

        copy_file_safe(os.path.join(SRC_DIR, "preload", "overlay-preload.js"), os.path.join(mod_preload_dir, "overlay-preload.js"))

        copy_file_safe(os.path.join(SRC_DIR, "preload", "karaoke-preload.js"), os.path.join(mod_preload_dir, "karaoke-preload.js"))

        copy_file_safe(os.path.join(SRC_DIR, "preload", "overlay-preload.js"), os.path.join(mod_app_dir, "overlay-preload.js"))

        copy_file_safe(os.path.join(SRC_DIR, "preload", "karaoke-preload.js"), os.path.join(mod_app_dir, "karaoke-preload.js"))

        copy_file_safe(os.path.join(SRC_DIR, "preload", "overlay-preload.js"), os.path.join(app_preload_dir, "overlay-preload.js"))

        copy_file_safe(os.path.join(SRC_DIR, "preload", "karaoke-preload.js"), os.path.join(app_preload_dir, "karaoke-preload.js"))



        # 6. Copy Overlay & Karaoke UI assets

        print("[+] Copying Overlay & Karaoke HUD assets...")

        for name in ["overlay.html", "overlay.css", "overlay.js"]:

            copy_file_safe(os.path.join(SRC_DIR, "overlay", name), os.path.join(mod_app_dir, name))

        for name in ["karaoke.html", "karaoke.css", "karaoke.js"]:

            copy_file_safe(os.path.join(SRC_DIR, "karaoke", name), os.path.join(mod_app_dir, name))



        # 7. Copy Renderer scripts & styles

        print("[+] Copying Renderer mod files...")

        copy_file_safe(os.path.join(SRC_DIR, "renderer", "mod-renderer.js"), os.path.join(mod_app_dir, "renderer.js"))

        copy_file_safe(os.path.join(SRC_DIR, "renderer", "mod-renderer.css"), os.path.join(mod_app_dir, "renderer.css"))



        # 8. Copy Custom Fonts

        print("[+] Copying Custom Fonts...")

        fonts_dir = os.path.join(SRC_DIR, "fonts")

        if os.path.exists(fonts_dir):

            for font_file in os.listdir(fonts_dir):

                copy_file_safe(os.path.join(fonts_dir, font_file), os.path.join(mod_app_dir, font_file))



        # 9. Patch index.js in root of staging

        print("[+] Patching index.js...")

        index_js_path = os.path.join(staging_dir, "index.js")

        with open(index_js_path, "r", encoding="utf-8") as f:

            index_content = f.read()



        # Neuter autoUpdater in index.js to prevent background checks and auto-installs
        if "electronUpdater.autoUpdater.checkForUpdates()" in index_content:
            index_content = index_content.replace(
                "const updateResult = await electronUpdater.autoUpdater.checkForUpdates();",
                "const updateResult = null; // Blocked by Yandex Music Mod"
            )
        if "electronUpdater.autoUpdater.quitAndInstall();" in index_content:
            index_content = index_content.replace(
                "electronUpdater.autoUpdater.quitAndInstall();",
                "// electronUpdater.autoUpdater.quitAndInstall(); Blocked by Mod"
            )

        if "yandexMusicMod/main.js" not in index_content:

            injection_hook = """

// === Injected by Yandex Music Mod ===

try {

  require("./app/yandexMusicMod/main.js");

} catch (modErr) {

  console.error("[YandexMusicMod Main Hook Error]", modErr);

}

"""

            index_content += "\n" + injection_hook

            with open(index_js_path, "w", encoding="utf-8") as f:

                f.write(index_content)

            print("[+] index.js patched with main process mod loader.")

        else:

            print("[i] index.js already has mod loader.")



        # 10. Patch preload.js in root of staging

        print("[+] Patching preload.js...")

        preload_js_path = os.path.join(staging_dir, "preload.js")

        with open(preload_js_path, "r", encoding="utf-8") as f:

            preload_content = f.read()



        with open(os.path.join(SRC_DIR, "preload", "mod-preload.js"), "r", encoding="utf-8") as f:

            mod_preload_content = f.read()



        if "// === Yandex Music Mod Preload Integration ===" in preload_content:

            idx = preload_content.find("// === Yandex Music Mod Preload Integration ===")

            preload_content = preload_content[:idx].rstrip() + "\n\n" + mod_preload_content

            with open(preload_js_path, "w", encoding="utf-8") as f:

                f.write(preload_content)

            print("[+] preload.js updated with latest mod contextBridge.")

        elif "yandexMusicMod" not in preload_content:

            preload_content += "\n\n" + mod_preload_content

            with open(preload_js_path, "w", encoding="utf-8") as f:

                f.write(preload_content)

            print("[+] preload.js patched with contextBridge exposure.")

        else:

            print("[i] preload.js already has mod contextBridge.")



        # 11. Patch application HTML files to include renderer script and css tag

        # IMPORTANT: Exclude yandexMusicMod folder so HUD overlay & karaoke windows are not contaminated!

        print("[+] Patching HTML entrypoints in app/ (excluding mod HUD overlays)...")

        app_dir = os.path.join(staging_dir, "app")

        injected_html_count = 0

        tag_to_inject = '<script id="ym-mod-renderer-script" src="/yandexMusicMod/renderer.js"></script><link id="ym-mod-renderer-style" rel="stylesheet" href="/yandexMusicMod/renderer.css" />'



        for root, _, files in os.walk(app_dir):

            if "yandexMusicMod" in root:

                continue

            for file in files:

                if file.endswith(".html"):

                    html_file = os.path.join(root, file)

                    with open(html_file, "r", encoding="utf-8") as f:

                        html_content = f.read()

                    if "/yandexMusicMod/renderer.js" not in html_content:

                        if "</head>" in html_content:

                            html_content = html_content.replace("</head>", f"{tag_to_inject}</head>")

                        elif "<head>" in html_content:

                            html_content = html_content.replace("<head>", f"<head>{tag_to_inject}")

                        else:

                            html_content = tag_to_inject + html_content

                        with open(html_file, "w", encoding="utf-8") as f:

                            f.write(html_content)

                        injected_html_count += 1



        print(f"[+] Injected mod tags into {injected_html_count} HTML files.")



        # 11b. Patch Next.js chunk to permanently disable top ad banner

        print("[+] Patching Top Advert Banner in Next.js chunks...")

        chunks_dir = os.path.join(staging_dir, "app", "_next", "static", "chunks")

        if os.path.exists(chunks_dir):

            for file in os.listdir(chunks_dir):

                if file.endswith(".js"):

                    chunk_path = os.path.join(chunks_dir, file)

                    with open(chunk_path, "r", encoding="utf-8") as f:

                        c = f.read()

                    if "b=(!u.isAuthorized||v.isFreeWebUser)&&h.isVisible" in c:

                        c = c.replace("b=(!u.isAuthorized||v.isFreeWebUser)&&h.isVisible", "b=!1&&h.isVisible")

                        with open(chunk_path, "w", encoding="utf-8") as f:

                            f.write(c)

                        print(f"[+] Permanently disabled Top Advert Banner in {file}!")

                    # Permanently disable official update notification banner in Next.js chunks
                    if 'className:(0,C.$)(N().root,N().important),message:s})' in c:
                        c = c.replace(
                            'return(0,o.jsx)(x.$,{className:(0,C.$)(N().root,N().important),message:s})',
                            'return null; // Blocked by Yandex Music Mod'
                        )
                        with open(chunk_path, "w", encoding="utf-8") as f:
                            f.write(c)
                        print(f"[+] Permanently disabled Update Notification Banner in {file}!")



        # 12. Repack staging directory into target ASAR

        new_asar_tmp = asar_path + ".tmp"

        print(f"[+] Repacking ASAR to {new_asar_tmp}...")

        pack_asar(staging_dir, new_asar_tmp)

        print(f"[+] ASAR repacked. Size: {os.path.getsize(new_asar_tmp)} bytes.")



        # Atomic replace with retry

        print(f"[+] Replacing {asar_path}...")

        import time

        replaced = False

        for attempt in range(10):

            try:

                check_process_running()

                if os.path.exists(asar_path):

                    os.remove(asar_path)

                os.rename(new_asar_tmp, asar_path)

                replaced = True

                break

            except PermissionError:

                time.sleep(1)

        if not replaced:

            if os.path.exists(asar_path):

                os.remove(asar_path)

            os.rename(new_asar_tmp, asar_path)



        # 13. Update ASAR integrity hash and Electron fuses in main executable

        patch_executable_integrity(asar_path)

        # Update PE icon inside executable
        try:
            from patch_exe_icon import patch_exe_icon
            app_dir = os.path.dirname(os.path.dirname(asar_path))
            for f in os.listdir(app_dir):
                if f.endswith(".exe") and not f.startswith("Uninstall"):
                    patch_exe_icon(os.path.join(app_dir, f), os.path.join(PROJECT_DIR, "assets", "icon.ico"))
                    break
        except Exception as e:
            print(f"[!] Warning patching exe icon in inject: {e}")

        # 14. Update application icons to mod red theme
        try:
            resources_dir = os.path.dirname(asar_path)
            repo_assets = os.path.join(PROJECT_DIR, "assets")
            target_assets = os.path.join(resources_dir, "assets")
            if os.path.exists(target_assets) and os.path.exists(repo_assets):
                src_ico = os.path.join(repo_assets, "icon.ico")
                if os.path.exists(src_ico):
                    shutil.copy2(src_ico, os.path.join(target_assets, "icon.ico"))
                src_logo = os.path.join(repo_assets, "logo.png")
                if os.path.exists(src_logo):
                    shutil.copy2(src_logo, os.path.join(target_assets, "logo.png"))
                print("[+] Application icons updated to red theme!")
        except Exception as e:
            print(f"[!] Warning: Could not update application icons: {e}")



        
        # Neutralize app-update.yml to block downloads
        resources_dir = os.path.dirname(asar_path)
        app_update_yml = os.path.join(resources_dir, "app-update.yml")
        if os.path.exists(app_update_yml):
            try:
                with open(app_update_yml, "w", encoding="utf-8") as yf:
                    yf.write("provider: generic\nurl: http://127.0.0.1:0/\nuseMultipleRangeRequest: false\nupdaterCacheDirName: yandexmusic-updater\n")
                print("[+] Neutralized resources/app-update.yml to block downloads.")
            except Exception as e:
                print(f"[!] Warning neutralizing app-update.yml: {e}")

        # Clear updater cache directory in %LOCALAPPDATA%
        updater_cache = os.path.expandvars(r"%LOCALAPPDATA%\yandexmusic-updater")
        if os.path.exists(updater_cache):
            try:
                shutil.rmtree(updater_cache, ignore_errors=True)
                print("[+] Cleared updater cache directory.")
            except Exception:
                pass

        print(f"[+] YANDEX MUSIC MOD INJECTED SUCCESSFULLY!")



    finally:

        # Clean up staging directory

        try:

            shutil.rmtree(staging_dir, ignore_errors=True)

        except Exception:

            pass



if __name__ == "__main__":

    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ASAR

    inject_mod(target)

