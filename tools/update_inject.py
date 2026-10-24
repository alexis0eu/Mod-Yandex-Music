with open(r'd:\Яндекс Музыка мод\tools\inject.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Replace preload patching logic to always update
old_preload_patch = '''        if "yandexMusicMod" not in preload_content:
            with open(os.path.join(SRC_DIR, "preload", "mod-preload.js"), "r", encoding="utf-8") as f:
                mod_preload_content = f.read()
            preload_content += "\\n\\n" + mod_preload_content
            with open(preload_js_path, "w", encoding="utf-8") as f:
                f.write(preload_content)
            print("[+] preload.js patched with contextBridge exposure.")
        else:
            print("[i] preload.js already has mod contextBridge.")'''

new_preload_patch = '''        with open(os.path.join(SRC_DIR, "preload", "mod-preload.js"), "r", encoding="utf-8") as f:
            mod_preload_content = f.read()

        if "// === Yandex Music Mod Preload Integration ===" in preload_content:
            idx = preload_content.find("// === Yandex Music Mod Preload Integration ===")
            preload_content = preload_content[:idx].rstrip() + "\\n\\n" + mod_preload_content
            with open(preload_js_path, "w", encoding="utf-8") as f:
                f.write(preload_content)
            print("[+] preload.js updated with latest mod contextBridge.")
        elif "yandexMusicMod" not in preload_content:
            preload_content += "\\n\\n" + mod_preload_content
            with open(preload_js_path, "w", encoding="utf-8") as f:
                f.write(preload_content)
            print("[+] preload.js patched with contextBridge exposure.")
        else:
            print("[i] preload.js already has mod contextBridge.")'''

c = c.replace(old_preload_patch, new_preload_patch)

with open(r'd:\Яндекс Музыка мод\tools\inject.py', 'w', encoding='utf-8') as f:
    f.write(c)

print("Updated inject.py preload patching logic")
