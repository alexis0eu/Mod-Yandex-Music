import ctypes
import os
import struct
import psutil

def patch_exe_icon(exe_path, ico_path):
    print(f"[+] Patching {exe_path} with icon {ico_path}...")
    with open(ico_path, "rb") as f:
        ico_data = f.read()

    idReserved, idType, idCount = struct.unpack_from("<HHH", ico_data, 0)
    if idType != 1:
        raise ValueError("Not a valid ICO file")

    print(f"    ICO contains {idCount} image frames")

    grp_entries = []
    icon_images = []

    offset = 6
    for i in range(idCount):
        bWidth, bHeight, bColorCount, bReserved, wPlanes, wBitCount, dwBytesInRes, dwImageOffset = struct.unpack_from("<BBBBHHII", ico_data, offset)
        offset += 16

        icon_id = i + 1
        img_bytes = ico_data[dwImageOffset : dwImageOffset + dwBytesInRes]
        icon_images.append((icon_id, img_bytes))

        # GRPICONDIRENTRY (14 bytes)
        grp_entry = struct.pack("<BBBBHHIH", bWidth, bHeight, bColorCount, bReserved, wPlanes, wBitCount, dwBytesInRes, icon_id)
        grp_entries.append(grp_entry)

    grp_header = struct.pack("<HHH", idReserved, idType, idCount) + b"".join(grp_entries)

    kernel32 = ctypes.windll.kernel32
    kernel32.BeginUpdateResourceW.restype = ctypes.c_void_p
    kernel32.BeginUpdateResourceW.argtypes = [ctypes.c_wchar_p, ctypes.c_bool]
    
    kernel32.UpdateResourceW.restype = ctypes.c_bool
    kernel32.UpdateResourceW.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ushort, ctypes.c_char_p, ctypes.c_uint]

    kernel32.EndUpdateResourceW.restype = ctypes.c_bool
    kernel32.EndUpdateResourceW.argtypes = [ctypes.c_void_p, ctypes.c_bool]

    hUpdate = kernel32.BeginUpdateResourceW(exe_path, False)
    if not hUpdate:
        err = kernel32.GetLastError()
        raise RuntimeError(f"BeginUpdateResourceW failed with error code {err}")

    # RT_ICON = 3, RT_GROUP_ICON = 14
    RT_ICON = 3
    RT_GROUP_ICON = 14
    LANG_NEUTRAL = 0

    for icon_id, img_bytes in icon_images:
        res = kernel32.UpdateResourceW(hUpdate, RT_ICON, icon_id, LANG_NEUTRAL, img_bytes, len(img_bytes))
        if not res:
            print(f"[!] Warning updating RT_ICON {icon_id}: err {kernel32.GetLastError()}")

    res = kernel32.UpdateResourceW(hUpdate, RT_GROUP_ICON, 1, LANG_NEUTRAL, grp_header, len(grp_header))
    if not res:
        print(f"[!] Warning updating RT_GROUP_ICON: err {kernel32.GetLastError()}")

    success = kernel32.EndUpdateResourceW(hUpdate, False)
    if not success:
        err = kernel32.GetLastError()
        raise RuntimeError(f"EndUpdateResourceW failed with error code {err}")

    print(f"[+] Successfully patched PE icon resources in {exe_path}!")

if __name__ == "__main__":
    app_dir = os.path.expandvars(r'%LOCALAPPDATA%\Programs\YandexMusic')
    exe_path = os.path.join(app_dir, 'Яндекс Музыка.exe')
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ico_path = os.path.join(repo_root, 'assets', 'icon.ico')

    for p in psutil.process_iter(['name']):
        try:
            if 'яндекс' in p.info['name'].lower() or 'yandex' in p.info['name'].lower():
                p.kill()
        except:
            pass

    patch_exe_icon(exe_path, ico_path)
