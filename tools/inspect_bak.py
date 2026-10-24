import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from asar_tool import extract_asar
import tempfile

bak_path = r"C:\Users\denbi\AppData\Local\Programs\YandexMusic\resources\app.asar.bak"
tmp = tempfile.mkdtemp()
extract_asar(bak_path, tmp)
with open(os.path.join(tmp, "preload.js"), "r", encoding="utf-8") as f:
    print(f.read())
