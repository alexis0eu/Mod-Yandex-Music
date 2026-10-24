import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from asar_tool import extract_asar
import tempfile

bak_path = r"C:\Users\denbi\AppData\Local\Programs\YandexMusic\resources\app.asar.bak"
tmp = tempfile.mkdtemp()
extract_asar(bak_path, tmp)
css_dir = os.path.join(tmp, "app", "_next", "static", "css")
if os.path.exists(css_dir):
    for f in os.listdir(css_dir):
        if f.endswith(".css"):
            fp = os.path.join(css_dir, f)
            print(f"CSS File: {f}, size: {os.path.getsize(fp)}")
