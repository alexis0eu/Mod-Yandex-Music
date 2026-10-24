import os
import re

css_path = r"src\renderer\mod-renderer.css"
with open(css_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "display: none" in line or "display:none" in line:
        start = max(0, i - 15)
        end = min(len(lines), i + 2)
        print(f"--- display: none at line {i+1} ---")
        print("".join(lines[start:end]))
