import os
import sys
import time
import subprocess
import psutil

app_dir = r"C:\Users\denbi\AppData\Local\Programs\YandexMusic"
exe_name = [f for f in os.listdir(app_dir) if f.endswith(".exe") and not f.startswith("Uninstall")][0]
exe_path = os.path.join(app_dir, exe_name)

# Kill any existing instances first
for p in psutil.process_iter(['pid', 'name']):
    try:
        n = p.info['name']
        if n and ('yandex' in n.lower() or 'музык' in n.lower()):
            p.kill()
    except Exception:
        pass

# Fix line 458 in src/renderer/mod-renderer.js FIRST!
renderer_file = r"src\renderer\mod-renderer.js"
with open(renderer_file, "r", encoding="utf-8") as f:
    r_code = f.read()

bad_banner = 'div[class*="Banner"]'
if bad_banner in r_code:
    # Replace with specific top banner element and exclude WithTopBanner_root and WithTopBanner_content
    r_code = r_code.replace(
        'div[class*="Banner"], div[data-test-id="NAVBAR_NAVIGATION_ITEM_PLUS"]',
        'div[class*="WithTopBanner_banner_"], div[class*="PromoBanner_"], div[class*="PaywallBanner_"], div[class*="SubscriptionBanner_"], div[data-test-id="NAVBAR_NAVIGATION_ITEM_PLUS"]'
    )
    with open(renderer_file, "w", encoding="utf-8") as f:
        f.write(r_code)
    print("FIXED bad div[class*=\"Banner\"] in mod-renderer.js!")

