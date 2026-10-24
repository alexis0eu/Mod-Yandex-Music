import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from asar_tool import extract_asar
import tempfile
import re

bak_path = r"C:\Users\denbi\AppData\Local\Programs\YandexMusic\resources\app.asar.bak"
tmp = tempfile.mkdtemp()
extract_asar(bak_path, tmp)

css_dir = os.path.join(tmp, "app", "_next", "static", "css")
for f in os.listdir(css_dir):
    if f.endswith(".css"):
        fp = os.path.join(css_dir, f)
        with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
            content = fh.read()
            if "WithTopBanner" in content or "DefaultLayout" in content or "SplashScreen" in content:
                print(f"File {f}:")
                for match in re.finditer(r"([^{}]*(?:WithTopBanner|DefaultLayout|SplashScreen)[^{}]*\{[^}]+\})", content):
                    print("  RULE:", match.group(1).strip())
