import os, json, struct, re

asar_path = r"C:\Users\denbi\AppData\Local\Programs\YandexMusic\resources\app.asar.bak"
with open(asar_path, "rb") as f:
    u1, u2, u3, u4 = struct.unpack("<IIII", f.read(16))
    header = json.loads(f.read(u4).decode("utf-8"))
    base_offset = 8 + u2

    def find_file(node, cur=""):
        for k, v in node.get("files", {}).items():
            p = cur + "/" + k
            if "files" in v:
                res = find_file(v, p)
                if res: return res
            elif "7229" in p:
                return (p, int(v["offset"]), int(v["size"]))
        return None

    p, off, size = find_file(header)
    f.seek(base_offset + off)
    data = f.read(size).decode("utf-8", errors="replace")

    idx = data.find("VIBE_PLAYERBAR")
    while idx != -1:
        print("=== AT", idx, "===")
        print(data[max(0, idx-100):min(len(data), idx+300)])
        print()
        idx = data.find("VIBE_PLAYERBAR", idx + 1)
