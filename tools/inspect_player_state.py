import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from asar_tool import extract_asar
import tempfile
import re

bak_path = r"C:\Users\denbi\AppData\Local\Programs\YandexMusic\resources\app.asar.bak"
tmp = tempfile.mkdtemp()
extract_asar(bak_path, tmp)
with open(os.path.join(tmp, "index.js"), "r", encoding="utf-8") as f:
    c = f.read()

for m in re.finditer(r"PLAYER_STATE", c):
    start = max(0, m.start() - 100)
    end = min(len(c), m.end() + 400)
    print("--- FOUND PLAYER_STATE ---")
    print(c[start:end])
