import os

# 1. Fix src/main/mod-main.js: add appFolder definition
MAIN_JS = r"src\main\mod-main.js"
with open(MAIN_JS, "r", encoding="utf-8") as f:
    main_code = f.read()

if "const appFolder =" not in main_code:
    main_code = main_code.replace(
        'const { SettingsManager } = require("./settings");',
        'const { SettingsManager } = require("./settings");\nconst appFolder = app ? app.getPath("userData") : path.join(process.env.APPDATA || "", "YandexMusic");'
    )
    with open(MAIN_JS, "w", encoding="utf-8") as f:
        f.write(main_code)
    print("[+] Fixed appFolder definition in mod-main.js")
else:
    print("[i] appFolder already defined in mod-main.js")

# 2. Fix src/renderer/mod-renderer.js: remove res.headers in new Response
RENDERER_JS = r"src\renderer\mod-renderer.js"
with open(RENDERER_JS, "r", encoding="utf-8") as f:
    r_code = f.read()

# Replace headers: res.headers with clean json headers
old_headers = "headers: res.headers,"
new_headers = 'headers: { "Content-Type": "application/json" },'

count = r_code.count(old_headers)
if count > 0:
    r_code = r_code.replace(old_headers, new_headers)
    print(f"[+] Replaced {count} instances of 'headers: res.headers' in mod-renderer.js")
else:
    print("[i] No 'headers: res.headers' found")

# Replace Stephanzion-style /account/about to only modify hasPlus without touching permissions
old_account_block = """          data.hasPlus = true;
          if (data.result) {
            data.result.hasPlus = true;
            if (data.result.plus) {
              data.result.plus.hasPlus = true;
              data.result.plus.isAvailable = true;
            } else {
              data.result.plus = { hasPlus: true, isAvailable: true };
            }
            if (data.result.permissions) {
              data.result.permissions.default = ["landing-play", "feed-play", "radio-play", "mix-play"];
              data.result.permissions.values = ["landing-play", "feed-play", "radio-play", "mix-play"];
            }
          }
          if (data.plus) {
            data.plus.hasPlus = true;
            data.plus.isAvailable = true;
          } else {
            data.plus = { hasPlus: true, isAvailable: true };
          }"""

new_account_block = """          data.hasPlus = true;
          if (data.result) {
            data.result.hasPlus = true;
          }"""

if old_account_block in r_code:
    r_code = r_code.replace(old_account_block, new_account_block)
    print("[+] Cleaned account about block to match Stephanzion spec")

with open(RENDERER_JS, "w", encoding="utf-8") as f:
    f.write(r_code)

print("[+] Updated mod-renderer.js")
