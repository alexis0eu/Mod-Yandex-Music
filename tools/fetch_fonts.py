import urllib.request
import re
import os

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def download_font(family_name, out_filename):
    query = family_name.replace(" ", "+")
    url = f"https://fonts.googleapis.com/css2?family={query}&display=swap"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            css = resp.read().decode('utf-8')
        m = re.findall(r'url\((https://[^\)]+\.woff2)\)', css)
        if m:
            woff2_url = m[-1]
            req2 = urllib.request.Request(woff2_url, headers=headers)
            with urllib.request.urlopen(req2, timeout=10) as f_resp:
                data = f_resp.read()
            out_path = os.path.join('src', 'fonts', out_filename)
            with open(out_path, 'wb') as fp:
                fp.write(data)
            print(f"Successfully downloaded {family_name} ({len(data)} bytes) to {out_path}")
        else:
            print(f"No woff2 found for {family_name}")
    except Exception as e:
        print(f"Failed to download {family_name}:", e)

def download_direct_font(url_candidates, out_filename):
    for url in url_candidates:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as f_resp:
                data = f_resp.read()
            if len(data) > 0 and data[:4] == b'wOF2':
                out_path = os.path.join('src', 'fonts', out_filename)
                with open(out_path, 'wb') as fp:
                    fp.write(data)
                print(f"Successfully downloaded {out_filename} ({len(data)} bytes) from {url}")
                return True
        except Exception as e:
            print(f"Attempt failed for {url}: {e}")
    print(f"Failed to download {out_filename} from all candidates")
    return False

if __name__ == "__main__":
    download_font("Press Start 2P", "PressStart2P.woff2")
    download_font("VT323", "VT323.woff2")
    download_font("Rubik Glitch", "RubikGlitch.woff2")
    download_font("Silkscreen", "Silkscreen.woff2")
    download_direct_font([
        "https://cdn.jsdelivr.net/gh/kaspernordkvist/uncut_sans@main/Webfonts/UncutSans-Regular.woff2",
        "https://raw.githubusercontent.com/kaspernordkvist/uncut_sans/main/Webfonts/UncutSans-Regular.woff2"
    ], "UncutSans-Regular.woff2")
