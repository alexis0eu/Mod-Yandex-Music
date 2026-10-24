import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from asar_tool import extract_asar
import tempfile
import re

bak_path = r"C:\Users\denbi\AppData\Local\Programs\YandexMusic\resources\app.asar.bak"
tmp = tempfile.mkdtemp()
extract_asar(bak_path, tmp)

for root, _, files in os.walk(tmp):
    for fn in files:
        if fn.endswith((".js", ".css", ".html")):
            fp = os.path.join(root, fn)
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    if "SplashScreen" in content:
                        print(f"Match SplashScreen in: {os.path.relpath(fp, tmp)}")
                        for m in re.finditer(r"SplashScreen[^\"\';,\s\(\)]*", content):
                            print("   token:", m.group(0))
            except Exception as e:
                pass
