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

for m in re.finditer(r"78401", c):
    start = max(0, m.start() - 200)
    end = min(len(c), m.end() + 800)
    print("--- USAGE OF 78401 ---")
    print(c[start:end])
