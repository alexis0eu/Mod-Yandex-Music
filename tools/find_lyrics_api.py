import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from asar_tool import extract_asar
import tempfile
import re

bak_path = r"C:\Users\denbi\AppData\Local\Programs\YandexMusic\resources\app.asar.bak"
tmp = tempfile.mkdtemp()
extract_asar(bak_path, tmp)

chunks_dir = os.path.join(tmp, "app", "_next", "static", "chunks")
for root, _, files in os.walk(chunks_dir):
    for f in files:
        if f.endswith(".js"):
            fp = os.path.join(root, f)
            with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                c = fh.read()
                if "/supplement" in c or "syncLyrics" in c:
                    print(f"File {f}:")
                    for m in re.finditer(r".{0,100}(?:/supplement|syncLyrics|lyrics).{0,100}", c):
                        print("  snippet:", m.group(0))
                        break
