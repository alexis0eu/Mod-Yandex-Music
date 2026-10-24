import os, json, struct, re

asar_path = r"C:\Users\denbi\AppData\Local\Programs\YandexMusic\resources\app.asar.bak"
with open(asar_path, "rb") as f:
    u1, u2, u3, u4 = struct.unpack("<IIII", f.read(16))
    header = json.loads(f.read(u4).decode("utf-8"))
    base_offset = 8 + u2

    def search_all(node, cur=""):
        results = []
        for k, v in node.get("files", {}).items():
            p = cur + "/" + k
            if "files" in v:
                results.extend(search_all(v, p))
            elif p.endswith(".js"):
                results.append((p, int(v["offset"]), int(v["size"])))
        return results

    files = search_all(header)
    for p, off, size in files:
        f.seek(base_offset + off)
        data = f.read(size).decode("utf-8", errors="replace")
        if "VIBE_PLAYERBAR" in data:
            print("Found in", p)
            idx = data.find("VIBE_PLAYERBAR")
            while idx != -1:
                print("  -->", data[max(0, idx-80):min(len(data), idx+200)])
                idx = data.find("VIBE_PLAYERBAR", idx + 1)
