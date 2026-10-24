import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

import shutil
import tempfile
import struct
import hashlib
import re
import subprocess
import threading
import time
import urllib.request
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from asar_tool import extract_asar, pack_asar

OFFICIAL_DOWNLOAD_URL = "https://music-desktop-application.s3.yandex.net/stable/Yandex_Music_x64_5.124.1.exe"
FALLBACK_DOWNLOAD_URL = "https://github.com/alexis0eu/Mod-Yandex-Music/releases/download/v1.1.0/Yandex_Music_x64_5.124.1.exe"

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def get_src_dir():
    base = get_base_dir()
    src = os.path.join(base, "src")
    if os.path.exists(src):
        return src
    # Fallback to local
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))

def find_yandex_music_dir():
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\YandexMusic"),
        os.path.expandvars(r"%APPDATA%\..\Local\Programs\YandexMusic"),
        r"C:\Users\denbi\AppData\Local\Programs\YandexMusic",
        os.path.expandvars(r"%PROGRAMFILES%\YandexMusic"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\YandexMusic"),
    ]
    for c in candidates:
        if os.path.exists(os.path.join(c, "resources", "app.asar")):
            return os.path.abspath(c)
    return os.path.abspath(candidates[0])

def is_yandex_music_installed(app_dir=None):
    if not app_dir:
        app_dir = find_yandex_music_dir()
    asar_path = os.path.join(app_dir, "resources", "app.asar")
    return os.path.exists(asar_path) and os.path.getsize(asar_path) > 10 * 1024 * 1024

def find_local_installer():
    candidates = []
    # 1. Directory of current executable or script
    if getattr(sys, 'frozen', False):
        candidates.append(os.path.dirname(sys.executable))
    candidates.append(os.getcwd())
    candidates.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    # 2. User Downloads folder
    downloads = os.path.expanduser("~/Downloads")
    candidates.append(downloads)
    # 3. Temp directory
    candidates.append(tempfile.gettempdir())

    for folder in candidates:
        if not os.path.exists(folder):
            continue
        try:
            for f in os.listdir(folder):
                lf = f.lower()
                if lf.startswith("yandex_music") and lf.endswith(".exe"):
                    full_path = os.path.join(folder, f)
                    if os.path.isfile(full_path) and os.path.getsize(full_path) > 40 * 1024 * 1024:
                        return full_path
        except Exception:
            pass
    return None

def download_file(url, dest_path, progress_callback=None, cancel_event=None):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) YandexMusicModInstaller"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        total_size = int(resp.headers.get("content-length", 0))
        downloaded = 0
        chunk_size = 256 * 1024  # 256 KB
        with open(dest_path, "wb") as f:
            while True:
                if cancel_event and cancel_event.is_set():
                    raise InterruptedError("Загрузка отменена")
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback:
                    progress_callback(downloaded, total_size)

def install_official_yandex_music(installer_path, log_callback=print):
    log_callback(f"[+] Запуск оригинального установщика в тихом режиме: {os.path.basename(installer_path)}...")
    kill_yandex_music()
    proc = subprocess.Popen([installer_path, "/S"])
    try:
        proc.wait(timeout=60)
    except subprocess.TimeoutExpired:
        log_callback("[!] Ожидание завершения распаковки...")

    # Wait for app.asar to appear in destination
    app_dir = find_yandex_music_dir()
    asar_path = os.path.join(app_dir, "resources", "app.asar")
    for _ in range(35):
        if os.path.exists(asar_path) and os.path.getsize(asar_path) > 10 * 1024 * 1024:
            break
        time.sleep(1)

    time.sleep(2)
    kill_yandex_music()

    if not os.path.exists(asar_path):
        raise RuntimeError("Установка завершена, но архив resources/app.asar не был создан. Проверьте права доступа.")

    log_callback(f"[+] Официальная Яндекс Музыка успешно установлена в: {app_dir}")
    return app_dir

def kill_yandex_music():
    try:
        subprocess.run(["taskkill", "/F", "/IM", "Яндекс Музыка.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["taskkill", "/F", "/IM", "YandexMusic.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def copy_file_safe(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)

def patch_executable_integrity(asar_path, log_callback=print):
    app_dir = os.path.dirname(os.path.dirname(asar_path))
    exe_file = None
    for f in os.listdir(app_dir):
        if f.endswith(".exe") and not f.startswith("Uninstall"):
            exe_file = os.path.join(app_dir, f)
            break
    if not exe_file:
        log_callback("[!] Исполняемый файл для патча целостности не найден.")
        return

    exe_bak = exe_file + ".bak"
    if not os.path.exists(exe_bak):
        log_callback(f"[+] Создание резервной копии exe: {exe_bak}")
        shutil.copy2(exe_file, exe_bak)

    with open(asar_path, "rb") as f:
        u1, u2, u3, u4 = struct.unpack("<IIII", f.read(16))
        header_bytes = f.read(u4)
    new_hash = hashlib.sha256(header_bytes).hexdigest().encode("ascii")

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
        log_callback(f"[+] Хеш целостности ASAR обновлен: {new_hash.decode('ascii')[:16]}...")
        patched = True
    else:
        match = re.search(rb'("file":"resources[\\/]app\.asar","alg":"SHA256","value":")([a-f0-9]{64})(")', exe_data)
        if match:
            exe_data = exe_data[:match.start(2)] + new_hash + exe_data[match.end(2):]
            log_callback(f"[+] Хеш целостности ASAR обновлен по паттерну: {new_hash.decode('ascii')[:16]}...")
            patched = True

    fuse_magic = b'dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX\x01\x0810111101'
    fuse_magic_disabled = b'dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX\x01\x0810110101'
    if fuse_magic in exe_data:
        exe_data = exe_data.replace(fuse_magic, fuse_magic_disabled)
        log_callback("[+] Предохранитель Electron (ASAR Integrity Fuse) отключен.")
        patched = True

    if patched:
        with open(exe_file, "wb") as f:
            f.write(exe_data)
        log_callback("[+] Контрольные суммы исполняемого файла успешно применены.")

def perform_install(app_dir, log_callback=print):
    resources_dir = os.path.join(app_dir, "resources")
    asar_path = os.path.join(resources_dir, "app.asar")
    src_dir = get_src_dir()

    if not os.path.exists(asar_path):
        raise FileNotFoundError(f"Файл app.asar не найден в папке: {resources_dir}")

    log_callback("[1/6] Закрытие активных процессов Яндекс Музыки...")
    kill_yandex_music()

    backup_path = asar_path + ".bak"
    if not os.path.exists(backup_path):
        log_callback(f"[2/6] Создание бэкапа оригинального архива: app.asar.bak")
        shutil.copy2(asar_path, backup_path)
    else:
        log_callback("[2/6] Бэкап app.asar.bak уже существует.")

    staging_dir = tempfile.mkdtemp(prefix="ym_mod_staging_")
    try:
        log_callback("[3/6] Распаковка app.asar во временное хранилище...")
        extract_asar(asar_path, staging_dir)

        log_callback("[4/6] Внедрение компонентов мода (Оверлей, Караоке, Шрифты, Темы)...")
        mod_app_dir = os.path.join(staging_dir, "app", "yandexMusicMod")
        mod_preload_dir = os.path.join(staging_dir, "preload")
        app_preload_dir = os.path.join(staging_dir, "app", "preload")
        os.makedirs(mod_app_dir, exist_ok=True)
        os.makedirs(mod_preload_dir, exist_ok=True)
        os.makedirs(app_preload_dir, exist_ok=True)

        # Main
        copy_file_safe(os.path.join(src_dir, "main", "mod-main.js"), os.path.join(mod_app_dir, "main.js"))
        copy_file_safe(os.path.join(src_dir, "main", "discord-rpc.js"), os.path.join(mod_app_dir, "discord-rpc.js"))
        copy_file_safe(os.path.join(src_dir, "main", "settings.js"), os.path.join(mod_app_dir, "settings.js"))

        # Preload
        for target in [mod_preload_dir, mod_app_dir, app_preload_dir]:
            copy_file_safe(os.path.join(src_dir, "preload", "overlay-preload.js"), os.path.join(target, "overlay-preload.js"))
            copy_file_safe(os.path.join(src_dir, "preload", "karaoke-preload.js"), os.path.join(target, "karaoke-preload.js"))

        # Overlay & Karaoke
        for name in ["overlay.html", "overlay.css", "overlay.js"]:
            copy_file_safe(os.path.join(src_dir, "overlay", name), os.path.join(mod_app_dir, name))
        for name in ["karaoke.html", "karaoke.css", "karaoke.js"]:
            copy_file_safe(os.path.join(src_dir, "karaoke", name), os.path.join(mod_app_dir, name))

        # Renderer
        copy_file_safe(os.path.join(src_dir, "renderer", "mod-renderer.js"), os.path.join(mod_app_dir, "renderer.js"))
        copy_file_safe(os.path.join(src_dir, "renderer", "mod-renderer.css"), os.path.join(mod_app_dir, "renderer.css"))

        # Fonts
        fonts_dir = os.path.join(src_dir, "fonts")
        if os.path.exists(fonts_dir):
            for font_file in os.listdir(fonts_dir):
                copy_file_safe(os.path.join(fonts_dir, font_file), os.path.join(mod_app_dir, font_file))

        # Patch index.js
        index_js_path = os.path.join(staging_dir, "index.js")
        with open(index_js_path, "r", encoding="utf-8") as f:
            index_content = f.read()
        if "yandexMusicMod/main.js" not in index_content:
            injection_hook = "\n// === Injected by Yandex Music Mod ===\ntry {\n  require(\"./app/yandexMusicMod/main.js\");\n} catch (modErr) {\n  console.error(\"[YandexMusicMod Main Hook Error]\", modErr);\n}\n"
            index_content += injection_hook
            with open(index_js_path, "w", encoding="utf-8") as f:
                f.write(index_content)

        # Patch preload.js
        preload_js_path = os.path.join(staging_dir, "preload.js")
        with open(preload_js_path, "r", encoding="utf-8") as f:
            preload_content = f.read()
        with open(os.path.join(src_dir, "preload", "mod-preload.js"), "r", encoding="utf-8") as f:
            mod_preload_content = f.read()

        if "// === Yandex Music Mod Preload Integration ===" in preload_content:
            idx = preload_content.find("// === Yandex Music Mod Preload Integration ===")
            preload_content = preload_content[:idx].rstrip() + "\n\n" + mod_preload_content
            with open(preload_js_path, "w", encoding="utf-8") as f:
                f.write(preload_content)
        elif "yandexMusicMod" not in preload_content:
            preload_content += "\n\n" + mod_preload_content
            with open(preload_js_path, "w", encoding="utf-8") as f:
                f.write(preload_content)

        # Patch HTML entry points
        app_html_dir = os.path.join(staging_dir, "app")
        tag_to_inject = '<script id="ym-mod-renderer-script" src="/yandexMusicMod/renderer.js"></script><link id="ym-mod-renderer-style" rel="stylesheet" href="/yandexMusicMod/renderer.css" />'
        for root, _, files in os.walk(app_html_dir):
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

        # Patch Next.js chunk to permanently disable top ad banner
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

        # Pack ASAR
        log_callback("[5/6] Сборка оптимизированного архива app.asar...")
        new_asar_tmp = asar_path + ".tmp"
        pack_asar(staging_dir, new_asar_tmp)

        if os.path.exists(asar_path):
            os.remove(asar_path)
        os.rename(new_asar_tmp, asar_path)

        # Patch integrity
        log_callback("[6/6] Патчинг сигнатуры и Fuses в Яндекс Музыка.exe...")
        patch_executable_integrity(asar_path, log_callback)

        log_callback("✔ УСТАНОВКА МОДА УСПЕШНО ЗАВЕРШЕНА!")
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

def perform_restore(app_dir, log_callback=print):
    resources_dir = os.path.join(app_dir, "resources")
    asar_path = os.path.join(resources_dir, "app.asar")
    asar_bak = asar_path + ".bak"

    kill_yandex_music()

    if os.path.exists(asar_bak):
        if os.path.exists(asar_path):
            os.remove(asar_path)
        shutil.copy2(asar_bak, asar_path)
        log_callback("[+] app.asar восстановлен из резервной копии.")
    else:
        log_callback("[!] Бэкап app.asar.bak не найден.")

    for f in os.listdir(app_dir):
        if f.endswith(".exe") and not f.startswith("Uninstall"):
            exe_file = os.path.join(app_dir, f)
            exe_bak = exe_file + ".bak"
            if os.path.exists(exe_bak):
                shutil.copy2(exe_bak, exe_file)
                log_callback(f"[+] {f} восстановлен из оригинала.")

    log_callback("✔ ВОССТАНОВЛЕНИЕ ОРИГИНАЛА ЗАВЕРШЕНО!")

def launch_app(app_dir):
    for f in os.listdir(app_dir):
        if f.endswith(".exe") and not f.startswith("Uninstall"):
            exe_path = os.path.join(app_dir, f)
            subprocess.Popen([exe_path], cwd=app_dir)
            return True
    return False

# Modern Frosted Dark GUI with Auto-Download & All-in-One Setup
class InstallerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Яндекс Музыка Мод — Установщик «Всё-в-одном»")
        self.root.geometry("660x540")
        self.root.resizable(False, False)
        self.root.configure(bg="#0f1117")

        icon_path = os.path.join(get_base_dir(), "assets", "icon.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(find_yandex_music_dir(), "resources", "assets", "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        self.progress_var = tk.DoubleVar(value=0)
        self.status_var = tk.StringVar(value="Проверка состояния...")
        self.setup_ui()
        self.check_installation_status()

    def setup_ui(self):
        # Header frame
        header = tk.Frame(self.root, bg="#161922", height=95)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        title = tk.Label(header, text="ЯНДЕКС МУЗЫКА МОД", font=("Segoe UI", 16, "bold"), fg="#ffffff", bg="#161922")
        title.pack(anchor="w", padx=24, pady=(16, 2))

        sub = tk.Label(header, text="Установка в 1 клик • Автоскачивание • Игровой HUD • Караоке • Discord RPC • Шрифты",
                       font=("Segoe UI", 9), fg="#94a3b8", bg="#161922")
        sub.pack(anchor="w", padx=24)

        # Body container
        body = tk.Frame(self.root, bg="#0f1117")
        body.pack(fill=tk.BOTH, expand=True, padx=24, pady=16)

        # Path selector
        path_label = tk.Label(body, text="Папка с Яндекс Музыкой:", font=("Segoe UI", 9, "bold"),
                              fg="#cbd5e1", bg="#0f1117")
        path_label.pack(anchor="w", pady=(0, 4))

        path_row = tk.Frame(body, bg="#0f1117")
        path_row.pack(fill=tk.X, pady=(0, 8))

        self.path_var = tk.StringVar(value=find_yandex_music_dir())
        self.path_entry = tk.Entry(path_row, textvariable=self.path_var, font=("Consolas", 9), bg="#1e2230",
                                   fg="#f1f5f9", insertbackground="#fff", relief=tk.FLAT, bd=6)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        browse_btn = tk.Button(path_row, text="Обзор...", font=("Segoe UI", 9), bg="#334155", fg="#ffffff",
                               activebackground="#475569", activeforeground="#ffffff", relief=tk.FLAT,
                               cursor="hand2", padx=12, command=self.on_browse)
        browse_btn.pack(side=tk.RIGHT, padx=(8, 0))

        # Status Label (dynamic detection)
        self.status_label = tk.Label(body, textvariable=self.status_var, font=("Segoe UI", 9, "bold"),
                                     fg="#38bdf8", bg="#0f1117")
        self.status_label.pack(anchor="w", pady=(0, 6))

        # Progress bar
        style = ttk.Style()
        style.theme_use('default')
        style.configure("Custom.Horizontal.TProgressbar", background="#8b5cf6", troughcolor="#1e2230", bordercolor="#0f1117", lightcolor="#8b5cf6", darkcolor="#8b5cf6")
        self.progress_bar = ttk.Progressbar(body, style="Custom.Horizontal.TProgressbar", variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))

        # Log console
        log_label = tk.Label(body, text="Журнал установки:", font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg="#0f1117")
        log_label.pack(anchor="w", pady=(0, 4))

        self.log_text = tk.Text(body, height=9, bg="#131620", fg="#38bdf8", insertbackground="#fff",
                                font=("Consolas", 8), relief=tk.FLAT, bd=8, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        # Button row
        btn_row = tk.Frame(body, bg="#0f1117")
        btn_row.pack(fill=tk.X)

        self.install_btn = tk.Button(btn_row, text="▶ Установить мод и запустить", font=("Segoe UI", 11, "bold"),
                                     bg="#8b5cf6", fg="#ffffff", activebackground="#7c3aed", activeforeground="#ffffff",
                                     relief=tk.FLAT, cursor="hand2", pady=8, command=self.start_install)
        self.install_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        self.restore_btn = tk.Button(btn_row, text="Оригинал (Откат)", font=("Segoe UI", 9),
                                     bg="#2d3748", fg="#cbd5e1", activebackground="#374151", activeforeground="#ffffff",
                                     relief=tk.FLAT, cursor="hand2", pady=8, padx=14, command=self.start_restore)
        self.restore_btn.pack(side=tk.RIGHT)

    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def on_browse(self):
        folder = filedialog.askdirectory(initialdir=self.path_var.get(), title="Выберите папку с Яндекс Музыкой")
        if folder:
            self.path_var.set(folder)
            self.check_installation_status()

    def check_installation_status(self):
        app_dir = self.path_var.get().strip()
        if is_yandex_music_installed(app_dir):
            self.status_var.set("✔ Найдена установленная Яндекс Музыка (готов к внедрению мода)")
            self.status_label.config(fg="#4ade80")
            self.install_btn.config(text="▶ Установить мод и запустить")
        else:
            local = find_local_installer()
            if local:
                self.status_var.set(f"ℹ Найден локальный инсталлятор в Загрузках: {os.path.basename(local)}")
                self.status_label.config(fg="#38bdf8")
                self.install_btn.config(text="⬇ Установить Яндекс Музыку с модом в 1 клик")
            else:
                self.status_var.set("ℹ Яндекс Музыка не найдена — будет скачана и установлена официальная версия")
                self.status_label.config(fg="#38bdf8")
                self.install_btn.config(text="⬇ Скачать Яндекс Музыку и установить с модом")

    def set_buttons_state(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.install_btn.config(state=state)
        self.restore_btn.config(state=state)

    def start_install(self):
        app_dir = self.path_var.get().strip()
        self.set_buttons_state(False)
        self.progress_var.set(0)
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)

        def worker():
            try:
                # 1. Check if Yandex Music is installed
                if not is_yandex_music_installed(app_dir):
                    self.log("[*] Яндекс Музыка не обнаружена в указанной папке.")
                    local_installer = find_local_installer()
                    installer_path = local_installer

                    if installer_path:
                        self.log(f"[+] Найден готовый установщик: {installer_path}")
                        self.progress_var.set(20)
                    else:
                        self.log("[+] Скачивание чистого официального дистрибутива Яндекс Музыки (5.124.1)...")
                        temp_installer = os.path.join(tempfile.gettempdir(), "Yandex_Music_x64_5.124.1.exe")

                        last_reported = [0]
                        def on_progress(downloaded, total):
                            if total > 0:
                                pct = (downloaded / total) * 100
                                self.progress_var.set(pct * 0.4)
                                mb_done = downloaded / (1024 * 1024)
                                mb_total = total / (1024 * 1024)
                                if int(pct) >= last_reported[0] + 10:
                                    last_reported[0] = int(pct)
                                    self.root.after(0, lambda: self.log(f"   Загрузка: {mb_done:.1f} МБ из {mb_total:.1f} МБ ({int(pct)}%)..."))

                        try:
                            download_file(OFFICIAL_DOWNLOAD_URL, temp_installer, on_progress)
                        except Exception as dl_err:
                            self.log(f"[!] Ошибка основного сервера ({dl_err}), скачиваем из резервного зеркала...")
                            download_file(FALLBACK_DOWNLOAD_URL, temp_installer, on_progress)

                        installer_path = temp_installer
                        self.log("[+] Загрузка официального дистрибутива завершена.")

                    self.progress_var.set(45)
                    self.log("[+] Установка официальной Яндекс Музыки...")
                    installed_dir = install_official_yandex_music(installer_path, self.log)
                    app_dir = installed_dir
                    self.root.after(0, lambda: self.path_var.set(app_dir))
                    self.progress_var.set(65)

                # 2. Perform mod injection
                self.progress_var.set(70)
                perform_install(app_dir, self.log)
                self.progress_var.set(95)

                self.log("[+] Запуск Яндекс Музыки с модом...")
                launch_app(app_dir)
                self.progress_var.set(100)
                self.root.after(0, self.check_installation_status)
                messagebox.showinfo("Успех", "Яндекс Музыка успешно установлена и пропатчена модом!\nПриятного прослушивания!")
            except Exception as e:
                self.log(f"[!] Ошибка: {e}")
                messagebox.showerror("Ошибка", f"Произошла ошибка при установке:\n{e}")
            finally:
                self.set_buttons_state(True)
                self.root.after(0, self.check_installation_status)

        threading.Thread(target=worker, daemon=True).start()

    def start_restore(self):
        app_dir = self.path_var.get().strip()
        if not os.path.exists(app_dir):
            messagebox.showerror("Ошибка", f"Папка {app_dir} не найдена!")
            return

        if not messagebox.askyesno("Подтверждение", "Вы уверены, что хотите вернуть чистую оригинальную версию без модов?"):
            return

        self.set_buttons_state(False)
        def worker():
            try:
                perform_restore(app_dir, self.log)
                messagebox.showinfo("Успех", "Оригинальная версия Яндекс Музыки успешно восстановлена.")
            except Exception as e:
                self.log(f"[!] Ошибка восстановления: {e}")
                messagebox.showerror("Ошибка", f"Произошла ошибка при восстановлении:\n{e}")
            finally:
                self.set_buttons_state(True)

        threading.Thread(target=worker, daemon=True).start()

def main():
    if "--silent" in sys.argv or "--cli" in sys.argv:
        app_dir = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("-") else find_yandex_music_dir()
        if not is_yandex_music_installed(app_dir) and "--restore" not in sys.argv:
            local = find_local_installer()
            if not local:
                temp_inst = os.path.join(tempfile.gettempdir(), "Yandex_Music_x64_5.124.1.exe")
                download_file(OFFICIAL_DOWNLOAD_URL, temp_inst)
                local = temp_inst
            app_dir = install_official_yandex_music(local, print)

        if "--restore" in sys.argv:
            perform_restore(app_dir, print)
        else:
            perform_install(app_dir, print)
            if "--launch" in sys.argv:
                launch_app(app_dir)
        return

    root = tk.Tk()
    app = InstallerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
