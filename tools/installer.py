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
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from asar_tool import extract_asar, pack_asar

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

# Modern Frosted Dark GUI
class InstallerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Яндекс Музыка Мод — Установщик & Лаунчер")
        self.root.geometry("640x510")
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

        self.setup_ui()

    def setup_ui(self):
        # Header frame
        header = tk.Frame(self.root, bg="#161922", height=95)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        title = tk.Label(header, text="ЯНДЕКС МУЗЫКА МОД", font=("Segoe UI", 16, "bold"), fg="#ffffff", bg="#161922")
        title.pack(anchor="w", padx=24, pady=(16, 2))

        sub = tk.Label(header, text="Игровой HUD-оверлей • Караоке • Discord RPC • Кастомные шрифты • Темное стекло",
                       font=("Segoe UI", 9), fg="#94a3b8", bg="#161922")
        sub.pack(anchor="w", padx=24)

        # Body container
        body = tk.Frame(self.root, bg="#0f1117")
        body.pack(fill=tk.BOTH, expand=True, padx=24, pady=18)

        # Path selector
        path_label = tk.Label(body, text="Папка с установленной Яндекс Музыкой:", font=("Segoe UI", 9, "bold"),
                              fg="#cbd5e1", bg="#0f1117")
        path_label.pack(anchor="w", pady=(0, 4))

        path_row = tk.Frame(body, bg="#0f1117")
        path_row.pack(fill=tk.X, pady=(0, 14))

        self.path_var = tk.StringVar(value=find_yandex_music_dir())
        self.path_entry = tk.Entry(path_row, textvariable=self.path_var, font=("Consolas", 9), bg="#1e2230",
                                   fg="#f1f5f9", insertbackground="#fff", relief=tk.FLAT, bd=6)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)

        browse_btn = tk.Button(path_row, text="Обзор...", font=("Segoe UI", 9), bg="#334155", fg="#ffffff",
                               activebackground="#475569", activeforeground="#ffffff", relief=tk.FLAT,
                               cursor="hand2", padx=12, command=self.on_browse)
        browse_btn.pack(side=tk.RIGHT, padx=(8, 0))

        # Log console
        log_label = tk.Label(body, text="Журнал установки:", font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg="#0f1117")
        log_label.pack(anchor="w", pady=(0, 4))

        self.log_text = tk.Text(body, height=10, bg="#131620", fg="#38bdf8", insertbackground="#fff",
                                font=("Consolas", 8), relief=tk.FLAT, bd=8, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(0, 14))

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

        self.log("Готов к установке. Нажмите «Установить мод и запустить».")

    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def on_browse(self):
        folder = filedialog.askdirectory(initialdir=self.path_var.get(), title="Выберите папку с Яндекс Музыкой")
        if folder:
            self.path_var.set(folder)

    def set_buttons_state(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.install_btn.config(state=state)
        self.restore_btn.config(state=state)

    def start_install(self):
        app_dir = self.path_var.get().strip()
        if not os.path.exists(os.path.join(app_dir, "resources", "app.asar")):
            messagebox.showerror("Ошибка", f"В папке {app_dir} не найден файл resources/app.asar!\nПожалуйста, укажите правильную папку с установленной Яндекс Музыкой.")
            return

        self.set_buttons_state(False)
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)

        def worker():
            try:
                perform_install(app_dir, self.log)
                self.log("[+] Запуск обновленной Яндекс Музыки...")
                launch_app(app_dir)
                messagebox.showinfo("Успех", "Мод успешно установлен!\nЯндекс Музыка запущена.")
            except Exception as e:
                self.log(f"[!] Ошибка установки: {e}")
                messagebox.showerror("Ошибка", f"Произошла ошибка при установке мода:\n{e}")
            finally:
                self.set_buttons_state(True)

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
