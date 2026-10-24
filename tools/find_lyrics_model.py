import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from asar_tool import extract_asar
import tempfile
import re

bak_path = r"C:\Users\denbi\AppData\Local\Programs\YandexMusic\resources\app.asar.bak"
tmp = tempfile.mkdtemp()
extract_asar(bak_path, tmp)

fp = os.path.join(tmp, "app", "_next", "static", "chunks", "2615.efbdca4fbec62c0b.js")
with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
    c = fh.read()

idx = c.find("getFullDescriptionTrack")
if idx != -1:
    print(c[max(0, idx - 200):idx + 1200])
