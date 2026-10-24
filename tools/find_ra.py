import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from asar_tool import extract_asar
import tempfile
import re

bak_path = r"C:\Users\denbi\AppData\Local\Programs\YandexMusic\resources\app.asar.bak"
tmp = tempfile.mkdtemp()
extract_asar(bak_path, tmp)

fpath = os.path.join(tmp, "app", "_next", "static", "chunks", "7229-0859a9424ac614b6.js")
with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
    c = fh.read()

idx = c.find("let ra=")
if idx != -1:
    print(c[idx:idx+1500])
