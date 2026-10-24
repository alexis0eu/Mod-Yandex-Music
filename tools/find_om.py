import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from asar_tool import extract_asar
import tempfile

bak_path = r"C:\Users\denbi\AppData\Local\Programs\YandexMusic\resources\app.asar.bak"
tmp = tempfile.mkdtemp()
extract_asar(bak_path, tmp)

fp = os.path.join(tmp, "app", "_next", "static", "chunks", "5740-a61b25dab5977432.js")
with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
    c = fh.read()

idx = c.find("downloadSyncLyrics")
if idx != -1:
    print(c[max(0, idx - 400):idx + 800])
